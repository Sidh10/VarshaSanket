"""Monsoon-trough position extractor over IMD Extended Range bulletins.

WHAT IMD GIVES US, AND WHAT IS OURS
-----------------------------------
IMD publishes a definition of Break Monsoon in its own glossary
(imdpune.gov.in/Reports/glossary.pdf), verbatim:

    "Break Monsoon -- Monsoon trough shifts northwards and runs close to foot
     hills of Himalayas, resulting in drastic reduction in rainfall over the
     country outside the foot hills and southernmost Peninsula"

So the *mechanism* -- trough north toward the Himalayan foothills implies
suppressed rainfall over the core zone -- is IMD's, published, and citable. That
is a real improvement over inventing the physics ourselves (D-15 addendum 3).

**But IMD does not hand us a regime label, and this module does not pretend
otherwise.** Three things here are OURS to defend, not IMD's:

  1. IMD never applies the word "break" to these bulletins. Across 96 JJAS
     bulletins the word appears once (D-15 addendum 1). There is no label in the
     source text; we are deriving one.
  2. The THRESHOLD is ours. IMD's definition says "shifts northwards and runs
     close to foot hills" without specifying how far north, for how long, or how
     to treat a trough that is north for half a week. Every such choice below is
     an authored modelling decision.
  3. The MAPPING from a categorical position to a break-favourable signal is
     ours. `break_favourable()` encodes it explicitly so it can be challenged
     rather than being buried in a scoring function.

If a reviewer asks "is this IMD's classification?", the answer is **no** -- it is
our classification built on IMD's published mechanism. Say that plainly.

COVERAGE
--------
D-15 addendum 1 measured the ceiling: only 62% of bulletins (60/96) carry a
trough *forecast* with an explicit position. This module does not attempt to
raise that number by loosening the patterns; a looser matcher would trade a
measured limitation for an unmeasured error rate. Sections with no explicit
position return NOT_STATED and are excluded downstream, not imputed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

# --- position categories -----------------------------------------------------
NORTH = "north"           # north of normal -- break-favourable per IMD's definition
FOOTHILLS = "foothills"   # explicitly at the Himalayan foothills -- IMD's own break wording
SOUTH = "south"           # south of normal -- active-favourable
NEAR_NORMAL = "near_normal"
MIXED = "mixed"           # genuinely ambiguous: two directions in one statement
NOT_STATED = "not_stated"

POSITIONS = [NORTH, FOOTHILLS, SOUTH, NEAR_NORMAL, MIXED, NOT_STATED]

_BULLET = re.compile(r"[•●▪]|➢|❖|✓|♦|•|➤|▪")

# Week-1 / Week-2 section headings, covering the 2021-2026 wording variants.
_HEAD = re.compile(
    r"(?:(?:Rainfall|Precipitation)\s*(?:Forecast)?\s*(?:for|of|during)\s*(?:the\s*)?[Ww]eek\s*[-–]?\s*([12])"
    r"|Weather\s+systems[^.]{0,60}?(?:Precipitation\s+)?during\s+Week\s*[-–]?\s*([12])"
    r"|^\s*[a-d]\)\s*Week\s*[-–]?\s*([12])\b)",
    re.I | re.M,
)
_TEMP_HEAD = re.compile(r"Temperature\s+forecast\s+for\s+Week", re.I)

_TROUGH = re.compile(r"\btrough\b", re.I)
_NORTH = re.compile(r"north\s+of\s+(?:its\s+)?normal|lies?\s+to\s+the\s+north|north\s+of\s+normal", re.I)
_SOUTH = re.compile(r"south\s+of\s+(?:its\s+)?(?:normal|position)|lies?\s+to\s+the\s+south|south\s+of\s+normal|southwards", re.I)
_NEAR = re.compile(r"near\s+(?:its\s+)?normal|around\s+its\s+normal|oscillate\s+(?:around|near)|at\s+its\s+normal", re.I)
_FOOT = re.compile(r"foot\s*hills?\s+of\s+(?:the\s+)?himalaya|along\s+the\s+foot\s*hills", re.I)
# Forecast modality vs a present-tense description of the current state.
_FORECAST = re.compile(r"\blikely\b|\bexpected\b|\bwill\b|\bwould\b|\bvery\s+likely\b", re.I)


@dataclass(frozen=True)
class TroughStatement:
    date: pd.Timestamp
    week: int                 # 1 or 2
    position: str             # one of POSITIONS
    is_forecast: bool         # modality: forecast vs present-tense description
    sentence: str


def _sections(text: str) -> list[tuple[int, str]]:
    """Split a bulletin into (week_number, section_text). Temperature blocks are
    cut off -- they are a different variable and share the 'Week N' heading."""
    ms = list(_HEAD.finditer(text))
    out: dict[int, str] = {}
    for i, m in enumerate(ms):
        wk = int(next(g for g in m.groups() if g))
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        body = text[m.end() : end]
        tm = _TEMP_HEAD.search(body)
        if tm:
            body = body[: tm.start()]
        out.setdefault(wk, body[:2500])
    return sorted(out.items())


def classify_position(sentence: str) -> str:
    """Classify one trough sentence.

    MIXED is returned whenever two different directions appear in the same
    statement. That is not a parser failure -- IMD genuinely writes compound
    positions, and they are irreducible without inventing a rule IMD does not
    state. Real examples from the corpus:

        "north of its normal or near normal position"
        "near normal / south of its position"
        "The western end ... is north of its normal position and its eastern end
         is south of its normal position"
        "north of its normal position during 1st half of the week and shift
         gradually southwards thereafter"

    Collapsing these to a single class (e.g. taking the first mentioned, or
    majority) would manufacture precision the source does not contain, so they
    are kept as MIXED and excluded from the directional signal downstream.
    """
    n, s = bool(_NORTH.search(sentence)), bool(_SOUTH.search(sentence))
    nr, ft = bool(_NEAR.search(sentence)), bool(_FOOT.search(sentence))

    # Foothills is IMD's own break wording and is the strongest single signal,
    # but only when it is not competing with a southward statement.
    if ft and not s:
        return FOOTHILLS
    directions = sum([n, s, nr])
    if directions > 1:
        return MIXED
    if n:
        return NORTH
    if s:
        return SOUTH
    if nr:
        return NEAR_NORMAL
    return NOT_STATED


def extract(texts: dict[str, str]) -> pd.DataFrame:
    """Extract trough-position statements from every bulletin.

    Returns one row per (bulletin date, week). Weeks with no trough sentence at
    all still produce a row with position=NOT_STATED so that coverage is
    visible in the output rather than silently absent.
    """
    rows: list[TroughStatement] = []
    for datestr, text in sorted(texts.items()):
        d = pd.Timestamp(datestr)
        for wk, body in _sections(text):
            body = _BULLET.sub(". ", body)
            best = None
            for sent in re.split(r"(?<=[.;])\s+", body):
                if not _TROUGH.search(sent):
                    continue
                pos = classify_position(sent)
                if pos == NOT_STATED:
                    continue
                fc = bool(_FORECAST.search(sent))
                # Prefer a forecast-modality statement over a present-tense one.
                if best is None or (fc and not best[1]):
                    best = (pos, fc, re.sub(r"\s+", " ", sent).strip())
                if fc:
                    break
            if best:
                rows.append(TroughStatement(d, wk, best[0], best[1], best[2]))
            else:
                rows.append(TroughStatement(d, wk, NOT_STATED, False, ""))
    return pd.DataFrame([r.__dict__ for r in rows])


def break_favourable(position: str) -> float | None:
    """Map a trough position to a break-favourable signal in [0, 1].

    **THIS MAPPING IS OURS, NOT IMD'S.** IMD supplies the mechanism (trough
    north / at the foothills -> drastic rainfall reduction over the core zone);
    it does not supply these numbers, and it does not label bulletins. Anyone
    challenging the result should challenge this function first -- it is the
    single place the authored assumption lives.

    Returns None where no directional claim exists, so that "we don't know" is
    propagated rather than being silently scored as 0.5.
    """
    return {
        FOOTHILLS: 1.0,     # IMD's own break wording -- strongest
        NORTH: 1.0,         # IMD's stated break direction
        NEAR_NORMAL: 0.0,
        SOUTH: 0.0,         # IMD associates active spells with a southward trough
        MIXED: None,
        NOT_STATED: None,
    }[position]


def advisory_evidence_for(
    target_date: pd.Timestamp, statements: pd.DataFrame
) -> tuple[str, str] | None:
    """Human-readable IMD trough evidence covering `target_date`, if any.

    RETURNS TEXT, NEVER A NUMBER. This exists to populate
    `RegimePrior.advisory_evidence` -- supporting context a farmer or extension
    officer can read and check against IMD's own bulletin. It is deliberately
    not convertible to a probability contribution:

      * D-16 measured this signal at 18% of week-sections / 33% of break events,
        on 4 break events total. That is far too thin to move a 20-year base
        rate, and fusing them would smuggle a 4-event association into a
        20-year statistic.
      * The physical mechanism is IMD's (glossary Break Monsoon definition), but
        the position -> break-favourable mapping is OURS (see
        `break_favourable`). Numeric fusion would bury that authored step inside
        a probability where nobody could audit it.

    Returns (evidence_text, source_label) or None.
    """
    for _, r in statements.iterrows():
        if break_favourable(r["position"]) is None:
            continue
        lead = 0 if int(r["week"]) == 1 else 7
        lo = r["date"] + pd.Timedelta(days=lead)
        if not (lo <= pd.Timestamp(target_date) < lo + pd.Timedelta(days=7)):
            continue
        phrasing = {
            NORTH: "north of its normal position",
            FOOTHILLS: "close to the Himalayan foothills",
            SOUTH: "south of its normal position",
            NEAR_NORMAL: "near its normal position",
        }[r["position"]]
        note = (
            " IMD's glossary defines Break Monsoon as the trough shifting north "
            "toward the Himalayan foothills, so this is break-favourable."
            if r["position"] in (NORTH, FOOTHILLS)
            else ""
        )
        return (
            f"IMD Extended Range bulletin of {r['date']:%d %b %Y} places the monsoon "
            f"trough {phrasing} in week {int(r['week'])}.{note}",
            f"IMD ERF bulletin {r['date']:%Y-%m-%d}, week {int(r['week'])}",
        )
    return None


def coverage_report(df: pd.DataFrame) -> str:
    n = len(df)
    lines = [f"trough statements: {n} rows ({df['date'].nunique()} bulletins x week 1/2)"]
    for pos in POSITIONS:
        c = int((df["position"] == pos).sum())
        lines.append(f"  {pos:12s} {c:>4}  ({100*c/n:5.1f}%)")
    usable = df["position"].map(lambda p: break_favourable(p) is not None).sum()
    lines.append(f"  usable directional signal: {usable}/{n} ({100*usable/n:.1f}%)")
    fc = int(df["is_forecast"].sum())
    lines.append(f"  forecast-modality statements: {fc}/{n} ({100*fc/n:.1f}%)")
    return "\n".join(lines)

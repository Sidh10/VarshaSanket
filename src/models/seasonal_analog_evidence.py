"""Stage 2 -- SEASONAL ANALOG EVIDENCE (historical fact lookup).

WHAT THIS IS
------------
Given a target year, find the K historical seasons whose PRE-SEASON (MAM)
Nino3.4/DMI state was closest, and report what actually happened in those
seasons -- the observed MCZ seasonal-rainfall tercile, straight from the record.

That is all it does. It looks up history. It does not model, predict, average,
or produce a probability.

WHY STAGE 2'S ROLE CHANGED
--------------------------
Stage 2 was originally a probability *downscaler*: reweight the outcome
distribution by analog proximity. D-17 tested that and it failed --

    RPSS vs climatology, LOYO over 20 seasons:
      JJAS (concurrent, diagnostic)  +0.039   CI [-0.179, +0.226]  -- spans zero
      MAM  (pre-season, operational) -0.249   CI [-0.383, -0.136]  -- WORSE

-- and it failed worst at the only operationally valid lead. Reweighting
probabilities by pre-season ENSO/IOD actively degrades them, because pre-season
Nino3.4 correlates +0.054 with seasonal MCZ rainfall in this record (concurrent
JJAS is -0.444, but that is not knowable before the season).

So Stage 2 no longer touches the probabilities. It supplies **disclosed
evidence** next to Stage 1's unchanged climatology: named years, real outcomes,
and the distances behind them, for a human to weigh.

THE DISAGREEMENT RULE
---------------------
The K nearest seasons frequently point in different directions -- which is the
honest signature of a predictor with r = +0.05. When they do, this module says
so explicitly and refuses to state a single expectation.

D-17's own failure cases are the argument: 2000 (La Nina, ended dry) and 2019
(warm ENSO, ended wettest on record, driven by a record IOD). Averaging two
seasons that disagree into "somewhat dry" would be more confident and less true
than reporting the split. **A confident-sounding average of disagreeing years is
worse than no evidence at all**, so `_summarise` has no code path that produces a
central expectation when the analogs are divided.

CODE REUSE
----------
`seasonal_analog_distances()` is the nearest-neighbour computation extracted
from `AnalogDownscaler.weights_for`, which now delegates to it -- the same
extract-and-delegate pattern used when `day_of_year_frequencies()` was lifted
out of the backtest climatology baseline. One implementation, so the leakage
safeguard is enforced in exactly one place and cannot drift between the two
callers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.features.seasonal_state import TERCILES, tercile_labels

# Fixed a priori. NOT tuned -- there is nothing to tune it against, because this
# module produces no score. K=5 is small enough to name every analog in a
# sentence a farmer could read and large enough to expose disagreement.
DEFAULT_K = 5
PRE_SEASON_WINDOW = "mam"  # operationally available; see D-17


def seasonal_analog_distances(
    table: pd.DataFrame,
    target_year: int,
    state_window: str = PRE_SEASON_WINDOW,
    pool_years: np.ndarray | None = None,
) -> pd.Series:
    """Standardised Euclidean distance in seasonal (Nino3.4, DMI) space.

    Extracted from `AnalogDownscaler.weights_for` so both the (now retired)
    reweighting path and this evidence path share one implementation.

    TARGET YEAR EXCLUSION IS ENFORCED ON THE MARKED LINE -- a hard filter on the
    pool index, not a zeroed weight that could be renormalised back in, and not
    a caller responsibility. Standardisation also uses the pool only, so the
    target year does not influence the scaling that positions it.

    Returns distance per pool year, ascending.
    """
    cols = [f"nino34_{state_window}", f"dmi_{state_window}"]
    pool = table.index.to_numpy() if pool_years is None else np.asarray(pool_years)

    # >>> LEAKAGE SAFEGUARD (ARCHITECTURE.md Stage 2, safeguard 1) <<<
    pool = pool[pool != target_year]
    # >>> the target year cannot re-enter after this line <<<

    mu = table.loc[pool, cols].mean().to_numpy()
    sd = table.loc[pool, cols].std().to_numpy()
    sd = np.where(sd > 0, sd, 1.0)

    x_t = (table.loc[target_year, cols].to_numpy() - mu) / sd
    x_p = (table.loc[pool, cols].to_numpy() - mu) / sd
    d = np.sqrt(((x_p - x_t) ** 2).sum(axis=1))
    return pd.Series(d, index=pool).sort_values()


@dataclass(frozen=True)
class SeasonalAnalogEvidence:
    """Auditable analog evidence. Prose plus every number behind it.

    Deliberately carries NO probability field. There is nothing here for Stage 4
    to multiply into a forecast -- if it wants a number it must use Stage 1's
    climatological probabilities, which this never touches.
    """

    target_year: int
    state_window: str
    k: int
    analogs: tuple[dict, ...]        # per analog: year, distance, outcome
    outcome_counts: dict[str, int]   # dry / normal / wet among the K
    agreement: str                   # "unanimous" | "leaning" | "divided"
    effective_n: float               # entropy-based, over distance-derived weights
    evidence_text: str
    method: str

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(int(a["year"]) for a in self.analogs)

    def describe(self) -> str:
        rows = "\n".join(
            f"    {a['year']}  d={a['distance']:.3f}  actual outcome: {a['outcome']}"
            for a in self.analogs
        )
        return (
            f"SeasonalAnalogEvidence {self.target_year} "
            f"[{self.state_window}, K={self.k}, agreement={self.agreement}]\n"
            f"{rows}\n"
            f"    counts={self.outcome_counts}  effective_n={self.effective_n:.2f}\n"
            f"    text: {self.evidence_text}"
        )


def _effective_n(distances: np.ndarray) -> float:
    """Entropy-based effective size of the shown analog set.

    An AUDIT statistic, not a probability weight: it says whether one season
    dominates the neighbourhood or the K are comparably close. Nothing consumes
    it as a forecast input. Uses the same exp(Shannon entropy) definition as
    Stage 2's retired reweighting path so the numbers stay comparable.
    """
    if len(distances) == 0:
        return 0.0
    w = np.exp(-(distances**2) / 2.0)
    if w.sum() <= 0:
        w = np.ones_like(w)
    w = w / w.sum()
    return float(np.exp(-np.sum(w * np.log(w))))


def _summarise(target_year: int, analogs: list[dict], counts: dict[str, int]) -> tuple[str, str]:
    """Build the evidence sentence. Returns (agreement_label, text).

    No branch of this function produces a single central expectation when the
    analogs disagree -- see the module docstring.
    """
    k = len(analogs)
    modal = max(counts, key=lambda c: counts[c])
    modal_n = counts[modal]
    spans_extremes = counts["dry"] > 0 and counts["wet"] > 0

    listing = "; ".join(f"{a['year']} was {a['outcome']}" for a in analogs)
    lead = (
        f"The {k} historical seasons whose pre-monsoon ENSO/IOD state most "
        f"resembled {target_year}: {listing}."
    )

    if modal_n == k:
        return "unanimous", (
            f"{lead} All {k} ended {modal}. Note this is what those seasons did, "
            f"not a forecast for {target_year}."
        )

    if spans_extremes or modal_n <= k / 2:
        extremes = [a for a in analogs if a["outcome"] in ("dry", "wet")]
        pair = ""
        if len(extremes) >= 2 and extremes[0]["outcome"] != extremes[-1]["outcome"]:
            pair = (
                f" For example {extremes[0]['year']} was {extremes[0]['outcome']} "
                f"while {extremes[-1]['year']} was {extremes[-1]['outcome']}, "
                f"despite similar pre-monsoon ENSO/IOD state."
            )
        return "divided", (
            f"{lead} These seasons diverged ({counts['dry']} dry, "
            f"{counts['normal']} normal, {counts['wet']} wet), so they do not "
            f"point to a single expectation.{pair} Pre-monsoon ENSO/IOD state "
            f"did not determine the outcome in these years."
        )

    return "leaning", (
        f"{lead} {modal_n} of {k} ended {modal}, but not all "
        f"({counts['dry']} dry, {counts['normal']} normal, {counts['wet']} wet). "
        f"This is a historical tendency among close seasons, not a forecast."
    )


def build_evidence(
    table: pd.DataFrame,
    target_year: int,
    k: int = DEFAULT_K,
    state_window: str = PRE_SEASON_WINDOW,
) -> SeasonalAnalogEvidence:
    """Look up the K nearest pre-season analogs and what actually happened.

    Outcomes are read from the observed record via `tercile_labels`, with the
    target year excluded from the tercile boundaries -- it must not help define
    the categories used to describe its own neighbours.
    """
    d = seasonal_analog_distances(table, target_year, state_window)
    nearest = d.iloc[:k]
    labels = tercile_labels(table.rain_total, exclude_year=int(target_year))

    analogs = [
        {"year": int(y), "distance": float(dist), "outcome": str(labels[y])}
        for y, dist in nearest.items()
    ]
    counts = {c: sum(1 for a in analogs if a["outcome"] == c) for c in TERCILES}
    agreement, text = _summarise(int(target_year), analogs, counts)

    return SeasonalAnalogEvidence(
        target_year=int(target_year),
        state_window=state_window,
        k=len(analogs),
        analogs=tuple(analogs),
        outcome_counts=counts,
        agreement=agreement,
        effective_n=_effective_n(nearest.to_numpy()),
        evidence_text=text,
        method=(
            f"K={len(analogs)} nearest historical seasons by standardised "
            f"pre-season ({state_window}) Nino3.4/DMI distance; outcomes are "
            f"OBSERVED terciles from the record, not modelled; target year "
            f"hard-excluded from both the pool and the tercile boundaries; "
            f"K fixed a priori, not tuned"
        ),
    )

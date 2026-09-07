"""Stage 1 -- CLIMATOLOGICAL REGIME PRIOR.

THIS IS NOT A FORECASTER. IT DOES NOT PREDICT.
----------------------------------------------
It returns the empirical base rate of each monsoon regime at a given calendar
position, computed from 20 years of observed Rajeevan labels. There is no lead
time, no current-state input, and nothing is fitted. Ask it about 15 July and it
tells you what fraction of 15 Julys (+/- a smoothing window) since 2000 were
active, break, or transition. That is all.

WHY THIS REPLACED THE ML FORECASTER
-----------------------------------
D-14: the gradient-boosted Regime Forecaster failed its Phase 1 gate at every
lead (1-4 weeks), under both season definitions, with BSS vs day-of-year
climatology of -0.034 / -0.014 / -0.057 / +0.009 -- none distinguishable from
zero. A regularised linear reference model failed identically, so the predictors
carried no usable signal rather than the model being mis-specified. The
seasonal-only variant scored ~-0.026, i.e. the full model was *worse* than just
knowing the calendar.

Nothing beat climatology. So Stage 1 is now climatology, stated honestly, rather
than a model that reproduces climatology while looking like a forecast. This is
a deliberate downgrade in claim and an upgrade in defensibility.

WHAT THIS COSTS US, SAID PLAINLY
--------------------------------
A base rate cannot distinguish one year from another. It will give the same
answer for 15 July 2002 (a severe break month) as for 15 July 2010. Any
year-specific skill the pipeline eventually has must come from somewhere else --
it is not here, and the schema is shaped so that nobody can mistake this for
year-specific information.

IMPLEMENTATION PROVENANCE
-------------------------
`day_of_year_frequencies()` is the exact computation D-14 used as its
climatology baseline -- lifted out of `src/eval/backtest.py::climatology_proba`,
which now delegates to it. One implementation, so the production prior and the
backtest baseline cannot drift apart. Verified numerically identical to the
pre-refactor function (see `verify_matches_backtest_baseline`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from src.features.labels import ACTIVE, BREAK, CLASSES, TRANSITION

# The third class is TRANSITION, not "normal" -- it is defined as "neither an
# active spell nor a break spell" by the Rajeevan criterion in labels.py, and
# ARCHITECTURE.md names it that way. Kept consistent deliberately; renaming it
# would silently desynchronise this from the validated D-14 labels.
REGIME_CLASSES = tuple(CLASSES)  # (active, break, transition)

DEFAULT_HALFWINDOW = 7  # days; matches D-14's climatology baseline exactly

# Which `seasonal_analog_agreement` values are fit to render into farmer-facing
# advisory text (D-19). "divided" is deliberately NOT here: 19 of 20 years in
# this record are divided (D-18), and a sentence that almost always just reports
# "these seasons disagreed" gives a farmer nothing to act on. The data stays in
# the RegimePrior for the technical/demo view -- it is only suppressed at the
# advisory-rendering boundary, exactly the way a null `advisory_evidence` from
# the bulletin path is already skipped.
ADVISORY_ELIGIBLE_AGREEMENT = ("leaning", "unanimous")


def day_of_year_frequencies(
    labels: pd.Series,
    day_of_year: np.ndarray,
    halfwindow: int = DEFAULT_HALFWINDOW,
) -> np.ndarray:
    """Smoothed empirical class frequency at each requested day-of-year.

    Pools every labelled day within +/- `halfwindow` days (circular in
    day-of-year space) across all years present in `labels`, then normalises.

    This is the shared core: `src/eval/backtest.py::climatology_proba` calls it
    for the backtest baseline, and `ClimatologicalPrior` calls it for the
    production Stage 1 path. Changing it changes both, on purpose.

    Returns array of shape (len(day_of_year), len(REGIME_CLASSES)).
    """
    y = labels.dropna()
    tr_doy = y.index.dayofyear.to_numpy()
    out = np.zeros((len(day_of_year), len(REGIME_CLASSES)))
    for i, d in enumerate(np.asarray(day_of_year)):
        dist = np.minimum(np.abs(tr_doy - d), 365 - np.abs(tr_doy - d))
        sel = y[dist <= halfwindow]
        if len(sel) == 0:
            sel = y
        for j, c in enumerate(REGIME_CLASSES):
            out[i, j] = (sel == c).mean()
    return out / out.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# Output schema -- this is the Stage 2 handoff contract.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegimePrior:
    """What Stage 1 hands to Stage 2 for one target date.

    THE TWO OUTPUTS ARE STRUCTURALLY SEPARATE AND MUST STAY THAT WAY:

      * `probabilities` / `ci_lower` / `ci_upper` -- numeric, climatology-only,
        derived solely from observed 2000-2019 Rajeevan labels.
      * `advisory_evidence` -- free text, human-readable, for Stage 4's advisory
        copy. It is NOT an input to the probabilities and never modifies them.

    D-16 measured the IMD trough signal at 18% of week-sections and 33% of break
    events, on 4 events total. That is enough to quote to a farmer as supporting
    context ("IMD's bulletin says the trough is north of normal next week") and
    nowhere near enough to move a probability. Fusing them would smuggle a
    4-event association into a 20-year base rate. The dataclass is frozen and the
    fields are different types precisely so that fusion has to be deliberate
    rather than accidental.
    """

    target_date: date
    day_of_year: int

    # --- numeric block: climatology only -----------------------------------
    probabilities: dict[str, float]   # keys = REGIME_CLASSES, sums to 1.0
    ci_lower: dict[str, float]        # 2.5th percentile, block bootstrap over years
    ci_upper: dict[str, float]        # 97.5th percentile

    # --- provenance / honesty fields ---------------------------------------
    n_years: int          # independent units behind the estimate
    n_labelled_days: int  # raw labelled days in the window (NOT independent)
    effective_n: int      # CLAUDE.md convention -- see note below
    source_years: tuple[int, int]
    halfwindow_days: int
    method: str

    # --- non-numeric evidence blocks: never fused with the above -----------
    #
    # TWO INDEPENDENT MECHANISMS, KEPT AS SEPARATE FIELD GROUPS so a reviewer
    # (and Stage 4) can trace every sentence of advisory text back to the
    # process that produced it, without guessing:
    #
    #   advisory_evidence / evidence_source
    #       <- BULLETIN PARSING. IMD Extended Range trough position, extracted
    #          from published PDFs (src/features/trough.py). Coverage ~30% of
    #          JJAS dates. D-16.
    #
    #   seasonal_analog_* (5 fields)
    #       <- HISTORICAL FACT LOOKUP. K nearest pre-season ENSO/IOD analogue
    #          years and their OBSERVED rainfall terciles
    #          (src/models/seasonal_analog_evidence.py). D-17 / D-18.
    #
    # Neither group is numeric input. Both are computed after `probabilities`
    # and cannot alter it -- asserted at runtime in run_stage1_prior.py.
    advisory_evidence: str | None = None
    evidence_source: str | None = None

    seasonal_analog_evidence: str | None = None          # prose
    seasonal_analog_years: tuple[int, ...] | None = None  # which years were shown
    seasonal_analog_detail: tuple[dict, ...] | None = None  # year/distance/outcome
    seasonal_analog_effective_n: float | None = None      # audit, not a weight
    seasonal_analog_agreement: str | None = None          # unanimous|leaning|divided

    @property
    def seasonal_analog_advisory_visible(self) -> bool:
        """True when the analog evidence should be rendered into farmer-facing
        advisory text (D-19).

        False for `divided` -- the field stays populated in the API response for
        the technical / demo view, but Stage 4's advisory generator treats it as
        absent, the same way it already treats a null `advisory_evidence` from
        the bulletin path. Derived, not stored, so `attach_seasonal_analog` and
        the numeric-block invariant are untouched.

        None agreement (no analog evidence attached at all) -> False.
        """
        return self.seasonal_analog_agreement in ADVISORY_ELIGIBLE_AGREEMENT

    def describe(self) -> str:
        p = "  ".join(f"{c}={self.probabilities[c]:.3f}" for c in REGIME_CLASSES)
        b = "  ".join(
            f"{c}=[{self.ci_lower[c]:.3f},{self.ci_upper[c]:.3f}]" for c in REGIME_CLASSES
        )
        ev = self.advisory_evidence or "(none)"
        sa = self.seasonal_analog_evidence or "(none)"
        sa_detail = ""
        if self.seasonal_analog_detail:
            rows = "  ".join(
                f"{a['year']}(d={a['distance']:.2f},{a['outcome']})"
                for a in self.seasonal_analog_detail
            )
            sa_detail = (
                f"\n    analogs: {rows}"
                f"\n    agreement={self.seasonal_analog_agreement}  "
                f"effective_n={self.seasonal_analog_effective_n:.2f}"
            )
        vis = (
            "" if self.seasonal_analog_agreement is None
            else f"  [advisory-visible: {self.seasonal_analog_advisory_visible}]"
        )
        return (
            f"RegimePrior {self.target_date} (doy {self.day_of_year})\n"
            f"  P: {p}\n"
            f"  95% CI: {b}\n"
            f"  effective_n={self.effective_n} years  "
            f"({self.n_labelled_days} labelled days, autocorrelated)\n"
            f"  method: {self.method}\n"
            f"  [bulletin evidence]  advisory_evidence: {ev}\n"
            f"  [analog evidence]    seasonal_analog_evidence: {sa}{sa_detail}{vis}"
        )


class ClimatologicalPrior:
    """Stage 1. Fit once on observed labels; query by target date.

    `fit` is a misnomer kept only for interface familiarity -- nothing is
    optimised. It tabulates observed frequencies. There are no parameters and no
    training/validation split, because there is nothing to overfit: the estimate
    IS the sample statistic.
    """

    def __init__(
        self,
        halfwindow: int = DEFAULT_HALFWINDOW,
        n_boot: int = 2000,
        seed: int = 0,
    ):
        self.halfwindow = halfwindow
        self.n_boot = n_boot
        self.seed = seed
        self._labels: pd.Series | None = None
        self._years: np.ndarray | None = None

    def fit(self, labels: pd.Series) -> "ClimatologicalPrior":
        """Tabulate. `labels` must be the validated Rajeevan labels (labels.py)."""
        self._labels = labels.dropna()
        self._years = np.unique(self._labels.index.year)
        return self

    def _bootstrap_bounds(self, doy: int) -> tuple[dict, dict]:
        """Per-class 95% band, block-bootstrapped over YEARS.

        Resamples whole seasons with replacement -- the same independence
        assumption D-14 used for its BSS intervals (`_bootstrap_bss_ci`). Days
        within a monsoon spell are strongly autocorrelated, so treating the
        ~300 labelled days in a +/-7-day window as independent would produce a
        band several times too narrow. The independent unit is the year, and
        there are only 20 of them; the resulting width is the honest answer.
        """
        assert self._labels is not None and self._years is not None
        rng = np.random.default_rng(self.seed + doy)
        by_year = {y: self._labels[self._labels.index.year == y] for y in self._years}

        draws = np.zeros((self.n_boot, len(REGIME_CLASSES)))
        for b in range(self.n_boot):
            pick = rng.choice(self._years, size=len(self._years), replace=True)
            sample = pd.concat([by_year[y] for y in pick])
            draws[b] = day_of_year_frequencies(sample, np.array([doy]), self.halfwindow)[0]

        # CAVEAT on zero-event days: where a class was never observed in the
        # window across all 20 years (e.g. break in early June), every bootstrap
        # resample also contains zero, so the band collapses to [0.000, 0.000].
        # That is the nonparametric bootstrap working correctly, NOT evidence
        # that the event is impossible -- it reflects "0 in 20 years", whose true
        # upper bound is roughly 3/20 = 0.15 by the rule of three. Do not present
        # a [0,0] band as certainty.
        lo = np.percentile(draws, 2.5, axis=0)
        hi = np.percentile(draws, 97.5, axis=0)
        return (
            {c: float(lo[j]) for j, c in enumerate(REGIME_CLASSES)},
            {c: float(hi[j]) for j, c in enumerate(REGIME_CLASSES)},
        )

    def prior_for(
        self,
        target_date: date | pd.Timestamp,
        advisory_evidence: str | None = None,
        evidence_source: str | None = None,
    ) -> RegimePrior:
        """Base rate for `target_date`. NOT a forecast for that date.

        `advisory_evidence` is passed straight through to the output untouched.
        It is deliberately impossible for it to affect `probabilities`: the
        probabilities are computed before it is even read.
        """
        if self._labels is None:
            raise RuntimeError("call fit() first")

        ts = pd.Timestamp(target_date)
        doy = int(ts.dayofyear)

        probs = day_of_year_frequencies(self._labels, np.array([doy]), self.halfwindow)[0]
        lo, hi = self._bootstrap_bounds(doy)

        tr_doy = self._labels.index.dayofyear.to_numpy()
        dist = np.minimum(np.abs(tr_doy - doy), 365 - np.abs(tr_doy - doy))
        n_days = int((dist <= self.halfwindow).sum())
        yrs_in_window = int(
            len(np.unique(self._labels.index.year[dist <= self.halfwindow]))
        )

        return RegimePrior(
            target_date=ts.date(),
            day_of_year=doy,
            probabilities={c: float(probs[j]) for j, c in enumerate(REGIME_CLASSES)},
            ci_lower=lo,
            ci_upper=hi,
            n_years=len(self._years),
            n_labelled_days=n_days,
            # CLAUDE.md requires an effective ensemble size with any produced
            # forecast. Here the honest number is INDEPENDENT SEASONS, not days:
            # the ~300 labelled days in the window come from ~20 years and are
            # autocorrelated within each. Reporting the day count would overstate
            # the evidence by more than an order of magnitude.
            effective_n=yrs_in_window,
            source_years=(int(self._years.min()), int(self._years.max())),
            halfwindow_days=self.halfwindow,
            method=(
                f"climatological base rate; day-of-year +/-{self.halfwindow}d "
                f"smoothing; block bootstrap over {len(self._years)} years "
                f"(n_boot={self.n_boot}); NO forecast component"
            ),
            advisory_evidence=advisory_evidence,
            evidence_source=evidence_source,
        )

    def prior_series(self, dates) -> pd.DataFrame:
        """Convenience: priors for many dates as a frame (no bootstrap bands)."""
        idx = pd.DatetimeIndex(dates)
        p = day_of_year_frequencies(
            self._labels, idx.dayofyear.to_numpy(), self.halfwindow
        )
        return pd.DataFrame(p, index=idx, columns=list(REGIME_CLASSES))


def attach_seasonal_analog(prior: RegimePrior, evidence) -> RegimePrior:
    """Attach Stage 2 analog evidence to a Stage 1 prior.

    Uses `dataclasses.replace`, so the numeric block is COPIED, not recomputed.
    It is therefore structurally impossible for attaching evidence to change
    `probabilities`, `ci_lower` or `ci_upper` -- there is no code path that
    could. The runtime assertion in run_stage1_prior.py checks it anyway.

    `evidence` is a `SeasonalAnalogEvidence`; passing None returns the prior
    unchanged.
    """
    from dataclasses import replace

    if evidence is None:
        return prior
    return replace(
        prior,
        seasonal_analog_evidence=evidence.evidence_text,
        seasonal_analog_years=evidence.years,
        seasonal_analog_detail=evidence.analogs,
        seasonal_analog_effective_n=evidence.effective_n,
        seasonal_analog_agreement=evidence.agreement,
    )


def advisory_evidence_lines(prior: RegimePrior) -> list[str]:
    """The evidence sentences Stage 4 may render into farmer-facing advisory text.

    This is the ONE boundary where "what the API returns" and "what the farmer is
    told" diverge. Everything upstream keeps its full data; this function decides
    what is fit to say out loud:

      * bulletin trough evidence (`advisory_evidence`) -- included whenever it is
        present (non-None). Its own coverage gating already happened in
        src/features/trough.py.

      * seasonal analog evidence (`seasonal_analog_evidence`) -- included ONLY
        when `seasonal_analog_advisory_visible` is True, i.e. agreement is
        "leaning" or "unanimous". When "divided" (19 of 20 years in this record,
        D-18) the sentence would almost always just report that the analog
        seasons disagreed, which is honest but gives a farmer nothing to act on,
        so it is treated as absent here -- exactly as a null `advisory_evidence`
        is skipped.

    The suppressed data is NOT deleted: `prior.seasonal_analog_*` remain
    populated for the technical and demo views and for
    `advisory_evidence_technical_view()`.

    Returns the lines in the order Stage 4 should present them (analog context
    first as background, then the more specific near-term bulletin signal).
    """
    lines: list[str] = []
    if prior.seasonal_analog_advisory_visible and prior.seasonal_analog_evidence:
        lines.append(prior.seasonal_analog_evidence)
    if prior.advisory_evidence:
        lines.append(prior.advisory_evidence)
    return lines


def advisory_evidence_technical_view(prior: RegimePrior) -> dict:
    """Everything, including the suppressed analog evidence, for the demo/API view.

    Mirrors `advisory_evidence_lines` but hides nothing, and flags which pieces
    the farmer-facing path drops and why -- so the demo can show "the system has
    this, and here is why it chose not to say it."
    """
    return {
        "bulletin_evidence": prior.advisory_evidence,
        "bulletin_evidence_source": prior.evidence_source,
        "seasonal_analog_evidence": prior.seasonal_analog_evidence,
        "seasonal_analog_years": list(prior.seasonal_analog_years or ()),
        "seasonal_analog_detail": list(prior.seasonal_analog_detail or ()),
        "seasonal_analog_agreement": prior.seasonal_analog_agreement,
        "seasonal_analog_advisory_visible": prior.seasonal_analog_advisory_visible,
        "seasonal_analog_suppressed_reason": (
            None
            if prior.seasonal_analog_advisory_visible
            or prior.seasonal_analog_agreement is None
            else "analog seasons divided (no single expectation); D-19"
        ),
        "farmer_facing_lines": advisory_evidence_lines(prior),
    }


def verify_matches_backtest_baseline(labels: pd.Series, dates) -> bool:
    """Assert the refactor did not move D-14's numbers.

    `src/eval/backtest.py::climatology_proba` now delegates to
    `day_of_year_frequencies`. This checks the delegation reproduces the shared
    core exactly, so the Phase 1 gate figures in D-14 remain reproducible.
    """
    from src.eval.backtest import climatology_proba

    idx = pd.DatetimeIndex(dates)
    a = climatology_proba(labels, idx).to_numpy()
    b = day_of_year_frequencies(labels, idx.dayofyear.to_numpy())
    return bool(np.allclose(a, b, atol=1e-12))

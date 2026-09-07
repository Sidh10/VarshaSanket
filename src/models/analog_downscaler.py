"""Stage 2 -- ANALOG DOWNSCALER.

Continuous-distance weighted KNN over historical YEARS, conditioned on seasonal
ENSO/IOD state, returning an empirical distribution of seasonal local outcomes
plus its effective ensemble size.

TWO CONDITIONING PATHS, KEPT STRUCTURALLY APART
-----------------------------------------------
  (a) Stage 1's day-of-year climatological regime probabilities (`RegimePrior`).
      Passed through untouched. Stage 2 does not recompute or adjust it.
  (b) Year-level analog weights from seasonal-mean Nino3.4 / DMI proximity.

These are separate objects in the output and are never multiplied together. (a)
is a within-season calendar base rate; (b) is a between-year seasonal-outcome
weighting. They answer different questions at different scales, and combining
them numerically would assert a coupling nothing here has tested.

THE SCALE DISCIPLINE THAT DEFINES THIS STAGE
---------------------------------------------
Analog weights are computed from **one seasonal-mean value per year**. There is
deliberately no code path that computes a week-specific ENSO/IOD distance, and
none that lets the teleconnection state select *which week within a season* is
analogous. That quantity is the claim D-14 tested and falsified (BSS -0.034 /
-0.014 / -0.057 / +0.009 at 1-4 week lead, with a linear reference model failing
identically). Re-introducing it here under the word "analog" would be the same
falsified claim relabelled.

What is being claimed instead is the separate, long-established seasonal-scale
relationship between ENSO/IOD and total monsoon rainfall. In this 20-year MCZ
sample that relationship is r = -0.44 for concurrent JJAS Nino3.4 -- and
r = +0.05 for pre-season MAM Nino3.4, which is why `state_window` exists and why
both must be reported (see `src/features/seasonal_state.py`).

AUTHORED PARAMETERS
-------------------
`bandwidth` and `recency_tau` are fixed a priori and are NOT tuned against the
held-out year. VERIFICATION.md section 3 / Michaelsen (1987): predictor and
hyper-parameter screening is the largest single source of artificial skill.
`src/eval/stage2_backtest.py` reports the full sensitivity grid so the spread is
visible, rather than the best cell being quoted as the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.features.seasonal_state import TERCILES
from src.models.climatological_prior import RegimePrior

# Fixed a priori. Bandwidth is in units of standard deviations of the (already
# standardised) seasonal index space; tau is an e-folding time in years.
DEFAULT_BANDWIDTH = 1.0
DEFAULT_RECENCY_TAU = 15.0  # Mondal & Mujumdar (2015) non-stationarity; see below
LOW_CONFIDENCE_NEFF = 10.0  # ARCHITECTURE.md safeguard 3


@dataclass(frozen=True)
class AnalogOutcome:
    """Stage 2 output. Consumes a Stage 1 `RegimePrior` and adds the seasonal
    local-outcome distribution, without altering anything Stage 1 produced.
    """

    target_year: int
    state_window: str                     # "jjas" (diagnostic) or "mam" (operational)

    # --- (b) seasonal analog block -----------------------------------------
    outcome_probabilities: dict[str, float]   # dry / normal / wet, sums to 1
    analog_weights: dict[int, float]          # year -> normalised weight
    effective_n: float                        # entropy-based, see effective_ensemble_size
    low_confidence: bool

    # --- (a) Stage 1 block, passed through untouched ------------------------
    regime_prior: RegimePrior | None = None

    # --- evidence block, passed through untouched ---------------------------
    advisory_evidence: str | None = None
    evidence_source: str | None = None

    # --- provenance ---------------------------------------------------------
    excluded_years: tuple[int, ...] = ()
    bandwidth: float = DEFAULT_BANDWIDTH
    recency_tau: float = DEFAULT_RECENCY_TAU
    method: str = ""

    def describe(self) -> str:
        p = "  ".join(f"{c}={self.outcome_probabilities[c]:.3f}" for c in TERCILES)
        top = sorted(self.analog_weights.items(), key=lambda kv: -kv[1])[:5]
        return (
            f"AnalogOutcome {self.target_year} [{self.state_window}]\n"
            f"  seasonal outcome P: {p}\n"
            f"  effective_n = {self.effective_n:.1f} analog years"
            f"{'   *** LOW CONFIDENCE ***' if self.low_confidence else ''}\n"
            f"  top analogs: " + ", ".join(f"{y}({w:.2f})" for y, w in top) + "\n"
            f"  excluded from pool: {self.excluded_years}\n"
            f"  advisory_evidence: {self.advisory_evidence or '(none)'}"
        )


def effective_ensemble_size(weights: np.ndarray) -> float:
    """Entropy-based effective sample size: exp(Shannon entropy of the weights).

    Equals N for uniform weights and collapses toward 1 as mass concentrates on
    a single analog. ARCHITECTURE.md safeguard 3 requires this be returned with
    every output, not computed on request -- so it is a constructor-time field
    of `AnalogOutcome`, and there is no way to obtain an outcome without it.
    """
    w = np.asarray(weights, dtype=float)
    w = w[w > 0]
    if w.size == 0:
        return 0.0
    w = w / w.sum()
    return float(np.exp(-np.sum(w * np.log(w))))


class AnalogDownscaler:
    """Weighted-analog lookup over historical years."""

    def __init__(
        self,
        state_window: str = "jjas",
        bandwidth: float = DEFAULT_BANDWIDTH,
        recency_tau: float = DEFAULT_RECENCY_TAU,
        use_recency: bool = True,
    ):
        if state_window not in ("jjas", "mam"):
            raise ValueError("state_window must be 'jjas' (diagnostic) or 'mam' (operational)")
        self.state_window = state_window
        self.bandwidth = bandwidth
        self.recency_tau = recency_tau
        self.use_recency = use_recency
        self._table: pd.DataFrame | None = None
        self._mu: np.ndarray | None = None
        self._sd: np.ndarray | None = None

    def _cols(self) -> list[str]:
        return [f"nino34_{self.state_window}", f"dmi_{self.state_window}"]

    def fit(self, table: pd.DataFrame) -> "AnalogDownscaler":
        """`table` is the per-year seasonal frame from seasonal_state."""
        self._table = table.copy()
        return self

    def weights_for(
        self, target_year: int, pool_years: np.ndarray | None = None
    ) -> pd.Series:
        """Normalised analog weights over the historical pool.

        TARGET YEAR EXCLUSION IS ENFORCED ON THE LINE MARKED BELOW. It is a hard
        filter on the pool index, not a zeroed weight that could be
        re-normalised back in, and not a caller responsibility.
        """
        assert self._table is not None, "call fit() first"
        t = self._table

        # DELEGATES to the extracted implementation in seasonal_analog_evidence.
        # The target-year exclusion and pool-only standardisation now live in
        # exactly ONE place, so the safeguard cannot drift between this (retired)
        # reweighting path and the evidence-lookup path that replaced it.
        from src.models.seasonal_analog_evidence import seasonal_analog_distances

        dist = seasonal_analog_distances(
            t, int(target_year), self.state_window, pool_years
        )
        pool = dist.index.to_numpy()
        d = dist.to_numpy()
        w = np.exp(-(d**2) / (2 * self.bandwidth**2))

        if self.use_recency:
            # Mondal & Mujumdar (2015): Indian extreme rainfall is non-stationary,
            # so older analogs are down-weighted. Cited, not re-derived.
            dy = np.abs(pool - target_year).astype(float)
            w = w * np.exp(-dy / self.recency_tau)

        if w.sum() <= 0:
            w = np.ones_like(w)
        return pd.Series(w / w.sum(), index=pool).sort_index()

    def downscale(
        self,
        target_year: int,
        outcome_labels: pd.Series,
        pool_years: np.ndarray | None = None,
        regime_prior: RegimePrior | None = None,
        advisory_evidence: str | None = None,
        evidence_source: str | None = None,
    ) -> AnalogOutcome:
        """Weighted empirical distribution of seasonal outcome for `target_year`.

        `regime_prior`, `advisory_evidence` and `evidence_source` are passed
        through untouched -- Stage 2 reads none of them and modifies none of
        them. The evidence separation enforced in Stage 1 therefore survives
        this stage unchanged.
        """
        w = self.weights_for(target_year, pool_years)
        probs = {c: float(w[[y for y in w.index if outcome_labels[y] == c]].sum())
                 for c in TERCILES}
        tot = sum(probs.values()) or 1.0
        probs = {c: v / tot for c, v in probs.items()}
        neff = effective_ensemble_size(w.to_numpy())

        return AnalogOutcome(
            target_year=int(target_year),
            state_window=self.state_window,
            outcome_probabilities=probs,
            analog_weights={int(k): float(v) for k, v in w.items()},
            effective_n=neff,
            low_confidence=neff < LOW_CONFIDENCE_NEFF,
            regime_prior=regime_prior,
            advisory_evidence=advisory_evidence,
            evidence_source=evidence_source,
            excluded_years=(int(target_year),),
            bandwidth=self.bandwidth,
            recency_tau=self.recency_tau,
            method=(
                f"seasonal-mean ({self.state_window}) Nino3.4/DMI Gaussian-kernel "
                f"analog weighting, bandwidth={self.bandwidth}, "
                f"recency_tau={self.recency_tau if self.use_recency else 'off'}; "
                f"target year hard-excluded; NO within-season trajectory used"
            ),
        )

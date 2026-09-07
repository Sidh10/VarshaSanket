"""Stage 4 -- DECISION ENGINE. Expected-loss comparison, both branches probabilistic.

THE MISTAKE THIS MODULE IS BUILT TO MAKE IMPOSSIBLE
----------------------------------------------------
DISCUSSION D-C (CLOSED):

    "`P > C/L` covers *protective* action. Sowing is the *risky* action. Both
     branches carry probability-weighted loss. Any worked example with one
     probabilistic side and one flat number is wrong."

This project already made that error once. It is not prevented here by careful
review; it is prevented by construction:

  * There is no scalar threshold anywhere in this module. No `C/L`, no single
    probability compared against a ratio.
  * Both branches are computed by the SAME function, `_expected_loss()`, as a
    dot product of the full 3-class probability vector with a 3-class loss
    vector. Neither branch can be a flat number because neither branch has a
    code path that produces one.
  * `_assert_is_expectation()` runs on every call and rejects a loss vector
    that is constant across regimes (which would make that branch effectively a
    scalar) or a probability vector that is not a full normalised distribution.

If a future edit tries to reduce one side to a single number, the assertion
fires rather than the number quietly shipping.

THE FORMULATION
---------------
Stage 1 supplies P(active), P(break), P(transition) for the target window.
Both actions are scored against that same full distribution:

    E[loss | SOW]  = P(active)·0
                   + P(break)·L_reseed
                   + P(transition)·(alpha · L_reseed)

    E[loss | WAIT] = P(active)·L_delay
                   + P(break)·0
                   + P(transition)·(beta · L_delay)

    recommend SOW  iff  E[loss|SOW] < E[loss|WAIT]

Sowing into a break spell loses the seed, tillage, fertiliser and labour, and
costs a reseed. Waiting through an active spell loses the planting window and
takes a late-sowing yield penalty. Transition carries a partial share of each,
set by `alpha`/`beta`. theta = L_reseed / L_delay is the loss ratio the farmer
can adjust; it is reported but never used as a threshold.

UNCERTAINTY IS PROPAGATED, NOT COLLAPSED
-----------------------------------------
Stage 1 also supplies a block-bootstrap CI per class. The decision is evaluated
at the point estimate AND at both ends of a sensitivity envelope, so a
recommendation that only holds at the central estimate is reported as FRAGILE
rather than presented as if it were firm.

**That envelope is built from MARGINAL percentiles and is not a joint credible
interval.** Stage 1's `ci_lower`/`ci_upper` are per-class bootstrap percentiles;
they do not jointly form a valid distribution. `_envelope()` therefore sets
P(break) to a bound and renormalises the remaining mass proportionally, which is
a defensible sensitivity probe and is labelled as one. Do not report it as a
credible interval on the decision.

PARAMETER PROVENANCE
--------------------
Every crop parameter here is PROVISIONAL and marked so. D-2 is still open and
the numbers in it are now actively doubted -- see `CROP_DEFAULTS` and
RESEARCH.md. Any `DecisionResult` built from unverified parameters carries
`uses_unverified_parameters=True` and a disclosure line, and the advisory text
refuses to imply an official source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.models.climatological_prior import (
    REGIME_CLASSES,
    RegimePrior,
    advisory_evidence_lines,
)

SOW, WAIT = "sow", "wait"


@dataclass(frozen=True)
class CropEconomics:
    """Per-crop loss inputs. All monetary values in INR per hectare.

    `source` and `verified` are mandatory and are surfaced in the output. A
    crop whose numbers are not traced to a published source CANNOT be presented
    as if it were -- `DecisionResult.disclosure()` renders the status.
    """

    crop: str
    l_reseed: float          # loss if sown and the window turns out to be a break
    l_delay: float           # loss if sowing is deferred and the window was active
    alpha: float = 0.4       # share of L_reseed borne in a transition window
    beta: float = 0.4        # share of L_delay borne in a transition window
    sowing_rain_threshold_mm: float | None = None  # advisory context only
    source: str = "PROVISIONAL - not traced to a published source"
    verified: bool = False

    @property
    def theta(self) -> float:
        """Loss ratio L_reseed / L_delay. Reported, never used as a threshold."""
        return self.l_reseed / self.l_delay if self.l_delay else float("inf")


# ---------------------------------------------------------------------------
# PROVISIONAL crop defaults. NOT ICAR-VERIFIED. See RESEARCH.md and D-20.
#
# D-2 recorded soybean 50-75 mm / groundnut 50 mm / cotton 50-100 mm as
# AI-generated and untraced. Attempting to trace them (2026-09-07) made the
# situation WORSE rather than better:
#
#   * A secondary trade source attributes "at least 100 mm" for soybean to
#     ICAR-IISR Indore, citing no bulletin, number or date.
#   * 100 mm CONTRADICTS the 50-75 mm figure in D-2.
#   * The primary ICAR-IISR bulletin could not be fetched -- the institute
#     subdomain does not resolve from here (DNS failure on
#     iisrindore.icar.gov.in and krishi.icar.gov.in; only icar.org.in resolves).
#
# So the D-2 numbers are not merely unverified, they are contradicted by the
# only attributable figure found. Nothing below may be quoted as ICAR guidance.
# The monetary values are illustrative placeholders and are not sourced at all.
# ---------------------------------------------------------------------------
CROP_DEFAULTS: dict[str, CropEconomics] = {
    "soybean": CropEconomics(
        crop="soybean",
        l_reseed=18000.0,
        l_delay=12000.0,
        sowing_rain_threshold_mm=None,  # deliberately NOT set: see note above
        source=(
            "PROVISIONAL / UNVERIFIED. Monetary values illustrative, not sourced. "
            "Rainfall threshold intentionally omitted: D-2's 50-75 mm is untraced "
            "and is contradicted by a secondary attribution of 100 mm to "
            "ICAR-IISR Indore that cites no bulletin. See RESEARCH.md, D-20."
        ),
        verified=False,
    ),
    "groundnut": CropEconomics(
        crop="groundnut",
        l_reseed=22000.0,
        l_delay=14000.0,
        sowing_rain_threshold_mm=None,
        source="PROVISIONAL / UNVERIFIED. Illustrative only. See RESEARCH.md, D-20.",
        verified=False,
    ),
    "cotton": CropEconomics(
        crop="cotton",
        l_reseed=30000.0,
        l_delay=20000.0,
        sowing_rain_threshold_mm=None,
        source="PROVISIONAL / UNVERIFIED. Illustrative only. See RESEARCH.md, D-20.",
        verified=False,
    ),
}


# ---------------------------------------------------------------------------
# The expectation machinery. One function, used by both branches.
# ---------------------------------------------------------------------------


def _assert_is_expectation(probs: np.ndarray, losses: np.ndarray, branch: str) -> None:
    """Reject anything that is not a genuine expectation over the full distribution.

    This is the structural guard against the D-C error. It fires if:
      * the probability vector is not a full, normalised distribution over all
        regime classes, or
      * the loss vector is constant across regimes -- which would make this
        branch a flat number dressed up as an expectation.
    """
    if probs.shape != (len(REGIME_CLASSES),):
        raise ValueError(
            f"[{branch}] expected a probability over all {len(REGIME_CLASSES)} "
            f"regimes, got shape {probs.shape}. A branch scored on a single "
            f"probability is the D-C error."
        )
    if not np.isclose(probs.sum(), 1.0, atol=1e-9):
        raise ValueError(f"[{branch}] probabilities sum to {probs.sum()}, not 1.")
    if losses.shape != probs.shape:
        raise ValueError(f"[{branch}] loss vector shape {losses.shape} != {probs.shape}")
    if np.allclose(losses, losses[0]):
        raise ValueError(
            f"[{branch}] loss vector is constant across regimes ({losses[0]}). "
            f"That makes this branch a flat number, which is exactly the "
            f"one-probabilistic-side-one-flat-number error closed in D-C."
        )


def _expected_loss(probs: np.ndarray, losses: np.ndarray, branch: str) -> float:
    """E[loss] = sum_r P(r) * L(r). The ONLY way either branch is scored."""
    _assert_is_expectation(probs, losses, branch)
    return float(np.dot(probs, losses))


def _loss_vectors(econ: CropEconomics) -> tuple[np.ndarray, np.ndarray]:
    """Loss vectors for SOW and WAIT, ordered as REGIME_CLASSES.

    REGIME_CLASSES is (active, break, transition).
      SOW : active -> 0 (germinates)      break -> L_reseed        transition -> alpha*L_reseed
      WAIT: active -> L_delay (missed)    break -> 0 (right call)  transition -> beta*L_delay
    """
    idx = {c: i for i, c in enumerate(REGIME_CLASSES)}
    sow = np.zeros(len(REGIME_CLASSES))
    wait = np.zeros(len(REGIME_CLASSES))
    sow[idx["break"]] = econ.l_reseed
    sow[idx["transition"]] = econ.alpha * econ.l_reseed
    wait[idx["active"]] = econ.l_delay
    wait[idx["transition"]] = econ.beta * econ.l_delay
    return sow, wait


def _probs_vector(d: dict[str, float]) -> np.ndarray:
    return np.array([d[c] for c in REGIME_CLASSES], dtype=float)


def _envelope(prior: RegimePrior) -> dict[str, np.ndarray]:
    """Marginal-based sensitivity envelope. NOT a joint credible interval.

    Sets P(break) to its bootstrap ci_lower / ci_upper and renormalises the
    remaining mass proportionally across the other classes. Labelled as a
    sensitivity probe wherever it is reported.
    """
    idx = {c: i for i, c in enumerate(REGIME_CLASSES)}
    base = _probs_vector(prior.probabilities)
    out = {"point": base}
    for name, bound in (("break_low", prior.ci_lower["break"]),
                        ("break_high", prior.ci_upper["break"])):
        v = base.copy()
        b = float(np.clip(bound, 0.0, 1.0))
        rest = 1.0 - b
        others = [i for c, i in idx.items() if c != "break"]
        share = base[others].sum()
        v[idx["break"]] = b
        v[others] = base[others] * (rest / share) if share > 0 else rest / len(others)
        out[name] = v
    return out


@dataclass(frozen=True)
class DecisionResult:
    target_date: str
    crop: str
    probabilities: dict[str, float]
    loss_sow: dict[str, float]
    loss_wait: dict[str, float]
    e_loss_sow: float
    e_loss_wait: float
    recommendation: str
    margin: float                       # E[wait] - E[sow]; >0 favours SOW
    theta: float
    envelope: dict[str, dict]           # scenario -> {e_sow, e_wait, recommendation}
    robust: bool                        # same recommendation across the envelope
    uses_unverified_parameters: bool
    parameter_source: str
    prior_effective_n: int
    evidence_lines: tuple[str, ...] = ()

    def disclosure(self) -> str:
        if not self.uses_unverified_parameters:
            return f"Cost parameters source: {self.parameter_source}"
        return (
            "PROVISIONAL COST PARAMETERS -- not traced to a published source. "
            "This recommendation demonstrates the decision method; the rupee "
            "values are illustrative and must be replaced with locally sourced "
            "figures before any farmer acts on it. " + self.parameter_source
        )

    def worked_example(self) -> str:
        rows = []
        for c in REGIME_CLASSES:
            rows.append(
                f"    {c:11s} P={self.probabilities[c]:.4f}  "
                f"L_sow={self.loss_sow[c]:>9,.0f}  L_wait={self.loss_wait[c]:>9,.0f}  "
                f"contrib_sow={self.probabilities[c]*self.loss_sow[c]:>9,.1f}  "
                f"contrib_wait={self.probabilities[c]*self.loss_wait[c]:>9,.1f}"
            )
        env = "\n".join(
            f"    {k:11s} E[sow]={v['e_sow']:>9,.1f}  E[wait]={v['e_wait']:>9,.1f}"
            f"  -> {v['recommendation'].upper()}"
            for k, v in self.envelope.items()
        )
        ev = "\n".join(f"    - {l}" for l in self.evidence_lines) or "    (none)"
        return (
            f"DECISION  {self.target_date}  crop={self.crop}\n"
            f"  Both branches are expectations over the SAME full distribution:\n"
            + "\n".join(rows)
            + f"\n    {'':11s} {'':>14} {'':>22} "
              f"E[loss|SOW]={self.e_loss_sow:>9,.1f}  E[loss|WAIT]={self.e_loss_wait:>9,.1f}\n"
            f"  theta = L_reseed/L_delay = {self.theta:.3f}\n"
            f"  RECOMMENDATION: {self.recommendation.upper()}  "
            f"(margin E[wait]-E[sow] = {self.margin:+,.1f} INR/ha)\n"
            f"  Sensitivity envelope (marginal CI on P(break); NOT a joint interval):\n"
            + env
            + f"\n    robust across envelope: {self.robust}\n"
            f"  Stage 1 effective_n: {self.prior_effective_n} years\n"
            f"  Farmer-facing evidence lines:\n{ev}\n"
            f"  {self.disclosure()}"
        )


def decide(
    prior: RegimePrior,
    econ: CropEconomics,
) -> DecisionResult:
    """Compare E[loss|SOW] against E[loss|WAIT] over Stage 1's full distribution.

    Evidence lines come from `advisory_evidence_lines(prior)` -- the D-19
    boundary function -- and never from the raw `advisory_evidence` /
    `seasonal_analog_*` fields, so the divided-case suppression is honoured
    automatically rather than reimplemented here.
    """
    probs = _probs_vector(prior.probabilities)
    sow_v, wait_v = _loss_vectors(econ)

    e_sow = _expected_loss(probs, sow_v, SOW)
    e_wait = _expected_loss(probs, wait_v, WAIT)
    rec = SOW if e_sow < e_wait else WAIT

    env = {}
    for name, pv in _envelope(prior).items():
        es = _expected_loss(pv, sow_v, f"{SOW}/{name}")
        ew = _expected_loss(pv, wait_v, f"{WAIT}/{name}")
        env[name] = {
            "e_sow": es,
            "e_wait": ew,
            "recommendation": SOW if es < ew else WAIT,
            "probabilities": {c: float(pv[i]) for i, c in enumerate(REGIME_CLASSES)},
        }
    robust = len({v["recommendation"] for v in env.values()}) == 1

    return DecisionResult(
        target_date=str(prior.target_date),
        crop=econ.crop,
        probabilities=dict(prior.probabilities),
        loss_sow={c: float(sow_v[i]) for i, c in enumerate(REGIME_CLASSES)},
        loss_wait={c: float(wait_v[i]) for i, c in enumerate(REGIME_CLASSES)},
        e_loss_sow=e_sow,
        e_loss_wait=e_wait,
        recommendation=rec,
        margin=e_wait - e_sow,
        theta=econ.theta,
        envelope=env,
        robust=robust,
        uses_unverified_parameters=not econ.verified,
        parameter_source=econ.source,
        prior_effective_n=prior.effective_n,
        # >>> D-19 BOUNDARY: the ONLY source of farmer-facing evidence text <<<
        evidence_lines=tuple(advisory_evidence_lines(prior)),
    )


def advisory_text(result: DecisionResult) -> str:
    """Terse English advisory preview for the Stage 4 worked example ONLY.

    SUPERSEDED for real delivery by `src/delivery/advisory.py::render`, which is
    language-aware, renders the farmer-facing (not technical) disclosure, and is
    what `WhatsAppSender` uses. This function stays only so
    `run_stage4_decision.py` can show a one-language preview inline; it is not on
    the delivery path. Do not add features here -- add them in src/delivery.
    """
    p_break = result.probabilities["break"]
    conf = "This is based on long-term averages for this date, not a forecast for this year."
    action = (
        "Conditions favour sowing now."
        if result.recommendation == SOW
        else "Waiting is the lower-risk choice right now."
    )
    hedge = "" if result.robust else (
        " This is a close call -- it changes within the uncertainty range, so treat it as weak."
    )
    ev = ("\n".join(f"  - {l}" for l in result.evidence_lines)) if result.evidence_lines else "  - (no additional evidence available for this date)"
    return (
        f"{action}{hedge}\n"
        f"Chance of a dry break spell around {result.target_date}: {p_break:.0%}. {conf}\n"
        f"Expected loss if you sow now: ~{result.e_loss_sow:,.0f} INR/ha; "
        f"if you wait: ~{result.e_loss_wait:,.0f} INR/ha.\n"
        f"Supporting information:\n{ev}\n"
        f"NOTE: {result.disclosure()}"
    )

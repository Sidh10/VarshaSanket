# VarshaSanket

**Hyperlocal Monsoon Onset & Break Prediction System (Block/Village Scale)**

Smart India Hackathon 2026 · Problem Statement **SIH26086**
Ministry of Earth Sciences (MoES) / NCMRWF · Software · Agriculture, FoodTech & Rural Development
Team: **Power Rangers** (ID: 0A649D)

---

## What this is

India already produces skillful 2–3 week monsoon active/break forecasts. IITM's ERPAS system has done this operationally for over a decade. **Those forecasts never reach a farmer as a decision.**

VarshaSanket is the last mile: it converts what is honestly known about monsoon risk on a given date into an economic **SOW or WAIT** recommendation, delivered to a farmer's phone.

> We do not replace the forecast. We turn what is known into a decision.

**What "honestly known" turned out to mean.** The original design put an ML regime *forecaster* at Stage 1. It was built, and it failed its gate: no lead time showed skill distinguishable from climatology (DISCUSSION **D-14**). A seasonal-analog downscaler was built next to reweight those probabilities; it failed too, and failed worst at the only operationally usable lead (**D-17**). Both were retired rather than papered over. What replaced them is narrower and defensible:

- **Stage 1 is a climatological prior, not a forecast.** P(active/break/transition) for a target date, as an empirical base rate by day-of-year over 20 years of observed Rajeevan labels, with a block-bootstrap confidence band. It carries **no lead time and no year-specific information**, and says so in its own output.
- **Stage 2 is disclosed evidence, not a probability.** Two mechanisms — the IMD Extended Range bulletin's trough position, and what actually happened in the K=5 most similar pre-monsoon seasons — attached as **text alongside** the prior. Neither can alter a number; that is enforced by runtime assertion, not convention. Analog disagreement is surfaced, never averaged away: across 20 target years the analogs are `divided` 19 times.
- **Stage 4 is the decision engine, and it is the actual contribution.** `E[loss|sow]` vs `E[loss|wait]`, both branches probability-weighted, with a per-farmer profile layer that adjusts **losses only** — never probabilities.

The honest limits in `CLAUDE.md` are load-bearing here, not disclaimers. **No skill or accuracy number is displayed anywhere in the demo**, because none survived its gate.

## The pipeline in one line

```
Climatological prior (base rate, no lead time)
  → disclosed evidence, text only (IMD trough + seasonal analogs)
    → decision engine: E[loss|sow] vs E[loss|wait], per-farmer losses
      → delivery: WhatsApp advisory + single-region risk card
```

Stage 3 (bias correction toward station data) is **specified but not built** — it is what block-scale output would require, and until it exists the output is monsoon-core-zone regional, not block-resolved.

Full detail in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Documentation map

*(Docs live at the repository root, not in a `docs/` directory — see DISCUSSION **D-10**.)*

| File | What's in it | Read it when |
|---|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Working rules for AI agents on this repo | **First, always** |
| [`AGENTS.md`](AGENTS.md) | Agent role definitions and handoff protocol | Before delegating work |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Stage-by-stage design, rationale, Q&A defenses | Building any stage |
| [`DATA.md`](DATA.md) | Every data source, access status, known limits | Touching data |
| [`VERIFICATION.md`](VERIFICATION.md) | Backtesting protocol — the anti-leakage rules | **Before reporting any accuracy number** |
| [`RESEARCH.md`](RESEARCH.md) | Verified claims + debunked claims registry | Making any factual claim |
| [`TASKS.md`](TASKS.md) | Phased build plan with gates | Planning work |
| [`DISCUSSION.md`](DISCUSSION.md) | Open decisions and their status (D-A…D-29) | Something feels unresolved |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` is pinned to the environment that produced the Phase 1 gate result and **requires Python 3.13**.

```bash
python -m src.models.run_stage1_prior     # Stage 1 prior + attached evidence
python -m src.models.run_stage4_decision  # Stage 4 worked example
python -m src.models.run_stage4_profile   # per-farmer profile worked example
python -m src.demo.server                 # demo: / (theta slider) and /profiles
python -m src.demo.run_demo               # headless demo check
python -m src.demo.run_profiles_demo      # full profile sweep over real HTTP
```

Model stages and the backtest harness live under `src/`; all data acquisition goes through `src/data/`. Accuracy metrics are computed **only** in `src/eval/`.

## Non-negotiables

1. **No accuracy number leaves this repo without passing [`VERIFICATION.md`](VERIFICATION.md).** Not in a slide, not in a README, not in a demo.
2. **No factual claim ships without a source in [`RESEARCH.md`](RESEARCH.md).** This project has already caught fabricated citations, invented government APIs, and an inflated impact statistic — see the debunked registry.
3. **The 14–30 day output is a regime outlook, never a date.** Overclaiming the horizon is the fastest way to lose credibility with a domain-literate judge.
4. **A claim in a doc is not evidence.** Every reported figure must point at a committed artifact under `artifacts/`. One sweep log went missing precisely because nobody checked this — see DISCUSSION **D-29**.

## Status

**Implementation, mid-build. Stages 1, 2 and 4 plus delivery and the demo are built; Stage 3 is not started.**

Verified as of 2026-09-08 (see `TASKS.md` for the per-item state):

| | State |
|---|---|
| Phase 0 — data access | Loaders verified. **Gate A and Gate C still open** — Gate C (one real conversation with a farmer/KVK/extension officer) is the highest-value open item in the project |
| Phase 1 — regime forecaster | Built, **gate NOT cleared** (D-14). Retired and replaced by the climatological prior |
| Phase 1R — climatological prior | Built (Stage 1) |
| Phase 2 — analog downscaler | Built, **skill gate NOT cleared** (D-17). Re-scoped to disclosed analog evidence (D-18/D-19) |
| Phase 3 — bias correction + full backtest | **Not started.** This is what block-scale output depends on |
| Phase 4 — decision engine + delivery | Built (D-20/D-21), plus the per-farmer profile layer (D-26). Open: ICAR sowing thresholds untraced and contested; monetary loss values illustrative and unsourced; **no target language chosen — blocking before any real send** |
| Phase 5 — demo | Built (D-22/D-27/D-28). Open: the profile-sweep evidence log is not committed (D-29) |

**Not claimed:** any skill or accuracy figure, block-resolved output, village-scale precision, or that this out-forecasts IMD or IITM.

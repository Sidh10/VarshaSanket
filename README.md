# VarshaSanket

**Hyperlocal Monsoon Onset & Break Prediction System (Block/Village Scale)**

Smart India Hackathon 2026 · Problem Statement **SIH26086**
Ministry of Earth Sciences (MoES) / NCMRWF · Software · Agriculture, FoodTech & Rural Development
Team: **Power Rangers** (ID: 0A649D)

---

## What this is

India already produces skillful 2–3 week monsoon active/break forecasts. IITM's ERPAS system has done this operationally for over a decade. **Those forecasts never reach a farmer as a decision.**

VarshaSanket is the last mile: it takes large-scale climate signals, works out what they mean for one specific block, quantifies the uncertainty honestly, and converts that into an economic **SOW or WAIT** recommendation delivered to the farmer's phone in their own language.

> We do not replace the forecast. We turn the forecast into a decision.

## The pipeline in one line

```
Climate signals → Regime forecast → Local analog match → Calibration → Economic decision → Farmer
```

Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Documentation map

| File | What's in it | Read it when |
|---|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Working rules for AI agents on this repo | **First, always** |
| [`AGENTS.md`](AGENTS.md) | Agent role definitions and handoff protocol | Before delegating work |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The 4-stage pipeline, design rationale, Q&A defenses | Building any stage |
| [`docs/DATA.md`](docs/DATA.md) | Every data source, access status, known limits | Touching data |
| [`docs/VERIFICATION.md`](docs/VERIFICATION.md) | Backtesting protocol — the anti-leakage rules | **Before reporting any accuracy number** |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | Verified claims + debunked claims registry | Making any factual claim |
| [`docs/TASKS.md`](docs/TASKS.md) | Phased build plan with gates | Planning work |
| [`docs/DISCUSSION.md`](docs/DISCUSSION.md) | Open decisions and their status | Something feels unresolved |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Data acquisition, model stages, and the backtest harness live under `src/`. See `docs/TASKS.md` for build order — **Stage 1 must be validated in isolation before anything downstream is wired up**, because if regime forecasting has no skill, the whole pipeline degrades to climatology regardless of how good Stages 2–4 are.

## Non-negotiables

1. **No accuracy number leaves this repo without passing `docs/VERIFICATION.md`.** Not in a slide, not in a README, not in a demo.
2. **No factual claim ships without a source in `docs/RESEARCH.md`.** This project has already caught fabricated citations, invented government APIs, and an inflated impact statistic — see the debunked registry.
3. **The 14–30 day output is a regime outlook, never a date.** Overclaiming the horizon is the fastest way to lose credibility with a domain-literate judge.

## Status

Idea/design phase complete. Entering implementation. See `docs/TASKS.md`.

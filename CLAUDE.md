# CLAUDE.md — Working Rules for This Repository

Read this before doing anything else. These rules exist because specific things went wrong during this project's research phase and cost real time to catch.

---

## Project identity (never re-derive this)

- **Problem:** SIH26086 — Hyperlocal Monsoon Onset & Break Prediction at block/panchayat scale
- **Sponsor:** Ministry of Earth Sciences / NCMRWF — note: NCMRWF *produces* IMDAA, the reanalysis this project trains on. That's a pitch asset, not a coincidence.
- **Solution:** VarshaSanket
- **Team:** Power Rangers, ID 0A649D
- **Positioning:** the last mile between existing forecasts and a farmer's decision. **We are not claiming to out-forecast IMD or IITM.**

---

## Rule 1 — Verify before asserting

This project's research phase produced multiple confident, plausible, **completely fabricated** claims from AI tools — including invented government API endpoints (three separate times, with different URLs each time), a citation attributed to authors who didn't write it, and a fake narrative about "past hackathon teams" that turned out to be current sibling problem statements.

**Therefore:**
- Any statistic, citation, API, dataset, or institutional claim you introduce must be checked against `docs/RESEARCH.md` or independently verified before it goes in a file.
- If you cannot verify something, write "UNVERIFIED" next to it. A flagged gap is more useful than a confident fabrication.
- Check `docs/RESEARCH.md` § Debunked before repeating anything that sounds authoritative. Several plausible-sounding claims in this domain are known-false and have resurfaced repeatedly.

## Rule 2 — Never report an accuracy number without the protocol

The single biggest technical risk on this project: a model that quietly predicts climatology, or a backtest with temporal leakage, will produce a **good-looking number that is meaningless**. Published monsoon forecasting has this exact documented failure (see Bürger 2019 in `docs/RESEARCH.md`), including in operational systems.

Before any CRPS, Brier, correlation, or skill figure is reported anywhere:
- It passed leave-one-year-out CV across all 20 years — not a single test year
- The target year was excluded from the analog pool
- It is reported **alongside** climatology and persistence baselines, never alone
- The event count is stated (~20 onsets, ~60 break events)

Full protocol in `docs/VERIFICATION.md`. **No exceptions, including for quick internal checks** — an unverified number written down once tends to end up in a slide.

## Rule 3 — Don't drift the architecture

The 4-stage design has been revised several times. Earlier versions were wrong in specific ways. If you find yourself writing any of the following, you have regressed to a superseded design:

| Wrong (superseded) | Correct |
|---|---|
| Stage 1 "Regime Classifier" | Stage 1 **Regime Forecaster** — it forecasts a future regime, not classifies a current one |
| Stage 2 forecasts local rainfall | Stage 2 is a **lookup conditioned on regime**, it never forecasts |
| Hierarchical GNN for bias correction | **Gradient boosting** — right-sized; a GNN needs multi-GPU for marginal gain |
| Decision rule `sow if P > C/L` | **Expected-loss comparison**: `E[loss\|sow]` vs `E[loss\|wait]` — both branches carry probability-weighted loss |
| Exact analog matching on ENSO+IOD+MJO | **Continuous-distance weighting** — exact matching leaves 2–5 analogs, not a distribution |
| Single 2019 test year | **Leave-one-year-out** across 20 years |

## Rule 4 — Honest limits are load-bearing, not disclaimers

These are stated proactively in the pitch because they're what makes the rest credible. Do not quietly drop them to make something sound better:

- IMDAA native resolution is **~12km**. IMD gridded rainfall via imdlib is **0.25° (~25km)**. Both are coarser than a village. Block-level output comes from bias correction toward station data; village-scale precision is a stretch goal, not a claim the data supports.
- Skill genuinely degrades past 2–3 weeks. Output is tiered: **7–14 days actionable forecast, 14–30 days regime outlook only.**
- Analog matching assumes historical patterns stay representative. Real non-stationarity is documented (Mondal & Mujumdar 2015). Mitigated by recency weighting, not solved.
- Effective analog count must be surfaced in the output. When it's low, confidence widens. A system that knows when it doesn't know is a feature.

## Rule 5 — Know the competitive landscape precisely

Do not write "nothing like this exists." Several things partly exist. Precision here is a credibility asset with a sponsor-side judge:

- **GKMS (IMD):** 5-day block-level advisories, vernacular, ~22M farmers, twice weekly
- **Mission Mausam / GPLWF (Oct 2024):** panchayat-level, but ≤10 days, deterministic, currently 12km (1km is a *future goal*)
- **IITM ERPAS/ERPv2:** real operational 2–3 week active/break forecasts — but regional scale, not farmer-facing, data access restricted
- **Meghdoot:** district-scale bulletins

What's genuinely unclaimed: block-scale active/break *probability*, an *economic decision layer*, and *end-to-end integration* to the farmer. That's the claim. Nothing broader.

---

## Code conventions

- Python, `scikit-learn` / `xgboost` for models — no deep learning frameworks unless a decision in `docs/DISCUSSION.md` changes this
- All data acquisition goes through `src/data/` — never hardcode a download in a notebook
- Any function that produces a forecast must also return its effective ensemble size
- Backtest code lives in `src/eval/` and is the only place accuracy metrics are computed

## When you're unsure

Check `docs/DISCUSSION.md` — it logs open decisions and the reasoning behind closed ones. If your question isn't there, add it there rather than guessing and moving on.

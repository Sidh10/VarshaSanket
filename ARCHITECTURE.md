# ARCHITECTURE

The pipeline, why each piece is shaped the way it is, and the answer to give when a judge or reviewer challenges it.

---

## Overview

```
[Teleconnection indices]              [Local block history]
 ENSO · IOD · MJO (NOAA CPC)          IMDAA reanalysis (IndiaWeatherBench)
          │                                      │
          ▼                                      │
  ┌───────────────────────────┐                  │
  │ STAGE 1 — REGIME FORECASTER│                 │
  │ index trajectory (t-30→t)  │                 │
  │ → P(active/break/transition)│                │
  │   at 1–4 week lead          │                │
  │ THE ONLY STAGE THAT FORECASTS│               │
  └────────────┬───────────────┘                 │
               ▼                                  │
  ┌───────────────────────────┐                  │
  │ STAGE 2 — ANALOG DOWNSCALER│◄────────────────┘
  │ given forecast regime, find │
  │ similar historical periods, │
  │ read off what happened HERE │
  │ • target year excluded      │
  │ • continuous-distance weights│
  │ • reports effective N       │
  └────────────┬───────────────┘
               ▼
  ┌───────────────────────────┐
  │ STAGE 3 — BIAS CORRECTION  │
  │ gradient boosting, calibrated│
  │ against real IMD records    │
  └────────────┬───────────────┘
               ▼
  ┌───────────────────────────┐
  │ STAGE 4 — DECISION ENGINE  │
  │ E[loss|sow] vs E[loss|wait] │
  │ adjustable θ, ICAR defaults │
  └────────────┬───────────────┘
        ┌──────┴──────┐
        ▼             ▼
   Risk map      WhatsApp advisory
   (block        (regional
    choropleth)   language)
```

---

## Stage 1 — Regime Forecaster

**Input:** trajectory of ENSO (Niño3.4), IOD (DMI), MJO (RMM1/RMM2) over t−30 → t, plus coarse H500 / T850 fields
**Output:** P(active), P(break), P(transition) for the target window at 1–4 week lead
**Model:** gradient-boosted classifier

**This is the only stage with genuine predictive skill.** That skill comes from MJO/BSISO phase propagation, which is quasi-oscillatory and therefore partially predictable 2–3 weeks out.

**Design note:** uses the *recent trajectory* of indices, not forecast indices. This keeps the system self-contained — we don't inherit another model's forecast error, and we don't depend on any restricted data feed.

**If this stage has no skill, the project has no skill.** Validate it in isolation first. See `docs/TASKS.md` Phase 1.

---

## Stage 2 — Analog Downscaler

**Input:** the regime probability from Stage 1 + 20 years of local block history
**Output:** an empirical probability distribution of local outcomes, plus effective ensemble size
**Method:** continuous-distance weighted nearest-neighbour search over historical periods

**Stage 2 never forecasts.** It answers: *"when the atmosphere was in this regime before, what actually happened at this block?"* That's a lookup conditioned on Stage 1's output.

### Why analogs instead of end-to-end deep learning

A model trained to regress rainfall directly from indices minimises average error by hedging — it predicts something close to the mean almost everywhere. This is the **double-penalty problem**, and it smooths away exactly the local extremes and true dry spells that determine a farmer's decision. Analogs sample *real observed outcomes*, so the output preserves realistic local variance by construction.

### Three specific safeguards

1. **Target year excluded from the pool.** This is the specific leakage risk analog methods carry — searching history for matches silently includes the test period unless explicitly prevented. Non-negotiable.
2. **Continuous distance, not exact matching.** Arithmetic: 20 years × ~3 break events ≈ 60 historical events per block. Requiring an exact joint match on ENSO *and* IOD *and* MJO state can leave **2–5 analogs** — a handful of anecdotes, not a distribution. Weighted distance lets near-matches contribute proportionally.
3. **Effective ensemble size reported with every forecast.** Computed as the entropy-based effective sample size of the analog weights. Below a threshold (~10), the system explicitly flags low confidence and widens bands rather than presenting false precision.

### Why recency weighting

Mondal & Mujumdar (2015) document real non-stationarity in Indian extreme rainfall. Recent analogs get higher weight. Mitsui & Boers (2021) independently show 15 years of training data suffices for skillful onset prediction, so this costs nothing in effective data volume.

---

## Stage 3 — Bias Correction

**Model:** gradient-boosted residual model
**Calibrated against:** IMD gridded rainfall records via `imdlib`

**Why not a Hierarchical GNN:** a GNN needs multi-GPU training and substantial engineering for marginal gain here. Right-sizing the model to the problem is a deliberate design position — the opposite of forcing an oversized architecture where it isn't needed. Be ready to say this out loud; it's a defensible answer, not an apology.

---

## Stage 4 — Decision Engine

**This is the actual differentiator.** Everything upstream is forecasting; this is the part nothing else does.

### The rule

```
E[loss | sow now] = P(false onset) × L_reseed
E[loss | wait]    = P(rains arrive) × L_delayed_sowing

Recommend SOW when  E[loss | sow now] < E[loss | wait]
```

### Why not the classic cost-loss rule

The textbook cost-loss framework (`act if P > C/L`) covers **protective** action — pay C to avoid loss L. **Sowing is not protective; it is the risky action.** Both branches carry loss:

- Sow, rains fail → lost seed, tillage, fertiliser, labour, plus reseeding cost
- Don't sow, rains come → lost planting window, yield penalty from late sowing

So it's a comparison of two expected losses. **Both sides must be probability-weighted.** A worked example with one side probabilistic and the other a flat number is wrong and will be caught.

### θ is an input, not a constant

C and L vary enormously by crop, landholding size, irrigation access, and whether the farmer can afford to reseed at all. Hardcoding θ ≈ 0.3 is indefensible. It's exposed as an adjustable parameter with ICAR-sourced per-crop defaults.

**Demo value:** sliding θ live and watching SOW flip to WAIT is one of the strongest interactive moments available.

---

## Output layer

**Risk map:** block-level choropleth, colour-coded by onset/break probability, for extension officers and district officials.

**Farmer advisory:** short regional-language message over WhatsApp Business API (Twilio Sandbox for demo — free, no business verification, live in minutes).

The advisory carries: probability, evidence (effective analog count), confidence level, and the recommendation. Not just a number — **prediction + evidence + uncertainty + consequence + action.**

---

## Output tiering — do not blur this

| Lead time | What we output |
|---|---|
| 7–14 days | Actionable probabilistic onset/break forecast |
| 14–30 days | Regime outlook only — elevated/reduced break risk. **Not a date, not a rainfall amount** |

IMD's own published guidance shows useful skill of roughly 2 weeks at *subdivision* scale, which is coarser than block. Claiming block-level precision at 30 days claims more than IMD achieves at a coarser scale over a shorter horizon. Stating the tiering yourself reads as competence.

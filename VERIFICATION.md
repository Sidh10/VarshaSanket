# VERIFICATION PROTOCOL

**No accuracy number leaves this project without passing every check on this page.**

This is not bureaucracy. It is the project's strongest differentiator and its biggest risk simultaneously.

---

## Why this exists

Published monsoon forecasting has a documented history of reporting inflated skill:

- **Bürger (2019)** found IMD's own operational onset forecast — reporting correlation 0.78 — had a **36% overlap between the data used to define the model and the data used to verify it**. The real skill is lower than reported.
- The same paper found a published competing method that claimed superiority actually scored **73% success against climatology's 75%** — worse than predicting the historical average, while being presented as an advance.
- **Michaelsen (1987)** established the mechanism: bias from *predictor screening* (0.36–0.71 artificial skill in his experiments) dwarfs bias from coefficient fitting (~0.06–0.14).

**This is the trap most teams working on this problem will fall into without knowing it exists.** Avoiding it deliberately, and being able to say so, is worth more than a slightly better model.

---

## The protocol

### 1. Leave-one-year-out cross-validation across all 20 years

For each year Y in 2000–2019:
- Train on the other 19 years
- Predict Y's onset date and break spells
- Record

Then aggregate skill across all 20 held-out years.

**Why not a single test year:** we predict *seasonal events*, not 6-hourly weather. One year yields roughly **one onset and 2–4 break events**. CRPS or Brier computed on that is noise. Leave-one-year-out gives **~20 onset events and ~60 break events** — a defensible sample.

> IndiaWeatherBench's own train/val/test split (2000–2017 / 2018 / 2019) is designed for 6-hourly weather forecasting with ~1,500 test samples. **Do not copy it for seasonal event prediction.**

### 2. Target year excluded from the analog pool

When predicting year Y, year Y must be removed from Stage 2's analog search pool entirely.

This is the specific leakage mode analog methods carry: searching history for "similar periods" will silently include the target period unless explicitly prevented. **This is the single easiest way to produce a fraudulent-looking result by accident.**

### 3. Feature selection inside training folds only

No predictor screening, no EOF computation, no distance-metric tuning, no hyperparameter choice may touch the held-out year. Per Michaelsen, this is where the largest bias enters.

### 4. Always report against baselines

Every reported figure must appear next to:

- **Daily climatology** — long-term mean for that calendar day, computed excluding the target year
- **Weekly progressing climatology** — captures the monsoon's northward march
- **Lagged persistence** — `X(t+L) = X(t)`

A number without its baselines is not a result.

### 5. Metrics

| Metric | Applied to |
|---|---|
| CRPS (latitude-weighted) | Probabilistic outlook |
| Brier score | Binary agronomic events: P(rain ≥ 25mm in 7d), P(break ≥ 5 days) |
| Reliability diagram | Calibration — is a stated 70% right ~70% of the time? |
| Spread/skill ratio | Ensemble dispersion (1.0 = calibrated, <1.0 = overconfident) |
| **Effective ensemble size** | Reported *with every forecast*, not just in evaluation |

---

## Pre-report checklist

Before any number appears in a slide, README, demo, or conversation:

- [ ] Computed via leave-one-year-out across 20 years, not a single split
- [ ] Target year excluded from the analog pool in every fold
- [ ] No feature/hyperparameter selection used held-out data
- [ ] Climatology baseline computed and reported alongside
- [ ] Persistence baseline computed and reported alongside
- [ ] Event count stated explicitly (~20 onsets / ~60 breaks)
- [ ] If the model beats climatology by a small margin, that margin is stated honestly, not rounded up

---

## The sanity check that matters most

**Ask: could this model be secretly predicting climatology?**

Weather is close to average most of the time, so a model that ignores its inputs and predicts the seasonal mean can score deceptively well on point metrics. Test for it explicitly:

- Compare against the climatology baseline. If the margin is near zero, the model has no real skill regardless of what the absolute number looks like.
- Check whether predictions actually vary with input regime. If Stage 1's output barely moves the final distribution, the pipeline has collapsed to climatology.

**Nobody on this team is a domain expert in climate verification.** That's a known gap (see `docs/DISCUSSION.md` D-1). This protocol is the compensation for it — follow it mechanically rather than relying on judgment about whether a number "looks right."

---

## What to say about this

> *"Published work shows monsoon onset forecasts — including operational ones — routinely report inflated skill from model-selection bias. We designed our verification specifically to avoid it: leave-one-year-out across twenty years, target year excluded from the analog pool, and every result scored against climatology and persistence, not just our own metrics."*

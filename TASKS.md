# TASKS

Build order with explicit gates. **Protect the MVP** — a working regime → probability → decision chain on *one district*, honestly validated, beats a half-finished national system.

---

## Phase 0 — Unblock (do these now, they gate everything)

- [ ] **Gate A:** Confirm with SPOC that SIH26086 is not blocked by another team at the college
- [ ] **Gate C:** One real conversation with a farmer, agricultural extension officer, or KVK staffer — *highest-value open item in the entire project*, still not done
- [x] Pull an IndiaWeatherBench subset, confirm it loads — *loaded via HTTP-range zip reads (climatology zarr + one train h5 timestep); grid/vars/dtype verified. See DISCUSSION D-6, D-8.*
- [x] Pull NOAA CPC index series, confirm endpoints live — *ENSO/Niño3.4 endpoints live at CPC; DMI and RMM are NOT CPC products (PSL / BoM respectively). See DISCUSSION D-7.*
- [x] `pip install imdlib`, confirm a rainfall download works — *imdlib 0.1.21; `rain` 2018 downloaded, 0.25° confirmed. See DISCUSSION D-6.*

**Gate C is not optional polish.** It's the one input no competing team can generate by prompting an AI, and it should open the pitch.

---

## Phase 1 — Regime Forecaster (Stage 1)

- [x] Build index-trajectory feature construction (t−30 → t lags for Niño3.4, DMI, RMM1/RMM2) — `src/features/trajectory.py`, 41 features, publication lags applied
- [x] Add coarse H500 / T850 fields as auxiliary inputs — `src/data/iwb_fields.py`, IndiaWeatherBench raw zarr via HTTP-range reads (595 MB, not 101 GB)
- [x] Define active/break/transition labels from historical rainfall (Rajeevan-style normalised anomaly over monsoon core zone) — `src/features/labels.py`
- [x] Train gradient-boosted **forecaster** (not a classifier — it predicts a *future* regime) — `src/models/regime_forecaster.py`
- [x] **Validate in isolation** — does it beat climatological regime frequency at 1, 2, 3, 4 week leads? — `src/eval/run_phase1.py`

> ⚠️ **This is the load-bearing stage.** If Stage 1 has no skill beyond climatology, the whole pipeline collapses to climatology no matter how good Stages 2–4 are. Test it alone before building anything downstream.

**Gate:** Stage 1 beats climatological regime frequency at ≥2 week lead. If not, stop and reassess — don't paper over it with downstream complexity.

### 🔴 GATE RESULT (2026-09-07): **NOT CLEARED** — see DISCUSSION D-14

Brier Skill Score vs day-of-year climatology, LOYO across 20 years. **JJAS (primary):**

| Lead | n | BSS vs climatology | 95% CI (block bootstrap over years) | Clears? |
|---|---|---|---|---|
| 1 week | 2180 | **−0.0342** | [−0.0724, +0.0099] | NO |
| 2 week | 2040 | **−0.0144** | [−0.0561, +0.0330] | NO |
| 3 week | 1900 | **−0.0569** | [−0.1052, −0.0005] | NO |
| 4 week | 1760 | **+0.0090** | [−0.0410, +0.0609] | NO |

Strict Jul–Aug (Rajeevan) sensitivity arm agrees: −0.0055 / −0.0119 / −0.0785 / −0.0910. **Both definitions fail; they do not disagree.**

No lead shows skill distinguishable from zero. The 4-week +0.009 has a CI spanning zero and is not credible as skill (skill rising with lead is physically backwards). Event counts: 40 break spells / 56 active spells over 20 years (JJAS).

**Per this gate, work has STOPPED. Phase 2 is not started.** Reassessment options are in DISCUSSION D-14.

---

## Phase 1R — Reassessment (BLOCKING; replaces "start Phase 2")

- [ ] Decide between the D-14 options (richer predictors / different target / accept regime-forecasting is not our contribution)
- [ ] If pivoting positioning: rewrite the Stage 1 claim in ARCHITECTURE.md and the pitch before any further build
- [ ] Do NOT begin Phase 2 until this is resolved

---

## Phase 2 — Analog Downscaler (Stage 2)

- [ ] Feature-space reduction over regional fields (PCA is sufficient; autoencoder only if PCA underperforms)
- [ ] Continuous-distance weighted KNN over historical periods
- [ ] **Target-year exclusion built in from the first commit**, not retrofitted
- [ ] Recency weighting on analog selection
- [ ] Effective ensemble size computation (entropy-based) returned with every forecast
- [ ] Low-confidence flagging when effective N drops below threshold

**Gate:** for a sample of regimes, effective N stays usable (≳10) rather than collapsing to a handful.

---

## Phase 3 — Calibration + Backtest (Stage 3) — **the highest-value phase**

- [ ] Gradient-boosted residual model against IMD gridded records
- [ ] Implement full leave-one-year-out harness per `docs/VERIFICATION.md`
- [ ] Climatology baseline
- [ ] Persistence baseline
- [ ] CRPS, Brier, reliability diagram, spread/skill ratio
- [ ] **Explicit climatology-collapse test** — does the model actually respond to regime input?

> **If time runs short, cut UI polish before cutting this.** A defensible number with stated event counts beats a prettier map. This is also the phase that produces the single most persuasive line in the pitch.

**Gate:** a real skill number vs. climatology, computed over ~20 onsets / ~60 breaks, that you'd be comfortable defending under questioning.

---

## Phase 4 — Decision Engine + Delivery (Stage 4)

- [ ] Expected-loss comparison — **both branches probability-weighted**
- [ ] Adjustable θ with per-crop defaults
- [ ] **Trace ICAR sowing thresholds to actual published bulletins** before hardcoding any number (currently unverified — see `docs/RESEARCH.md`)
- [ ] Advisory text generation (probability + evidence + confidence + recommendation)
- [ ] Regional language output
- [ ] Twilio WhatsApp Sandbox integration
- [ ] Block-level choropleth risk map

---

## Phase 5 — Demo

- [ ] Pre-baked, guaranteed-working demo case for one district
- [ ] Live θ slider (SOW ↔ WAIT flip is the strongest interactive moment)
- [ ] Effective analog count visible in the demo UI
- [ ] Backtest number on screen with event count stated
- [ ] Rehearse until flawless

---

## Ongoing / cross-cutting

- [ ] Correct **"120 million"** → **93.09 million agricultural households** everywhere it appears (slides, docs, scripts)
- [ ] Keep `docs/RESEARCH.md` updated as new claims enter
- [ ] Log every architectural decision in `docs/DISCUSSION.md`

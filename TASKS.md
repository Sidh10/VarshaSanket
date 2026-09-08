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

### Phase 1R build cycle 1 — IMD trough-position signal (2026-09-07)

- [x] Trough-position extractor over the 96 JJAS bulletins — `src/features/trough.py`
- [x] MCZ reconciliation from real sub-division geometry — `src/features/mcz.py`
- [x] Bulletin acquisition via the archive listing (filenames never constructed) — `src/data/imd_bulletins.py`
- [x] Join against Rajeevan/imdlib labels + honest association check — `src/eval/phase1r_trough_check.py`
- [x] **STOPPED at the gate. Stage 2 interface NOT built.**

**Result: real signal, but a hard coverage ceiling.** Full detail in DISCUSSION **D-16**.

| Measure | Value |
|---|---|
| P(break \| trough north/foothills) | **0.50** (n=8) |
| P(break \| trough south/near-normal) | **0.00** (n=22) |
| Fisher exact two-sided p (pooled) | **0.003** |
| Fisher exact p (week 2, lead 7–13 d) | **0.021** |
| LOO-calibrated BSS vs climatology (year-level) | **+0.395** pooled, **+0.336** week 2 |
| Raw hard-0/1 BSS | −0.154 pooled (overconfident, uncalibrated) |
| *(BSS correction: point-level LOO gave +0.296/+0.233; year-level LOO — the leak-free fold — gives the +0.395/+0.336 above. Went up, not down. See D-16.)* | |
| **Usable directional signal** | **18.3%** of week-sections (35/191) |
| **Break events the pipeline can see** | **4 of 12 (33%)** |
| **Real event count** | **4 break-dominant windows** |

- [x] **DECISION TAKEN:** trough signal is *not* a standalone Stage 1 (4 events, 18% coverage). Retained as **disclosed advisory evidence text only**, structurally separated from the numeric path. See build cycle 2.

### Phase 1R build cycle 2 — Stage 1 replaced by a climatological prior (2026-09-07)

The ML Regime Forecaster is retired. Stage 1 is now the empirical base rate that D-14 already proved nothing beat.

- [x] Checked for an existing climatology implementation **before** writing one — found `src/eval/backtest.py::climatology_proba` (day-of-year, ±7d), D-14's own baseline
- [x] Extracted its core to `day_of_year_frequencies()` in `src/models/climatological_prior.py`; `climatology_proba` now **delegates** to it — one implementation, no drift
- [x] **Verified the refactor is bit-identical** to the pre-refactor body (max abs diff **0.0**), so D-14's reported figures stay reproducible
- [x] P(regime) by **day-of-year** (matching D-14's unit) from the validated 2000–2019 Rajeevan labels; docstring states it has no lead time and is not a forecast
- [x] Uncertainty via **block bootstrap over years** — same independence unit as D-14's BSS intervals; per-day bounds treating days as independent would be dishonestly narrow
- [x] `RegimePrior` schema defined — the Stage 2 handoff contract
- [x] `advisory_evidence: str | None` as a **separate, non-numeric** field, with a runtime assertion that it cannot alter the probabilities
- [x] ARCHITECTURE.md Stage 1 rewritten (old forecaster language **removed**, not left alongside); output-tiering table flagged as aspirational since it presumes a Stage 1 that forecasts
- [x] **Stage 2 NOT wired.** Contract defined, then stopped.

Run: `python -m src.models.run_stage1_prior` · log `artifacts/stage1_prior_schema.txt`

Measured: IMD trough evidence covers **180/610 JJAS dates 2021–2025 (30%)** — consistent with D-16's 31%, measured rather than assumed.

- [ ] **Phase 2 remains gated.** Stage 1 now supplies a base rate with no year-specific information, so a Stage 2 built on it downscales climatology. Decide whether that is worth building before building it.

---

## Phase 2 — Analog Downscaler (Stage 2)

- [x] Continuous-distance weighted KNN over historical **years**, on seasonal-mean Niño3.4/DMI — `src/models/analog_downscaler.py`
- [x] **Target-year exclusion built in from the first commit** — one line, `pool = pool[pool != target_year]`; verified across all 20 folds
- [x] Recency weighting (Mondal & Mujumdar 2015), reported both on and off
- [x] Effective ensemble size (entropy-based) as a **required field** of every output, not bolted on
- [x] Low-confidence flagging below N_eff ≈ 10
- [x] `advisory_evidence` / `evidence_source` passed through byte-identical — Stage 2 reads neither
- [ ] ~~Feature-space reduction over regional fields (PCA)~~ — not reached; the skill gate failed first
- [x] **STOPPED at the gate. Stage 4 NOT started.**

**Gate:** for a sample of regimes, effective N stays usable (≳10) rather than collapsing to a handful.

### GATE RESULT (2026-09-07) — see DISCUSSION **D-17**

**Effective-N gate: ✅ CLEARED.** Median N_eff **12.5** (JJAS) / **11.9** (MAM), min 6.3, at the a-priori bandwidth.

**Skill gate: 🔴 NOT CLEARED.** LOYO over 20 seasons, RPS on ordered terciles vs unweighted climatology:

| Window | RPSS | 95% CI | Verdict |
|---|---|---|---|
| JJAS (concurrent, **diagnostic only**) | **+0.039** | [−0.179, +0.226] | spans zero — indistinguishable from climatology |
| MAM (pre-season, **operationally usable**) | **−0.249** | [−0.383, −0.136] | significantly **worse** than climatology |

Root cause, visible before fitting: Niño3.4 correlates **−0.444** with seasonal MCZ rainfall *concurrently* but **+0.054** *pre-season*. The usable predictor has no signal. **N = 20 seasonal events.**

- [x] **DECISION TAKEN:** probability reweighting retired. Stage 2 re-scoped to **disclosed analog evidence** alongside Stage 1's unchanged climatology. See build cycle below.

### Phase 2 build cycle 2 — Stage 2 re-scoped to analog evidence (2026-09-07)

- [x] **Extracted** `seasonal_analog_distances()` from `AnalogDownscaler.weights_for`; the retired downscaler now **delegates** to it — same extract-and-delegate pattern as `day_of_year_frequencies()`. Leakage safeguard now lives in exactly one place.
- [x] **Verified the extraction is byte-identical** — max weight diff **5.6e-17**; D-17's RPSS reproduces exactly (+0.0391 JJAS / −0.2491 MAM)
- [x] K=5 nearest historical seasons by **pre-season (MAM)** Niño3.4/DMI distance — the operationally honest predictor per D-17. K fixed a priori, not tuned (nothing to tune against — this path produces no score)
- [x] Outcomes are **observed** MCZ seasonal terciles read from the record, not modelled
- [x] **Disagreement surfaced explicitly** — `_summarise()` has no code path producing a central expectation when analogs are divided
- [x] Five new schema fields, structurally parallel to and separate from the trough-position evidence, so each advisory sentence is traceable to its mechanism
- [x] Per-analog **distances and effective N in the output**, not only the prose
- [x] Runtime assertions: `probabilities` / `ci_lower` / `ci_upper` / `effective_n` identical with and without evidence attached; both mechanisms attachable simultaneously without fusion
- [x] ARCHITECTURE.md Stage 2 rewritten; retired-downscaler subsections removed or marked superseded, not left alongside
- [x] **Stage 4 NOT started.**

Run: `python -m src.models.run_stage1_prior` · log `artifacts/stage1_prior_schema.txt`

**The headline finding:** across all 20 target years the analogs are **`divided` 19 times and `leaning` once — never unanimous.** That is the honest signature of a predictor correlating +0.054 with the outcome. The evidence mechanism works; what it truthfully reports, most of the time, is that pre-season ENSO/IOD did not determine the outcome.

### Phase 2 build cycle 3 — farmer-facing evidence filter (2026-09-07)

Resolves the open question above: `divided` analog evidence stays in the API, is withheld from the farmer.

- [x] Documented the exact `_summarise()` rule (quoted, not paraphrased): `unanimous` iff `modal_n == k`; `divided` iff `spans_extremes or modal_n <= k/2`; `leaning` otherwise. Record: 19 divided / 1 leaning (2018) / 0 unanimous.
- [x] Confirmed the evidence text is **fully templated** — 3 f-string branches + 1 optional clause, no free generation
- [x] `RegimePrior.seasonal_analog_advisory_visible` — derived property, True only for `leaning`/`unanimous`
- [x] `advisory_evidence_lines(prior)` — the single API↔farmer boundary; drops `divided` analog evidence, same as it skips a null `advisory_evidence`
- [x] `advisory_evidence_technical_view(prior)` — full view for demo/API, reports `seasonal_analog_suppressed_reason`
- [x] Runtime assertions: `divided`-case data stays populated in the schema; never appears in `advisory_evidence_lines`
- [x] Schema gains `seasonal_analog_advisory_visible` + `farmer_facing_evidence_lines`
- [x] ARCHITECTURE.md + TASKS.md updated. See DISCUSSION **D-19**.

- [ ] **Stage 4 not started.** When built, its advisory generator consumes `advisory_evidence_lines(prior)`, not the raw fields.

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

### Built 2026-09-07 — see DISCUSSION **D-20**. Run: `python -m src.models.run_stage4_decision`

- [x] Expected-loss comparison — **both branches probability-weighted** over Stage 1's full {active, break, transition} distribution. Enforced by construction: one `_expected_loss()` dot-product used by both branches, plus `_assert_is_expectation()` rejecting a constant loss vector or a non-distribution. No threshold token in executable code (AST-verified, docstrings stripped).
- [x] Uncertainty propagated — decision evaluated at the point estimate and both ends of a **marginal** sensitivity envelope (explicitly *not* a joint credible interval); `robust` flag when the recommendation holds across it
- [x] Adjustable θ with per-crop defaults — θ **reported, never used as a threshold**; the sensitivity sweep recomputes both expectations at each value
- [x] Advisory text generation — consumes `advisory_evidence_lines(prior)` only; **verified by AST inspection** that no raw evidence field is read (`raw evidence fields read directly: NONE`)
- [x] ~~🔴 **Trace ICAR sowing thresholds — STILL OPEN, and now CONTESTED.** The tracing attempt weakened the claim: D-2's 50–75 mm is untraced, a trade site attributes **100 mm** to ICAR-IISR citing no bulletin, and the two are incompatible. Primary ICAR-IISR host does not resolve from this network.~~ — **SOYBEAN DONE 2026-09-08 (D-29).** Primary bulletin retrieved from `icar.org.in`: ICAR-IISR, *Weekly Advisory for Soybean Farmers (4-10th July 2022)*, F.No. टेक 10-6/2022, 04.07.2022 — **100 mm**, cited with its scope limit (single-week operational advisory; the next week's does not repeat it). `sowing_rain_threshold_mm=100.0` for soybean.
- [ ] 🟡 **Trace groundnut (50 mm) and cotton (50–100 mm) thresholds — STILL OPEN.** Unchanged by D-29; both still untraced and still `None` in code. D-2's soybean 50–75 mm also remains untraced (plausibly a misattributed maize figure — D-29, hypothesis only).
- [ ] 🔴 **Source the crop economics — this is what actually gates `verified`.** `l_reseed`/`l_delay` are illustrative placeholders, unsourced for all three crops. `verified=False` everywhere, `uses_unverified_parameters=True`, disclosure rendered in the WhatsApp advisory and the risk SVG. D-29 sourced a *rainfall depth*, not rupees, so the flag correctly did not move. Needs locally sourced cost figures. See RESEARCH.md § Verified / Agronomic thresholds and D-29.
- [ ] Replace illustrative monetary values (L_reseed / L_delay) with locally sourced figures — currently **not sourced at all**, illustrative only

### Per-farmer profile layer built 2026-09-08 — `src/models/farmer_profile.py`, see DISCUSSION **D-26**. Run: `python -m src.models.run_stage4_profile`

- [x] `FarmerProfile` schema — crop, sowing status, growth stage, irrigation access, soil type, risk preference. Enums (out-of-range value fails at construction). Every profile is an **illustrative demo profile**, `profile_is_illustrative` cannot be set False, named "Demo profile A/B/…" — no farmer database exists.
- [x] Each field maps to a **LOSS-side** term only, never a probability: irrigation → `L_delay` factor; soil → `alpha` + `L_reseed` factors ("how a rainfall probability translates to sowing-readiness risk"); risk preference → effective-θ scaling via `L_reseed`; sowing status → **which decision applies** (pre-sowing = SOW/WAIT; already-sown = a different action set, *not modelled*, no recommendation emitted).
- [x] Profile → adjusted `CropEconomics` → **existing `decide()`**. No second scoring function. `_assert_is_expectation()` therefore runs on every profile path unchanged — verified across the full 27-combo grid **on both crops' base economics**; a collapsed-branch adjustment is **rejected** by the guard, a zeroed multiplier is caught one layer earlier with a "fix the table, don't special-case" message.
- [x] Stage 1 immutability — `DecisionResult.probabilities == prior.probabilities` byte-identical across all 27 profiles (× both crops); AST check confirms no probability field is reachable from the adjust/decide core.
- [x] All-reference profile reproduces the base `decide()` bit-for-bit (every multiplier's reference level is exactly 1.0) — soybean and cotton.
- [x] Advisory evidence still via `advisory_evidence_lines(prior)` only — AST-verified for `farmer_profile.py` (`raw evidence fields read directly: NONE`); evidence lines asserted identical across base / Profile A / Profile B.
- [x] Worked example: two illustrative profiles, **same date, same regime probabilities, opposite recommendations** — A (soybean / rainfed / black soil / risk-tolerant) → SOW (E[sow] 4,093 < E[wait] 4,888, but `robust=False`); B (cotton / assured irrigation / sandy / risk-averse) → WAIT (E[sow] 24,357 ≫ E[wait] 4,481, `robust=True`). Both expected losses shown term-by-term. Control: B's fields on soybean still → WAIT, so the flip is the profile not the crop. Log `artifacts/stage4_profile_example.txt`.
- [ ] Post-sowing action set (protect standing crop vs hold) — **not modelled.** `growth_stage` is carried in the schema for it; `decide_for_profile` declines rather than misapplying the pre-sowing model. Would need stage-dependent value-at-risk + protection-cost/effectiveness params, all currently unsourced.
- [ ] Profile multiplier tables are **illustrative**, not calibrated to surveyed farm economics — same standard as the D-20 crop-loss thresholds.
### Delivery layer built 2026-09-08 — `src/delivery/`, see DISCUSSION **D-21**. Run: `python -m src.delivery.run_delivery_demo`

- [x] Advisory text generation — `src/delivery/advisory.py`; combines recommendation + both expected losses + `advisory_evidence_lines(prior)`; **AST-verified** it imports the boundary function and reads no raw evidence field; farmer-facing ICAR disclosure rendered in the message body when `uses_unverified_parameters` (D-20), not only the technical view
- [x] Twilio WhatsApp Sandbox integration — `src/delivery/whatsapp.py`; env-var credentials, `dry_run=True` default, refuses to go live without explicit `dry_run=False` **and** all three env vars; sandbox join flow documented; **nothing sent** in the build
- [x] **24-h WhatsApp session window handled as an explicit precondition** (D-21). `send()` takes `recipient_in_session` (default False → dry run); Twilio out-of-window errors surfaced. Demo path (a) = farmer joins/messages the sandbox; production path (b) = approved Meta template, **scoped not built**.
  - [ ] Production: approved Meta message template + WhatsApp Business API onboarding (path b)
- [~] **Regional language output — NO LANGUAGE IS SPECIFIED IN ANY DOC.** All references ("regional language" / "their own language" / "vernacular") are generic. English is the verified default and send default. Hindi provided as a **fully-templated machine-generated stub** with an UNVERIFIED banner; `WhatsAppSender` refuses to send it without an explicit override.
  - [ ] 🔴 **BLOCKING pre-demo (AGENTS.md):** decide the actual target language(s); have a native speaker review every template before any real send
- [x] Risk display — `src/delivery/risk_display.py`; **single regional indicator, one uniform colour, NOT a choropleth**; "regional estimate, not resolved to individual blocks or villages" baked into both the text card and the SVG image
- [ ] ~~Block-level choropleth risk map~~ — **not built by design.** Stage 1 has no per-block number; a choropleth would show spatial variation that doesn't exist. Marked aspirational in ARCHITECTURE.md. Revisit only if a block-resolved forecast is ever built.

---

## Phase 5 — Demo

### Built 2026-09-08 — `src/demo/`, see DISCUSSION **D-22**. Run: `python -m src.demo.server` (live) / `python -m src.demo.run_demo` (headless check)

- [x] Pre-baked demo case — **2018-07-15, soybean, fixed** (`src/demo/case.py`). MCZ-regional, not a district (Stage 1's actual scale). The one `leaning` analog year, so both evidence lines are farmer-facing. Only `l_reseed` varies.
- [x] **Live θ slider** — stdlib `http.server`; every slider event → `/api/decide` → real `decide()` → `_expected_loss()`. No lookup table. Verified over HTTP by `src/demo/smoke_server.py`. Three real transitions shown: θ≈0.77 sow robust→fragile, **θ≈0.95 SOW→WAIT** (the recommendation flip — D-20's "θ≈0.75" was the *robustness* boundary, corrected in D-22), θ≈1.14 wait fragile→robust.
- [x] **Both effective-N figures on-screen at all times, labelled separately, never merged** — Stage 1 `20 monsoon seasons` (year count) vs Stage 2 `4.99 effective analog seasons` (entropy concentration, explicit "NOT a confidence"). *(Task said ~3.8; that's the 2019 value — 2018's analogs are closer, so 4.99. D-22.)*
- [x] Old "backtest number" slot → **Stage 1 base rate + block-bootstrap CI**, exact advisory wording ("based on 20-year averages… not a forecast for this year"), explicit *"no accuracy/skill figure is shown"* note (D-14–D-17). **No manufactured skill number.**
- [x] Full advisory rendered exactly as Phase 4b built it — both evidence lines, ICAR disclosure in the message body, single-region risk SVG with "not resolved to individual blocks" baked into the image.
- [x] **Rehearse-until-flawless (headless):** `run_demo --repeat 5` → 5 identical payload hashes, ~26 s each, zero manual intervention, no live IMD call (asserts the bulletin cache).
- [ ] **Before starting the real demo server, kill any process already bound to the demo port (8765).** A stale `src.demo.server` instance from an earlier session silently swallowed requests and made freshly-added routes 404 (D-27) — cheap to check first (`Get-CimInstance Win32_Process -Filter "Name='python.exe'"` on Windows, or `lsof -i :8765`), expensive to discover live.
- [x] **Live-send rehearsal (real WhatsApp message):** `python -m src.delivery.rehearse_live_send --confirm-live-send` — standalone, refuses to run without the flag, never in the regression suite. Sends the real 2018 advisory to `VARSHASANKET_DEMO_TO`; checks `SendResult.status`; on a 63015/63016 session-window failure prints the plain-language opt-in fix. **Run once, a few minutes before presenting** (D-21). Needs `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` / `VARSHASANKET_DEMO_TO`.
- [x] **Scope held:** one case, one slider variable. No second district, no crop dropdown, no date picker.

### Per-farmer profile screen built 2026-09-08 — `/profiles` on the SAME server, see DISCUSSION **D-27**. Run: `python -m src.demo.server` → `http://localhost:8765/profiles` / headless: `python -m src.demo.run_profiles_demo --repeat 5`

- [x] Farmer selector — **four illustrative demo profiles**, clearly labelled not real users: A (soybean/rainfed/black soil/risk-tolerant, D-26's `PROFILE_A`) → SOW, fragile; B (cotton/assured irrigation/sandy soil/risk-averse, D-26's `PROFILE_B`) → WAIT, robust; C (soybean/partial irrigation/black soil/risk-tolerant — same as A but for irrigation) → WAIT, the closest-to-tied margin in the whole 81-combo pre-sowing grid, fragile; D (soybean, already sown, germination) → no SOW/WAIT recommendation.
- [x] Extends `src/demo/server.py` in place — **no parallel app.** New `/profiles` route + `/api/profile_decide` endpoint; the original `/` screen is unchanged; both share one cached `DemoCase`, no live IMD call.
- [x] Selecting a profile calls the real `decide_for_profile()` against the SAME 2018-07-15 prior and renders the full advisory — recommendation, both `E[loss]`, `advisory_evidence_lines` output, the ICAR/illustrative-cost disclosure — nothing simplified from Phase 4b.
- [x] **Composition finding applied directly, not left open:** risk preference lives ONLY inside the selected farmer profile; the `/profiles` screen has NO theta/l_reseed slider of any kind. The slider stays on `/`, a different screen — no double-counting risk.
- [x] Base vs effective loss inputs shown side by side, explicitly labelled ("base (crop default)" vs "effective (post multiplier)"), never ambiguous which is which.
- [x] Confirmed end-to-end for all four profiles with no manual intervention; `run_profiles_demo --repeat 5` gives an identical payload hash across all 5 runs (same determinism standard as Phase 5's `run_demo.py`). *(Superseded 2026-09-08 by the full sweep below — free selection made "repeat four fixed cases" the wrong shape of test. D-28.)*

### Free profile selection added 2026-09-08 — same `/profiles` screen, see DISCUSSION **D-28**. Sweep: `python -m src.demo.run_profiles_demo`

- [x] **Free selectors for crop, irrigation, soil, risk** — options generated by `profile_option_values()` from `FarmerProfile`'s enums and `CROP_DEFAULTS` and served via `/api/profile_options`. The page holds **zero quoted schema value literals** (asserted every run by `check_no_schema_literals_in_page()`), so it cannot offer a value the schema does not define.
- [x] **No new reachable code path:** the 4 decision-bearing selectors give exactly the **81 pre-sowing combinations** already dumped in D-27, whose per-crop 27-combo slices are what `check_guard_covers_profile_paths` drives through `_assert_is_expectation()` (D-26). Sown combinations short-circuit in `decision_applicability()` before `adjusted_economics()`/`decide()` are called at all.
- [x] **Sowing status is its own control; growth stage appears only when sown** — mirroring `__post_init__`'s coherence rule exactly (pre-sowing carries `NOT_APPLICABLE`, which per D-26 does nothing in that path, so the UI shows no stage selector at all). **Enforcement stays in `FarmerProfile.__post_init__`** — the UI mirrors, never replaces it; a rejected combination returns HTTP **400 with a plain-language reason**, never a raw exception or traceback.
- [x] **Region: a static label, not a disabled dropdown** — "monsoon core zone (single region)" plus the reason there is nothing to break it out into (Stage 1 computes one MCZ-mean base rate; D-16). A disabled selector would still promise a choice that is not coming; a label does not.
- [x] **The four presets are unchanged and still on the same code path** — `?profile=<key>` still resolves through `build_profile_payload()`. Clicking a preset now populates the free-form controls from the preset's own field values (served by `demo_preset_summaries()`, so the UI holds no copy of them) and submits through the ordinary path. Both resolvers converge on `_payload_for_profile()` — the single `decide_for_profile()` call site.
- [x] **Full-sweep verification replaced the fixed-case determinism check** (D-28): every combination the schema can express, driven through the **real HTTP endpoint** on an ephemeral port (so a stale server on 8765 cannot mask it). **648 combinations swept: 81 scored (3 SOW / 78 WAIT), 243 no-decision (already sown), 324 refused with a clean validation message, 0 failures, 0 tracebacks reaching the client.** The 3-SOW/78-WAIT split independently reproduces D-27's grid dump. Each preset was also confirmed byte-identical to its free-form equivalent — proof there is one decision path, not two. Log: `artifacts/demo_profiles_endtoend.txt`.

---

## Ongoing / cross-cutting

- [ ] Correct **"120 million"** → **93.09 million agricultural households** everywhere it appears (slides, docs, scripts)
- [ ] Keep `docs/RESEARCH.md` updated as new claims enter
- [ ] Log every architectural decision in `docs/DISCUSSION.md`

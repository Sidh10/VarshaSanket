# DISCUSSION — Decision Log & Open Questions

Append-only. Newest entries at the bottom of each section. Read bottom-up for freshest state.

---

## Closed decisions

### D-A: Analog ensemble over end-to-end deep learning — **CLOSED**
Direct regression from indices to rainfall hedges toward the mean (double-penalty problem), smoothing away the local extremes and true dry spells that drive the farmer's decision. Analogs sample real observed outcomes, preserving realistic variance by construction.

### D-B: Gradient boosting over Hierarchical GNN for Stage 3 — **CLOSED**
A GNN needs multi-GPU training for marginal gain on this task. Right-sizing is a defensible design position. *(Note: an AI research pass recommended a GNN while simultaneously rating GNN buildability "Medium-Low" in its own comparison table — an internal contradiction. Rejected.)*

### D-C: Expected-loss comparison over classic cost-loss threshold — **CLOSED**
`P > C/L` covers *protective* action. Sowing is the *risky* action. Both branches carry probability-weighted loss. Any worked example with one probabilistic side and one flat number is wrong.

### D-D: Continuous-distance analog matching over exact regime matching — **CLOSED**
Arithmetic: ~60 historical break events per block; exact joint matching on ENSO+IOD+MJO can leave 2–5 analogs. Weighted distance keeps the ensemble usable; effective N is surfaced so sparse cases are visible rather than hidden.

### D-E: Leave-one-year-out over single test year — **CLOSED**
IndiaWeatherBench's 2019 test split is designed for 6-hourly weather (~1,500 samples). Seasonal event prediction gets ~1 onset from one year. LOYO gives ~20 onsets / ~60 breaks.

### D-F: Stage 1 forecasts, Stage 2 downscales — **CLOSED**
Kept separate deliberately. Stage 1 maps indices → future regime (the only part with real multi-week skill). Stage 2 is a lookup conditioned on that regime, never a forecast. Merging them would conflate prediction with interpretation and lose defensibility.

### D-G: Positioning as "last mile," not "better forecast" — **CLOSED**
Research confirmed active/break forecasting is operational at IITM for a decade, analog methods are published for Indian precipitation, and ML post-processing of Indian S2S forecasts is an active field. Claiming novelty on the forecast itself would be caught. The genuine claim is block-scale probability + economic decision layer + end-to-end delivery.

### D-H: Impact figure corrected — **CLOSED**
"120 million farm households" was unsourced and inflated. Authoritative figure: **93.09 million agricultural households** (NSO 77th Round, 2018–19); 101.98 million operational holdings. Correct everywhere.

---

## Open questions

### D-1: No domain expert for verification sanity-checking — **OPEN, MITIGATED**
Nobody on the team can independently recognise a leaked backtest or a disguised-climatology result. Coding agents can build the pipeline but have no particular reason to catch a methodologically-invalid-but-plausible number.

**Mitigation in place:** `docs/VERIFICATION.md` exists precisely to be followed *mechanically* rather than by judgment. The evaluation agent has explicit authority to block a number.

**Still open:** whether anyone reviews the evaluation agent's own output. Consider assigning one person to own this and read `docs/VERIFICATION.md` closely enough to spot a violation.

### D-2: ICAR sowing thresholds unverified — **OPEN**
Per-crop thresholds (soybean 50–75mm, groundnut 50mm, cotton 50–100mm) came from AI-generated research and are plausible/consistent, but not traced to a specific published bulletin. **Must be traced before any number is hardcoded into Stage 4** — the "every recommendation is traceable to an official source" claim depends on it.

### D-3: Ground truth is coarser than target output — **OPEN, DISCLOSE**
Stage 3 calibrates against IMD gridded rainfall at 0.25° (~25km), while target output is block-level. We're correcting toward a coarser reference. Real methodological caveat. Currently handled by disclosure rather than solution. Is there a finer ground-truth source worth pursuing?

### D-4: Gate C not yet done — **OPEN, BLOCKING QUALITY**
No real farmer/extension officer conversation yet. This is the single highest-value action available and it has been open since early in the project. It's what makes the pitch load-bearing rather than merely well-argued.

### D-5: Village-scale claim vs 12km data — **OPEN, DISCLOSE**
The PS title says "Block/Village Scale." IMDAA is 12km; a village is 1–5km. Current position: block-level is defensible, village-scale is a stretch goal, and we say so proactively. Watch that this framing doesn't read as quietly redefining the problem to something easier.

---

### D-6: IndiaWeatherBench channel count — DATA.md says 39, dataset has 43 — **CORRECTION, verified 2026-09-07**
`DATA.md` and `RESEARCH.md` both state "39 channels" (cited to Nguyen et al. 2025, arXiv:2509.00653). The actual HuggingFace dataset (`tungnd/IndiaWeatherBench`) exposes **43** weather fields per HDF5 timestep:
6 single-level (TMP, UGRD, VGRD, APCP, PRMSL, TCDCRO) + 5 pressure-level fields × 7 levels [925, 850, 700, 600, 500, 250, 50 hPa] (HGT, RH, TMP_prl, UGRD_prl, VGRD_prl = 35) + 2 static (MTERH, LAND) = 43, plus a `time` scalar.
The paper reconciles both numbers: *"a total of 43 distinct channels"* in the curated dataset, but models are *"train[ed] using a consistent set of 39 input channels"* (43 minus static/excluded fields — exact split is in the paper, not yet transcribed here).
**Fix:** DATA.md should read "43 channels (39 used as ML model input)". Flagged inline in DATA.md pending sign-off. Not load-bearing for our pitch, but it's the kind of number that ends up on a slide. Note (see D-11): the authors' own GitHub README also says "39 channels" over a category list that sums to 43 — the ambiguity is upstream, not ours.
Also confirmed and unchanged: 0.12° / ~12 km, 256×256, 6-hourly, 2000–2019, train 2000–2017 / val 2018 / test 2019.

### D-7: "NOAA CPC" is the wrong provider for DMI and RMM — **CORRECTION, verified live 2026-09-07**
`DATA.md` bundles ENSO (Niño3.4), IOD (DMI), and MJO (RMM1/RMM2) under one row: *"NOAA CPC | Daily time series | Free, no registration."* Two of the three are not CPC products, and "daily" is wrong for two of the three. All URLs below were hit live and returned data on 2026-09-07:

| Index | Real source (verified live) | Cadence | Notes |
|---|---|---|---|
| ONI (3-mo Niño3.4 anomaly) | `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt` | monthly (rolling seasons) | CPC ✅, 1950–present |
| Weekly Niño SST (1+2, 3, 3.4, 4) | `https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for` | **weekly** | CPC ✅, OISST, from Sep 1981 |
| Monthly Niño SST/anom (ERSSTv5) | `https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii` | monthly | CPC ✅, 1950–present |
| Detrended Niño3.4 | `https://www.cpc.ncep.noaa.gov/data/indices/detrend.nino34.ascii.txt` | monthly | CPC ✅ |
| DMI / Dipole Mode Index (IOD) | `https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data` | **monthly** | **NOAA PSL, not CPC.** HadISST-based, 1870–present, file marked "Preliminary". CPC does not publish DMI. |
| MJO RMM1 / RMM2 (Wheeler–Hendon) | `https://www.bom.gov.au/clim_data/IDCKGEM000/rmm.74toRealtime.txt` | **daily** | **Australian Bureau of Meteorology, not NOAA.** 1974–realtime; cols: year, month, day, RMM1, RMM2, phase, amplitude. |
| CPC MJO index (alternative) | `https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_mjo_index/proj_norm_order.ascii` | pentad | CPC's own MJO index is 10 longitude-band 200 hPa velocity-potential indices — a *different quantity* from RMM1/RMM2, not a drop-in substitute. |

- **No endpoint was fabricated.** One plausible guess — `https://psl.noaa.gov/data/correlation/dmi.data` — returned **HTTP 404** and is reported as dead, not silently swapped.
- **Impact on Phase 1:** the t−30→t lag-feature plan assumes daily series. Only RMM is daily. Niño3.4 lags come from a weekly series (OISST) or monthly (ERSST); DMI lags are monthly. Feature construction needs to handle mixed cadence (resample/forward-fill or use monthly lags) rather than assuming one daily frame.
- **Fix:** split the DATA.md row into three sources with correct providers and cadences. Flagged inline pending sign-off.

### D-8: IndiaWeatherBench has no server-side subset — 3 monolithic archives — **CORRECTION, verified 2026-09-07**
`DATA.md`: *"IndiaWeatherBench is large (216 GB full; subset before pulling)."* There is no partial-download / subsetting mechanism on the HF repo. It is exactly three files:

| File | Size | Format |
|---|---|---|
| `climatology_2000_2017.zarr.zip` | 9.1 GB | zipped zarr v2, day-of-year 6-hourly climatology (1460 steps), 11 vars |
| `indiaweatherbench_h5.zip` | 105.84 GB (98.57 GiB) download; ~330 GB extracted | 29,220 HDF5 files, one per timestep, pre-split train/val/test (+ `norm_params.json`). DEFLATE ~3.12× — see D-12 |
| `indiaweatherbench_raw.zarr.zip` | 101 GB | zipped zarr v2, full raw fields |

The "216 GB" ≈ h5 + raw zarr downloads combined (~207 GB); extracted footprint is much larger. **Workaround demonstrated and working:** HTTP range-reads into the remote zip's central directory (`fsspec` HTTP filesystem + stdlib `zipfile`) allow pulling a single `.h5` timestep (~11 MB) or a single zarr chunk without downloading the archive. The `src/data/` loader should wrap this pattern; a naive `hf_hub_download` pulls 100+ GB.

### D-9: IndiaWeatherBench license is CC-BY-NC-SA-4.0 (non-commercial) — **DISCLOSE**
`DATA.md` lists access as "HuggingFace, free". The license is **CC BY-NC-SA 4.0**: non-commercial, share-alike; commercial use requires written permission from `director@ncmrwf.gov.in`, and publications must be sent to the same address. IMDAA itself (the underlying reanalysis) carries NCMRWF terms. Fine for a hackathon prototype and research, but it constrains any "productize this" language in the pitch — worth stating proactively (Rule 4) rather than having a sponsor-side judge raise it.

### D-10: docs live at repo root, not `docs/` — **MINOR**
`CLAUDE.md` and `DATA.md` reference `docs/RESEARCH.md`, `docs/VERIFICATION.md`, etc., but all markdown files are currently at the repository root. `src/` does not exist yet. Not fixing paths unilaterally — noting so the next agent either creates `docs/` or updates the references, consistently.

### D-11: Is `tungnd/IndiaWeatherBench` the paper authors' repo? — **CLOSED, confirmed 2026-09-07**
Question raised: does the HF repo identify itself as the authors' mirror, or is maintainership unconfirmed? Checked directly, findings (not inferred):

- **HF repo card / metadata**: does **not** self-identify. No author names, no paper citation, `citation` field null, no "official" language. Just a plain dataset card (license, tags, variable list). Created 2025-09-06, one day before arXiv:2509.00653; owner HF username `tungnd`, HF fullname **"Tung Nguyen"**, member of org `mint-multix`.
- **The paper (arXiv:2509.00653v1)**: authors are Tung Nguyen, Harkanwar Singh, Nilay Naharas, Lucas Bandarkar, Aditya Grover (all UCLA); corresponding `tungnd@cs.ucla.edu`. Data & Code Availability section says *"Code is available at https://github.com/tung-nd/IndiaWeatherBench"* and *"We publish both versions at Google Drive"* (a Drive folder link). **The paper does not mention HuggingFace at all.**
- **The authors' GitHub repo** `github.com/tung-nd/IndiaWeatherBench` (the one the paper cites): its `README.md` carries a badge — `[![HuggingFace](...)](https://huggingface.co/datasets/tungnd/IndiaWeatherBench)` — linking directly to the HF repo in question.

**Conclusion:** The HF repo **is** the authors' distribution point, confirmed by transitive link: paper → cited GitHub repo → 🤗 badge → this HF repo, plus matching identity (`tung-nd` / `tungnd` / "Tung Nguyen", paper's corresponding author). It is **not** independently forgeable prior-art of the kind Rule 1 guards against. Residual caveat, stated for honesty: the confirmation is transitive, not a direct statement on the HF card, and the paper's *named* dataset location is Google Drive. If a reviewer challenges data provenance, cite the GitHub README badge, not the HF card alone.
- Side finding: the GitHub README **also** says "39 channels" and then lists categories summing to 43 — so the "39 vs 43" confusion in D-6 is an inconsistency inherited from the authors' own docs, not one we introduced. HF card says "43".

### D-12: h5 archive size — 11.3 MB × 29,220 ≈ 330 GB, but archive is 106 GB — **CLOSED, reconciled 2026-09-07**
The gap is compression, and the earlier extrapolation mixed compressed and uncompressed figures.

- **Actual listed size of `indiaweatherbench_h5.zip`** (HTTP `Content-Length`, read directly): **105,835,768,154 bytes = 105.84 GB = 98.57 GiB.** The "106 GB" in D-8 was right.
- Archive holds **29,220 `.h5` files** (+ 4 dir entries + one `indibench_h5/norm_params.json`, 23,711 bytes — normalization params, a bonus find). Split: 26,300 train / 1,460 val / 1,460 test.
- Every `.h5` member is **11.29 MB uncompressed** and stored **DEFLATE-compressed** inside the zip (`compress_type=8`), averaging **~3.12×**. Compressed per file ≈ 3.6 MB.
- 29,220 × 11.29 MB = **329.9 GB uncompressed**; sum of compressed member sizes = **105.8 GB** → matches the archive. Ratio 329.9 / 105.8 = 3.12×.
- **The error** in the "~330 GB" estimate: `ZipInfo.file_size` (and the bytes you get after extraction) is the *uncompressed* size; comparing that total against the *compressed* archive size. Both numbers are real — 106 GB is the download, ~330 GB is the on-disk footprint if you extract the whole thing.
- **Implication for `src/data/`**: extracting the full h5 archive needs **~330 GB free**, not 106. The range-read path (D-8) sidesteps this: ~3.6 MB over the wire per timestep, decompressed locally to 11.3 MB, nothing extracted to disk.

### D-13: IOD/DMI source — NOAA PSL confirmed, BOM claim corrected — **CLOSED**
Earlier session (pitch Q&A prep) stated IOD source as "Australian Bureau of Meteorology." Verified false as a raw-data claim: BOM publishes an interpretive page but the actual numeric series is NOAA-computed in every form checked (PSL/HadISST, CPC/ERSSTv5, or OSMC/Reynolds-OISST via NOAA-ESRL, the last one being what BOM's page links to). No BOM-served ASCII DMI file exists.
Decision: use NOAA PSL (`dmi.had.long.data`) — already verified live, ASCII, longest stable record. Trade-off disclosed, not hidden: DMI is monthly cadence vs. weekly Niño3.4 and daily RMM, so t-30→t lag features treat DMI as near-constant within most windows.
Action: pitch script / Q&A bank line "IOD source: Australian BOM" needs correcting to "NOAA PSL, Dipole Mode Index, HadISST-based" before next rehearsal.

*Implementation note (2026-09-07):* `src/data/indices.py` implements exactly this — DMI from NOAA PSL, and RMM1/RMM2 from BOM (RMM **is** genuinely a BOM product; D-13 concerns DMI only, and D-7's RMM→BOM attribution stands). The mixed-cadence consequence D-13 predicted is visible in the built features: `dmi_d30` is near-constant by construction. Confirmed, not assumed.

### D-14: Phase 1 gate — Stage 1 Regime Forecaster **FAILS** to beat climatology — **OPEN, BLOCKING**

**Run:** `python -m src.eval.run_phase1`, 2026-09-07. Full log `artifacts/phase1_run_log.txt`, machine-readable `artifacts/phase1_stage1_validation.json`, per-year Brier `artifacts/phase1_*_per_year_lead*.csv`.

#### Verdict

**GATE NOT CLEARED.** Stage 1 does not beat climatological regime frequency at any lead, under either season definition.

Brier Skill Score vs day-of-year climatology (higher is better; 0 = no better than climatology). Leave-one-year-out over all 20 years, 95% CI block-bootstrapped **over years** (2000 resamples) because days inside a monsoon spell are strongly autocorrelated and a day-level CI would be dishonestly narrow.

**JJAS (primary):**

| Lead | n | BSS vs clim | 95% CI | BSS vs persistence | seasonal-only | logistic diag |
|---|---|---|---|---|---|---|
| 1 wk | 2180 | −0.0342 | [−0.0724, +0.0099] | +0.4994 | −0.0226 | −0.0101 |
| 2 wk | 2040 | −0.0144 | [−0.0561, +0.0330] | +0.4985 | −0.0259 | −0.0377 |
| 3 wk | 1900 | −0.0569 | [−0.1052, −0.0005] | +0.4925 | −0.0269 | −0.0696 |
| 4 wk | 1760 | +0.0090 | [−0.0410, +0.0609] | +0.5418 | −0.0265 | −0.0404 |

**Jul–Aug (strict Rajeevan) sensitivity:**

| Lead | n | BSS vs clim | 95% CI |
|---|---|---|---|
| 1 wk | 980 | −0.0055 | [−0.0426, +0.0465] |
| 2 wk | 840 | −0.0119 | [−0.0732, +0.0528] |
| 3 wk | 700 | −0.0785 | [−0.1912, +0.0050] |
| 4 wk | 560 | −0.0910 | [−0.2151, +0.0129] |

The two definitions **agree** — there is no favourable arm to be tempted by.

#### Event counts (VERIFICATION.md requires these with any score)
JJAS labels over 20 years: **233 active days / 56 spells**, **225 break days / 40 spells**, 1982 transition days.
At the 2-week target: 148 active days, 182 break days, 1710 transition; 28 active spells, 27 break spells.
Note this is **fewer than the "~60 break events" in CLAUDE.md Rule 2** — that figure is ARCHITECTURE.md's *per-block* count for Stage 2 analog pooling (20 yr × ~3/yr). MCZ-wide Rajeevan spells are a different, rarer object. The two numbers are not in conflict but must not be used interchangeably.

#### Why this is a real negative and not a broken harness
- **Not a capacity/overfitting artefact.** A regularised multinomial logistic reference model, run through the identical folds, is *also* negative at every lead (−0.010 to −0.229). If the GBM were merely over-parameterised for ~2k samples, the linear model would have shown positive skill. It does not. The predictors do not carry usable signal for this target.
- **Not an untuned-model artefact.** Capacity is selected by inner GroupKFold over training years only (`RegimeForecaster._select_capacity`). Pinning arbitrary hyperparameters would have understated the ceiling; it was not done.
- **Climatology-collapse test is informative in the opposite direction.** The seasonal-only model (day-of-year features alone) scores ≈ −0.026 at every lead. The full model is *worse than* seasonal-only at 1 and 3 weeks — adding the teleconnection indices actively degrades the forecast. This is the signature of fitting noise, not of a model quietly reproducing climatology.
- **"BSS vs persistence = +0.50" is not a result.** Hard one-hot persistence is a terrible *probabilistic* baseline; beating it is trivial and means nothing. It is reported only because VERIFICATION.md requires it. **Do not put this number in a slide** — it is exactly the kind of impressive-looking figure with no content that this project's rules exist to catch.
- **Pipeline sanity is independently evidenced.** The label builder reproduces the known July 2002 monsoon failure as two long break spells (6–16 Jul, 23–31 Jul) without being told about it; z is properly standardised (mean 0.002, SD 0.979); H500 ≈ 5855 gpm, T850 ≈ 295.7 K and the north-minus-south T850 gradient is +1.55 K, all physically correct. The machinery works; the signal is absent.
- **Label leakage quantified, not assumed:** relabelling leave-one-year-out changes 45/2440 days (1.84%) in JJAS, 16/1240 (1.29%) in Jul–Aug. Too small to explain the result.

#### What this does and does not mean
It does **not** mean subseasonal active/break forecasting is impossible — IITM's ERPAS does it operationally (RESEARCH.md, Sahai et al. 2013). It means **this particular predictor set** — RMM1/RMM2 + Niño3.4 + DMI trajectories plus three coarse MCZ-mean scalars — does not resolve MCZ regime at 1–4 weeks. ERPAS uses a dynamical ensemble initialised from the full 3-D atmospheric state; we used ~41 scalars. In hindsight the ARCHITECTURE.md claim that this stage carries "genuine predictive skill" from MJO phase propagation was **asserted, never tested**, and it is now tested and unsupported.

#### Options for reassessment (Phase 1R — not yet decided, decide before any further build)
1. **Richer predictors.** Spatial structure rather than area-means: EOFs of H500/T850/wind over the region, OLR, and 20–60-day BSISO-filtered fields. This is the most likely source of real signal and is a genuine build, not a tweak. Risk: Michaelsen — any predictor screening must stay inside folds.
2. **Change the target.** MCZ-wide 3-class regime may be the wrong object. A binary "break onset within the next N days" target, or per-block rainfall tercile, may be both more forecastable and more decision-relevant.
3. **Accept and re-position.** CLAUDE.md's stated positioning is already "the last mile between existing forecasts and a farmer's decision. **We are not claiming to out-forecast IMD or IITM.**" That positioning survives this result *if* Stage 1 consumes an external regime forecast (IITM ERPAS-style) rather than generating one — but ERPv2 access is restricted (DATA.md), which is why the self-contained design was chosen in the first place. This is the honest fallback and it needs a decision, not a workaround.
4. **Do not** proceed to Stage 2 on the current Stage 1. TASKS.md is explicit, and D-14's own numbers show downstream stages would be conditioning on noise.

**Whatever is chosen, the pitch cannot currently claim Stage 1 skill.** This is a genuinely defensible thing to present — "we built the load-bearing stage, tested it honestly against climatology across 20 years, and it failed our own gate, so we stopped" demonstrates exactly the methodological discipline VERIFICATION.md was written to enforce. Bürger (2019) documents operational systems that reported inflated skill because nobody ran this test.

### D-15: IMD Extended Range bulletin recon — **RECON COMPLETE, schema decision OPEN**

Recon for the D-14 reassessment (Option 3: consume an external regime forecast rather than generate one). **No code written, nothing in `src/`.** Evidence: `artifacts/d15_bulletin_samples.txt`. All probes run live 2026-09-07.

#### Correction to the starting premise
The task described `internal.imd.gov.in/press_release/...` as "already confirmed live for 2026." Verified before use, and the directory itself is **not** open:

```
GET https://internal.imd.gov.in/press_release/   ->  HTTP 200
     body: <title>No ACCESS</title> "You are not authorised to access here."
```

**A status-code-only check reports this as live.** It is not — the listing is blocked. *Individual* PDFs under that path do serve (verified across all six years), so the path works only if you already know the exact filename. Filenames come from the archive page, not from the directory.
Also probed and **dead**: `mausam.imd.gov.in/responsive/pressReleaseArchive.php` → 404; `mausam.imd.gov.in/imd_latest/contents/press_release.php` → 500. Neither exists; do not cite either.
The archive that *does* work: **`https://internal.imd.gov.in/pages/press_release_mausam.php`** (3.88 MB, 3,326 PDF links, 2020–2026).

#### 1. How far back the archive actually goes

**Answer: 6 monsoon seasons (2021–2026) of Extended Range bulletins. Not 20.**

254 "Current Weather Status and Extended Range Forecast" bulletins, weekly, year-round:

| Year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| All bulletins | 20 | 46 | 49 | 50 | 52 | 37 (partial yr) |
| **JJAS only** | **13** | **18** | **18** | **18** | **18** | **14** |

**99 JJAS bulletins total; 97 downloaded successfully** (2 failed: 2025-09-25, 2026-06-04). Series starts mid-2021 — there is no 2020 or earlier ERF bulletin in the archive.

#### 2. What `extendedrangeforecast.php` actually serves — **images, not data**
It is a **navigation page**, not a data page. Its content is PNG/GIF maps from an `ERPAS/` directory, with the current cycle date hardcoded into the HTML each week:

```
https://mausam.imd.gov.in/ERPAS/rfactual_MME2026090200.png
https://mausam.imd.gov.in/ERPAS/rfanom_MME2026090200.png
                          tminactual_/tminanom_/tmaxactual_/tmaxanom_/wind850_/windano850_
                          prec_wind850hPa_MME_20260902.gif   (animations)
```

**It is NOT more machine-readable than the bulletins — it is considerably less.** No tercile tables, no probability values, no numeric fields: colour-mapped rainfall/temperature anomaly maps that would need image processing to read, and reading a category off a colour ramp is exactly the kind of brittle step that produces a confident wrong number.

**And it is shallower.** ERPAS PNG retention, scanned day-by-day across five monsoon seasons:

| Year | 2026 | 2025 | 2024 | 2023 | 2022 |
|---|---|---|---|---|---|
| Weekly cycles reachable | 14 | 15 | **0** | **0** | **0** |

2024 and earlier are **404 under every filename variant tried** (`_MME{date}00`, `_MME{date}`, `_MME_{date}00`, `_MME_{date}`, plus the `.gif` products) — genuinely absent, not a renaming. **ERPAS graphics give 2 seasons; the bulletins give 6.** The bulletins are the deeper and more parseable source. ERPAS images are not worth pursuing.

#### 3. Is the MJO / trough language consistent, or was the one bulletin unusual?

**Consistent.** Measured over all 94 JJAS bulletins that parsed, with a whitespace-tolerant parser:

| Field | Rate | Note |
|---|---|---|
| Text layer extracts (not scanned) | **100%** (94/94) | no OCR needed |
| MJO mentioned | 99% (93/94) | |
| MJO **phase** (1–8) | 99% | |
| MJO **amplitude** (3 bins) | 96% | |
| Trough *forecast* sentence present | 83% | |
| **Trough forecast with explicit N/S/near-normal position** | **64%** (60/94) | *the real ceiling* |
| Word **"break"** anywhere | **1%** (1/94) | only 2023-08-31 |

The MJO sentence is near-templated across all six years:
> 2021: "The Madden Julian Oscillation (MJO) Index currently lies in **Phase 2** with amplitude **more than 1**."
> 2022: "The Madden Julian Oscillation Index (MJO) currently lies in **phase 5** with amplitude **less than 1**."
> 2023: "The Madden–Julian Oscillation (MJO) Index is currently in **Phase 1** with amplitude **less than 1**."
> 2024: "The Madden Julian Oscillation (MJO) index is currently in **phase 1** with amplitude **close to 1**."
> 2025: "Madden Julian Oscillation (MJO) is currently in **phase 8** with an amplitude **close to 1**."
> 2026: "Madden-Julian Oscillation (MJO) index is currently in **Phase 8**, with an amplitude **less than 1**."

A naive regex scored only 77%; the misses were **phrasing and PDF-extraction artefacts, not missing content** — e.g. `"amplitude less t han 1"` and `"phas e 4"` (spurious spaces from the PDF text layer), `"amplitude close to zero"`, and short forms like `"MJO is currently in Phase 4 with amplitude < 1"`. A tolerant parser recovers these to 96–99%. **So the bulletin found earlier was not unusually detailed — that level of MJO detail is the norm.**

#### Three findings that change what this is worth

1. **The MJO content is a *degraded duplicate* of data we already have.** Phase 1–8 plus a 3-bin amplitude ("more than 1" / "close to 1" / "less than 1") is strictly coarser than the BoM RMM1/RMM2 daily series already wired into `src/data/indices.py` — which is part of the predictor set that **already failed** in D-14. Parsing MJO out of these PDFs adds nothing and must not be mistaken for new signal.

2. **The genuinely new content is the trough-position *forecast*** — and it is the classic physical mechanism for a break (trough north toward the Himalayan foothills = suppressed rain over the core zone), forecast separately at Week 1 and Week 2, i.e. exactly the leads where D-14 failed:
   > 2022 wk2: "The monsoon trough is very likely to be **active & south of its normal position** during most days of the week."
   > 2023 wk2: "Monsoon trough is likely to be **north of its normal position** during most days of the week."
   > 2024 wk2: "Monsoon trough is likely to be **active and oscillate near its normal position** during the week."
   > 2025 wk2: "The monsoon trough at mean sea level is likely to **run north of its normal position** during many days of the week."
   > 2026 wk2: "The seasonal monsoon trough is likely to be **near normal or north of its normal position** during the week."

   But it is present with an explicit position in only **64%** of bulletins, the phrasing varies substantially (hedging "very likely"/"likely"; duration "most days"/"many days"/"some days"; and genuinely ambiguous compounds like *"near normal **or** north of"*), and *observed*-trough sentences must be separated from *forecast* ones — 83% have a forecast sentence but only 64% pin a position.

3. **IMD does not use active/break vocabulary.** The word "break" appears once in 94 bulletins. There is **no regime label to parse** — any active/break signal must be *derived* by an interpretive mapping from trough position + rainfall-anomaly language. That mapping is a modelling assumption we would be authoring, not an IMD product we would be consuming, and it must be labelled as ours.

#### The answer to the question this recon was for

> *Is Phase 1R a parsing task, or must we fall back on IMD's own published skill evaluations?*

**It is a parsing task — but the backtest it enables is 6 seasons, not 20, and that is a demotion, not a detail.**

- The predictor (bulletins) exists only from **mid-2021**. The IMD rainfall labels go back to 2000, but a bulletin-driven Stage 1 can only be scored where the bulletin exists.
- Usable yield: ~60 weekly issue times with an explicit trough-position forecast, ×2 leads (Week 1, Week 2). Leave-one-year-out becomes **6 folds, not 20**.
- Expected event count: roughly **12–18 break spells**, versus the 40 break spells / 56 active spells D-14 scored against, and versus VERIFICATION.md's stated "~20 onsets / ~60 breaks".
- So: a real backtest is possible and we do **not** have to rely solely on cited third-party skill claims. But it is materially weaker than the protocol assumes, and **VERIFICATION.md's event-count requirement must be restated honestly for this arm rather than quietly reinterpreted.** A 6-fold LOYO over ~15 break events cannot support a confident skill claim; it can support "consistent with / not worse than", with wide intervals.
- Two leads only (Week 1, Week 2). The 3- and 4-week leads in D-14's table have **no bulletin equivalent** — IMD's own product stops at two weeks. That is itself corroboration of ARCHITECTURE.md's output tiering.

#### Schema options — NOT chosen, for the human to pick (per instruction, nothing built)

| | **A. Trough-position categorical** | **B. Bulletin-derived rainfall-anomaly tercile** | **C. Evidence-bundle passthrough (no regime label)** |
|---|---|---|---|
| **Extract** | trough position ∈ {north, near-normal, south} + hedge + duration, per Week 1 / Week 2 | Week-1/Week-2 regional rainfall wording ("above/below/near normal") mapped to a 3-class tercile | All fields as typed text + MJO phase/amp, no regime inference |
| **Coverage** | **64%** of bulletins | ~83% have week-wise rainfall text (**not yet measured per-region** — would need a second pass) | ~99% |
| **Maps to Rajeevan active/break?** | Yes, via the accepted physical mechanism — but the mapping is **ours**, not IMD's | Closer to the D-14 target (rainfall anomaly), but regional wording ≠ MCZ-mean z-score | No mapping made; nothing to defend |
| **Pro** | Directly the break mechanism; short, near-templated sentences | Same physical quantity the labels are built from; better coverage | Zero interpretive risk; usable as Stage-2 evidence text and in the advisory |
| **Con** | 1 in 3 bulletins unusable; ambiguous compounds ("near normal **or** north of"); an author-defined mapping a judge can challenge | Region names must be reconciled to the MCZ box; a second, unmeasured extraction problem | Provides no regime probability — does **not** by itself unblock Stage 1 |
| **Honest read** | Highest signal, lowest coverage, most defensible physics | Best aligned to the existing label, most unmeasured risk | Safest, but defers the D-14 decision rather than answering it |

**Recommendation if asked:** measure Option B's per-region coverage before choosing, since it is the only unmeasured cell in the table and it is the option most directly comparable to the D-14 target. Do not build any of the three until that number exists and a choice is made.

#### Caveats carried forward
- These are IMD/MoES public press releases. Text is quoted here as **format evidence**; any operational use should note IMD as the source, and the ERPAS products are IITM/IMD's, consistent with CLAUDE.md's "we are not claiming to out-forecast IMD or IITM."
- `internal.imd.gov.in` blocks directory listing and rate-limited at ~8 parallel connections; 2 of 99 fetches failed transiently. Any future fetcher needs retries and must not hammer the host.
- Nothing here is validated as *skillful* — this recon establishes only that the data exists, how deep it goes, and how reliably it parses. **Whether a bulletin-driven Stage 1 beats climatology is untested and remains the D-14 question.**

#### D-15 APPENDIX (2026-09-07) — three follow-up checks. Basis corrected 94 → **96**.

##### Check 1 — the 99 → 97 → 94 gap is fully accounted for, and it was *my* bookkeeping, not the archive's

| Step | n | Cause |
|---|---|---|
| Archive-listed JJAS ERF entries | 99 | — |
| − same-date re-issues | **−3** | 2024-08-28 (`pr_3180`/`pr_3181`), 2025-07-03 (`pr_4113`/`pr_4114`), 2025-07-31 (`pr_4184`/`pr_4185`) |
| Distinct bulletins | **96** | |
| − transient fetch failures (first pass) | −2 | 2025-09-25, 2026-06-04 |
| Measured in original D-15 | 94 | |

**The 3 duplicates are byte-identical.** Re-fetched both members of each pair: MD5 match, identical text length, `text_identical=True`, same forecast window in the title. IMD posted the same PDF under two PR numbers. Deduplicating loses zero information — this is correct behaviour, not a drop.

**Both "failures" were transient and are now recovered.** On retry, 2025-09-25 (`pr_4328`) returned 928,809 bytes and 2026-06-04 (`pr_5053`) returned 1,526,573 bytes. **All 96 distinct bulletins are retrievable.**

> ⚠️ **Self-caught fabrication.** In the first retry I constructed the filename `20260604_pr_5040.pdf` from memory instead of reading it from the archive listing. It 404'd, and I was one step from reporting "2026-06-04 is a dead link on IMD's server." The real filename is `20260604_pr_5053.pdf` and it downloads fine. The 404 was mine, not IMD's. Logged because this is precisely the `api.imd.gov.in` failure mode in CLAUDE.md Rule 1 — **PR numbers are not derivable and must always be read from `press_release_mausam.php`, never guessed.**

**No year or format bias.** Duplicates fall in 2024 (1) and 2025 (2); the two transient failures in 2025 and 2026. Neither cluster relates to formatting, and both categories are now resolved rather than excluded. Per-year basis is now 2021:13, 2022:18, 2023:18, 2024:17, 2025:16, 2026:14 = 96.

**Restated rates on the full 96** (D-15's headline table was computed on 94 and was 1–2 pp optimistic — both recovered bulletins happen to lack a trough position):

| Field | on 94 (D-15) | **on 96 (correct)** |
|---|---|---|
| MJO mentioned | 99% | 99% (95/96) |
| MJO phase | 99% | **98%** (94/96) |
| MJO amplitude | 96% | 96% (92/96) |
| MJO phase + amplitude | 96% | **95%** (91/96) |
| Trough forecast sentence | 83% | **81%** (78/96) |
| **Trough forecast w/ position** | 64% | **62%** (60/96) |

Conclusion unchanged; the trough-position ceiling is **62%**, not 64%.

##### Check 2 — broader vocabulary: **IMD's language is NOT a de facto regime label**

Per-bulletin presence, same 96:

| Term | Bulletins | Term | Bulletins |
|---|---|---|---|
| above normal | **100%** (96) | weak | 55% (53) |
| below normal | 89% (85) | subdued | 19% (18) |
| near normal | 82% (79) | vigorous | 14% (13) |
| enhanced | 62% (60) | revival | 7% (7) |
| active | 61% (59) | **break** | **1%** (1) |
| reduction/decrease | 54% (52) | suppressed / lull | **0%** / **0%** |

At least one intensity word appears in 100% of bulletins — but that headline is misleading three ways, and each one matters:

1. **"Above/below normal" is ~half temperature.** Of 791 occurrences, **388 (49%) sit in a temperature context** ("Above normal maximum temperatures by 2-4°C") vs 354 (45%) rainfall. The 100% figure is not a rainfall signal. Rainfall-context anomaly wording is present in 95/96 (99%), so the field survives — but only after the temperature confound is stripped, which the naive count hides.

2. **The vocabulary is asymmetric — there is no "break" side.** Active-side vs break-side vocabulary per bulletin: **both 33%**, active-only 28%, break-side-only 30%, neither 8%. Only a third of bulletins contain both poles, so a contrastive within-bulletin reading is not available. The break side has no dedicated term at all: "suppressed" and "lull" score **0%**, "subdued" 19%, "break" 1%. It must be inferred from negation ("weak", "decrease in rainfall", "confined to northern parts") or from trough position.

3. **"Active" describes the wrong object.** Of 114 occurrences: **the monsoon trough 54%**, the monsoon system 34%, unclear 11%, and **rainfall/convection just 2%**. Rajeevan active/break is defined on the MCZ-mean *rainfall* z-score. IMD's "active" is a synoptic-system descriptor, not a rainfall-regime label. Equating them would be a substitution, not a translation.

**Answer: no.** IMD's own language is a rich *intensity and synoptic* vocabulary, not a regime label. Confirming D-15's original finding by a much wider net: **any active/break label remains ours to author and ours to defend**, and D-14's warning applies — a mapping we invent is a modelling assumption, not an IMD product we consume.

##### Check 3 — Option B granularity: **far finer than all-India, but it is not a tercile**

> ⚠️ **Correction to my own D-15 schema table.** I named Option B "rainfall-anomaly **tercile**." That word was mine, not IMD's. **IMD does not issue a rainfall tercile in these bulletins.** Anyone reading D-15 alone would have looked for a field that does not exist.

What IMD actually issues is its **official spatial-distribution scale**, which is a genuine ordinal and is used near-universally:

| Category | Bulletins | Hits |
|---|---|---|
| isolated | **100%** (96) | 1488 |
| fairly widespread | **100%** (96) | 544 |
| widespread | **100%** (96) | 412 |
| scattered | 86% (83) | 296 |
| dry | 5% (5) | 5 |

**Granularity — the real numbers:**

| Measure | Result |
|---|---|
| Both Week-1 and Week-2 sections present | **100%** (96/96) |
| Subject line promises "next two weeks" | 99% (95/96) |
| Central India named | **100%** (96/96, 397 hits) |
| Northwest India named | 100% (423 hits) |
| East & NE India named | 100% (396 hits) |
| South Peninsular named | 90% (318 hits) |
| Individual states named (MP, Chhattisgarh, Vidarbha, Odisha, …) | **100%** (3,475 hits) |
| Met "subdivision" as a word | 1% (1/96) |
| **Sentence carrying an MCZ-region name + a distribution category** | **99%** (95/96) |
| **Sentence carrying an MCZ-region name + rainfall anomaly wording** | **52%** (50/96) |

**So: it resolves at state / homogeneous-region level, not all-India.** That is finer than the MCZ box, not coarser — the constraint is alignment, not resolution.

Three caveats that stop this from being a solved parse, stated because the 99% figure otherwise reads as a green light:

- **Geography is free-text state lists, not a fixed region field.** e.g. *"Fairly widespread to widespread rainfall with isolated heavy to very heavy falls very likely over Odisha, Gangetic West Bengal, Jharkhand and Bihar during 29–31 July and over East Madhya Pradesh and Chhattisgarh during 2…"*. Mapping that onto the MCZ box (18–28°N, 65–88°E) is an area-weighting decision we author. IMD's "Central India" homogeneous region is the closest single match but **under-covers** the MCZ's northern and eastern parts (which fall in Northwest and East & NE India). The MCZ is not co-extensive with any one IMD region.
- **Observed and forecast statements are interleaved** and the 99% counts both. Sampled sentences include past-tense ("had occurred", "today, the 22nd July") alongside genuine forecasts ("very likely over … during 29–31 July"). The trough finding had this same confound (83% have a trough forecast sentence, only 62% pin a position).
- **Measurement is definition-sensitive, so I am giving a range, not a false point estimate.** Region+category co-occurrence scores **70%** with a tight week-block window and **100%** with a loose 1400-char window (blocks overlap and the test degenerates). The sentence-level 99% is the stable, well-defined number, but sentence-level co-occurrence still is not the same as a reliable *(region, week, category)* assignment. **A single trustworthy assignment rate cannot be produced without building the extractor** — which was explicitly out of scope here, and I am not going to substitute a confident-sounding guess for it.

##### Net effect on the D-15 schema options

- **Option A (trough position)** — ceiling drops 64% → **62%**. Unchanged otherwise.
- **Option B** — is **not** a tercile; it is IMD's ordinal distribution scale (isolated → widespread) attached to free-text state lists, at 99% sentence-level co-occurrence but with an unmeasured assignment rate and an MCZ-alignment decision we would own. Better coverage than A, more interpretive work, and its headline number is softer than it looks.
- **Option C (evidence passthrough)** — strengthened. It is the only option that needs no authored mapping, and Check 2 shows an authored mapping is unavoidable for both A and B.
- The Check-2 result cuts across all three: **there is no IMD regime label to consume.** Framing this arm as "consuming IMD's forecast" is only accurate for Option C. A and B are "deriving our own regime label from IMD's text," which is a materially different claim to defend in front of a sponsor-side judge.

Still no schema built. Decision pending.

#### D-15 ADDENDUM 2 (2026-09-07) — IMD's own activity formula: verified at source, then **coverage collapses to 0%**

##### Part 1 — the criteria, read directly. The premise as stated is **materially wrong in four ways**

Read both sources rather than taking the framing as given.

**Source A — `mausam.imd.gov.in/imd_latest/contents/monsoon_activity.php`** (live, 200, criteria table present), verbatim:

| Term | Specification |
|---|---|
| **Weak monsoon** | "Rainfall less than half the normal." |
| **Normal monsoon** | "Rainfall half to less than 1½ times the normal." |
| **Active monsoon** | "Rainfall 1½ to 4 times the normal. The rainfall in **at least two stations should be 5 cm** if that sub-division is along the west coast and **3 cm** if it is elsewhere. Rainfall in that sub-division should be **fairly widespread to widespread**." |
| **Vigorous monsoon** | "Rainfall **more than 4 times the normal**. …at least two stations should be **8 cm** / **5 cm**… Rainfall …should be fairly widespread or widespread." |
| **Subdued monsoon** | "Spatial distribution of rainfall remains **dry, isolated or scattered for two consecutive days**. Mean actual rainfall of that particular sub-division remains **less than the normal for the consecutive two days**. The **forecast issued for the next 48 hrs** …is also dry, isolated or scattered. Upon satisfying **all** the above criteria simultaneously, monsoon activity be described as subdued on the second day." |

**Source B — `imdpune.gov.in/Reports/glossary.pdf`** (live, 200, 13 pp), verbatim: *"Weak/subdued Monsoon — Rainfall less than half the normal (over the land area)"*, then Normal / Active / Vigorous with the same ratios and station thresholds as Source A.

**Where the stated premise — "rainfall relative to normal + spatial distribution category + a 2-day/48hr window" — does not hold:**

1. **Distribution applies to only 3 of 5 terms.** Weak and Normal are defined **purely on the rainfall ratio**, with no distribution criterion whatsoever. Applying a distribution test to them would invent a requirement IMD does not impose.
2. **The 2-day/48-hr window belongs to Subdued alone.** Weak, Normal, Active and Vigorous carry **no temporal window** — they are single-period descriptions. The 48-hr clause is one of three conjunctive conditions inside the Subdued definition only.
3. **A third input is omitted entirely: absolute station thresholds.** Active requires ≥2 stations at **5 cm** (west coast) / **3 cm** (elsewhere); Vigorous at **8 cm** / **5 cm**. This is station-level measurement, and it is a hard conjunct — not decoration.
4. **The two IMD sources disagree with each other.** Source A treats **Weak** and **Subdued** as two distinct terms with different definitions (Subdued needing 3 simultaneous conditions). Source B collapses them into a single **"Weak/subdued"** term defined only as <½ normal, with **no distribution and no window**. A "mechanical application of IMD's own formula" therefore has no single unambiguous formula to apply — the choice of source changes the label.

Everything is defined at **meteorological sub-division** level ("that sub-division", "mean actual rainfall of that particular sub-division"), and the ratios are **quantitative multiples of normal** (0.5×, 1.5×, 4×), not qualitative wording.

##### Part 2 — a significant find that improves an *earlier* conclusion

`glossary.pdf` defines Break Monsoon verbatim:

> **"Break Monsoon — Monsoon trough shifts northwards and runs close to foot hills of Himalayas, resulting in drastic reduction in rainfall over the country outside the foot hills and southernmost Peninsula"**

**This partially retracts D-15's caveat that "the trough→break mapping is ours to author."** It is not ours — it is IMD's own published definition, and it is precisely the trough-position mechanism D-15 identified as the extractable signal. Option A can now cite IMD's glossary for the mapping rather than defending an invented one. What remains ours is only the *thresholding* (how far north, for how long) and the MCZ reconciliation. That is a real upgrade in defensibility for Option A and should be reflected if the pitch discusses it.

Also captured from the glossary — the distribution scale is **percentage of stations reporting ≥2.5 mm**, i.e. *spatial coverage, not amount*: Widespread ≥75%, Fairly widespread 51–74%, Scattered 26–50%, Isolated ≤25%, Mainly dry 0. **A distribution category alone carries no information about rainfall relative to normal.** That is exactly why both inputs are required, and why the next result matters.

##### Part 3 — mechanical application to the 96 bulletins: **the path collapses**

Each bulletin split into Week-1 / Week-2 forecast sections (temperature blocks excluded). **191 sections** recovered from 96 bulletins (96 × week-1, 95 × week-2); zero bulletins had no detectable week section.

| Requirement | Sections | Rate |
|---|---|---|
| (a) distribution category present in the section | 117/191 | **61%** |
| (b) rainfall-vs-normal comparison present in the section | 94/191 | **49%** |
| both present *anywhere* in the same section | 90/191 | **47%** |
| **both present in the SAME SENTENCE — the ceiling** | **0/191** | **0.0%** |

Same standard as the 99% distribution+region sentence-level check in Addendum 1, so the two are directly comparable: **region+category co-occurs at 99%; category+anomaly co-occurs at 0%.**

**The first pass reported 1/191, and that single hit was a false positive I chased down.** In `20230627` week-2 the raw text reads `…reduction thereafter  Overall, rainfall activity is likely to be above normal…` — `` is a Wingdings bullet glyph, not sentence punctuation, so the splitter merged two separate bullets that describe **different regions** (distribution over east Rajasthan/Uttarakhand/UP; anomaly over west coast/Gujarat/NE India). Re-running with bullet glyphs treated as separators gives **0/191**. Reporting 1/191 would have implied a non-zero floor that does not exist.

##### Why it collapses — structural, not a parsing shortfall

The two inputs live in **different sentence types serving different purposes**, and are never joined per-area:

- **Distribution sentences** are spatial-coverage statements over named states: *"Fairly widespread to widespread rainfall with isolated heavy to very heavy falls very likely over Odisha, Gangetic West Bengal, Jharkhand and Bihar during 29–31 July."*
- **Anomaly sentences** are separate summary statements over different, usually broader areas: *"Overall, rainfall activity is likely to be above normal over west coast of India, Gujarat state and adjoining areas of west central India, northeast India; near normal over rest parts of the country…"*

A better parser cannot fix this — the pairing is absent from the source, not merely hard to see. And even a perfect pairing would still miss IMD's **station-threshold conjunct** (≥2 stations at 5/3 cm), which appears nowhere in the bulletins in any form, so **Active and Vigorous are not derivable from these documents at all** — only a proxy that drops a criterion IMD treats as mandatory.

##### Verdict — plainly

**This is not a usable path. Coverage does not degrade; it goes to zero once both inputs are required together.**

The reason is now clear and is worth stating in one line: **the ERF press bulletin is not the product in which IMD publishes its monsoon-activity label.** IMD computes Weak/Normal/Active/Vigorous/Subdued operationally from sub-divisional station data and publishes it elsewhere; the ERF bulletin is narrative synoptic guidance that happens to *mention* both ingredients in unrelated sentences.

**Consequence for the D-15 options:**
- **Option B is dead in its "apply IMD's formula" form.** Addendum 1 already corrected it from "tercile" (a field that does not exist) to the ordinal distribution scale; this addendum shows the distribution scale **cannot be converted into IMD's activity label** from these bulletins. What survives of B is the raw distribution category alone — spatial coverage with no anomaly information, which is not a regime signal.
- **Option A is now the strongest**, and stronger than D-15 rated it: its ceiling is 62%, but its trough→break mapping is now backed by **IMD's own published Break Monsoon definition** rather than an authored assumption.
- **Option C is unaffected.**

**Pointer for the next step, flagged as UNVERIFIED.** `monsoon_activity.php` links a family of products that would plausibly carry the computed label directly — "Daily monsoon activity", "Sub-divisional rainfall activity" (`index_rainfall_subdiv.php`), "Week by week rainfall activity" (`week_rainfall_activity.php`), "Daily activity map" (`daily_activity_map.php`). All return HTTP 200, but their HTML contains **zero** activity-label words and their sizes (~34 KB) match the nav-shell signature already seen on `extendedrangeforecast.php` — consistent with map-image products rather than text. **I have not established what they serve**; that needs its own check and is out of scope here. If one of them publishes the sub-divisional label as data, it would supersede this entire derive-from-bulletin approach.

Sub-division ↔ MCZ reconciliation deliberately **not** attempted — that remains the next step. Still no schema built.

#### D-15 FINAL ADDENDUM (2026-09-07) — the three product pages: **two image maps, one structured dataset**

Each of the three fetched and inspected at source level (HTML content region, `<img>`/`<iframe>`/`<table>` counts, inline JS, and magic-byte verification of every image target). **Not inferred from file size** — that was the unverified shortcut flagged at the end of Addendum 2, and it turns out to have been wrong for one of the three. Each judged independently; no extrapolation.

##### (1) "Week by week rainfall activity" — `week_rainfall_activity.php` → **IMAGE MAP**
Content region 4,564 b: **one `<img>`, zero tables, zero iframes**. Target `../../ClimateInformation/imdweb/DAY_WEEK/weekwise.gif` fetched directly: HTTP 200, **143,743 b, magic bytes `GIF89a`** — confirmed a real GIF. No text data.

##### (2) "Daily activity map" — `daily_activity_map.php` → **IMAGE MAP**
Content region 4,550 b: **one `<img>`, zero tables, zero iframes**. Target `../../ClimateInformation/imdweb/DAY_WEEK/dtoday.gif`: HTTP 200, **22,932 b, magic bytes `GIF87a`** — confirmed a real GIF. No text data.

##### (3) "Sub-divisional rainfall activity" — `index_rainfall_subdiv.php` → **STRUCTURED DATA. Not an image map.**

Content region **29,788 b with zero `<img>` tags**. It renders an AmCharts choropleth whose geometry comes from `district_shapefiles/sd_boundary_rainfall.json` (HTTP 200, 900,948 b, valid GeoJSON, **36 features** = IMD's 36 meteorological sub-divisions) — but that file carries **boundaries only** (`OBJECTID, object_id, name, state_code, region_cod, subdivisio, uorder`), **no rainfall**, despite its filename.

**The rainfall values are server-side rendered directly into the page HTML** as an `"areas"` array — plain text, parseable with no image processing.

*(Noted so it is not mistaken for an endpoint: the page also contains the string `data.php`, but it is inside a commented-out AJAX block — `// url:"data.php"` — i.e. dead code, not a live data source.)*

**Exact fields — 41 entries** = 36 met sub-divisions + 4 homogeneous-region roll-ups + 1 `COUNTRY : INDIA` total. Keys: `title`, `id`, `color`, `info`, `balloonText`.

| Field | Content | Example |
|---|---|---|
| `title` | sub-division / region / country name | `"EAST UTTAR PRADESH"` |
| `info` | rainfall **departure %** | `"62%"` |
| `balloonText` | **Departure % + Actual mm + Normal mm** | `"ARUNACHAL PRADESH : Departure : -73% Actual : 2.4 mm Normal : 8.8 mm"` |
| `color` | hex encoding the departure class | `#FFFF00` |

**Departure classification** (read from the page's own legend, IMD's standard rainfall-departure scale): `No Data` · `No Rain [-100%]` · `Large Deficient [-99% to -60%]` · `Deficient [-59% to -20%]` · `Normal [-19% to 19%]` · `Excess [20% to 59%]` (+ large-excess class).

**Cadence — four periods, selectable** (`value=D/W/M/C`, D default), all at the same 36-sub-division granularity:

| Selector | Period | As rendered on 2026-09-07 |
|---|---|---|
| `D` | **Daily** | 07-09-2026 |
| `W` | **Weekly** | 07-09-2026 |
| `M` | **Monthly** (month-to-date) | 01-09-2026 → 07-09-2026 |
| `C` | **Cumulative** (season-to-date) | 01-06-2026 → 07-09-2026 |

##### Two caveats that decide whether this actually supersedes anything

1. **It is OBSERVED rainfall, not a forecast.** Every field is Actual vs Normal for a *completed* period. Stage 1 needs a **forecast of a future regime**; this product forecasts nothing. So it does **not** supersede Option A as a *predictor* source. Where it could supersede is the **label/ground-truth side** — it is IMD's own official sub-divisional rainfall accounting, which is a more authoritative and more natural-granularity label than our current Rajeevan MCZ-mean derived from the imdlib 0.25° grid, and it would also dissolve much of the sub-division ↔ MCZ reconciliation problem by letting labels be defined on IMD's own sub-divisions.

2. **Current-day only; no historical access discovered.** The page renders one snapshot. Five parameter forms were tried (`date`, `dt`, `day/month/year`, `rdate`, and a POST) — **all returned byte-identical content** (83,684 b, same 07-09-2026 dates). **This does not prove no archive exists** — I was guessing parameter names, which is exactly the mistake that produced the false "dead link" in Addendum 1. It means only: *no historical access found by guessing, and guessing is not evidence.* Without an archive this is a live-operations feed, not a backtest source, and it cannot support any leave-one-year-out evaluation.

3. Separately: this product carries the **rainfall-departure** scale (Deficient/Normal/Excess), **not** the Weak/Normal/Active/Vigorous/Subdued **monsoon-activity** label from Addendum 2. They are different IMD scales and must not be conflated.

##### Verdict

**The "all three are image maps" branch does not hold** — (1) and (2) are confirmed image maps, but (3) is genuine structured data and my Addendum 2 nav-shell hypothesis was wrong for it. Judging them separately mattered.

**Option A is not yet superseded, and remains the leading candidate** for the *forecast* signal: trough position, IMD's own published Break Monsoon definition behind the mapping, 62% ceiling, MCZ reconciliation still open.

**But a genuinely new and better option is now on the table for the label side**, conditional on one unanswered question:

> **Is there a historical archive of `index_rainfall_subdiv.php`'s sub-divisional actual/normal/departure data?**
> - **If yes** → it likely supersedes both the current Rajeevan/imdlib label construction *and* the MCZ reconciliation problem, and Phase 1R should be re-planned around it before anything is built.
> - **If no** → it is a live-operations feed only: useful for the demo and for real-time advisories, useless for backtesting, and Option A stands unchanged.

Nothing built. Per instruction, stopping here rather than pursuing the archive question — that is the next decision, and it should be taken deliberately given how much it would change the plan.

#### D-15 ADDENDUM 5 (2026-09-07) — subdivisional archive hunt: **no usable historical source found. Keep Rajeevan/imdlib.**

##### Check 1 — `rainfall_statistics.php`: parameter read from the page, **no archive selector exists**

The page discloses its own parameter in its markup — `rainfall_statistics.php?PAGE=N` — so nothing was guessed.

| Product | PAGE | What it actually serves |
|---|---|---|
| Subdivision — week by week departures (**Cumulative**) | 6 | **Nothing.** Zero content images; the only `<img>` tags are site logos and app-store icons. Currently empty or broken. |
| Subdivision — week by week departures (**Weekly**) | 7 | **3 PNGs** at `../Rainfall/tmpf/f-{0,1,2}.png` — verified real (`\x89PNG`, 257,901 b) |
| Subdivision-wise rainfall distribution | 8 | **4 PNGs** at `../Rainfall/tmpg/g-{0..3}.png` — verified real (`\x89PNG`, 208,079 b) |

**Contents (read by viewing the images):**
- **PAGE=7** — *"Subdivision - Week By Week Departures (Weekly), Period: 01-06-2026 To 02-09-2026"*. A table of **~36 subdivisions × 14 weekly columns** (03-06-2026 … 02-09-2026), each cell a **departure %**. Structurally this is exactly the label matrix Phase 1R would want.
- **PAGE=8** — *"SUBDIVISION-WISE RAINFALL (MM) DISTRIBUTION"*, with **DAY** and **PERIOD (season-to-date)** blocks, each giving **ACTUAL(mm) · NORMAL(mm) · %DEP · CAT** per subdivision plus region roll-ups. Same content as `index_rainfall_subdiv.php` (Addendum 4) but rendered as an image — so **the HTML version from Addendum 4 remains strictly the better machine-readable route**.

**Date parameter / archive selector: NONE.** All three pages contain **zero `<select>`, zero `<input>`, and no form** other than a Google site-search box. Image paths are fixed temp filenames (`tmpf`, `tmpg`) regenerated in place, with no date component. Directory listings `Rainfall/` and `Rainfall/tmpf/` both return **403**.

**One genuine positive:** PAGE=7 covers the **entire current season** week by week, not just today. So within-season weekly history exists — it is *previous seasons* that are unavailable, and it is locked in a PNG.

##### Check 2 — Dataful 21444: **could not verify. Citation is not sufficient.**

`dataful.in/datasets/21444` = *"Year, Month and IMD Sub Division-wise (State) Actual Rainfall Data Since 1901"* — 1901–2025, **58,622 rows**, schema `year · month · sub_division · rainfall_type · value · units · notes`, with **36 distinct subdivisions**, 126 years, 13 month values, 2 rainfall types. Cited to Ministry of Earth Sciences.

**It is paywalled.** The page's own payload carries `"Free":false`, download requires sign-in, and **only 22 preview rows are visible — all December 2025**, of which 8 of the 10 subdivision values shown are `0`.

**Verification attempt and outcome — negative:**
- Located IMD's own **"Statement on the Climate of India during 2025"** (`20260101_pr_4602.pdf`, 1.33 MB, 8 pp) via the press-release archive. It is a **narrative national/seasonal** document: **zero** matches for "sub-division", no subdivision table, no December subdivision figures.
- The **Monthly Climate Summary** series (see Check 3) is likewise all-India / homogeneous-region, not subdivisional.
- **Conclusion: no IMD source reachable in this session publishes December-2025 subdivision monthly rainfall as text, so not one Dataful value could be checked.**

**However, a factual error in Dataful's own metadata *was* verified.** Its dataset overview states, verbatim:

> *"…the current normal rainfall for India, which is **868.6 mm annually and 868.6 mm for the southwest monsoon season**."*

This is internally contradictory — the same figure cannot be both — and it is **refuted by IMD's own 2025 statement**: *"The 2025 annual rainfall over the country as a whole was (1274 mm) 110% of the Long Period Average (LPA)"*, which puts the **annual LPA at ≈1158 mm**. 868.6 mm is the **southwest-monsoon (JJAS) LPA only**. (Corroborating scale: the July-2024 Monthly Climate Summary gives July's LPA alone as 280.5 mm.)

**Verdict:** the error is in Dataful's *documentation*, not demonstrably in its *values* — but combined with the paywall and the unverifiable preview, **treating this dataset as a validated IMD mirror is not justified on present evidence.** Per CLAUDE.md Rule 1 it should carry **UNVERIFIED** if it is cited at all.

##### Check 3 — regional offices: a real dated archive exists, but **at the wrong granularity**

| Target | Result |
|---|---|
| `mausam.imd.gov.in/pune` | **403 Forbidden** — exists but access blocked |
| `mausam.imd.gov.in/delhi` | **404** — does not exist |
| `imdpune.gov.in` | 200 — the actual Pune institutional site |
| `dsp.imdpune.gov.in` | 200 — IMD Data Service Portal |

**Found: `imdpune.gov.in/mcs.php` — "Monthly Climate Summary", a genuine dated archive.** Its selectors were read from the markup (`olrList1` = year 2021–2026, `olrList` = month 1–12) and the filename pattern from its own JS:

```js
image.src = "cmpg/Product/Monthly_Climate_Summary/Monthly_Clim_Summary_" + period + "_" + year + ".pdf";
```

Enumerated against that exact pattern: **65 PDFs reachable, April 2021 → August 2026**, matching the page's own note *"(Available from April-2021)"*. No gaps within range.

> ⚠️ **Recurring self-flag.** Before reading that JS I tested a *constructed* name (`Monthly_Climate_Summary_{m}_{y}.png`) and got uniform 404s — which would have supported a false "no archive exists" conclusion. The real name is `Monthly_Clim_Summary_{m}_{y}.**pdf**`. This is the third time in D-15 that a guessed filename produced a misleading 404 (see Addendum 1's `pr_5040`, Addendum 4's parameter guessing). **Filenames and parameters must always be read from the serving page.**

**But the granularity is wrong.** The July-2024 summary is 13 pages / 4.15 MB but only **14,504 characters** of extractable text — mostly figures. Its content is **all-India and homogeneous-region**: *"Rainfall over the country as a whole for July 2024 was 305.8 mm … 9% more than its LPA of 280.5 mm"*, *"the homogeneous region of Central India (427.2 mm)"*. Only 3 subdivision names appear anywhere in the text, and there is **no subdivision table**.

Likewise `dsp.imdpune.gov.in/home_freedataaccess.php` → *"All India Monthly and Seasonal Rainfall (mm) Series"*, whose region selector (`region1`) offers only **`WHI` Whole India · `NEI` · `NWI` · `PNI` · `CNI` Central India** — **5 aggregates, not 36 subdivisions.**

*(Unexplored lead, flagged not claimed: the DSP states its series are "also available on Open Government Data Platform (data.gov.in)". `data.gov.in` responds 200 but is a JS-rendered SPA and was not pursued — it may host the free primary series Dataful repackages.)*

##### What is actually reachable, at what granularity, how far back

| Source | Granularity | Depth | Machine-readable? |
|---|---|---|---|
| `index_rainfall_subdiv.php` (Add. 4) | **36 subdivisions** | **current day only** | ✅ HTML text |
| `rainfall_statistics.php?PAGE=7` | **36 subdivisions × weekly** | **current season only** | ❌ PNG |
| `rainfall_statistics.php?PAGE=8` | 36 subdivisions | current day + season-to-date | ❌ PNG |
| `mcs.php` Monthly Climate Summary | all-India + 4 regions | **Apr 2021 – Aug 2026 (65 PDFs)** | ⚠️ narrative text + figures |
| DSP free rainfall series | all-India + 4 regions | (not enumerated) | ✅ but wrong granularity |
| Dataful 21444 | 36 subdivisions, monthly | claims 1901–2025 | ❌ paywalled, **unverified** |
| **imdlib gridded rainfall (current)** | **0.25° grid** | **1901–present, verified working (D-6)** | ✅ |

##### Decision this feeds

**Phase 1R should KEEP the current Rajeevan/imdlib label construction. The MCZ reconciliation problem is NOT dissolved.**

Reasoning, plainly: no free, verified, machine-readable **historical** subdivision-level rainfall source was found. IMD's subdivisional products are current-day (HTML) or current-season (PNG); the one genuinely deep dated archive (MCS, 65 PDFs back to Apr 2021) is regional, not subdivisional; and the one claimed 1901–2025 subdivisional series is paid, unverifiable from its preview, and ships a demonstrable factual error in its own metadata. Against that, `imdlib` is free, already verified working, and supports the full 20-year leave-one-year-out that D-14's protocol requires — which **none** of the IMD subdivisional routes can, since the deepest is 5 seasons and the subdivisional ones are 1.

**So the plan stands as it was:** Rajeevan/imdlib supplies the label; **Option A** (trough position, IMD's own published Break Monsoon definition, 62% ceiling) supplies the predictor; MCZ reconciliation remains open and must still be solved rather than sidestepped.

Two things worth revisiting later, neither blocking: the subdivisional HTML feed (Addendum 4) is still the right choice for **live demo/advisory** output even though it cannot backtest; and `data.gov.in` was not explored.

Nothing built. No schema.

### D-16: Phase 1R build cycle 1 — IMD trough signal is **real but too sparse to stand alone** — **OPEN, decision required**

First actual Phase 1R code (not recon). Run: `python -m src.eval.phase1r_trough_check`, log `artifacts/phase1r_trough_check.txt`. **Stage 2 was not touched** — same gate discipline as Phase 1.

#### Built
| Module | Purpose |
|---|---|
| `src/data/imd_bulletins.py` | Acquire ERF bulletins. **Filenames are always read from the archive listing, never constructed** — D-15 logged three guessed-filename false 404s. |
| `src/features/trough.py` | Week-1/Week-2 trough-position extractor + classifier |
| `src/features/mcz.py` | Sub-division ↔ MCZ reconciliation from real polygon geometry |
| `src/eval/phase1r_trough_check.py` | Join to Rajeevan labels + association check (metrics live only in `src/eval/`) |

Acquisition reproduces the recon exactly: 254 ERF bulletins in the archive → 96 JJAS 2021–2026 after de-duplicating same-date re-issues → 96 downloaded → 96 texts.

#### Correction to D-15: the 62% ceiling was measured too generously

D-15 addendum 1 reported "trough forecast with explicit position: 62% (60/96)". **That replicates exactly** (60/96) when measured its way — a forecast-modality trough sentence with a position *anywhere in the document*. But that is not the same as being able to attribute a position to a **specific forecast week**, which is what a lead-time signal requires.

**253 of 384 trough sentences fall outside the Week-1/Week-2 sections** — they sit in the "Salient Observed Features" narrative describing the week just *past*, and carry no lead attribution. Restricting to week sections, where the lead is unambiguous:

| Measure | D-15 (per bulletin, whole doc) | **Corrected (per week-section)** |
|---|---|---|
| Usable directional trough position | 62% (60/96) | **18.3%** (35/191) |
| Bulletins with ≥1 usable week-attributed position | — | **31%** (30/96) |

This is not a parser regression — the stricter measure is the correct one for a forecast signal. **The usable ceiling is roughly half what D-15 implied.**

Position distribution over 191 week-sections: `not_stated` 124 (64.9%), `mixed` 32 (16.8%), `south` 14, `near_normal` 13, `north` 7, `foothills` 1. `mixed` is kept as its own class and excluded, not collapsed — IMD genuinely writes compound positions (*"north of its normal or near normal position"*, *"near normal / south of its position"*, *"western end … north … eastern end … south"*, *"north … during 1st half of the week and shift gradually southwards thereafter"*). Forcing these to a single class would manufacture precision the source does not contain.

#### MCZ reconciliation — measured, not asserted

Computed by intersecting IMD's own 36 sub-division polygons with the Rajeevan box (18–28°N, 65–88°E) rather than declaring a proxy.

**18 sub-divisions are MCZ-relevant** (≥25% of area inside the box — that threshold is ours and is a parameter), and they span **four** IMD homogeneous regions: Central India 10, North West India 4, East & North East India 3, South Peninsula 1.

**The "Central India ≈ MCZ" shortcut is wrong in one direction and only one:**
- In MCZ but **not** Central India (8): Bihar, East Rajasthan, East Uttar Pradesh, Gangetic West Bengal, Jharkhand, Telangana, West Rajasthan, West Uttar Pradesh
- In Central India but not MCZ: **0**

So Central India is a strict *subset* — it never over-reaches, but it captures only **10 of 18** MCZ sub-divisions. Using it as a proxy would silently discard the entire northern and eastern flank of the core zone.

Encouragingly, the bulletins themselves are not the bottleneck here: per-bulletin **MCZ area-weighted coverage has median 0.78** (min 0.23, max 0.94, n=96). Bulletins do name most of the core zone; it is the *trough attribution*, not the geography, that is scarce.

#### The result — join to Rajeevan/imdlib labels, 2021–2025

Joinable range is **2021–2025, five seasons**: bulletins start mid-2021, and imdlib rejects 2026 (`"mismatch in size of data-length"` — partial year). Labels built with the Rajeevan criterion, daily climatology from the long 2000–2025 record for stability.

| | pooled | week 1 (lead 0–6 d) | week 2 (lead 7–13 d) |
|---|---|---|---|
| N week-statements | 30 | 11 | 19 |
| observed break-dominant windows | 4 (base rate 0.13) | 1 | 3 |
| **P(break \| north/foothills)** | **0.50** (n=8) | 0.50 (n=2) | 0.50 (n=6) |
| **P(break \| south/near-normal)** | **0.00** (n=22) | 0.00 (n=9) | 0.00 (n=13) |
| Fisher exact two-sided p | **0.003** | 0.182 | **0.021** |
| raw hard-0/1 BSS vs climatology | −0.154 | −0.100 | −0.188 |
| **LOO-calibrated BSS vs climatology** (year-level, corrected) | **+0.395** | (N too small) | **+0.336** |

**Two numbers that look contradictory and are not.** The raw signal's BSS is *negative* because it is a hard 0/1 assertion against a 0.13 base rate — Brier punishes overconfidence even when the association is strong. This is the same trap flagged for hard persistence in D-14, and it is a calibration failure, not an absence of information. Refitting the calibration leave-one-out gives positive skill against climatology.

##### Correction (2026-09-07, prompted by a review question): LOO fold level

The first version of `loo_calibrated_brier` did leave-one-out **at the point level** — 30 folds, one held-out week-statement at a time. That is wrong. Trough position and the observed regime both persist across the consecutive weekly bulletins of one spell, so week-statements from the same season are correlated in *both* the predictor and the outcome, and a point-level fold lets a held-out point's calibration be fitted partly on its own season. **Redone at the season level** (5 folds, one held-out year):

| | point-level (original, leaky) | **year-level (corrected)** |
|---|---|---|
| pooled BSS | +0.296 | **+0.395** |
| week-2 BSS | +0.233 | **+0.336** |

**The number went *up*, not down — the leakage was not inflating it.** Mechanically: break events here are near-singletons per season (2021/2022/2023/2025 have exactly one break-dominant window each; 2024 has none), so a point-level fold that holds out a break point still leaves that season's *non*-break week-statements in training, pulling `P(break | signal)` toward the base rate; removing the whole season lifts that drag.

**But a BSS that *rises* when you delete a season of data is itself a warning about stability, not a reassurance.** One of the five folds (2024) contains zero break events; the other four contain exactly one each. This is not a calibration curve, it is four events. `src/eval/phase1r_trough_check.py` now folds at the year level and its docstring records the before/after. The honest reading is unchanged: **"not inconsistent with real skill", never a skill figure.**

#### Why this still does not clear a gate

Two limits, both hard:

1. **Only 4 break events.** The entire result rests on 4 break-dominant windows and 8 positive-signal cases. The perfect separation (`P(break | south/near) = 0.00`) depends on there being *zero* counterexamples among 22 cases; a single reclassified window would materially weaken both the p-value and the BSS. This is not a sample that can support a skill claim, and it must never be quoted alongside D-14's 20-year figures as though comparable.

2. **The pipeline sees only a third of break events.** Of 12 break-dominant windows in 2021–2025 covered by a bulletin week-section, only **4 (33%)** had a usable trough position at all. The other 8 are invisible — not misclassified, simply *unstated by IMD for that week*. A Stage 1 that is silent for two-thirds of the events it exists to warn about cannot be the load-bearing stage.

So the honest summary: **where the signal speaks it is informative and correctly directed; it speaks too rarely.** High precision on a narrow subset, low pipeline recall.

#### Decision required (Phase 1R, still open)

- **Not supportable:** trough position as a standalone Stage 1. Coverage of 18% of week-sections / 33% of events disqualifies it, independent of how good the 30-point statistic looks.
- **Arguable:** trough position as a *supplementary* input alongside a denser predictor, or as an evidence string in the advisory (Option C from D-15) where "IMD's bulletin says the trough is north of normal next week" is a citable, human-legible justification even when it is only available sometimes.
- **Worth noting for the pitch:** the mechanism is IMD's published Break Monsoon definition, so the *reasoning* is citable even where the *coverage* is thin. The mapping from position to break-favourable remains ours — `trough.break_favourable()` isolates it deliberately so it is the first thing a reviewer can attack.

**Stage 2 not started.** This build cycle cost one cycle and answered the question, which was the point.

### D-17: Stage 2 analog downscaler — **effective-N gate CLEARED, skill gate NOT** — **OPEN, decision required**

Run: `python -m src.eval.stage2_backtest`, log `artifacts/stage2_backtest.txt`. Stage 4 not touched.

#### Built
`src/features/seasonal_state.py` (one row per year, no week-level API by construction) · `src/models/analog_downscaler.py` · `src/eval/stage2_backtest.py`.

#### The scale discipline, and why it is the whole design

D-14 falsified *within-season* index trajectories predicting sub-seasonal regime. Stage 2 therefore operates on a **different claim at a different scale**: ENSO/IOD modulation of **seasonal total** rainfall. To keep these from being conflated, `seasonal_state` computes exactly one value per year and exposes no week-level API, and `analog_downscaler` has **no executable line referencing weeks or lags** (verified by AST-stripping docstrings — the three `week` matches in the file are all prose). A week-specific ENSO/IOD distance is not merely unused here; there is no code path that could produce one.

#### The finding that determined the result, visible before any model was fitted

| Predictor | r vs seasonal MCZ rainfall (n=20) |
|---|---|
| **Niño3.4 JJAS** (concurrent — *not knowable before the season*) | **−0.444** |
| **Niño3.4 MAM** (pre-season — *operationally usable*) | **+0.054** |
| DMI JJAS | +0.150 |
| DMI MAM | +0.066 |

The canonical ENSO–monsoon relationship is present and textbook in the concurrent window (2002/2009/2015 El Niño → three driest seasons; 2019's record +0.63 IOD → wettest despite warm ENSO). **In the pre-season window it is absent.** Both windows are implemented and both are reported, because quoting the concurrent number alone would describe a system that cannot exist operationally.

#### Result — LOYO over 20 seasons, RPS on ordered terciles vs unweighted climatology

| Window | RPSS vs climatology | 95% CI (block bootstrap over years) | BSS | Verdict |
|---|---|---|---|---|
| **JJAS** (concurrent, diagnostic) | **+0.039** | [−0.179, +0.226] | −0.031 | spans zero — **not distinguishable from climatology** |
| **MAM** (pre-season, operational) | **−0.249** | [−0.383, −0.136] | −0.255 | **significantly worse than climatology** |

Sensitivity grid printed in full (bandwidth 0.5/1.0/2.0 × recency on/off). JJAS spans −0.005 → +0.081, all small and straddling zero; MAM spans −0.71 → −0.06, **negative everywhere**. No cell was selected as "the" result — the a-priori parameters (bandwidth 1.0, τ=15 yr) are what is reported, per Michaelsen.

**N = 20 seasonal events** (≈7 dry / 6 normal / 7 wet). Not 20 years of daily data — 20 events. A seasonal-scale question cannot have a large sample from a 20-year record, and nothing here may be quoted as if it did.

#### Where it succeeds and fails is physically interpretable
Strong-ENSO seasons are called well (2002 P(dry)=0.53, 2009 0.51, 2015 0.54, 2007/2008/2011 P(wet)≈0.54 vs a 0.37 base rate). The two failures are informative: **2000** (dry season, model said wet — La Niña that did not deliver) and **2019** (wettest season, model said dry — warm ENSO overridden by the record positive IOD). The method captures the canonical relationship and misses years where IOD dominates or the ENSO link breaks down. With n=20, two such misses are enough to erase the aggregate skill.

#### Gates
- **Phase 2 effective-N gate (TASKS.md: "effective N stays usable ≳10"): CLEARED.** Median N_eff 12.5 (JJAS) / 11.9 (MAM), min 6.3, at the a-priori bandwidth. Entropy-based, returned as a required field of every `AnalogOutcome` — there is no way to obtain an outcome without it. (At bandwidth 0.5 the median falls to ~5.3, below the gate; the a-priori choice was not tuned to pass it.)
- **Skill gate: NOT CLEARED.** Concurrent is indistinguishable from climatology; operational is worse than it.

#### Safeguards verified, not assumed
- **Target-year exclusion** — enforced at one line, `pool = pool[pool != target_year]`, a hard filter on the pool index rather than a zeroed weight that could be renormalised back in. Checked across all 20 folds: the target year never appears in its own pool; pool size 19; weights sum to 1. The held-out year is additionally excluded from the index standardisation, the tercile boundaries, and the climatology baseline.
- **Evidence separation survives Stage 2** — `advisory_evidence` / `evidence_source` and the Stage 1 `RegimePrior` pass through byte-identical; outcome probabilities are identical with and without evidence present. Stage 2 reads none of them.
- **Recency weighting** per Mondal & Mujumdar (2015), cited not re-derived; reported both on and off in the grid (it makes little difference: JJAS +0.039 on vs +0.081 off).

#### Honest verdict
**Stage 2 does not add demonstrable skill over Stage 1.** The mechanism it encodes is real — the concurrent ENSO–rainfall correlation is −0.44 and the per-year behaviour is physically sensible — but it does not convert into calibrated seasonal skill on 20 events, and the operationally available (pre-season) form is actively harmful.

The architecture already anticipated this: ARCHITECTURE.md now states that a Stage 2 conditioned on a climatological Stage 1 "downscales a base rate, and cannot manufacture year-specific skill that Stage 1 does not have." That is what the numbers say. The analog machinery is correct, safeguarded, and well-behaved on effective-N; what it lacks is a predictor with seasonal skill to condition on.

**Stage 4 not started.** Decision required before proceeding.

### D-18: Stage 2 re-scoped — analog **evidence**, not analog reweighting — **BUILT; one question open**

Run: `python -m src.models.run_stage1_prior`, log `artifacts/stage1_prior_schema.txt`. Stage 4 not started.

#### What changed and why
D-17 showed analog *reweighting* of probabilities fails, and fails worst at the only operationally valid lead (MAM RPSS **−0.249**, CI [−0.383, −0.136]) because pre-season Niño3.4 correlates **+0.054** with seasonal MCZ rainfall. Stage 2 therefore stopped touching the probabilities and now does the one thing the data supports: **look up what actually happened in the most similar past seasons, and disclose it as text next to Stage 1's unchanged climatology.**

#### Reuse, not reimplementation
`seasonal_analog_distances()` was **extracted** from `AnalogDownscaler.weights_for`, and the retired downscaler now **delegates** to it — the same extract-and-delegate pattern used for `day_of_year_frequencies()`. Consequence: the target-year leakage safeguard exists in exactly one line, in one function, with two callers, and cannot drift.

**Extraction verified byte-identical:** max weight difference **5.55e-17** across all 20 folds × both windows, and D-17's headline figures reproduce exactly (+0.0391 JJAS / −0.2491 MAM).

#### The headline finding — and it is not a flattering one
Across all 20 target years the K=5 analogs are:

| agreement | count |
|---|---|
| `divided` | **19** |
| `leaning` | 1 |
| `unanimous` | **0** |

**Not one year produces agreeing analogs.** This is exactly what an r = +0.054 predictor should produce, and the module reports it rather than hiding it. Example (2019, wettest season in the record):

> *"The 5 historical seasons whose pre-monsoon ENSO/IOD state most resembled 2019: 2010 was normal; 2017 was normal; 2016 was wet; 2015 was dry; 2009 was dry. These seasons diverged (2 dry, 2 normal, 1 wet), so they do not point to a single expectation. For example 2016 was wet while 2009 was dry, despite similar pre-monsoon ENSO/IOD state. Pre-monsoon ENSO/IOD state did not determine the outcome in these years."*

`_summarise()` has **no branch that emits a central expectation when the analogs are divided.** A confident-sounding average of two disagreeing seasons is more confident and less true than reporting the split — this was the D-17 failure mode (2000 and 2019) turned into a design constraint.

#### Two evidence mechanisms, traceable to source
`RegimePrior` now carries two independent, clearly-labelled evidence groups so Stage 4 never has to guess which process produced a sentence:

| Fields | Mechanism | Coverage |
|---|---|---|
| `advisory_evidence`, `evidence_source` | IMD **bulletin parsing** (trough position, D-16) | ~30% of JJAS dates |
| `seasonal_analog_evidence`, `seasonal_analog_years`, `seasonal_analog_detail`, `seasonal_analog_effective_n`, `seasonal_analog_agreement` | **historical fact lookup** (D-18) | all years, but 19/20 `divided` |

`attach_seasonal_analog()` uses `dataclasses.replace`, so the numeric block is *copied* rather than recomputed — evidence cannot alter it by construction. Asserted at runtime anyway: `probabilities`, `ci_lower`, `ci_upper` and `effective_n` all identical with and without evidence, both mechanisms attachable simultaneously without fusion.

#### Auditability
Per-analog **distance** and the entropy-based **effective N** are in the structured output, not only the prose (2019: N_eff 3.82 over 5 shown analogs, distances 0.68→2.23). `effective_n` here is explicitly an *audit* statistic — how concentrated the neighbourhood is — not a probability weight; nothing consumes it as forecast input.

#### Recency weighting: implemented, deliberately not in the live path
Mondal & Mujumdar (2015) motivates it and the retired downscaler applies it; D-17 reported it on and off (little difference). The evidence path does **not** apply it, because ranking shown analogs by recency as well as similarity would mean the named years are not simply the most similar ones — making the evidence harder for a farmer or reviewer to check against the record. Retained in `AnalogDownscaler` only for reproducing D-17.

#### The open question, stated plainly
The mechanism is correct, safeguarded, auditable, and honest. But **19 of 20 years produce a sentence that essentially says "these seasons disagreed."** Before Stage 4 renders any of this to a farmer, someone should decide whether that earns space in an advisory. It is defensible to include — it is checkable, it names real years, and it truthfully conveys that pre-season state carries little information. It is equally defensible to conclude that a sentence which almost always reports disagreement gives a farmer nothing to act on, and that the honest move is to show Stage 1's climatology and the IMD bulletin evidence alone.

This is a presentation decision, not a modelling one, and it should be taken deliberately rather than by default.

---

### D-19: farmer-facing evidence filter — `divided` analogs stay in the API, are withheld from the advisory — **CLOSED**

Resolves D-18's open question. Run: `python -m src.models.run_stage1_prior`.

#### The exact agreement rule (quoted from `src/models/seasonal_analog_evidence.py::_summarise`, not paraphrased)

```
k = len(analogs)                         # = DEFAULT_K = 5
modal   = max(counts, key=counts.get)    # tercile with the most analogs
modal_n = counts[modal]
spans_extremes = counts["dry"] > 0 and counts["wet"] > 0

if modal_n == k:                         -> "unanimous"
elif spans_extremes or modal_n <= k / 2: -> "divided"
else:                                    -> "leaning"
```

With k=5: `modal_n <= k/2` means `modal_n ∈ {1,2}` (pigeonhole floor is 2). So:
- **unanimous** — all 5 analogs in one tercile
- **divided** — at least one dry *and* one wet analog, OR the plurality tercile has ≤2 of 5
- **leaning** — plurality of 3 or 4, and not spanning both extremes

**Enumerated over the full 2000–2019 record: 19 `divided`, 1 `leaning` (2018: 0 dry / 2 normal / 3 wet), 0 `unanimous`.**

#### The evidence text is fully templated — verified branch by branch

`_summarise` returns one of exactly three f-strings, each built only from `k` (constant 5), `target_year` (int), the deterministic `listing` join, and the integer tercile counts:

| Branch | Template (condensed) |
|---|---|
| `unanimous` | `"{lead} All {k} ended {modal}. Note this is what those seasons did, not a forecast for {target_year}."` |
| `divided` | `"{lead} These seasons diverged ({d} dry, {n} normal, {w} wet), so they do not point to a single expectation.{pair} Pre-monsoon ENSO/IOD state did not determine the outcome in these years."` |
| `leaning` | `"{lead} {modal_n} of {k} ended {modal}, but not all ({d} dry, {n} normal, {w} wet). This is a historical tendency among close seasons, not a forecast."` |

`{lead}` = `"The {k} historical seasons whose pre-monsoon ENSO/IOD state most resembled {target_year}: {listing}."` and `{pair}` is an optional `"For example {yr A} was {X} while {yr B} was {Y}, despite similar pre-monsoon ENSO/IOD state."`, added only when the nearest and farthest dry/wet analogs disagree. **No LLM, no free text, no randomness.** As auditable as the probabilities.

#### The filter

| Piece | Where it lives | Behaviour |
|---|---|---|
| `ADVISORY_ELIGIBLE_AGREEMENT` | `climatological_prior.py` | `("leaning", "unanimous")` |
| `RegimePrior.seasonal_analog_advisory_visible` | property, derived | `agreement in ADVISORY_ELIGIBLE_AGREEMENT`; not stored, so `attach_seasonal_analog` and the numeric invariant are untouched |
| `advisory_evidence_lines(prior)` | `climatological_prior.py` | **the one API↔farmer boundary.** Returns bulletin line when present; analog line **only** when `advisory_visible`. Order: analog context first, then bulletin. |
| `advisory_evidence_technical_view(prior)` | `climatological_prior.py` | full view for demo/API; adds `seasonal_analog_suppressed_reason` when a `divided` line was withheld |

`divided` analog evidence is handled exactly as a null `advisory_evidence` from the bulletin path — the generator skips it. **The data is not deleted:** `seasonal_analog_evidence` / `_years` / `_detail` / `_effective_n` / `_agreement` stay in the `RegimePrior` and in the schema. Asserted at runtime: divided-case data present in the technical view, absent from `advisory_evidence_lines`.

Worked (2019, `divided`): schema carries the full 5-year analog listing and `seasonal_analog_advisory_visible: false`; `farmer_facing_evidence_lines` contains only the IMD bulletin sentence. For 2018 (`leaning`) the analog sentence *is* in `farmer_facing_evidence_lines`.

Schema additions: `seasonal_analog_advisory_visible` (bool), `farmer_facing_evidence_lines` (list[str]).

**Stage 4 not started.** When built, its advisory generator consumes `advisory_evidence_lines(prior)` rather than the raw fields.

### D-20: Stage 4 decision engine built; ICAR citation **STILL OPEN and now contested** — **BUILT / one item open**

Run: `python -m src.models.run_stage4_decision`, log `artifacts/stage4_decision_example.txt`. Last core stage.

#### D-C enforced by construction, not by care

D-C closed the cost-loss threshold error once. This module makes it unrepresentable rather than merely discouraged:

- **One scoring function.** Both branches go through `_expected_loss(probs, losses, branch)` — a dot product of the *full* 3-class probability vector with a 3-class loss vector. There is no code path that yields a scalar branch. 4 call sites (both branches at the point estimate, plus the envelope).
- **`_assert_is_expectation()` runs on every call** and raises if the probability vector is not a full normalised distribution over all regimes, or if the loss vector is *constant across regimes* — the latter being precisely "one probabilistic side and one flat number". Both rejections are exercised in the run log.
- **No threshold token in executable code.** Verified by AST-stripping docstrings: `C/L` appears only in the docstring explaining what not to do (the same prose-vs-code false positive already hit on `week` in the analog module, so the check strips docstrings before scanning).

The formulation, both sides over the same distribution:

```
E[loss|SOW]  = P(active)·0        + P(break)·L_reseed + P(transition)·(alpha·L_reseed)
E[loss|WAIT] = P(active)·L_delay  + P(break)·0        + P(transition)·(beta·L_delay)
recommend SOW iff E[loss|SOW] < E[loss|WAIT]
```

`theta = L_reseed/L_delay` is **reported, never used as a threshold** — the theta sensitivity table re-computes both expectations at each value rather than comparing a probability to a ratio.

#### Uncertainty propagated, and honestly labelled
The decision is evaluated at the point estimate and at both ends of a sensitivity envelope built from Stage 1's per-class bootstrap CI. **This is explicitly NOT a joint credible interval** — `ci_lower`/`ci_upper` are marginal percentiles that do not jointly form a distribution, so `_envelope()` sets P(break) to a bound and renormalises the rest proportionally. Labelled as a sensitivity probe everywhere it is reported. A recommendation that holds only at the central estimate is flagged `robust=False` and the advisory text adds *"this is a close call."*

#### D-19 boundary verified by inspection, not assumption
`check_d19_boundary()` parses `decision_engine`'s AST and confirms: `advisory_evidence_lines` is **imported**, is **called**, and **no raw evidence field** (`advisory_evidence`, `seasonal_analog_evidence`, `seasonal_analog_years`, …) is read anywhere in the module. Result: `raw evidence fields read directly: NONE`. The divided-case suppression is therefore inherited automatically rather than reimplemented.

#### Worked example (2018-07-15, soybean — 2018 is the one `leaning` year, so analog evidence is farmer-facing)

| regime | P | L_sow | L_wait | contrib_sow | contrib_wait |
|---|---|---|---|---|---|
| active | 0.0767 | 0 | 12,000 | 0.0 | 920.0 |
| break | 0.0967 | 18,000 | 0 | 1,740.0 | 0.0 |
| transition | 0.8267 | 7,200 | 4,800 | 5,952.0 | 3,968.0 |
| | | | **totals** | **E[loss\|SOW] = 7,692** | **E[loss\|WAIT] = 4,888** |

theta = 1.50 → **WAIT**, margin −2,804 INR/ha. Envelope: WAIT at point, `break_low` and `break_high` alike → **robust = True**. theta sweep flips to SOW at L_reseed ≤ 9,000 (theta ≤ 0.75), with both expectations recomputed each time.

Both farmer-facing evidence lines appear (analog + bulletin), and the advisory carries the provisional-parameters disclosure.

#### ICAR citation status: **STILL OPEN — and the attempt made it worse**

Reported plainly, as asked. Tracing D-2's soybean threshold did not confirm it:

- **50–75 mm** (D-2, AI-generated) — never traced to any source.
- **100 mm** — attributed to "ICAR – National Soybean Research Institute, Indore" by a **trade website**, which cites **no bulletin, number or date**.
- **The two figures are incompatible.** A 50 mm vs 100 mm difference would change a real sowing decision, so D-2's number cannot be inherited as settled.
- **The primary source could not be retrieved:** a candidate ICAR-IISR bulletin URL was found, but `iisrindore.icar.gov.in` and `krishi.icar.gov.in` **do not resolve from this network** (only `icar.org.in`/`icar.gov.in` do). That is a network result and says nothing about the document's contents — a later attempt elsewhere may succeed.

**Enforced in code:** `sowing_rain_threshold_mm=None` for every crop; all `CropEconomics.verified=False`; every `DecisionResult` carries `uses_unverified_parameters=True` and renders a disclosure in both the technical output and the farmer-facing advisory. **No ICAR number is hardcoded.** The monetary values are illustrative placeholders and are not sourced at all — they demonstrate the method, and must be replaced with locally sourced figures before anyone acts on a recommendation.

D-2 remains **OPEN**; RESEARCH.md now carries a new **§ Contested** section recording both figures and the failed retrieval.

### D-21: Delivery layer built; **no target language is specified anywhere in the repo** — **BUILT / one blocking item open**

Run: `python -m src.delivery.run_delivery_demo`, log `artifacts/delivery_demo_2018.txt`, SVG `artifacts/delivery_risk_indicator_2018.svg`. Integration work — follows the Stage 1/2/4 interfaces, invents no new data shapes.

#### Which language? — quoted, not assumed

Every reference to language in the repo, verbatim:

| File | Text |
|---|---|
| `ARCHITECTURE.md` | *"short **regional-language** message"* |
| `README.md` | *"delivered to the farmer's phone **in their own language**"* |
| `AGENTS.md` | *"**Regional language** output must be reviewable by someone who reads that language before demo"* |
| `CLAUDE.md` | GKMS is *"vernacular"* — describing a **competitor**, not a spec |

**No specific language (Hindi, Marathi, Telugu, …) is named anywhere in the repo.** So the build does not pick one silently:

- **`en` is the default and the only rendering treated as verified.** It is what `WhatsAppSender` sends unless explicitly overridden.
- **`hi` (Hindi) is a worked stub.** Hindi is the single most defensible choice — Hindi-belt sub-divisions (MP ×2, Rajasthan ×2, UP ×2, Bihar, Chhattisgarh, Jharkhand) are the plurality of the 18 MCZ-relevant sub-divisions (D-19). But it is **machine-generated and unreviewed**: every `hi` output carries a `MACHINE TRANSLATION, NOT REVIEWED` banner, and `WhatsAppSender.send()` raises unless `allow_unverified_language=True` is passed on purpose ("never a real farmer").
- The frame is **fully templated per language** — fixed strings with slot substitution, no per-instance free translation — so a reviewer checks ~12 template strings, not every output. The D-19 evidence lines stay in English inside `hi` (they are themselves templated English from `trough.py` / `seasonal_analog_evidence.py`; translating them is part of the open task).
- **AGENTS.md's "reviewable by someone who reads that language before demo" is OPEN and blocking.** Target language(s) must be chosen and every template natively reviewed before any real send.

#### D-19 boundary — held through the delivery layer, AST-verified

`src/delivery/advisory.py::render` calls `advisory_evidence_lines(prior)` directly and `_assert_boundary_respected()` checks it equals `DecisionResult.evidence_lines` (Stage 4's own boundary-sourced copy). The demo's `_check_no_raw_evidence_access()` parses the module AST: `advisory_evidence_lines` **imported ✓**, raw evidence fields (`advisory_evidence`, `seasonal_analog_*`) read directly **NONE**. So the divided-case suppression from D-19 carries through automatically.

#### The ICAR gap is rendered to the farmer, not just the technician

`DecisionResult.disclosure()` is a long technical string. The advisory templates carry a **separate short plain-language line** shown whenever `result.uses_unverified_parameters` is True (currently always — D-20):

> *"IMPORTANT: the rupee figures above are illustrative examples, not verified local prices. Check current input and reseeding costs with your Krishi Vigyan Kendra before deciding."*

It is in the WhatsApp message body and the risk card, not only the technical dump.

#### Risk display — one region, one colour, by design

`RegionalRiskIndicator` renders a **single** probability triple + recommendation for the whole MCZ — because that is exactly what Stage 1 computes (MCZ-mean, 2684 cells; no per-block number exists). The optional SVG is **one uniform rectangle**, with *"Whole monsoon core zone shown as one colour by design: regional estimate, NOT resolved to individual blocks or villages"* rendered **inside the image**, plus the MCZ box coordinates and "climatological base rate, not a forecast". A judge skimming the map cannot mistake it for block-resolved. ARCHITECTURE.md's "block-level choropleth" is now flagged aspirational.

#### No live IMD fetch on the delivery path

The delivery demo consumes `data/cache/bulletin_texts.json` (D-15/D-16 batch pipeline) and **asserts the cache exists rather than fetching**. `_no_live_fetch_check()` + an AST scan for `internal.imd.gov.in` / `requests.get` / `urlopen` in executable code (docstrings stripped — the module docstring mentions the host as prose, the same false-positive class already hit on `week` and `C/L`). Nothing in `src/delivery/` calls `internal.imd.gov.in`.

#### Twilio — built, nothing sent

`WhatsAppSender(dry_run=True)` is the default. Going live needs `dry_run=False` **and** `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` in the environment; absent either, it returns a dry-run result explaining which. No credentials in the repo. Sandbox join flow (`SANDBOX_JOIN_HELP`) is printed by the demo. `twilio` 9.11.0 added to `requirements.txt`; imported only inside a real send.

#### The 24-hour WhatsApp session window — now an explicit precondition (added 2026-09-08)

**The original build silently assumed an open session.** `send()` called `client.messages.create()` directly — no opt-in check, no inbound-message tracking, no session-window state anywhere in the code or any onboarding flow. A live send to a number that never opted in would have been rejected by Twilio (error 63015/63016) and caught only after the fact via `SendResult.status`.

WhatsApp permits free-form outbound messages **only within 24 hours of the recipient's last inbound message**. Outside that window needs an **approved Meta message template**.

- **(a) Demo path — sufficient, and exactly what Twilio Sandbox already enforces.** The farmer sends the sandbox join code (or any message); a 24h window opens; advisories flow. No Meta review, no template.
- **(b) Production path — out of scope for this build.** An approved Meta template for send-anytime delivery, requiring WhatsApp Business API onboarding and template approval.

**Code change (minimal, matching the `allow_unverified_language` precedent):** `send()` now takes `recipient_in_session: bool = False`. The caller must affirm the recipient messaged within 24h (or just joined); this module does **not** track that state. Default `False` → dry-run result naming the blocker. A live send that still lands outside the window has Twilio's error (`_OUT_OF_SESSION_CODES`) surfaced verbatim in `status` with a plain-language hint. The demo prints what an un-opted-in recipient produces:

```
not sent (no credentials in env; recipient_in_session=False (no confirmed opt-in / 24h window))
```

This is **not** a full opt-in registry — tracking real inbound timestamps per farmer is production work (path b). It converts a silent assumption into a declared precondition.

#### Superseded
`src/models/decision_engine.py::advisory_text` is now a **terse inline preview for the Stage 4 worked example only** — its docstring says so and points to `src/delivery/advisory.py::render` as the real path. Not left as a competing implementation.

#### Final advisory text — 2018-07-15, soybean (the Stage 4 / D-20 case)

```
VarshaSanket advisory - 2018-07-15 - soybean
Recommendation: WAIT. Sowing now carries the higher risk.
Chance of a dry break spell around this date: 10%. Based on 20-year averages for this date, not a forecast for this year.
Expected loss if you sow now: about Rs 7,692/ha. If you wait: about Rs 4,888/ha.
Supporting information:
- The 5 historical seasons whose pre-monsoon ENSO/IOD state most resembled 2018: 2001 was normal; 2006 was wet; 2003 was wet; 2008 was wet; 2012 was normal. 3 of 5 ended wet, but not all (0 dry, 2 normal, 3 wet). This is a historical tendency among close seasons, not a forecast.
- IMD Extended Range bulletin places the monsoon trough north of its normal position in week 2, which IMD's glossary associates with a break in rainfall over central India.
Regional estimate for the monsoon core zone (central India). Not resolved to individual blocks or villages.
IMPORTANT: the rupee figures above are illustrative examples, not verified local prices. Check current input and reseeding costs with your Krishi Vigyan Kendra before deciding.
```

1067 chars (within WhatsApp's 1600-char single-message limit). 2018 was chosen deliberately: it is the one `leaning` analog year (D-19), so the seasonal-analog line *is* farmer-facing here; for the 19 `divided` years only the bulletin line would appear.

---

## Handoff notes

*(Append session notes here — what changed, what was decided, what the next agent should know.)*

**Session — project scaffolding created**
Established docs structure. Ran final verification pass on load-bearing claims. Two corrections found: the 120M impact figure was wrong (→93.09M, NSO 77th Round) and imdlib's real resolution is 0.25°/~25km, coarser than previously implied — logged as D-3. `imdlib` confirmed real, MIT, on PyPI. Next agent: start Phase 0, and treat Gate C as urgent rather than background.

**Session — Phase 0 data-reachability probe (2026-09-07)**
Ran the three data-existence checks in TASKS.md Phase 0. No modeling code written; no `src/` created. All work was throwaway probes in scratchpad. Results:

1. **IndiaWeatherBench — loads. ✅** Repo is `tungnd/IndiaWeatherBench` on HF (Tung Nguyen = arXiv author; not gated). Opened `climatology_2000_2017.zarr.zip` via HTTP-range zip reads and decoded real arrays: `APCP` full shape (1460, 256, 256), `TMP_prl` (1460, 7, 256, 256); grid 256×256 at 0.12° over 6.12–36.72°N / 66.6–97.2°E; levels [925,850,700,600,500,250,50] hPa. Also pulled one training timestep `indibench_h5/train/2010-06-15_00.h5` (11.3 MB) and loaded all 43 fields with h5py — APCP field min/mean/max 0.0 / 0.36 / 51.8 mm, physically sane. Corrections logged: **D-6** (43 channels, not 39), **D-8** (no subset mechanism — monolithic 9/106/101 GB zips; range-read workaround demonstrated), **D-9** (CC-BY-NC-SA, non-commercial).

2. **NOAA CPC indices — partially as documented. ⚠️** CPC Niño3.4/ENSO endpoints are live (`oni.ascii.txt`, `wksst9120.for`, `ersst5.nino.mth.91-20.ascii`, `detrend.nino34.ascii.txt`), all returning data through Aug 2026. **DMI is a NOAA PSL product, RMM1/RMM2 is Australian BoM — neither is CPC**, and only RMM is daily (Niño3.4 is weekly/monthly, DMI monthly). One guessed URL (`psl.noaa.gov/data/correlation/dmi.data`) 404'd and is reported as dead, not swapped. Full table + working URLs in **D-7**.

3. **imdlib — works, resolution confirmed. ✅** `pip install imdlib` → 0.1.21. `imdlib.get_data("rain", 2018, 2018)` downloaded from `imdpune.gov.in` in ~107 s; `get_xarray()` → dims (time 365, lat 129, lon 135), **0.25° grid** over 6.5–38.5°N / 66.5–100.0°E, `-999.0` ocean fill, July 2018 all-India mean ~8.85 mm/day. DATA.md's "0.25° (~25km)" and D-3 are **independently confirmed**. (Note: imdlib `tmax`/`tmin` are 1.0°, coarser — only `rain` is 0.25°.)

Next agent: Gate A and Gate C are still open and still block everything. Before writing `src/data/`, note D-8 (range-read pattern) and D-7 (mixed-cadence index series). DATA.md has inline `[FLAG: see DISCUSSION D-n]` markers pending sign-off — resolve those into clean DATA.md edits once reviewed.

**Session — IndiaWeatherBench provenance + size check (2026-09-07)**
Two follow-ups on the Phase 0 findings, both now **closed**:
- **D-11 (provenance):** `tungnd/IndiaWeatherBench` is the authors' repo — confirmed, not inferred. The HF card itself does not self-identify, and the paper names Google Drive rather than HF; but the paper's cited GitHub repo (`github.com/tung-nd/IndiaWeatherBench`) links to this exact HF dataset with a 🤗 badge, and the HF account fullname is "Tung Nguyen" (paper's corresponding author). Chain: paper → GitHub → HF.
- **D-12 (size):** `indiaweatherbench_h5.zip` actual listed size is **105.84 GB**. The ~330 GB figure came from multiplying the *uncompressed* per-file size (11.29 MB × 29,220) — the zip stores every member DEFLATE-compressed at ~3.12×. Both numbers are real: 106 GB download, ~330 GB extracted. `src/data/` should use range-reads, not full extraction (~330 GB disk).
DATA.md HuggingFace row updated with the confirmed provenance status and corrected sizes.

**Session — Phase 1 Stage 1 built and validated (2026-09-07)**
Built the Regime Forecaster end to end and ran its isolation gate. **The gate FAILED and work stopped there — Phase 2 was not started.** Full numbers in D-14; D-13 logged as given and cross-checked against the implementation.

What exists now (`src/`, first code in the repo):
- `src/data/indices.py` — Niño3.4 (CPC, weekly), DMI (PSL, monthly), RMM1/RMM2 (BOM, daily), all parsed from live endpoints
- `src/data/imd_rainfall.py` — 20 yr IMD 0.25° daily rainfall → MCZ mean (2684 valid cells, 18–28°N / 66.5–88°E)
- `src/data/iwb_fields.py` — coarse H500/T850 over the MCZ from IndiaWeatherBench raw zarr. **The level dimension is chunked at 1**, so one pressure level is reachable by HTTP-range read: 595 MB fetched instead of a 101 GB download. This is the reusable trick for all future field access.
- `src/features/labels.py` — Rajeevan active/break/transition; reproduces the July 2002 monsoon failure unprompted
- `src/features/trajectory.py` — 41 t−30→t features with per-source publication lags
- `src/models/regime_forecaster.py` — XGBoost; `lead_days` is required and must be positive, so a nowcaster cannot be built by accident (CLAUDE.md Rule 3)
- `src/eval/backtest.py`, `src/eval/run_phase1.py` — LOYO harness, the only place metrics are computed

Next agent: **do not build Stage 2.** Read D-14 and pick a Phase 1R option first. Three doc/code corrections were made along the way where a file described its own behaviour incorrectly (a stale "no hyperparameter tuning" docstring after inner-fold tuning was added; a cached-fields path that logged "0 MB fetched") — if you touch those modules, keep the docstrings honest, since these files are the evidence trail for a number.

**`src/` layout deviates from AGENTS.md.** AGENTS.md says the modelling agent owns `src/stages/`. Stage 1 was built as `src/models/regime_forecaster.py` with feature construction split into `src/features/` and metrics isolated in `src/eval/` (the latter matches AGENTS.md). Rationale: Stage 1's model, its features, and its evaluation are separable concerns and only one stage exists so far. If Phase 1R proceeds to a real multi-stage build, either rename to `src/stages/` or update AGENTS.md — flagged here rather than silently reorganised. `requirements.txt` and `.gitignore` were added at first commit (README referenced a `requirements.txt` that did not exist); versions are pinned to what produced the D-14 numbers. `data/` is gitignored (~490 MB of acquired IMD GRD + IWB caches); the loaders recreate it.

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

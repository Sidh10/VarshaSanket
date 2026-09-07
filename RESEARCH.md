# RESEARCH — Verified Claims & Debunked Registry

Every factual claim this project makes, with verification status. **Check here before asserting anything.**

Status codes: ✅ verified against primary source · ⚠️ verified via secondary source only · ❌ debunked, do not use

---

## § Verified — safe to cite

### Core method literature

| Claim | Source | Status |
|---|---|---|
| Analog Ensemble is an established probabilistic forecasting method | Delle Monache, L. et al. (2013), *Monthly Weather Review* 141:3498 | ✅ |
| Predictor screening introduces more artificial skill than coefficient fitting (0.36–0.71 vs ~0.06–0.14 in his experiments) | Michaelsen, J. (1987), *J. Climate & Applied Meteorology* 26:1589–1600 | ✅ verified against original PDF |
| ISM onset predictable at seasonal lead with RMSE 4.5–5.4 days, correlation 0.5–0.7; 80% accuracy within ±7 days; 15 years training data sufficient | Mitsui, T. & Boers, N. (2021), *Environ. Res. Lett.* 16:074024, DOI 10.1088/1748-9326/**ac0acb** | ✅ verified against original PDF |
| IMD's operational onset forecast had 36% overlap between model-definition and verification data; a competing published method scored 73% vs climatology's 75% | Bürger, G. (2019), arXiv:1907.08114 | ✅ |
| Indian extreme rainfall is non-stationary; local temperature is a dominant driver | Mondal, A. & Mujumdar, P.P. (2015), *J. Hydrology* 521:217–231 | ✅ |
| Analog ensembles have been applied to Indian precipitation (NW Himalaya, station scale) | Singh & Kumar (2020), *Meteorology and Atmospheric Physics*, DOI 10.1007/s00703-019-00694-5 | ✅ |
| Active/break spell prediction ~2 weeks ahead is established and operational | Sahai, A.K. et al. (2013), IITM | ⚠️ |

### Datasets

| Claim | Source | Status |
|---|---|---|
| IndiaWeatherBench: 12km, 6-hourly, 2000–2019, pre-split train/val/test; **43 distinct channels, 39 used as ML model input** (was recorded here as "39 channels" — corrected 2026-09-07 against the paper + the live HF dataset; see DISCUSSION D-6) | Nguyen, T. et al. (2025), arXiv:2509.00653 | ✅ |
| BharatBench: ~100km regridded IMDAA, 1990–2020, published CNN/ConvLSTM baselines | Choudhury, A., Panda, J. & Mukherjee, A. (2024), arXiv:2405.07534 | ✅ |
| `imdlib` downloads IMD gridded rainfall/temperature; MIT licensed; on PyPI | github.com/iamsaswata/imdlib · imdlib.readthedocs.io | ✅ |
| **IMD gridded rainfall via imdlib is 0.25° (~25km)** — coarser than block level | imdlib docs | ✅ **important limitation** |
| NOAA CPC publishes **ENSO/Niño3.4** indices as free plain-text series, no registration (weekly OISST + monthly ERSST — *not daily*) | cpc.ncep.noaa.gov | ✅ verified live 2026-09-07 |
| ~~NOAA CPC publishes IOD and MJO RMM indices~~ — **partly wrong.** DMI/IOD is a **NOAA PSL** product (monthly); RMM1/RMM2 is **Australian BoM** (daily). CPC's own MJO index is a different quantity (pentad velocity-potential). See DISCUSSION D-7 | psl.noaa.gov / bom.gov.au | ✅ corrected 2026-09-07 |
| Twilio WhatsApp Sandbox is free, requires no business verification | twilio.com docs | ✅ |

### Competitive landscape

| Claim | Status |
|---|---|
| GKMS provides 5-day block-level agromet advisories, vernacular, ~22M farmers, twice weekly | ✅ |
| Mission Mausam / GPLWF launched 24 Oct 2024 with Ministry of Panchayati Raj; delivered via e-GramSwaraj, Meri Panchayat, Mausamgram; **≤10 day horizon, currently 12km** (1km is a stated future goal) | ✅ |
| IITM ERPAS/ERPv2 produces operational extended-range active/break forecasts; **data access restricted** on IRI Data Library | ✅ |
| 199 District Agromet Units (DAMUs) wound up from March 2024 | ✅ |
| NAMASTE portal (Ministry of Ayush) is real — standardized Ayush terminology, ICD-11 integrated | ✅ *(context only, not used by this project)* |

### Impact figures

| Claim | Source | Status |
|---|---|---|
| **93.09 million agricultural households in India** (2018–19) | NSO 77th Round / Situation Assessment Survey, published Sept 2021 | ✅ **use this figure** |
| 101.98 million operational holdings (2018–19) | Same source | ✅ |
| Total rural households: 172.44 million, of which ~54% are agricultural | Same source | ✅ |

---

## § Debunked — do NOT use

These all surfaced during research as confident, plausible, specific claims. All are false. Several **resurfaced more than once** across different tools, so they need active guarding against.

| ❌ Claim | Why it's wrong |
|---|---|
| **"120 million farm households"** | **Inflated.** The authoritative NSO 77th Round figure is **93.09 million** agricultural households (or ~102 million operational holdings). The 120M figure was never sourced. Earlier drafts of the pitch used it — correct anywhere it appears. |
| **`api.imd.gov.in` real-time API** (also `mausam.imd.gov.in/responsive/apis.php`, `imdgeospatial.imd.gov.in`, "IMDAPIs Portal", IP-whitelisting process) | Claimed by three separate AI research passes with different URLs each time. Never independently confirmed to exist. **Do not build against it.** |
| **"Barnston & Livezey (1987), Cross-Validation and Statistical Predictability in Meteorology, J. Clim. Appl. Meteorol. 26:1589–1608"** | Fabricated. That journal/volume/page is **Michaelsen (1987), single author, different title** — verified against the original PDF. Barnston & Livezey are real scientists whose actual 1987 work is on circulation pattern classification. |
| **"Jaiswal, Kishtawal & Bhomia (2018)"** analog multi-model ensemble for monsoon | Never located despite repeated search. Do not cite. |
| **SIH26080 / SIH26081 described as "past hackathon teams" with "judge feedback"** | They are **2026 sibling problem statements** from the same sponsor — currently open, zero prior submissions. An entire fabricated prior-art narrative was built on this. |
| **"Mausam Gram" 1km block-level forecasts as current capability** | The Oct 2024 launch is real, but current resolution is **12km**; 1km is a stated future objective, not a shipped capability. |
| **Cost-loss rule `sow if P > C/L`** | Superseded — sowing is the risky action, not the protective one. Use expected-loss comparison (see ARCHITECTURE.md Stage 4). |
| **Single held-out test year (2019) as validation** | Superseded — gives ~1 onset event. Meaningless sample. Use leave-one-year-out. |

---

## § Known unverified — flagged, not used as load-bearing

- ~~Exact ICAR sowing thresholds per crop (soybean 50–75mm, groundnut 50mm, cotton 50–100mm) — plausible and consistent across sources~~ — **STATUS DOWNGRADED 2026-09-07 after a tracing attempt. Now actively doubted, not merely untraced.** See § Contested below and DISCUSSION D-20.
- IITM ARDC THREDDS (`ardc.tropmet.res.in`) accessibility — appears open, listed on AIKosh, but not tested end-to-end.

---

## § Contested — a figure with two incompatible values, neither traced to a primary source

### ICAR soybean sowing rainfall threshold — **UNRESOLVED, do not use**

Attempted trace, 2026-09-07 (for Stage 4). The attempt **weakened** the claim rather than confirming it:

| Value | Attribution | Primary source? |
|---|---|---|
| **50–75 mm** | D-2 / earlier AI-generated research | **None.** Never traced. |
| **100 mm** | "ICAR – National Soybean Research Institute, Indore", via `global-agriculture.com` (trade site) | **None.** The page cites *no bulletin, number, or date.* Quote: *"farmers are strongly advised to sow soybean only after the monsoon arrives in their area and after receiving at least 100 mm of rainfall."* |

**The two figures are incompatible** (50–75 mm vs 100 mm — a difference that would change a sowing decision). That disagreement is itself evidence that the D-2 number should not be inherited as settled.

**Primary source could not be reached.** A candidate ICAR-IISR extension bulletin URL was identified (`iisrindore.icar.gov.in/pdfdoc/ExtensionBulletin2023E_3.pdf`) but **the host does not resolve from this network** — DNS failure on `iisrindore.icar.gov.in` and `krishi.icar.gov.in`; only `icar.org.in` / `icar.gov.in` resolve (144.16.144.82). So the bulletin is neither confirmed nor refuted; it was simply not retrievable here. *That is a network result, not evidence about the document's contents* — a later attempt from a different network may succeed.

**Consequence, enforced in code:** `src/models/decision_engine.py` sets `sowing_rain_threshold_mm=None` for every crop and marks all `CropEconomics` as `verified=False`. Any `DecisionResult` built from them carries `uses_unverified_parameters=True`, and both the worked example and the farmer-facing advisory render an explicit provisional-parameters disclosure. **No ICAR number is hardcoded anywhere.**

**To close this:** retrieve an actual ICAR/IISR/SAU publication, record its title, number and year here, and only then set the threshold and flip `verified=True`.

---

## Verification practice for new claims

1. Search for the primary source, not a summary
2. If the claim includes a number, confirm the number in the source — not just the topic
3. If the claim includes author names, confirm the author list (two decks reviewed in this project had real papers with **padded or wrong author lists**)
4. Record the result here with a status code
5. If it fails, add it to § Debunked with the reason — the registry is as valuable as the verified list

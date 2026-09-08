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
| WhatsApp free-form outbound messages are allowed only within **24 h of the farmer's last inbound message**; outside that needs an approved Meta template. Demo path (a): farmer sends the sandbox join code → 24 h window opens → advisories flow, no Meta review. Production path (b): approved template, WhatsApp Business API onboarding, **scoped not built**. See DISCUSSION D-21. | Twilio / Meta WhatsApp policy docs | ✅ |

### Competitive landscape

| Claim | Status |
|---|---|
| GKMS provides 5-day block-level agromet advisories, vernacular, ~22M farmers, twice weekly | ✅ |
| Mission Mausam / GPLWF launched 24 Oct 2024 with Ministry of Panchayati Raj; delivered via e-GramSwaraj, Meri Panchayat, Mausamgram; **≤10 day horizon, currently 12km** (1km is a stated future goal) | ✅ |
| IITM ERPAS/ERPv2 produces operational extended-range active/break forecasts; **data access restricted** on IRI Data Library | ✅ |
| 199 District Agromet Units (DAMUs) wound up from March 2024 | ✅ |
| **`imdgeospatial.imd.gov.in/agromet.html` launcher page; hosts links to KALP and SANKALP** — Accessed 2026-09-08: both KALP (`webgis.imd.gov.in/agro/`, Django + Leaflet, 0.125° GFS-derived grid, 5-day rolling retention) and SANKALP (`mausamsankalp.imd.gov.in/`, Flask + Plotly, 30-year dry/wet-spell climatology at block scale) verified live, no login/CAPTCHA gates. Resolves to 103.215.208.101. See D-25 full analysis. | ✅ **(formerly wrongly listed in § Debunked)** |
| NAMASTE portal (Ministry of Ayush) is real — standardized Ayush terminology, ICD-11 integrated | ✅ *(context only, not used by this project)* |

### Agronomic thresholds

| Claim | Source | Status |
|---|---|---|
| **Soybean sowing rainfall threshold: minimum 100 mm** — verbatim: *"Farmers are advised to sow their soybean crop this week in case of receipt of minimum 100 mm rainfall in their area."* | ICAR-Indian Institute of Soybean Research (ICAR-IISR), Khandwa Road, Indore-452001. *Weekly Advisory for Soybean Farmers (4-10th July 2022)*, F.No. टेक 10-6/2022, dated 04.07.2022. [PDF](https://icar.org.in/sites/default/files/2023-02/Weekly%20Advisory%20for%20Soybean%20Farmers%204th-10th%20July%202022.pdf) | ✅ **verified against the original PDF, read page-by-page** — but **cite it with its scope limit, below** |

**SCOPE LIMIT — cite this figure only with the qualifier.** It is a **single-week operational advisory**, issued for one week of a season the same document calls *"uneven and erratic"*. It is **not** a demonstrated standing ICAR-IISR constant, and two negative findings bound it (both from D-29):

1. The **very next week's** advisory (11–17 July 2022) does **not** repeat the 100 mm figure. It treats the sowing window as *closing*: farmers who have not sown are told to *"go for sowing of alternate remunerative crop."*
2. The **ICAR Kharif Agro-Advisories for Farmers 2025** (310 pp, national) is **silent on any soybean sowing-rain trigger**. Its only "100 mm" hits are **maize** (75–100 mm).

**Do not write "ICAR says sow soybean after 100 mm" as a standing rule.** Write "ICAR-IISR's July 2022 weekly advisory told farmers to sow after ≥100 mm that week."

**Consumed nowhere.** `sowing_rain_threshold_mm=100.0` is advisory context in `CROP_DEFAULTS` only — AST-verified as read by no code. It does not enter the decision path, and `verified` stays `False` because it sources the rainfall number, not the crop economics. D-29.

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
| **`api.imd.gov.in` real-time REST API** (with IP-whitelisting authentication; also `mausam.imd.gov.in/responsive/apis.php`, "IMDAPIs Portal") | Claimed by three separate AI research passes with different URLs each time. Never independently confirmed to exist. **Do not build against it.** |
| **"Barnston & Livezey (1987), Cross-Validation and Statistical Predictability in Meteorology, J. Clim. Appl. Meteorol. 26:1589–1608"** | Fabricated. That journal/volume/page is **Michaelsen (1987), single author, different title** — verified against the original PDF. Barnston & Livezey are real scientists whose actual 1987 work is on circulation pattern classification. |
| **"Jaiswal, Kishtawal & Bhomia (2018)"** analog multi-model ensemble for monsoon | Never located despite repeated search. Do not cite. |
| **SIH26080 / SIH26081 described as "past hackathon teams" with "judge feedback"** | They are **2026 sibling problem statements** from the same sponsor — currently open, zero prior submissions. An entire fabricated prior-art narrative was built on this. |
| **"Mausam Gram" 1km block-level forecasts as current capability** | The Oct 2024 launch is real, but current resolution is **12km**; 1km is a stated future objective, not a shipped capability. |
| **Cost-loss rule `sow if P > C/L`** | Superseded — sowing is the risky action, not the protective one. Use expected-loss comparison (see ARCHITECTURE.md Stage 4). |
| **Single held-out test year (2019) as validation** | Superseded — gives ~1 onset event. Meaningless sample. Use leave-one-year-out. |

---

## § Known unverified — flagged, not used as load-bearing

- ~~Exact ICAR sowing thresholds per crop (soybean 50–75mm, groundnut 50mm, cotton 50–100mm) — plausible and consistent across sources~~ — **STATUS DOWNGRADED 2026-09-07 after a tracing attempt. Now actively doubted, not merely untraced.** **SOYBEAN SUPERSEDED 2026-09-08 by D-29** — the primary bulletin was retrieved and gives **100 mm**, not 50–75 mm; see § Verified below. **Groundnut (50 mm) and cotton (50–100 mm) remain untraced and are unchanged** — still not used, still `None` in code. See § Contested below and DISCUSSION D-20 / D-29.
- IITM ARDC THREDDS (`ardc.tropmet.res.in`) accessibility — appears open, listed on AIKosh, but not tested end-to-end.

---

## § Contested — a figure with two incompatible values, neither traced to a primary source

### ICAR soybean sowing rainfall threshold — ~~**UNRESOLVED, do not use**~~ → **SUPERSEDED 2026-09-08 by D-29**

> **SUPERSEDED, NOT DELETED.** The record below is the state of this question on 2026-09-07 and is kept because it documents how the figure was contested and why the D-2 number was refused. **It was resolved on 2026-09-08 (D-29): the primary ICAR-IISR bulletin was retrieved from `icar.org.in` and it does say 100 mm.** The full citation and its scope limit are in § Verified above. Two corrections to what is written below: the 100 mm figure is **no longer** attributable only to a trade site, and the retrieval failure was **host-specific** (`iisrindore.icar.gov.in` still does not resolve; `icar.org.in` does and served the document).
>
> **What D-29 did NOT resolve:** the crop economics. `l_reseed`/`l_delay` remain unsourced illustrative placeholders, so `verified` stays `False` for every crop and the disclosure still renders. D-2's 50–75 mm also remains untraced — see D-29 for why it is plausibly a misattributed maize figure.

Attempted trace, 2026-09-07 (for Stage 4). The attempt **weakened** the claim rather than confirming it:

| Value | Attribution | Primary source? |
|---|---|---|
| **50–75 mm** | D-2 / earlier AI-generated research | **None.** Never traced. |
| **100 mm** | "ICAR – National Soybean Research Institute, Indore", via `global-agriculture.com` (trade site) | **None.** The page cites *no bulletin, number, or date.* Quote: *"farmers are strongly advised to sow soybean only after the monsoon arrives in their area and after receiving at least 100 mm of rainfall."* |

**The two figures are incompatible** (50–75 mm vs 100 mm — a difference that would change a sowing decision). That disagreement is itself evidence that the D-2 number should not be inherited as settled.

**Primary source could not be reached.** A candidate ICAR-IISR extension bulletin URL was identified (`iisrindore.icar.gov.in/pdfdoc/ExtensionBulletin2023E_3.pdf`) but **the host does not resolve from this network** — DNS failure on `iisrindore.icar.gov.in` and `krishi.icar.gov.in`; only `icar.org.in` / `icar.gov.in` resolve (144.16.144.82). So the bulletin is neither confirmed nor refuted; it was simply not retrievable here. *That is a network result, not evidence about the document's contents* — a later attempt from a different network may succeed.

**Consequence, enforced in code** *(as of 2026-09-07; superseded for soybean by D-29, which sets `sowing_rain_threshold_mm=100.0` for soybean only and leaves `verified=False`)***:** `src/models/decision_engine.py` sets `sowing_rain_threshold_mm=None` for every crop and marks all `CropEconomics` as `verified=False`. Any `DecisionResult` built from them carries `uses_unverified_parameters=True`, and both the worked example and the farmer-facing advisory render an explicit provisional-parameters disclosure. **No ICAR number is hardcoded anywhere.**

~~**To close this:** retrieve an actual ICAR/IISR/SAU publication, record its title, number and year here, and only then set the threshold and flip `verified=True`.~~ — **DONE for the threshold, 2026-09-08 (D-29); NOT done for `verified`.** The publication was retrieved and recorded, and the threshold is set. `verified` deliberately stays `False`: it is an object-wide flag covering `l_reseed`/`l_delay` too, and those are still unsourced. Flipping it would delete the farmer-facing cost disclosure from the WhatsApp advisory and the risk SVG on the strength of a bulletin that says nothing about rupees.

---

## Verification practice for new claims

1. Search for the primary source, not a summary
2. If the claim includes a number, confirm the number in the source — not just the topic
3. If the claim includes author names, confirm the author list (two decks reviewed in this project had real papers with **padded or wrong author lists**)
4. Record the result here with a status code
5. If it fails, add it to § Debunked with the reason — the registry is as valuable as the verified list

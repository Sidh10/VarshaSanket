# DATA SOURCES

Everything this project reads, where it comes from, and what its real limits are.

---

## Primary sources — verified accessible

| Source | Role | Resolution / Coverage | Access |
|---|---|---|---|
| **IndiaWeatherBench** | Primary training data | 12km (0.12°), 6-hourly, 2000–2019, ~~39 channels~~ **43 channels (39 ML input)** `[FLAG: DISCUSSION D-6]`, 256×256 grid | HuggingFace `datasets/tungnd/IndiaWeatherBench`, **CC-BY-NC-SA-4.0 (non-commercial)** `[FLAG: DISCUSSION D-9]`. **Provenance: authors' repo — confirmed** (the paper's cited GitHub repo `github.com/tung-nd/IndiaWeatherBench` links to it with a 🤗 badge; HF user = "Tung Nguyen" = paper corresponding author). Caveat: the paper text names Google Drive, not HF, and the HF card doesn't self-identify — chain is paper→GitHub→HF. See DISCUSSION D-11. No server-side subset — archives are 9.1 GB / **105.84 GB** / 101 GB (h5 = ~330 GB *extracted*); use HTTP-range zip reads `[FLAG: DISCUSSION D-8, D-12]` |
| **BharatBench** | Lighter alternative + published baselines to benchmark against | ~100km (1.08°), 6-hourly, 1990–2020 | Kaggle/GitHub, free |
| **NOAA CPC** `[FLAG: DISCUSSION D-7 — provider/cadence partly wrong]` | ENSO / Niño3.4 (CPC ✅, **weekly or monthly, not daily**). DMI/IOD → **NOAA PSL, not CPC, monthly**. RMM1/RMM2 → **Australian BoM, not NOAA, daily**. | mixed cadence | Free, no registration; verified live 2026-09-07 |
| **imdlib** | IMD gridded rainfall for ground-truth calibration | **0.25° (~25km)**, daily `[confirmed live 2026-09-07: 129×135 grid, 6.5–38.5°N/66.5–100°E]`; `tmax`/`tmin` are 1.0° | `pip install imdlib`, MIT |
| **ICAR Kharif advisories** | Crop sowing thresholds for the decision engine | Per-crop, per-region | Public bulletins |

### Optional / stretch

| Source | Role | Status |
|---|---|---|
| IITM ARDC THREDDS (`ardc.tropmet.res.in`) | GFS forecast archives via OPeNDAP | Appears open, **not tested end-to-end** |
| IITM ERPv2 (IRI Data Library) | Operational extended-range forecasts | ⚠️ **Restricted access — not a dependency** |

---

## Do not use

**Any `api.imd.gov.in` real-time endpoint.** Claimed to exist by three separate AI research passes, each with a different URL and a plausible-sounding access process. Never independently verified. See `docs/RESEARCH.md` § Debunked.

---

## The resolution problem — read this before writing "block-level"

Three different resolutions are in play, and none of them is a village:

| Layer | Native resolution | Roughly |
|---|---|---|
| IMDAA / IndiaWeatherBench (training) | 0.12° | ~12 km |
| IMD gridded rainfall via imdlib (ground truth) | 0.25° | ~25 km |
| An Indian administrative block | — | ~10–30 km across |
| A village | — | ~1–5 km |

**Honest framing:** block-level output is achievable by bias-correcting the 12km field toward station-informed gridded data. **Village-scale precision is a stretch goal, not something the underlying data supports on its own.** Say this before a judge asks.

This also means the ground truth for calibration (0.25°) is *coarser* than the target output (block). Stage 3 is correcting toward a coarser reference — a real methodological caveat worth stating rather than hiding.

---

## Data acquisition rules

- All downloads go through `src/data/` — never a one-off in a notebook that nobody can reproduce
- Cache aggressively; IndiaWeatherBench is large (216 GB full; subset before pulling)
- Record the exact subset/date range used for any reported result
- **Never let acquisition code touch the held-out year during a backtest fold** — see `docs/VERIFICATION.md`

---

## Impact figures (for pitch/README use)

Use these, not estimates:

- **93.09 million agricultural households** in India (NSO 77th Round, 2018–19)
- 101.98 million operational holdings
- 172.44 million rural households total, ~54% agricultural

⚠️ Earlier drafts of this project used **"120 million farm households"** — that figure is unsourced and inflated. Correct it wherever it appears.

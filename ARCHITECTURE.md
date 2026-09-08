# ARCHITECTURE

The pipeline, why each piece is shaped the way it is, and the answer to give when a judge or reviewer challenges it.

---

## Overview

```
[20 yr observed Rajeevan labels]      [Local block history]
 IMD gridded rainfall (imdlib)        IMDAA reanalysis (IndiaWeatherBench)
          │                                      │
          ▼                                      │
  ┌───────────────────────────┐                  │
  │ STAGE 1 — CLIMATOLOGICAL   │                 │
  │           REGIME PRIOR     │                 │
  │ target date → base rate    │                 │
  │ P(active/break/transition) │                 │
  │ + block-bootstrap CI       │                 │
  │ NO LEAD TIME. NOT A FORECAST│                │
  └────────────┬───────────────┘                 │
               ▼                                  │
  ┌───────────────────────────┐                  │
  │ STAGE 2 — SEASONAL ANALOG   │◄───────────────┘
  │           EVIDENCE          │
  │ K=5 nearest pre-season yrs, │
  │ report what ACTUALLY happened│
  │ • target year excluded      │
  │ • disagreement surfaced     │
  │ • TEXT ONLY — no probability│
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
  │ adjustable θ, PROVISIONAL   │
  │ defaults (unsourced - D-29) │
  └────────────┬───────────────┘
        ┌──────┴──────┐
        ▼             ▼
   Risk map      WhatsApp advisory
   (block        (regional
    choropleth)   language)
```

---

## Stage 1 — Climatological Regime Prior

**Input:** 20 years (2000–2019) of observed Rajeevan active/break/transition labels, built from IMD gridded rainfall via `imdlib`
**Output:** `RegimePrior` — P(active), P(break), P(transition) for a **target date**, with a block-bootstrap 95% band
**Method:** empirical base rate by day-of-year (±7-day smoothing). Nothing is fitted.
**Code:** `src/models/climatological_prior.py`

### This stage does not forecast, and the previous version of this section was wrong

An earlier version of this document claimed Stage 1 was a gradient-boosted forecaster producing P(regime) at 1–4 week lead, and asserted it was *"the only stage with genuine predictive skill"* from MJO/BSISO phase propagation. **That claim was asserted and never tested. It was then tested and failed** (DISCUSSION D-14):

| Lead | BSS vs day-of-year climatology | 95% CI |
|---|---|---|
| 1 week | −0.034 | [−0.072, +0.010] |
| 2 week | −0.014 | [−0.056, +0.033] |
| 3 week | −0.057 | [−0.105, −0.001] |
| 4 week | +0.009 | [−0.041, +0.061] |

Leave-one-year-out across 20 years, both season definitions agreeing. A regularised linear reference model failed identically at every lead, so this was an absent signal rather than a mis-specified model — and the seasonal-only variant (calendar features alone) scored *better* than the full model at two of four leads.

**Nothing beat climatology. So Stage 1 is now climatology, declared as such.** This is a smaller claim honestly held rather than a model that reproduces the base rate while carrying the vocabulary of a forecast.

### What it therefore cannot do

A base rate has no year-specific information. It returns the same distribution for 15 July 2002 (a severe break month) as for 15 July 2010. It has **no lead time** — asking it for "a 2-week forecast" is a category error; it answers "what usually happens on this date", not "what will happen".

Any year-specific skill the pipeline eventually gains must come from somewhere else. It is not in this stage, and the output schema is deliberately shaped so that nobody downstream can mistake it for year-specific information.

### The IMD trough evidence field — text, never a number

`RegimePrior` carries a second, structurally separate output: `advisory_evidence: str | None`, populated from IMD Extended Range bulletins when they state a monsoon-trough position covering the target date (measured coverage: **30% of JJAS dates, 2021–2025**).

**It does not modify the probabilities and cannot.** They are computed before it is read, the assertion in `src/models/run_stage1_prior.py` checks this, and the two blocks are different types. The reason is D-16: that signal is real (P(break | trough north) = 0.50 vs 0.00 for south/near, Fisher p = 0.003) but rests on **4 break events** with 18% week-section coverage. That is enough to quote to a farmer as checkable supporting context — *"IMD's bulletin says the trough is north of normal next week"* — and nowhere near enough to move a 20-year base rate. Fusing them would bury a 4-event association inside a 20-year statistic where nobody could audit it.

The physical mechanism is IMD's own (glossary: *Break Monsoon — monsoon trough shifts northwards and runs close to foot hills of Himalayas*). The mapping from position to break-favourable is **ours**, isolated in `src/features/trough.py::break_favourable` so it is the first thing a reviewer can attack.

### Why this is still a defensible thing to present

The stage is honest about being a base rate, it carries a real uncertainty band computed over the only plausibly independent unit (years, not days), and it states its own event counts. Bürger (2019) documents operational monsoon systems reporting inflated skill because nobody ran the comparison this stage failed. Running it, failing it, and saying so is the differentiator — see `docs/VERIFICATION.md`.

---

## Stage 2 — Seasonal Analog Evidence

**Input:** the `RegimePrior` from Stage 1 + the per-year seasonal ENSO/IOD table
**Output:** named historical analog years with their **observed** rainfall outcomes, attached to the prior as text plus auditable numbers. **No probability is produced or modified.**
**Method:** K=5 nearest historical seasons by standardised **pre-season (MAM)** Niño3.4/DMI distance; outcomes read from the record
**Code:** `src/models/seasonal_analog_evidence.py`

### This stage no longer downscales probabilities, and the previous version of this section was wrong

Stage 2 was specified as a probability *downscaler* — reweight the outcome distribution by analog proximity. That was built and tested (D-17), and it failed:

| Window | RPSS vs climatology (LOYO, 20 seasons) | 95% CI | |
|---|---|---|---|
| JJAS (concurrent — **not knowable pre-season**) | +0.039 | [−0.179, +0.226] | spans zero |
| MAM (pre-season — **operationally usable**) | **−0.249** | [−0.383, −0.136] | **worse than climatology** |

It failed *worst at the only operationally valid lead*. The cause is visible without any model: Niño3.4 correlates **−0.444** with seasonal MCZ rainfall **concurrently**, but **+0.054 pre-season**. Reweighting probabilities by a predictor with r = +0.05 does not add information; it adds noise, and the numbers say so.

**So Stage 2 stopped touching the probabilities.** It now does the one thing the data actually supports: historical fact lookup, disclosed as evidence next to Stage 1's unchanged climatology.

### What it does instead

For a target year it names the K=5 seasons whose pre-monsoon ENSO/IOD state was closest, and reports **what actually happened** in each — the observed MCZ seasonal-rainfall tercile, straight from the record. This is lookup, not prediction. Nothing is averaged, modelled, or converted to a probability.

### Disagreement is surfaced, never averaged away

The analogs frequently point in different directions, and the module says so explicitly rather than collapsing them into a mean. **Across all 20 target years, 19 are classified `divided` and 1 `leaning` — not one is `unanimous`.** That is the honest signature of an r = +0.05 predictor, and it is exactly what the output should say.

Worked example (2019, the wettest season in the record):
> *"The 5 historical seasons whose pre-monsoon ENSO/IOD state most resembled 2019: 2010 was normal; 2017 was normal; 2016 was wet; 2015 was dry; 2009 was dry. These seasons diverged (2 dry, 2 normal, 1 wet), so they do not point to a single expectation. For example 2016 was wet while 2009 was dry, despite similar pre-monsoon ENSO/IOD state. Pre-monsoon ENSO/IOD state did not determine the outcome in these years."*

`_summarise()` has **no code path that produces a central expectation when the analogs are divided**. A confident-sounding average of two disagreeing seasons is more confident and less true than reporting the split.

### The exact agreement rule, and what the farmer sees

`seasonal_analog_agreement` is set by a deterministic rule over the K=5 outcome counts (`src/models/seasonal_analog_evidence.py::_summarise`), with `modal_n` = the largest tercile count and `spans_extremes` = (≥1 dry **and** ≥1 wet):

| Label | Condition | Farmer-facing? |
|---|---|---|
| `unanimous` | `modal_n == k` (all 5 in one tercile) | **yes** |
| `divided` | `spans_extremes or modal_n <= k/2` (both extremes present, or the plurality is ≤2 of 5) | **no** |
| `leaning` | otherwise (plurality of 3–4, no dry↔wet split) | **yes** |

In this 20-year record: **19 `divided`, 1 `leaning` (2018), 0 `unanimous`.**

The evidence text is **fully templated** — three f-string branches (one per label) plus one optional "for example {year A} was {X} while {year B} was {Y}" clause, all built from integers and year/tercile lookups. No free generation, no model call, no randomness. It is as auditable as the probabilities.

**The `divided` case is kept in the API response but withheld from the advisory.** `advisory_evidence_lines(prior)` — the single boundary where the API view and the farmer view diverge — includes the analog sentence only when `seasonal_analog_advisory_visible` is true (agreement `leaning`/`unanimous`). For `divided`, `prior.seasonal_analog_*` stay fully populated for the technical/demo view, and `advisory_evidence_technical_view()` reports `seasonal_analog_suppressed_reason`, but Stage 4's advisory generator treats the field as absent — the same handling as a null `advisory_evidence` from the bulletin path. Nothing is deleted; it is just not said to the farmer.

### Two evidence mechanisms, structurally separate

`RegimePrior` now carries two independent evidence groups so a reviewer — and Stage 4 — can trace every sentence of advisory text back to the process that produced it, without guessing:

| Fields | Mechanism | Source |
|---|---|---|
| `advisory_evidence`, `evidence_source` | **bulletin parsing** | IMD Extended Range trough position (D-16), ~30% of JJAS dates |
| `seasonal_analog_evidence`, `seasonal_analog_years`, `seasonal_analog_detail`, `seasonal_analog_effective_n`, `seasonal_analog_agreement` | **historical fact lookup** | observed terciles of nearest pre-season analog years (D-18) |

Neither is numeric input. `attach_seasonal_analog()` uses `dataclasses.replace`, so the numeric block is *copied* rather than recomputed — it is structurally impossible for evidence to change `probabilities`, `ci_lower` or `ci_upper`, and `run_stage1_prior.py` asserts it at runtime anyway.

### Safeguards retained from the retired downscaler

- **Target-year exclusion** — `seasonal_analog_distances()` enforces it at one line (`pool = pool[pool != target_year]`), a hard filter on the pool index. The retired `AnalogDownscaler` now *delegates* to this same function, so the safeguard exists in exactly one place and cannot drift. Verified byte-identical to the previous inline implementation (max weight diff 5.6e-17; D-17's RPSS figures reproduce exactly).
- The target year is also excluded from the index standardisation and from the tercile boundaries used to describe its own neighbours.
- **Effective N and per-analog distances are returned in the output**, not just in the prose, so the evidence is itself auditable. Note `effective_n` here is an *audit* statistic — it says whether one season dominates the neighbourhood — not a probability weight; nothing consumes it as a forecast input.

### Why analogs at all, given the above

The original rationale for analogs over end-to-end regression still holds and is unaffected by D-17: a model regressing rainfall directly from indices hedges toward the mean (the **double-penalty problem**), smoothing away the local extremes and true dry spells that drive a farmer's decision. Analogs sample *real observed outcomes*. What D-17 changed is not whether analogs are the right object, but whether their proximity should be allowed to move a probability. It should not.

### Status of the three original safeguards

These were written for the probability-reweighting design. Where they went:

1. **Target year excluded from the pool** — **retained and strengthened.** Now enforced in one shared function (see Safeguards above), extended to the standardisation and the tercile boundaries.
2. **Continuous distance, not exact matching** — **superseded.** It existed to stop exact joint matching on ENSO+IOD+MJO collapsing the pool to 2–5 analogs. The evidence design takes the K=5 nearest by continuous distance and *names them individually*, so a small analog set is no longer a hidden weakness in a distribution — it is the visible output, with each distance printed.
3. **Effective ensemble size with every forecast** — **retained, role changed.** Still entropy-based and still returned with every output, but it is now an **audit** statistic describing how concentrated the neighbourhood is, not a weight on any probability. Nothing consumes it as forecast input.

### Recency weighting — implemented, and not used in the active path

Mondal & Mujumdar (2015) document real non-stationarity in Indian extreme rainfall, which is why the retired downscaler down-weighted older analogs (`recency_tau`, e-folding 15 yr). D-17 reported it both on and off and it made little difference (JJAS RPSS +0.039 on vs +0.081 off).

**The evidence-lookup path does not apply it.** Ranking the K nearest seasons by recency as well as similarity would mean the years shown to a farmer are not simply the most similar ones, which would make the evidence harder to check against the record rather than easier. The code remains in `AnalogDownscaler` for reproducing D-17; it is not in the live path.

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

C and L vary enormously by crop, landholding size, irrigation access, and whether the farmer can afford to reseed at all. Hardcoding θ ≈ 0.3 is indefensible. It's exposed as an adjustable parameter with per-crop defaults.

**Those defaults are NOT ICAR-sourced, and this line previously said they were.** Corrected 2026-09-08. The per-crop `l_reseed`/`l_delay` values are **illustrative placeholders, not traced to any source** — every `CropEconomics` carries `verified=False`, every `DecisionResult` carries `uses_unverified_parameters=True`, and the disclosure renders in both the farmer-facing advisory and the risk SVG. The only ICAR-sourced number in `CROP_DEFAULTS` is soybean's `sowing_rain_threshold_mm=100.0` (D-29), which is advisory context read by no code and is **not** part of θ. See D-20 / D-29.

**Demo value:** sliding θ live and watching SOW flip to WAIT is one of the strongest interactive moments available.

---

## Output layer

**Code:** `src/delivery/` — `advisory.py` (text), `whatsapp.py` (Twilio sandbox), `risk_display.py` (indicator).

**Risk display:** a **single regional indicator** for the whole monsoon core zone — one probability triple, one colour, one recommendation. `src/delivery/risk_display.py`.

> 🔴 The "block-level choropleth" this section originally described is **aspirational and not built**. Stage 1 computes an MCZ-*mean* base rate (18–28°N, 66.5–88°E, 2684 cells); there is no per-block number in the pipeline (D-16 also showed the sub-division reconciliation is coarse). Drawing spatial variation that isn't in the numbers would mislead. The indicator therefore renders the pilot area as **one uniform fill**, with *"regional estimate, not resolved to individual blocks or villages"* baked into both the text card and the SVG image itself — so a judge skimming the map cannot mistake it for block-resolved. A per-block choropleth becomes possible only if a block-resolved forecast is ever built.

**Farmer advisory:** short message over WhatsApp (Twilio Sandbox — free, no business verification, verified in RESEARCH.md). `src/delivery/advisory.py` → `src/delivery/whatsapp.py`.

- **Language: not specified in any doc.** ARCHITECTURE/README/AGENTS all say "regional language" / "their own language" generically; no language is named. **English is the verified default and the send default.** A Hindi rendering exists as a fully-templated stub — Hindi covers the plurality of MCZ sub-divisions — but it is **machine-generated and unreviewed**: every `hi` output carries an UNVERIFIED banner and `WhatsAppSender` refuses to send it without an explicit override. AGENTS.md's "reviewable by someone who reads that language before demo" is an **open blocking task** (D-21).
- The advisory carries **prediction + evidence + uncertainty + consequence + action**, never a bare number: recommendation, both expected losses, P(break) with its "20-year average, not a forecast" caveat, the D-19 evidence lines, the regional-scale caveat, and — when cost parameters are unverified (currently always, D-20) — a plain-language disclosure *in the farmer-facing text*, not only the technical view.
- Evidence text comes **only** through `advisory_evidence_lines(prior)` (the D-19 boundary); the raw fields are never read in the delivery layer (AST-verified).
- **No live IMD call on the delivery path.** Trough evidence is read from the cached, batch-parsed bulletin pipeline (D-15/D-16); the demo errors rather than fetching if the cache is absent.

**Q&A — "how do you actually reach the farmer's phone; doesn't WhatsApp block unsolicited messages?"**
> *"Yes — WhatsApp only allows free-form messages within 24 hours of the farmer messaging us. For the demo that's exactly the Twilio Sandbox flow: the farmer sends a join code once, which opens the window, and advisories go out over it — no Meta business review needed. For production the real path is an approved Meta message template for send-anytime delivery; that's a WhatsApp Business API onboarding step we've scoped but not built. The sender enforces the opt-in as an explicit precondition rather than assuming a session is always open."* (D-21)

---

## Output tiering — do not blur this

| Lead time | What we output |
|---|---|
| 7–14 days | Actionable probabilistic onset/break forecast |
| 14–30 days | Regime outlook only — elevated/reduced break risk. **Not a date, not a rainfall amount** |

IMD's own published guidance shows useful skill of roughly 2 weeks at *subdivision* scale, which is coarser than block. Claiming block-level precision at 30 days claims more than IMD achieves at a coarser scale over a shorter horizon. Stating the tiering yourself reads as competence.

> 🔴 **This table is currently ASPIRATIONAL, not delivered.** It describes lead-time tiering for a Stage 1 that *forecasts*. Stage 1 is now a climatological prior with **no lead time at all** (D-14), so as of today the pipeline outputs a base rate for a target date, not a 7–14 day forecast. Do not present this table as current capability. It becomes valid only if Phase 1R produces a predictor with demonstrated skill; until then the honest statement is *"we output the climatological base rate with its uncertainty, plus IMD's own bulletin evidence where available."*

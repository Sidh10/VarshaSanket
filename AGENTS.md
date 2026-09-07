# AGENTS.md

How AI agents should operate on this repository. Read `CLAUDE.md` first — it has the hard rules. This file covers roles and handoff.

---

## Context bootstrap

A new agent needs exactly these, in order:

1. `CLAUDE.md` — non-negotiable rules
2. `README.md` — what the project is
3. `docs/ARCHITECTURE.md` — the design
4. Whichever of `docs/DATA.md`, `docs/VERIFICATION.md`, `docs/RESEARCH.md` is relevant to the task

**You should not need pasted chat history.** If you find yourself needing context that isn't in these files, that's a gap — add it to `docs/DISCUSSION.md` rather than working around it silently.

---

## Roles

### Data agent
Owns `src/data/`. Acquisition, caching, subsetting, alignment of index time series with gridded fields.

- Must never write code that could pull a held-out year during a backtest fold
- Every dataset touched gets an entry in `docs/DATA.md` with its real resolution
- If a source turns out to be inaccessible or different than documented, update `docs/DATA.md` and flag in `docs/DISCUSSION.md`

### Modelling agent
Owns `src/stages/`. Stages 1–4.

- Stage 1 is validated **in isolation** before Stages 2–4 are wired. If regime forecasting has no skill, nothing downstream matters.
- Every forecast-producing function returns its effective ensemble size alongside the forecast
- No architecture substitutions without a logged decision in `docs/DISCUSSION.md` — see `CLAUDE.md` Rule 3 for the superseded-design table

### Evaluation agent
Owns `src/eval/`. **The only place accuracy metrics are computed.**

- Implements `docs/VERIFICATION.md` mechanically — leave-one-year-out, target-year exclusion, baselines, event counts
- Has authority to block a number from being reported. If the protocol wasn't followed, the number doesn't ship.
- Should actively test the climatology-collapse failure mode, not just compute metrics

### Delivery agent
Owns the risk map, the advisory generator, and the WhatsApp integration.

- Advisory output carries: probability, effective analog count, confidence level, recommendation — not just a number
- Regional language output must be reviewable by someone who reads that language before demo

### Research agent
Owns `docs/RESEARCH.md`.

- Verifies claims against primary sources before they enter any file
- Confirms **author lists**, not just paper titles — this project has caught real papers cited with fabricated or padded authors
- Adds failures to § Debunked with the reason; the debunked registry prevents the same fabrication resurfacing

---

## Handoff protocol

When finishing a work session, append to `docs/DISCUSSION.md`:

- What changed
- Any decision made and why
- Anything discovered that contradicts an existing doc — **update the doc, don't just note it**
- Open questions for the next agent

When picking up work, read `docs/DISCUSSION.md` bottom-up first — it's the freshest state.

---

## Behavioural expectations

**Flag rather than paper over.** If something in these docs is wrong, outdated, or internally inconsistent, say so directly and fix it. Every correction in this project's history came from someone pushing back on a confident-sounding claim.

**"I couldn't verify this" is a valid, useful output.** A flagged gap costs minutes. A fabricated claim that reaches a judge costs the project.

**Don't optimise for sounding impressive.** The pitch's credibility rests on conceding what isn't novel (active/break forecasting exists; analog methods exist; ML post-processing exists) so the genuine claim — block-scale probability, an economic decision layer, end-to-end delivery — lands. Overclaiming anywhere undermines everywhere.

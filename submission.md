# Bonsai — Hackathon Submission

> **AI Engineer World's Fair Hackathon 2026.** Paste-ready text for the submission form. Placeholders marked `‹…›` — fill before submitting.

---

## Project name

**Bonsai** — a self-improving eval harness.

## Tagline (one line)

A self-improving eval *harness*: it watches an agent fail, mints a new check to catch that failure forever, and proves it stayed honest against a frozen gold set the improving loop can never read.

## Links

- **Live demo:** https://bonsai-h7rzp.ondigitalocean.app/
- **Repo (public):** https://github.com/enturesting/bonsai
- **1-min video:** ‹video URL — record Sunday AM›

---

## What it does (elevator)

Evals are the bottleneck on safe autonomy — they're written by hand, they go stale, and nobody trusts them. **Bonsai is a self-improving eval harness** for cited-answer agents. It runs an agent-under-test (Gemini 3.5) that answers questions from sources and cites them, then catches the failure mode where a claim has **no verbatim supporting quote** in the source it cites. It clusters those failures by embedding similarity (MongoDB Atlas `$vectorSearch` over Voyage vectors), and for each *kind* of mistake it **mints a brand-new general check** — keeping it only if it passes every known-good answer and catches at least two distinct sibling failures. It autonomously grows and prunes this rubric over a mutable working pool, and reports whether it actually improved as **direction + a Wilson confidence interval** against a **frozen, human-authored gold set the improving loop is build-time-provably unable to read.**

It is a **harness** — a checking loop — not retrieval-augmented generation.

## The demo (what a judge sees)

On the dashboard, a column of **red** claim pills — Gemini-3.5 answers with unsupported claims. Click **Improve** on one:

1. 🟡 the pill flips yellow — `CHECKING…`
2. the grower's rule-rewrite (Gemini 3.5) **streams token-by-token** into the rule panel
3. 🌱 a branch sprouts on the bonsai-tree as the check is minted
4. 🟢 the pill flips green — the answer now passes a check that didn't exist five seconds ago

Then the receipt: the minted `Check` object **in code** (with its `is_general` gate), the gold-gap **score panel** (before→after counts + Wilson CI), and the **honesty-gate test** that fails the build if `/loop` ever imports `/eval/gold`.

## Why it's novel

To our knowledge, Bonsai is the first eval-generation system to make honesty a **build-time architectural invariant**: its autonomous, failure-clustered check-minting loop is *provably unable to read* the frozen gold set it is scored against, so every reported improvement is a direction-plus-confidence-interval against a judge the system cannot overfit to. Prior art (EvalGen, AutoChecklist, LangSmith Engine, ProbeLLM, Self-Harness) *generates* evals; the wedge here is **gating the generator** — separating the improver from the judge — plus reporting improvement as direction + CI rather than a bare number.

---

## Tech, per prize

### MongoDB Atlas Vector Search + Voyage (placement)

Atlas Vector Search is the **engine**, not a bolt-on store. `store/vectors.py` runs real `$vectorSearch` on the `failvec` index (1024-dim, cosine); `store/embed.py` uses **Voyage `voyage-3`** asymmetric embeddings (`document` for failures, `query` for retrieval). Crucially, `store/failures.py` embeds *question + claim + diagnosis* together, so the neighborhood clusters by **kind of mistake** — and that clustering (`loop/grower.py` `grow()` → `nearest_failures()` → `mint_check()` → `is_general()`) is what makes a minted check **general** instead of memorized. Vector search here is *failure clustering*, the core mechanism — not document retrieval.

### $5,000 Best Gemini 3.5

**Gemini 3.5 powers the entire loop, end to end, via Vertex AI.** `gemini-3.5-flash` is both the **agent-under-test** — `fixtures/gemini_client.py` produces cited answers (JSON mode) strictly from candidate sources, every claim card badged **"Answered by Gemini 3.5"** with its `[S#]` citations — **and** the **checker + grower** (`loop/llm.py`, `LOOP_BACKEND=gemini`) that judges the claims and rewrites the rules token-by-token. So Gemini isn't just answering: it's the self-improving engine itself. It runs on Vertex through ADC, drawing GCP credit (no per-key prepay).

### $600 Best DigitalOcean

**Deployed and live: https://bonsai-h7rzp.ondigitalocean.app/.** DigitalOcean App Platform builds the `Dockerfile` (Python 3.12) and runs it via a `Procfile`: `uvicorn main:app --port $PORT --timeout-keep-alive 75`, `/healthz` health check. It deploys **fully offline** (mock flags, no secrets) — so the public demo can't fail on anyone's network — and the SSE flip survives the LB idle timeout (`--timeout-keep-alive 75` + sse-starlette `ping=20`).

### Anthropic (Claude) — optional, swappable loop backend

The loop runs on Gemini by default, but it's model-pluggable behind one seam (`loop/llm.py`): set `LOOP_BACKEND=anthropic` and the same harness runs on Claude **Opus 4.8** (grower/judge/skeptic, `thinking=adaptive` + `effort=high`) + **Haiku 4.5** (cheap first-pass checker) with a deterministic→Haiku→Opus escalation. Same loop, swappable engine.

---

## What's real vs mocked (24h, honest)

The whole spine is real, incrementally-committed code: `checker → skeptic → grower/minting → pruner → eval_stream`, the htmx+SSE flip UI, Atlas/Voyage data layer, and the build-enforced honesty gate (**69 tests green**). And it's **live, not just wired**: the loop runs end-to-end on live Gemini 3.5 (Vertex), live Atlas `$vectorSearch` is seeded with real Voyage vectors (the lineage shows real cosine scores), and the app is **deployed on DigitalOcean**. For the *stage* demo we present the deterministic `MOCK_AUT`/mock-stream path — bulletproof, reproducible, identical on screen — with the live path as the "it's genuinely running" reveal. The frozen gold set is authored **on-site, one commit per item**, by design — that discipline *is* the honesty rail, not a gap.

## The bigger picture

Every autonomous system needs a verification layer that grows with it. Evals are the bottleneck on safe autonomy — you can't ship an agent you can't continuously verify. **Bonsai is a prototype of that trust layer**: a harness that keeps its own evals honest and growing as the agent does.

---

## Honesty notes (we hold to these)

- It's a **harness**, never "basic RAG."
- We report **before→after counts + a Wilson CI**, never a bare percentage.
- The gold set **agrees with a human-authored reference** — it does not *prove* honesty. The honesty is structural: `/loop` cannot read `/eval/gold` (build-failing test). The gate guarantees the loop can't overfit to the judge; it does **not** claim the judge is complete.

# Bonsai — Hackathon Submission

> **AI Engineer World's Fair Hackathon 2026.** Paste-ready text for the submission form. Placeholders marked `‹…›` — fill before submitting.

---

## Project name

**Bonsai** — a self-improving eval harness.

## Tagline (one line)

A self-improving eval *harness*: it watches an agent fail, mints a new check to catch that failure forever, and proves it stayed honest against a frozen gold set the improving loop can never read.

## Links

- **Live demo:** ‹DigitalOcean public URL — https://…›
- **Repo (public):** ‹GitHub URL›
- **1-min video:** ‹video URL›

---

## What it does (elevator)

Evals are the bottleneck on safe autonomy — they're written by hand, they go stale, and nobody trusts them. **Bonsai is a self-improving eval harness** for cited-answer agents. It runs an agent-under-test (Gemini 3.5) that answers questions from sources and cites them, then catches the failure mode where a claim has **no verbatim supporting quote** in the source it cites. It clusters those failures by embedding similarity (MongoDB Atlas `$vectorSearch` over Voyage vectors), and for each *kind* of mistake it **mints a brand-new general check** — keeping it only if it passes every known-good answer and catches at least two distinct sibling failures. It autonomously grows and prunes this rubric over a mutable working pool, and reports whether it actually improved as **direction + a Wilson confidence interval** against a **frozen, human-authored gold set the improving loop is build-time-provably unable to read.**

It is a **harness** — a checking loop — not retrieval-augmented generation.

## The demo (what a judge sees)

On the dashboard, a column of **red** claim pills — Gemini-3.5 answers with unsupported claims. Click **Improve** on one:

1. 🟡 the pill flips yellow — `CHECKING…`
2. an Opus rule-rewrite **streams token-by-token** into the rule panel
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

The agent-under-test is **Gemini 3.5**. `fixtures/gemini_client.py` calls `gemini-3.5-pro` (JSON mode) to produce cited answers strictly from candidate sources, surfacing the load-bearing claim Bonsai then checks. Every claim card in the UI is badged **"Answered by Gemini 3.5"** with its `[S#]` citations, so it's visibly Gemini doing the real work that drives the whole harness.

### $600 Best DigitalOcean

Deployed on **DigitalOcean App Platform** via `deploy/app.yaml` + `deploy/Dockerfile`: `uvicorn main:app --host 0.0.0.0 --port 8080 --timeout-keep-alive 75`, `/healthz` health check, four secret envs (`MONGODB_URI`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `GEMINI_API_KEY`), region near Atlas. The SSE flip survives the 75s load-balancer idle timeout (`--timeout-keep-alive 75` + sse-starlette `ping=20`). Public link: ‹URL›.

### Anthropic (Claude) — the engine inside the loop

Claude **Opus 4.8** grows/judges/skeptics the checks (`thinking={"type":"adaptive"}`, `output_config={"effort":"high"}`); Claude **Haiku 4.5** does the cheap first-pass checking. The deterministic→Haiku→Opus escalation keeps cost down while reserving the strong model for minting general checks.

---

## What's real vs mocked (24h, honest)

The whole spine is real, incrementally-committed code: `checker → skeptic → grower/minting → pruner → eval_stream`, the htmx+SSE flip UI, Atlas/Voyage data layer, and the build-enforced honesty gate. Tests are green and the red→green flip is verified end-to-end in mock (Chrome CDP). For demo determinism and speed we run the AUT in `MOCK_AUT` mode; live Gemini, live Atlas `$vectorSearch`, and the DigitalOcean public link are wired behind real keys and a flag. The frozen gold set is authored **on-site, one commit per item**, by design — that discipline *is* the honesty rail, not a gap.

## The bigger picture

Every autonomous system needs a verification layer that grows with it. Evals are the bottleneck on safe autonomy — you can't ship an agent you can't continuously verify. **Bonsai is a prototype of that trust layer**: a harness that keeps its own evals honest and growing as the agent does.

---

## Honesty notes (we hold to these)

- It's a **harness**, never "basic RAG."
- We report **before→after counts + a Wilson CI**, never a bare percentage.
- The gold set **agrees with a human-authored reference** — it does not *prove* honesty. The honesty is structural: `/loop` cannot read `/eval/gold` (build-failing test). The gate guarantees the loop can't overfit to the judge; it does **not** claim the judge is complete.

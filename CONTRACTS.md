---
title: Bonsai — CONTRACTS.md (cross-terminal interface freeze)
created: 2026-06-27
---

# CONTRACTS.md — Bonsai eval harness

> Single source of truth for the seams between terminals. **Names are LOCKED.** To change a signature here, change it HERE first, then ping the affected terminal. Pinned implementation code lives in `build-cheat-sheet.md` (vault) — each section points to it. Don't reinvent; reference.

Demo task = **CITED ANSWERS**: the Gemini 3.5 AUT answers a question and cites sources; Bonsai catches claims with no real supporting quote. First check id: `numeric-cites-source`.

---

## 1. Data models (Pydantic v2) — `store/models.py`

Every terminal imports from `store.models`. **Nothing redefines these locally** (this includes `/loop` — there is no `loop/models.py`). See `store/models.py` for the authoritative code: `Source{id,title,url,text}`, `AUTOutput{input,claim,output,sources[]}` (+ `sources_text` property), `Failure{id,input,claim,expected,actual,why,embedding[1024]}`, `Check{id,property,rationale,positive_example,negative_example,overfit_risk}`, `Verdict{passed,confidence,reason}`, `EMBED_DIM=1024`.

Conventions: `claim` is always the unit of evaluation (one assertion). A `Check` is a predicate over `(check, claim, output)` where `output` is an `AUTOutput`. Mongo `_id` is the `id` field; `motor` async driver.

---

## 2. SSE event contract

Endpoint: `GET /stream/improve/{claim_id}` → `EventSourceResponse` (sse-starlette ≥2.1, `ping=20`, header `X-Accel-Buffering: no`). `/web` iterates `loop.eval_stream(claim_id)` (yields semantic dicts) and serializes each to the wire shape below. **Exactly four event names** (+ optional `error`). htmx disconnects on `done`.

| event | `/loop` dict `data` | wire `data` (`/web` emits) | htmx target / swap |
|---|---|---|---|
| `pill` | `{"color":"red\|yellow\|green","claim_id":str,"label":str}` | `<span id="pill-{claim_id}" class="pill pill--{color}">{LABEL}</span>` | `sse-swap="pill"`, `hx-swap="outerHTML"` |
| `chunk` | `{"token":str}` | `<span>{html_escaped_token}</span>` | `sse-swap="chunk"`, `hx-swap="beforeend"` into `#rule-stream` |
| `score` | `{"passed":bool,"before":int,"after":int,"n":int,"ci":[lo,hi]}` | JSON string of that dict | `sse-swap="score"`, `hx-swap="innerHTML"` |
| `done` | `{}` | `""` | `sse-close="done"` |
| `error` | `{"message":str}` (optional) | HTML span | `sse-error="abort"` |

Lifecycle, in order: `pill`(yellow / CHECKING…) → `chunk`×N → `pill`(green|red) → `score` → `done`. `ci` floats are 0..1 (Wilson). `score` carries the honesty numbers (counts + CI, never a bare %).

**Envelope (AUTHORITATIVE 2026-06-27 — reconciled to `/loop`'s COMMITTED `engine.py`; this block overrides the table's "/loop dict data" column).** `eval_stream` yields **semantic** dicts shaped `{"event": <name>, "data": {...}}` — **NO HTML** (the cheat-sheet §3a HTML-in-generator shape is superseded; `/web` renders). Exact committed shapes:
- pill:  `{"event":"pill","data":{"color":"red|yellow|green","check_id":str,"label":str}}`
- chunk: `{"event":"chunk","data":{"token":str}}`
- score: `{"event":"score","data":{"passed":bool,"before":int,"after":int,"n":int,"ci":[lo,hi]}}`
- done:  `{"event":"done","data":{}}`   ·   error: `{"event":"error","data":{"message":str}}`

**⚠️ pill-identity:** the `data["check_id"]` field **holds the `claim_id` value** (engine calls `_pill(claim_id, …)`; the key name is a legacy artifact). Use it as the pill DOM id. `/web/sse.py`: for each dict, render per the wire column using `d["data"]`, then `ServerSentEvent(event=d["event"], data=<rendered>)`. **Pill DOM id = `pill-{d["data"]["check_id"]}` (= claim_id); the dashboard MUST render its pills with the same claim_id value** or the `outerHTML` swap misses. (`/loop` is committed + reviewed — do not change it; `/web` builds to this.)

**Additive amendment (2026-07-02) — the `mint` field.** `score.data` gained one OPTIONAL key, `mint` (object | null): the grow story for a confirmed failure. A RED re-check now also drives the REAL grow path *inside* `eval_stream` (cluster → `mint_check` → `is_general` → persist via `upsert_check`), and the after-count is computed over the rubric INCLUDING a gated-in mint. Shape: `{"attempted": bool, "gated": bool, "id": str|null, "property": str|null, "cluster_size": int, "caught_siblings": int, "n_known_good": int|null, "error": str|null, "source": "loop"|"mock"}`; `mint` is `null` when the re-check flipped GREEN (a cleared false positive mints nothing). Both backends emit it (`loop.eval_stream` from `grow_report`; the mock scripted and labeled `"source":"mock"`). Event names are UNCHANGED — still exactly four + optional `error`. (2026-07-02 v2 surface: the final pill's `label` strings are now `SUPPORTED` / `CAUGHT` — the pill judges the ANSWER; label is display data, colors/DOM unchanged.) Wire nuance: `/web` HTML-entity-escapes the score's JSON string (the `#score-raw` target is an `innerHTML` swap; the browser's `textContent` read decodes it back to the exact JSON — unescaped, a minted property containing `<...>` would be parsed as markup and corrupt the payload). A grow-seam failure (Atlas/model unreachable) degrades to `mint.error` and the after-count falls back to the rewritten check alone — reported, never hidden. The engine caches each red-click's report (`loop.last_grow_report(claim_id)`; cleared by `loop.reset_grow_reports()`), and `/web`'s `/tree/{claim_id}` lineage REUSES it instead of re-running `grow` — one mint per click, and the panel shows the mint that actually happened.

---

## 3. Module interfaces

### `/store` — Atlas + Voyage (cheat-sheet §1)

```python
from store.models import Failure, Check, Verdict, AUTOutput, Source, EMBED_DIM

def get_db() -> "motor.motor_asyncio.AsyncIOMotorDatabase": ...   # singleton over MONGODB_URI
def embed(texts: list[str]) -> list[list[float]]: ...   # input_type="document"; 1024-dim
def embed_one(text: str) -> list[float]: ...            # convenience over embed([text])
def embed_query(text: str) -> list[float]: ...          # input_type="query" (asymmetric)
def ensure_index() -> None: ...                         # idempotent: create failvec (1024, cosine)
def seed(db) -> None: ...                               # numeric-cites-source seed Check + starters
async def save_failure(f: Failure, db) -> str: ...      # embeds if empty, upserts, returns id
async def nearest_failures(seed_text: str, db, *, limit: int = 12,
                           num_candidates: int = 200) -> list[Failure]: ...  # $vectorSearch on failvec
async def get_checks(db) -> list[Check]: ...
async def upsert_check(c: Check, db) -> str: ...
async def known_good_sample(db, k: int = 8) -> list[AUTOutput]: ...  # held-back passers for is_general
```

### `/loop` — eval engine (cheat-sheet §2)

**LLM backend (one seam — `loop/llm.py`).** The whole loop — `run_check` / `skeptic` / `grow` / `rewrite_rule_stream` — routes through `loop/llm.py` behind **`LOOP_BACKEND`**. Default **`gemini`** (Gemini 3.5 via Vertex/ADC — keyless, all-Google). Alternate **`anthropic`** runs the SAME functions on Opus 4.8 / Haiku 4.5 (the constants + request shapes below). **Cross-family independence:** the agent-under-test is always Gemini (`/fixtures`); set `LOOP_BACKEND=anthropic` so the checker/grower judges it from a *different* model family (Claude) — the headline config is then not "Gemini grading Gemini." The deterministic check anchors the demo task regardless of backend.

```python
HAIKU = "claude-haiku-4-5"; OPUS = "claude-opus-4-8"; CONF_FLOOR = 0.75   # anthropic backend
PRUNE_HI, PRUNE_LO = 0.95, 0.05

def deterministic(check: Check, claim: str, output: AUTOutput) -> bool | None: ...
def haiku_check(check: Check, claim: str, output: AUTOutput) -> Verdict: ...   # plain, no effort/adaptive
def opus_check(check: Check, claim: str, output: AUTOutput) -> Verdict: ...    # adaptive + effort=high
def run_check(check: Check, claim: str, output: AUTOutput) -> Verdict: ...     # det→Haiku→Opus escalation
def skeptic(output: AUTOutput, verdict: Verdict) -> Verdict: ...               # Opus adversarial: refute a pass
def mint_check(failure: Failure) -> Check: ...                                  # Opus, output_format=Check
def mint_check_from_miss(output: AUTOutput, why: str) -> Check: ...             # build Failure→save→grow
def mint_check_from_standard(text: str) -> Check: ...                           # owner's plain-English standard → Check (added 2026-07-02; id = std-<slug>)
def is_general(check: Check, known_good: list[AUTOutput],
               cluster_failures: list[AUTOutput]) -> bool: ...                  # pos==all & neg>=2
async def grow(worst_check: Check, db) -> Check | None: ...                     # cluster→mint→gate
async def grow_report(worst_check: Check, db) -> "GrowReport": ...              # grow + the full story (added 2026-07-02; grow() wraps it)
def prune(rubric: list[Check], items: list[AUTOutput]) -> list[Check]: ...      # drop <5% / >95% pass
async def rewrite_rule_stream(claim_id: str) -> "AsyncIterator[str]": ...       # yields rule-rewrite tokens
async def run_checker(claim_id: str, rule_text: str) -> bool: ...               # re-check after rewrite
async def eval_stream(claim_id: str) -> "AsyncIterator[dict]": ...              # §2 semantic dicts; /web consumes
```

`run_check`: returns det. result when present & agreeing with Haiku; escalates to Opus on det/Haiku disagreement OR (Haiku `confidence < 0.75` and no det. anchor). Escalation rate target 10–20%. `eval_stream` is the single generator `/web` iterates; internally it drives `rewrite_rule_stream` + `run_checker` and emits the §2 lifecycle.

### `/fixtures` — Gemini AUT + fixture questions

```python
def run_agent(fixture: dict) -> AUTOutput: ...          # Gemini 3.5 (or MOCK_AUT) over one fixture
def load_fixture_questions() -> list[dict]: ...         # working-pool fixtures (NOT gold)
def run_all() -> list[AUTOutput]: ...
def seed_failures(db) -> list[Failure]: ...             # run AUT, catch initial failure pool → Atlas
# gemini_answer(question, candidate_sources) -> AUTOutput  is PRIVATE to gemini_client.py
```

`run_agent` is the ONLY Gemini call site. Must populate `sources[].text` so deterministic checks match verbatim quotes. `MOCK_AUT` env flag gives a deterministic, no-API path. Targets the $5k Gemini prize.

### `/eval` — gold set + scoring + stats (cheat-sheet §5)

```python
def load_gold() -> list[dict]: ...                      # /eval/gold/*.json — frozen items (authored on-site, frozen:true, never edited in place) + owner-added items (g-owner-*.json, frozen:false, written ONLY via /web's copy-verified add path; 2026-07-03); read-only for /loop always
def score_rubric(rubric: list[Check], gold: list[dict]) -> list[bool]: ...      # per-item green/red
def wilson(passes: int, n: int) -> tuple[float, float]: ... # 95% CI, correct at small n
def sign_test(before: list[bool], after: list[bool]) -> dict | None: ...        # {"helped","hurt","p"}
def headline(before: list[bool], after: list[bool]) -> dict: ...                # {"before","after","n","ci"}
def lint_source(src: str) -> list[str]: ...             # eval/honesty.py — forbidden gold/eval patterns matched in one source blob (2026-07-03)
def run_honesty_lint(loop_dir=LOOP_DIR) -> dict: ...    # eval/honesty.py — the CI honesty gate as a function: {"clean","files_scanned","offenders"}; test_honesty_gate.py AND /web's cheat station call THIS (2026-07-03)
```

**Hard rail:** `/eval` is verification-only. `/loop` must NEVER import from `/eval` or read `/eval/gold/*.json`. One leak kills the honesty claim. Report direction + count + CI, never a bare %.

### `/web` — htmx/SSE UI (cheat-sheet §3)

```
GET  /                                       -> dashboard (rubric + claims, each with a RED pill)
POST /run                                    -> run AUT over a fixture → claim_ids + pill skeleton
GET  /fragment/improve-container/{claim_id}  -> HTML sse-connect div
GET  /stream/improve/{claim_id}              -> EventSourceResponse (emits §2 events via eval_stream)
GET  /tree                                   -> bonsai-tree viz (rubric grow/prune history)
POST /teach                                  -> owner intake: plain-English standard → check + REAL gate verdict (2026-07-02; keyless boxes record it "unverified", never a fake ADMITTED)
GET  /fragment/value-strip                   -> the three health tiles (refreshes on the `grow` event) (2026-07-02)
POST /cheat                                  -> "try to cheat it": lint a would-be /loop snippet AS TEXT via eval.honesty (the SAME checker CI's honesty gate runs) — a lint, not a sandbox; snippets are never written or executed (2026-07-03)
POST /gold/add                               -> answer-key manager: owner adds ONE labeled gold example → eval/gold/g-owner-*.json (frozen items untouched; rail-safe — only /loop is barred from gold). Copy-verify: written, read back, compared; a failed verify removes the file and is reported. Provenance (owner-added vs frozen) explicit in storage + receipt copy (2026-07-03)
# /healthz lives on the root app in main.py (DO health check)
```

`/web` imports `loop.eval_stream`, `fixtures.run_agent`, `fixtures.load_fixture_questions`, `eval.headline`; `web/sse.py` maps §2 dicts → `ServerSentEvent`. Owns NO checking/minting logic.

### `/deploy` — DigitalOcean (cheat-sheet §4)

```
deploy/app.yaml   # name: bonsai, http_port 8080, health /healthz, secrets via env
run: uvicorn main:app --host 0.0.0.0 --port 8080 --timeout-keep-alive 75
env (SECRET): MONGODB_URI · ANTHROPIC_API_KEY · VOYAGE_API_KEY · GEMINI_API_KEY
```

---

## 4. Cross-cutting invariants (don't break these)

- `claim` is the atomic eval unit everywhere; `AUTOutput.sources_text` is what deterministic checks match quotes against.
- Embeddings are **always** 1024-dim voyage-3: failures `input_type="document"`, queries `input_type="query"`.
- Rubric = `list[Check]`; it mutates only via `grow`/`prune` over the **working pool**, never the gold set.
- **LLM request shapes are per-backend, all behind `loop/llm.py`:** *gemini* (default) — Vertex `response_schema` JSON mode for structured verdicts/checks + `thinking_budget=0` (Gemini 3.x thinking shares the output budget, so disable it); *anthropic* — Opus calls `thinking={"type":"adaptive"}` + `output_config={"effort":"high"}` (no `budget_tokens`), Haiku plain.
- Models imported from `store.models`; no terminal redefines `Failure/Check/Verdict/AUTOutput/Source`.
- `/loop` never imports `/eval`; `/fixtures` never imports `/loop`,`/store`,`/web` (except `store.models` + `store.save_failure` inside `seed_failures`). `/fixtures` is the **agent-under-test** seam (always Gemini); the loop's **checker/grower** also run on Gemini by default (`LOOP_BACKEND=gemini`) or Claude (`anthropic`) — each behind its own seam (`fixtures/gemini_client.py`, `loop/llm.py`).
- This is an **eval harness**, not "basic RAG." Say harness.

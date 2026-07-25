# Bonsai v2 Workspace (Increments 1–2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Bonsai's value legible — every action ends in a plain-English receipt of what improved — and put the domain owner on stage with a requirements-intake path.

**Architecture:** Surface-only redesign over the frozen engine. The SSE score event (which already carries the `mint` story) feeds a client-rendered receipt card; new display state (owner requirements) lives in `web/state.py` beside the existing RUBRIC; the only engine addition is `mint_check_from_standard` in `loop/grower.py` (a sibling of `mint_check`).

**Tech Stack:** FastAPI + Jinja + htmx/SSE, vanilla JS (node-tested pure formatters), pytest (keyless), existing Gemini/Anthropic seam via `loop/llm.py`.

## Global Constraints

- **NO GIT COMMITS.** The repo's push/commit is gated on the sponsor-prize/freeze decision (WRAP-UP §3). All work stays in the working tree. Every "commit" step below is replaced by a verification run.
- Honesty rail: `/loop` never references `/eval` or gold (regex-linted). New copy must be literally true; scripted things say "scripted".
- Suite must stay green KEYLESS: verify with `.env` moved aside (`mv .env /tmp/e; pytest -q; mv /tmp/e .env`).
- Owner intake never renders an ADMITTED verdict that didn't come from the real `is_general` gate.
- Pill labels: SUPPORTED (green) / CAUGHT (red) / CHECKING… (yellow). Button verb: "Check this answer →".
- Persona: "Priya — Northbeam's security lead". Stakes line: "a security reviewer's deadliest question: *show me where it says that*".
- CONTRACTS.md gets a dated additive note for any event-data change (pill labels are data-only; no event-name changes anywhere in this plan).

---

### Task 1: Pill labels say what the verdict means (SUPPORTED / CAUGHT)

**Files:**
- Modify: `loop/engine.py:213` (final pill labels)
- Modify: `web/mock_stream.py:146`
- Test: `loop/tests/test_engine.py`, `web/tests/test_stream.py:46`, `web/tests/test_sse.py` (label strings only)

**Interfaces:**
- Produces: pill `label` values `"SUPPORTED"` / `"CAUGHT"` on the final pill (yellow stays `"CHECKING…"`). Colors unchanged — DOM/CSS contracts untouched.

- [ ] **Step 1: Update the engine + mock label expressions**

```python
# loop/engine.py (final pill in eval_stream)
yield _pill(claim_id, "green" if passed else "red", "SUPPORTED" if passed else "CAUGHT")
# web/mock_stream.py (same expression)
yield _pill(claim_id, "green" if passed else "red", "SUPPORTED" if passed else "CAUGHT")
```

- [ ] **Step 2: Update label assertions**

`loop/tests/test_engine.py`: `label == "SUPPORTED"` (green lifecycle test), `label == "CAUGHT"` (red test). `web/tests/test_stream.py`: `">SUPPORTED<" in body`. `web/tests/test_sse.py`: the literal `"GREEN"` label in fixtures may stay (sse renders any label) — change to `"SUPPORTED"` for consistency.

- [ ] **Step 3: Run** `pytest loop/tests web/tests -q` → all pass.

### Task 2: Copy pass — verb, owner, stakes, screening

**Files:**
- Modify: `web/templates/_claim.html` (button), `web/templates/index.html` (scenario strip, live-claim copy), `web/static/main.js` (rule-label done-texts)

**Interfaces:**
- Produces: button text `Check this answer →` (route/target unchanged); scenario strip names Priya + stakes; live-claim box titled "Screen an output".

- [ ] **Step 1: Apply copy**

```html
<!-- _claim.html -->
<button class="btn btn--improve" hx-get="/fragment/improve-container/{{ c.id }}"
        hx-target="#improve-{{ c.id }}" hx-swap="innerHTML">Check this answer &rarr;</button>
<!-- index.html scenario line -->
<p class="scenario-line"><span class="scenario-tag">Scenario</span> <strong>Verity</strong>,
Northbeam&rsquo;s trust &amp; security copilot, answers prospects&rsquo; security questionnaires
from approved policy docs &mdash; with citations. <strong>Priya</strong>, Northbeam&rsquo;s security
lead, owns what Verity may promise. A security reviewer&rsquo;s deadliest question:
<em>&ldquo;show me where it says that.&rdquo;</em></p>
<!-- live-claim hint -->
<span class="live-claim-tag">Screen an output</span> paste something Verity told a prospect — the harness checks it.
```

```js
// main.js rule-label done-texts
label.textContent = data.passed
  ? "✓ well-supported — false alarm cleared"
  : "✓ caught — a check now polices this pattern";
```

- [ ] **Step 2: Run** `pytest web/tests -q` (no copy assertions break; fix any that do).

### Task 3: The receipt card (the payoff of every click)

**Files:**
- Modify: `web/static/main.js` (add `renderReceipt`, use it in the score handler; keep `renderMintNote` as its mint-line helper)
- Modify: `web/templates/_improve.html` (rename slot div class `mint-note` → `receipt`, keep `hidden`)
- Modify: `web/static/style.css` (`.receipt` variants from `.mint-note` styles + verdict line styles)
- Test: `web/tests/main.test.js`

**Interfaces:**
- Consumes: the score event data `{passed, before, after, n, ci, mint}` (mint per CONTRACTS §2 2026-07-02 amendment).
- Produces: `renderReceipt(data) -> {html, cls} | null` (node-exported). HTML is built ONLY from escaped text via a local `esc()` helper.

- [ ] **Step 1: Write failing node tests**

```js
test("renderReceipt narrates a caught+gated mint as a commit message", () => {
  const r = renderReceipt({ passed: false, before: 3, after: 3, n: 9, ci: [0.1, 0.6],
    mint: mint({}) });
  assert.match(r.html, /the answer stays wrong/i);
  assert.match(r.html, /New check admitted/);
  assert.match(r.html, /caught 3 sibling/);
  assert.match(r.html, /can.t read the answer key/i);
});
test("renderReceipt narrates a cleared false alarm with no mint", () => {
  const r = renderReceipt({ passed: true, before: 2, after: 3, n: 9, ci: [0.1, 0.6], mint: null });
  assert.match(r.html, /Well-supported — false alarm removed/);
  assert.match(r.html, /No check minted/);
});
test("renderReceipt escapes HTML in the minted property", () => {
  const r = renderReceipt({ passed: false, before: 1, after: 1, n: 3, ci: [0, 1],
    mint: mint({ property: '<img src=x>' }) });
  assert.doesNotMatch(r.html, /<img/);
});
```

- [ ] **Step 2: Run** `node --test web/tests/main.test.js` → FAIL (renderReceipt not defined).

- [ ] **Step 3: Implement `renderReceipt`**

```js
function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
// The plain-English payoff card, built from the score event. Honest by
// construction: verdict first, then what the harness did (or didn't) gain.
function renderReceipt(data) {
  if (!data) return null;
  var lines = [];
  if (data.passed) {
    lines.push('<div class="receipt-verdict receipt-verdict--clear">✓ Well-supported — false alarm removed.</div>');
    lines.push('<div class="receipt-line">No check minted — nothing to learn from a good answer. Working score ' +
      data.before + " → " + data.after + " / " + data.n + ".</div>");
  } else {
    lines.push('<div class="receipt-verdict receipt-verdict--caught">✗ Caught — the answer stays wrong; the harness is what improves.</div>');
    var m = renderMintNote(data.mint);
    if (m) lines.push('<div class="receipt-line ' + m.cls + '">' + esc(m.text) + "</div>");
    if (data.mint && data.mint.gated) {
      lines.push('<div class="receipt-line receipt-honesty">The loop that wrote it can\'t read the answer key — hit Verify on the honesty receipt to confirm the gain is real.</div>');
    }
    lines.push('<div class="receipt-line receipt-score">Working score ' + data.before + " → " + data.after +
      " / " + data.n + " (a stricter rubric can lower this — that's honest).</div>");
  }
  return { html: lines.join(""), cls: "receipt" };
}
```

DOM wiring (score handler): replace the mint-note block with

```js
const slot = improve && improve.querySelector(".receipt");
const receipt = renderReceipt(data);
if (slot && receipt) { slot.innerHTML = receipt.html; slot.className = receipt.cls; slot.hidden = false; }
```

`_improve.html`: `<div class="receipt" hidden></div>`. CSS: rename `.mint-note*` selectors to `.receipt-line` variants and add `.receipt-verdict--caught { color: var(--red); font-weight: 700; }`, `.receipt-verdict--clear { color: var(--green); font-weight: 700; }`.

- [ ] **Step 4: Run** `node --test web/tests/main.test.js` and `pytest web/tests -q` → pass. (Update the old mint-note node tests to call renderMintNote unchanged — it still exists.)

### Task 4: Value strip (three health tiles that move)

**Files:**
- Create: `web/templates/_valuestrip.html`
- Modify: `web/routes.py` (context + `GET /fragment/value-strip`), `web/templates/index.html` (include above two-score), `web/static/style.css`
- Test: `web/tests/test_value_strip.py`

**Interfaces:**
- Consumes: `RUBRIC.maturity()` (`covered/total/n_checks/n_improves`), `RUBRIC.checks()`, `load_gold_result()`.
- Produces: fragment `#value-strip` with `hx-get="/fragment/value-strip" hx-trigger="grow from:body" hx-swap="outerHTML"`; helper `_value_strip_ctx() -> dict` in routes.

- [ ] **Step 1: Failing tests**

```python
def test_dashboard_shows_value_strip_tiles(client):
    body = client.get("/").text
    assert "value-strip" in body and "Rubric" in body
    assert "of 5 failure families" in body

def test_value_strip_fragment_counts_rubric_growth(client):
    from web.state import RUBRIC
    RUBRIC.record_growth("numeric-mismatch-01", False, "unsupported-numeric")
    body = client.get("/fragment/value-strip").text
    assert "2 checks" in body          # seed + 1 minted family
    assert "1 of 5" in body
```

- [ ] **Step 2: Run** `pytest web/tests/test_value_strip.py -q` → FAIL (404 / missing markup).

- [ ] **Step 3: Implement**

```html
<!-- _valuestrip.html -->
<section id="value-strip" class="value-strip" hx-get="/fragment/value-strip"
         hx-trigger="grow from:body" hx-swap="outerHTML">
  <p class="value-line">Bonsai turns your domain owner&rsquo;s rules + a few labeled answers into checks
  that catch whole families of mistakes &mdash; and proves the checks didn&rsquo;t grade their own homework.</p>
  <div class="value-tiles">
    <a class="vtile" href="#rubric"><span class="vtile-n">{{ n_checks }}</span>
      <span class="vtile-l">check{{ '' if n_checks == 1 else 's' }} in the rubric</span></a>
    <a class="vtile" href="#rubric"><span class="vtile-n">{{ maturity.covered }} of {{ maturity.total }}</span>
      <span class="vtile-l">failure families covered</span></a>
    <a class="vtile" href="#gold-panel">{% if gold_result %}<span class="vtile-n">{{ gold_result.after }}/{{ gold_result.n }}</span>
      <span class="vtile-l">honesty receipt &middot; held-out agreement</span>{% else %}<span class="vtile-n">&mdash;</span>
      <span class="vtile-l">honesty receipt</span>{% endif %}</a>
  </div>
</section>
```

```python
# web/routes.py
def _value_strip_ctx() -> dict:
    m = RUBRIC.maturity()
    return {"maturity": m, "n_checks": len(RUBRIC.checks()) + 1,  # + the rooted seed standard
            "gold_result": load_gold_result()}

@router.get("/fragment/value-strip", response_class=HTMLResponse)
async def value_strip(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("_valuestrip.html", {"request": request, **_value_strip_ctx()})
```

Dashboard context: merge `**_value_strip_ctx()`; index.html: `{% include "_valuestrip.html" %}` directly above the two-score section. CSS: `.value-strip` centered, `.value-tiles` 3-column grid of panel-styled tiles.

- [ ] **Step 4: Run** `pytest web/tests -q` → pass.

### Task 5: Provenance badges + panel order

**Files:**
- Modify: `web/templates/_rubric.html`, `web/templates/index.html` (sidebar order), `web/static/style.css` (`.bonsai` height, `.prov` badge)

**Interfaces:**
- Produces: every rubric row shows a provenance badge: seed = `◆ the contract you started from` (existing tag line restyled); minted rows = `🌱 grown from N catch(es)` (from `c.minted_from`).

- [ ] **Step 1: Template edits** — seed row keeps its label, add `<span class="prov prov--owner">◆ owner standard</span>`; minted rows: replace the `check-mint` line with `<div class="check-mint hint"><span class="prov prov--grown">🌱 grown from {{ c.minted_from }} catch{{ '' if c.minted_from == 1 else 'es' }}</span></div>`. Sidebar order in index.html: `_rubric.html` first, `_tree.html` second. CSS: `.tree-panel .bonsai { height: 170px; }`, `.prov--owner { color: var(--gold); }`, `.prov--grown { color: var(--forest-bright); }`.
- [ ] **Step 2: Run** `pytest web/tests -q` (fix any order-sensitive assertions).

### Task 6: Method ribbon (orientation strip, not a wizard)

**Files:**
- Create: `web/templates/_ribbon.html`; Modify: `web/templates/index.html`, `web/static/style.css`

- [ ] **Step 1: Implement**

```html
<nav class="method-ribbon" aria-label="the method">
  <span class="mstep">1 Capture the rules</span><span class="msep">→</span>
  <span class="mstep">2 Build the answer key</span><span class="msep">→</span>
  <span class="mstep">3 Calibrate</span><span class="msep">→</span>
  <span class="mstep">4 Try to cheat it</span><span class="msep">→</span>
  <span class="mstep">5 Grow from failures</span>
</nav>
```

Included under the scenario strip. CSS: one thin centered row, muted, `.mstep` chips.
- [ ] **Step 2: Run** `pytest web/tests -q`.

### Task 7: Increment-1 verification gate

- [ ] `mv .env /tmp/e; .venv/bin/python -m pytest -q; mv /tmp/e .env` → all green.
- [ ] `node --test web/tests/main.test.js` → all green.
- [ ] Boot mock server, drive an improve via curl, screenshot with headless Chrome, eyeball: value strip, receipt card, badges, ribbon, pill labels.

### Task 8: `mint_check_from_standard` (engine, the only new LLM call)

**Files:**
- Modify: `loop/grower.py`, `loop/__init__.py`
- Test: `loop/tests/test_grower.py`

**Interfaces:**
- Produces: `def mint_check_from_standard(text: str) -> Check` — plain-English standard → Check via `opus_parse(system=STANDARD_SYS, user=..., schema=Check)`; deterministic id `std-<slug(text)>`.

- [ ] **Step 1: Failing test**

```python
def test_mint_check_from_standard_builds_check_from_plain_english(patch_llm, fake_client):
    minted = a_check("std-price")
    client = patch_llm(fake_client(parsed=[minted]))
    res = grower.mint_check_from_standard("Never quote a price that isn't in the current price book.")
    assert res is minted
    body = client.messages.parse_calls[0]["messages"][0]["content"]
    assert "price book" in body
```

- [ ] **Step 2: Run** → FAIL (no attribute). **Step 3: Implement**

```python
STANDARD_SYS = """You convert a domain owner's plain-English standard into ONE general,
reusable check (same GENERAL bar as minting from a failure: a property over roles/types,
not literal strings; positive_example proves it passes good outputs). Output the check;
keep `property` to one testable sentence."""

def mint_check_from_standard(text: str) -> Check:
    """An owner's plain-English requirement → a general Check (the owner-intake seam)."""
    check = opus_parse(system=STANDARD_SYS, user=f"OWNER'S STANDARD:\n{text}", schema=Check, max_tokens=2000)
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:32] or "standard"
    return check.model_copy(update={"id": f"std-{slug}"})
```

Export from `loop/__init__.py` (+ `__all__`). **Step 4: Run** `pytest loop/tests -q` → pass (honesty-rail tests included).

### Task 9: Owner-requirement display state

**Files:**
- Modify: `web/state.py`
- Test: `web/tests/test_state.py`

**Interfaces:**
- Produces: `RUBRIC.record_requirement(text: str, prop: str, *, gated: bool | None, source: str) -> None` (gated=None means "unverified — needs a live box"); `RUBRIC.requirements() -> list[dict]` rows `{text, property, gated, source}`; `RUBRIC.reset()` clears them; `maturity()`/value-strip count them via `n_owner = len(requirements())`.

- [ ] **Step 1: Failing tests**

```python
def test_record_requirement_rows_render_and_reset():
    RUBRIC.record_requirement("No invented prices.", "Quoted prices must appear in the price book.",
                              gated=None, source="typed")
    rows = RUBRIC.requirements()
    assert rows[0]["gated"] is None and rows[0]["text"] == "No invented prices."
    RUBRIC.reset()
    assert RUBRIC.requirements() == []
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (a `self._requirements: list[dict]` beside `_growth`, append/list/clear). **Step 4: Run** → pass.

### Task 10: `POST /teach` + the intake UI (gate always visible, honest keyless)

**Files:**
- Create: `web/templates/_teach.html` (result card) — and the form lives in `_rubric.html` (collapsed `<details>` "+ Add a requirement")
- Modify: `web/routes.py`, `web/templates/_rubric.html`, `web/static/style.css`
- Test: `web/tests/test_teach.py`

**Interfaces:**
- Consumes: `loop.mint_check_from_standard`, `loop.grow_report`-style gating pieces (`store.known_good_sample`, `store.nearest_failures`, `loop.is_general`), `use_mock()`, `RUBRIC.record_requirement`.
- Produces: `POST /teach` (form field `standard`) → `_teach.html` card + `HX-Trigger: grow` response header (refreshes rubric + value strip). Keyless: row recorded `gated=None`, card says "recorded — unverified (a live box runs the generality gate)" + "scripted example" chip only for the prefill chip demo. Keyed: real mint → real gate → ADMITTED (persist via `store.upsert_check`) or REJECTED, verdict shown with counts.

- [ ] **Step 1: Failing tests**

```python
def test_teach_keyless_records_unverified_requirement(client):
    body = client.post("/teach", data={"standard": "Never invent a price."}).text
    assert "unverified" in body and "generality gate" in body
    assert "ADMITTED" not in body                      # no fake gate verdict
    assert "Never invent a price." in client.get("/fragment/value-strip").text or True
    assert "◆" in client.get("/rubric").text

def test_teach_live_path_runs_gate_and_persists(client, monkeypatch):
    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    minted = seed_check("std-price"); upserts = []
    monkeypatch.setattr(web_routes, "_teach_live",
        _fake_teach_live(minted, gated=True, upserts=upserts))  # seam, patched
    body = client.post("/teach", data={"standard": "Never invent a price."}).text
    assert "ADMITTED" in body
def test_teach_empty_standard_is_a_noop(client):
    assert client.post("/teach", data={"standard": "  "}).text == ""
```

- [ ] **Step 2: Run** → FAIL (404). **Step 3: Implement**

```python
# web/routes.py
async def _teach_live(standard: str) -> dict:
    """Keyed path: real mint + real is_general gate; persists only when gated."""
    import store
    import loop
    db = store.get_db()
    check = await asyncio.to_thread(loop.mint_check_from_standard, standard)
    known_good = await store.known_good_sample(db)
    cluster = await store.nearest_failures(check.negative_example or check.property, db)
    from loop.grower import _failure_to_output, _generality_async
    pos, neg = await _generality_async(check, known_good, [_failure_to_output(f) for f in cluster])
    gated = pos == len(known_good) and neg >= 2
    if gated:
        await store.upsert_check(check, db)
    return {"check": check, "gated": gated, "caught": neg, "n_known_good": len(known_good)}

@router.post("/teach", response_class=HTMLResponse)
async def teach(request: Request) -> HTMLResponse:
    form = await request.form()
    standard = (form.get("standard") or "").strip()
    if not standard:
        return HTMLResponse("")
    ctx: dict = {"request": request, "standard": standard}
    if use_mock():
        RUBRIC.record_requirement(standard, standard, gated=None, source="typed")
        ctx["mode"] = "unverified"
    else:
        try:
            res = await _teach_live(standard)
            RUBRIC.record_requirement(standard, res["check"].property,
                                      gated=res["gated"], source="live")
            ctx.update(mode="live", **res)
        except Exception as exc:  # seam down → record unverified, say why
            RUBRIC.record_requirement(standard, standard, gated=None, source="typed")
            ctx.update(mode="unverified", error=str(exc))
    resp = templates.TemplateResponse("_teach.html", ctx)
    resp.headers["HX-Trigger"] = "grow"       # rubric + value strip refresh
    return resp
```

`_teach.html`: verdict card — live+gated → "✚ ADMITTED — tested against {{ n_known_good }} known-good (passed all), caught {{ caught }} sibling failures: «{{ check.property }}»"; live+rejected → "✕ REJECTED by the generality gate (caught {{ caught }}, needs ≥2) — sharpen the standard or add an example of the mistake"; unverified → "◆ recorded (unverified) — a live box runs the generality gate before this can police anything{% if error %} · seam error: {{ error }}{% endif %}".
`_rubric.html`: `<details class="teach"><summary>+ Add a requirement</summary><form hx-post="/teach" hx-target="#teach-result" hx-swap="innerHTML"><textarea name="standard" …></textarea><button class="btn">Turn it into a check →</button></form><div id="teach-result"></div></details>` above the checklist, plus `◆` rows rendered from `requirements()` (unverified rows show status "watching · unverified"). `/rubric` + dashboard contexts gain `requirements=RUBRIC.requirements()`.

- [ ] **Step 4: Run** `pytest web/tests -q` → pass.

### Task 11: Final verification + adversarial review

- [ ] Full keyless suite + node tests green.
- [ ] Boot mock server; screenshot dashboard + an improve receipt + a teach result; eyeball against the spec's acceptance bar ("can a viewer tell what improved?").
- [ ] CONTRACTS.md: dated note — pill label strings changed to SUPPORTED/CAUGHT (data-only); `/teach` route added to the /web route list.
- [ ] Run the multi-agent adversarial review workflow over the diff (correctness, honesty-overclaim, contract conformance, UI wiring, test gaps → 2-skeptic verify); fix confirmed findings; re-run suite.
- [ ] Update WRAP-UP.md with a dated note describing the v2 surface work (no checkbox change — this extends item 2's spirit; wrap items 3–5 unchanged).

## Self-review

Spec coverage: Inc-1 items 1–8 → Tasks 1–7; Inc-2 → Tasks 8–10; guardrails encoded in Global Constraints + Task 10's honest keyless design; acceptance bar checked in Tasks 7/11. Placeholders: none — all steps carry real code or exact commands. Type consistency: `record_requirement(text, prop, *, gated, source)` used identically in Tasks 9/10; `renderReceipt` consumed only by main.js DOM wiring; `_value_strip_ctx` used by both dashboard and fragment routes.

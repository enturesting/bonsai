# NEXT — the Bonsai work queue

*The resume point. Retuned 2026-07-02 (late) per the continue/stop analysis:
vault `private/projects/bonsai/16-where-it-plugs-in-continue-stop.md` — verdict:
**continue, narrowly**. The queue now optimizes for ONE thing: **the owner's
side visibly working** (a taught rule really catching a claim), then the
time-sensitive public payoff (essay + plugin — the honesty-gate window is
narrowing: `auto-harness` OSS now ships an equivalent mechanic).*

## How to resume (any session, human or agent)

1. Read `WRAP-UP.md` (state + goals + tripwire), then this file, then the
   continue/stop analysis above if direction feels unclear.
2. Sanity check: `mv .env /tmp/e; .venv/bin/python -m pytest -q; mv /tmp/e .env`
   (expect ~175 passed keyless) and `node --test web/tests/main.test.js` (16 pass).
3. Run it: `WEB_MOCK_STREAM=1 MOCK_AUT=1 WEB_MOCK_DELAY=0.04 .venv/bin/python -m uvicorn main:app --port 8000`
4. Pick the top unchecked item. Design intent:
   `docs/superpowers/specs/2026-07-02-bonsai-v2-workspace-design.md`.

**Standing rules:** no commits/pushes (frozen until Q10). Honesty first: no UI
sentence may overclaim; scripted things say scripted; gate verdicts are always
the real `is_general` outcome. Tripwire: if anything blows past ~2 weeks of
evenings, stop and ship Q11 — it's the payoff regardless.

---

## Queue (ranked — owner-visibility first, payoff second)

### The load-bearing move

- [ ] **Q6 · Screen-an-output, REAL path on a keyed box (M) — TOP.** A typed
  claim runs real `run_check` against the current rubric (incl. taught,
  gate-admitted checks). This turns the owner's side from *recorded* to
  *catching* — prerequisite for M4, M1, and a truthful Q9. Files:
  `web/routes.py:/live-claim`, `web/streams.py` guards, `web/live_claims.py`.
  Accept: teach "dogs can never fly" on a keyed box → screen "dogs can always
  fly" → CAUGHT by *your* check, receipt says so.
- [ ] **M4 · Owner golden-path demo (S, after Q6).** The acceptance test made a
  scripted-free ritual: owner adds a rule → real `is_general` verdict on screen
  → contradicting claim screened → CAUGHT. One recorded pass = the demo bar
  ("the owner's part visibly working"). Do Q6 alone first; this is the fusion.
- [x] **Q5 · Answer-key manager (M).** Owner adds labeled gold examples from
  /web (rail-safe: only /loop is barred from gold). The other half of the
  owner's side: their labels, not just their rules. Files: `web/gold.py`,
  new fragment, `eval/gold/` write path with copy-verify discipline.
  DONE 2026-07-03 (Track C wave): `POST /gold/add` → `add_gold_item` with real
  copy-verify (write → read back → compare; mismatch removes the file and the
  panel says so); items land as `g-owner-*.json` with `frozen:false` +
  `provenance:"owner-added"`; frozen 15 untouchable (no overwrite; ❄ vs ◆
  chips in `_goldkey.html`); stored receipt now says owner-added items are
  not in it; traversal-safe ids; 12 tests in `web/tests/test_gold_add.py`.

### The payoff (time-sensitive — publish before the window closes)

- [ ] **Q11 · Essay + themeless pytest plugin (2 evenings for the publishable
  unit).** Evening 1: the essay — COIN the pattern + its taxonomy: runtime
  blindness (auto-harness — cite generously, incl. their open issue #25 asking
  for exactly our regression-test layer) · build-time gate (us, reference impl)
  · owner calibration (us, direction+CI receipt) = "defense in depth for
  self-improving eval loops." Evening 2: extract `test_honesty_gate.py` + the
  Wilson receipt into the `honesty-gate` pytest plugin (importable checker seam
  + pytest entrypoint), publish. Needs ZERO new engine work — do not block on
  Q6/M4 (their recording strengthens it later). Strategy + recon: vault
  `private/projects/bonsai/16-*.md` addendum. The moat is owning the
  DEFINITION, not the 47-line lint (a weekend clone) — first-to-name decays,
  so this ships before everything except Q6. **Ships regardless of all else.**
  PLUGIN HALF DONE 2026-07-03 (Track C wave): standalone `honesty-gate/`
  package — importable checker seam (`check()`/`forbid_*` → structured
  violations, never-vacuous), `pytest11` entrypoint, Wilson receipt module
  (formatter cannot emit a bare %); own 26-test suite green keyless (run from
  the package dir; deliberately NOT pip-installed, NOT in root testpaths, NOT
  published — publish is Q10-gated). REMAINING: Evening-1 essay (Nic's voice,
  attended) + publish; add package-local CI before publishing.
- [ ] **M2 · (folded into Q11)** The plugin IS the themeless library the factory
  imports later — design its API with an importable checker seam, not just the
  pytest entrypoint.
- [x] **Q4 · "Try to cheat it" station (M).** Runs the ACTUAL honesty-gate lint
  keyless ("the exact check CI runs, running now"), labeled "a lint, not a
  sandbox." Makes the moat legible to a visitor; doubles as the plugin's demo.
  DONE 2026-07-03 (Track C wave): checker extracted verbatim to
  `eval/honesty.py`; the CI gate test now calls the same `run_honesty_lint()`
  (plus new vacuous-scan guard + injected-leak tests — rail strengthened, not
  weakened); station lives in the gold honesty band (`_cheat.html`,
  `POST /cheat`), canned + typed snippets linted as text by the real checker;
  9 tests in `web/tests/test_cheat.py`; CONTRACTS.md updated.

### Hand-held intake (after Q6 — it needs something real to feed)

- [ ] **M1 · Owner-intake Claude skill, HAND-HELD (M).** Conversational
  interview (doc 08 shape: one skill, run *with* the owner, self-serve is
  fantasy) that emits requirements + labeled examples into `eval/gold/` +
  `/teach`. Kill-criterion: if the minted checks read as generic YAML the owner
  ignores, stop at the manual 30-min interview.

### Factory dogfood (gated — do not start before the factory's g1/g2 close)

- [ ] **M3 · Disposable dogfood probe (≤1 evening, ADVISORY-ONLY).** Nic labels
  5 past research artifacts pass/fail (held-out), teaches one plain-English
  standard, checks the gated judge agrees with the labels above baseline AND
  reads as "that's my standard." Kill if it's generic YAML or the labels are
  the only signal. Never standing infra; no autonomous push (doc 07 envelope).
  BLOCKED BY: factory g1 (no work bead has ever round-tripped) + g2 (no
  sweeper). A dumber 80% substitute exists (FLOOR verdict column) — the probe
  must beat it to justify itself.

### Wrap & admin

- [ ] **Q9 · Prove it once, on camera (user-driven) — REFRAMED.** Center the
  OWNER, not the mint mechanics: teach a rule live → real gate fires → typed
  claim CAUGHT → Verify-now recompute. (= record M4 on the wired box.)
  Blocked on: user at keyboard + GCP/Atlas creds.
- [ ] **Q10 · Sponsor-prize / freeze decision (user-driven).** Check Discord →
  decide commit/push (public repo + DO app still run pre-wrap code until then).
- [ ] **Q12 · Banner the repo (S, after Q10).** README: "capstone / stable
  reference implementation."
- [x] **Q3 · Teach-form expectations on keyless boxes (S) — REWORDED.** Hint
  before submit: "demo records your rule but can't test it — a live box runs
  the gate" + unverified card gains "won't catch anything yet"; point at the
  Q6 path. (Keeps the flying-dogs confusion from recurring.)
  DONE 2026-07-03 (Track C wave): `_teachpanel.html` keyless branch on
  `can_verify` + `_teach.html` card copy; Q6 pointer is prose-only by design
  (no link until screening exists); 3 tests in `web/tests/test_teach.py`.
- [x] **Q1 · Demo-mode banner (S) — DEMOTED.** Honest labeling for the scripted
  mock (mode chip + screen-an-output hint + mock-lineage "re-enactment"
  narration — Q2 folded in here). Worth an hour, never an evening; the real
  fix for the confusion is Q6.
  DONE 2026-07-03 (Track C wave): header chip "demo mode — scripted mock" /
  "live mode — real model + gate" driven by one real `use_mock()` probe
  (`index.html`), mock-only hero hint, live-claim copy now says "scripted
  replay" (true in every mode today), lineage badge "re-enactment · offline
  mock" + re-enactment narration (`_lineage.html`); tests in `test_routes.py`
  + `test_lineage.py` incl. cross-mode negatives.

### Cut / deferred (traceability — don't silently resurrect)

- ~~Q2 · Mock lineage narration~~ — folded into Q1 (same honest-labeling pass).
- ~~Q7 · Hero-flip layout~~ — cosmetic; no owner signal; spec says never near a demo.
- ~~Q8 · CoverPilot second workspace~~ — old "second scenario" goal; no owner
  signal; risks the one real gold receipt. Revisit only if a regulated-domain
  demo is actually scheduled.
- ~~Enterprise sidecar/product~~ — killed by analysis: Anthropic Outcomes ships
  the primitive; concede the category (essay/plugin/workshop transfer instead).

---

## Done (recent, for context)

- [x] 2026-07-03 — Track C wave (Q3, Q1+Q2, Q4, Q5, Q11-plugin-half), keyless
  + commit-free per HANDOFF.md: suite 175→215 green keyless (+3 skip) + 16
  node + 26 plugin tests; 37-agent workflow (per-item implement → 3 skeptics →
  verified blockers → fix → suite gate), final audit ACCEPT on all five.
  Small follow-ups it surfaced: (a) conditionalize the mock lineage diagram's
  node meta labels ("Atlas $vectorSearch" etc., `_lineage.html:34-56`) on
  `lineage.source == "atlas"` — narration above already disclaims them;
  (b) when Q6 lands, revisit ALL forward-promise screening copy in one pass
  (hero hint, live-claim hint, Q3 teach hints) or it flips honest→stale;
  (c) owner gold is add-only (no UI delete) — say so or add removal later.
- [x] 2026-07-02 AM — WRAP-UP item 2 "pitch true in the live path": grow wired
  into `eval_stream`, gold Verify-now, two-score hero; 25-agent review, 4 fixes.
- [x] 2026-07-02 PM — v2 workspace surface (spec + plan in `docs/superpowers/`):
  receipt card, value strip, provenance badges, SUPPORTED/CAUGHT pills, Priya +
  stakes, method ribbon, owner intake (`/teach`, honest keyless degradation);
  28-agent review, 4 fixes (incl. the 4ms teach-card wipe); layout fit passes
  (laptop + wide monitor). Suite 175 keyless + 16 node.
- [x] 2026-07-02 late — continue/stop deep research (10-leg cited + 2-skeptic
  workflow): verdict "continue, narrowly"; queue retuned to owner-visibility +
  time-sensitive Q11. Deliverable: vault `private/projects/bonsai/16-*.md`.

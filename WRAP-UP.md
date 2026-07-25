# Bonsai: where it is, where it needs to be, and what "done" means
*Written 2026-07-01, after the AIEWF hackathon and a full market + code review. This is the single file to read before touching the project again.*

> **Resuming work? The live work queue is [`NEXT.md`](NEXT.md)** — ordered, sized, with file pointers and a how-to-resume header. This file is the why; NEXT.md is the what-next.

---

## 1. What Bonsai does (say it this way)

**Hallway version (one sentence):**
> Bonsai catches an AI citing a source that doesn't actually say what the AI claims, and turns each miss into a permanent test.

**The novel part (one sentence, this is the differentiator):**
> It has a CI test that fails the build if the self-improving eval loop ever peeks at the human answer key it's graded against.

**Work vocabulary version (for compliance/enterprise ears):**
> Write down a domain owner's pass/fail judgment once as labeled examples, tune an automated checker until it agrees with them, block anything below that bar, and grow the example set from real failures.

**Plain paragraph (repeatable by a non-technical person):**
Bonsai watches an AI assistant that answers questions with citations. When the assistant says something its cited source doesn't actually support, Bonsai catches it, groups it with similar past mistakes, and writes a reusable check so that whole family of mistake gets caught from then on. To prove it isn't grading its own homework, progress is measured against a small human-written answer key that the self-improving part is forbidden, by a code check, from ever reading.

If a listener can't repeat one of these back, the pitch failed, not the listener. Never lead with mint/grow/prune mechanics; that's Q&A depth only.

---

## 2. Where we are (honest state, verified 2026-07-01)

**Real and working:**
- The spine code exists and is tested (checker, skeptic, grower, pruner, eval_stream). 93 green tests.
- Atlas $vectorSearch live-verified once (cosine ~0.85, voyage-3 1024-dim); Gemini 3.5 via Vertex live-verified (`scripts/gemini_live.py`).
- Deployed and public: https://bonsai-h7rzp.ondigitalocean.app/ (runs the scripted mock; keyless).
- The gold numbers are real, computed once and stored: 9 of 15 agree before, 14 after, Wilson 95% CI [70.2%, 98.8%], 5 helped / 0 hurt, sign test p = 0.031.
- The frozen gold set is ~15 real human-authored items in `eval/gold/`.

**The four gaps (claim vs. code)** *(snapshot as verified 2026-07-01, kept as written for the record. Update 2026-07-02: gaps 1 and 2 closed — see the ticked §3 item; gap 3 closed with the honesty-debt item; gap 4's streams-gating half turned out already fixed pre-wrap, while `prune`/`skeptic`/the autonomous cycle still have no live runtime caller — deliberately out of wrap scope):*
1. Clicking **Improve does not mint a check.** `loop/engine.py eval_stream()` only rewrites the seed check's property string in memory. The real grow/mint/is_general path runs only in the `/tree/{claim_id}` lineage route and unit tests.
2. The **9→14 receipt is precomputed**, loaded from `eval/gold_result.json` at page load (`web/routes.py:60-72`). Clicks never recompute it.
3. The **honesty gate is not build-failing.** `eval/tests/test_honesty_gate.py` exists but `pytest.ini` testpaths exclude it, and there is no `.github/workflows`. README, DIAGRAM, and submission still say "build-failing" in six places. This is the project's own worst overclaim.
4. `prune`, `skeptic`, and the autonomous cycle have **no live runtime caller**. Also: `web/streams.py` only enables the real stream when `ANTHROPIC_API_KEY` is set, so the Gemini backend can't drive the live path.

**Housekeeping:** `enterprise-demo-BANK.md` is mislabeled (it contains the Medicare scenario, not the bank one). Rename or delete it.

**Market reality (July 2026):** the failure-to-regression-check loop is shipped product now. Braintrust Loop converts production failures into eval cases in one click; LangSmith Engine watches traces, clusters failures, and proposes eval coverage; OpenAI acquired Promptfoo in March. Bonsai cannot and should not race this. **No surveyed platform ships the honesty gate** (a build-enforced "the eval generator can't read the held-out gold set" guarantee, with improvement reported as direction plus a confidence interval, never a bare percent). That remnant is the whole reason to finish this properly. 2026 research on verifier gaming (models overwriting unit tests, monkey-patching scorers) says the problem is real.

---

## 3. Where we need to be ("complete" = every sentence in section 1 is literally true)

Definition of done, in order:

- [x] **Pay the honesty debt (half day).** DONE 2026-07-02: `pytest.ini` testpaths now include `loop/tests` + `eval/tests` (suite went 93 → 140 tests, all green, runs without `.env`); `.github/workflows/ci.yml` runs pytest on push; the gate was verified to fail on an injected `eval/gold` leak and pass after revert; "provably"/"architecturally"/"physically separated"/"prove the improver didn't cheat" overclaims corrected in README + DIAGRAM; submission.md got a dated errata note (preserved as submitted); `enterprise-demo-BANK.md` renamed to `enterprise-demo-v1-superseded.md` with a status note. NOTE: the public GitHub repo stays overclaiming until these changes are committed and pushed, which is gated on the sponsor-prize / freeze decision.
- [x] **Make the pitch true in the live path (1-2 days).** DONE 2026-07-02 (code + tests; the live end-to-end proof run is the next item): (1) `eval_stream` now drives the REAL grow path on a confirmed-failure re-check — new `loop.grower.grow_report()` (cluster→mint→`is_general`→persist; `grow()` wraps it) called via a patchable `_grow_from_miss` seam, the after-count computed over the rubric INCLUDING the gated-in check, and the mint story riding an additive `mint` field on the SSE `score` event (CONTRACTS §2 amended; the mock mirrors it labeled `source:"mock"`; seam failures degrade to a reported `mint.error`, never a dead stream). (2) Gold receipt recompute behind an explicit **Verify now** button (`POST /gold/verify` + `web/gold.py`; keyless/mock boxes keep the precomputed receipt honestly labeled; a failed rescore falls back to the stored receipt visibly). (3) The `ANTHROPIC_API_KEY`-only gating in `web/streams.py` was ALREADY fixed before this pass (Gemini backend exempted + tested `test_gemini_backend_needs_no_anthropic_key_uses_real_loop`) — that gap note was stale when written. (4) The two-score gap is now the hero band: working score vs. frozen-gold receipt side by side above the fold, with the "if the left climbs while the right stalls, the loop is gaming its own tests" tell. Suite 140 → 160 tests, green, verified offline with `.env` removed. A 25-agent adversarial review (5 lenses × 2-skeptic verification, Opus 4.8) then confirmed 4 findings, all fixed: the gold receipt now renders regressions as regressions (direction-aware copy + a red `down` state — it used to hardcode "gain is real" over a drop); the working-score copy no longer claims a confirmed failure "stays flat" (a gated-in mint can lower the conjunction count — copy now says so); the mint-note surfaces the ACTUAL seam error instead of a canned "store unreachable"; the score JSON is entity-escaped for its innerHTML swap (a minted property containing `<...>` would have corrupted the payload). Plus one self-caught bug the fleet missed: the `/tree` lineage route re-ran `grow()` after the stream had already minted — it now reuses the click's cached `GrowReport` (`loop.last_grow_report`), one mint per click. NOT yet done: an actual wired-box run of the new path (Atlas + Vertex) — that is exactly what the recording item below proves.
- **[v2 surface, added 2026-07-02 — extends the item above]** After a 3-design × 3-judge panel (raw output in the vault: `bonsai-hackathon/v2-design-panel-raw-2026-07-02.json`), the surface was rebuilt around "a workspace with a visible owner" (spec: `docs/superpowers/specs/2026-07-02-bonsai-v2-workspace-design.md`): pill labels now judge the ANSWER (SUPPORTED/CAUGHT — the answer never "turns green" because the harness improved); every check run ends in a plain-English **receipt card** (verdict → mint story with real gate counts → score delta); a **value strip** (checks / family coverage / gold receipt) that moves on the same grow event; **provenance badges** (◆ owner standard vs 🌱 grown from catch); Priya (the owner persona) + stakes line; a method ribbon; the tree demoted; and the roadmap's unbuilt Move-2 **owner intake** (`POST /teach` + `mint_check_from_standard`): plain-English standard → check → the REAL `is_general` verdict (keyless boxes record it "unverified" — never a fake ADMITTED). A second 28-agent adversarial review (4 lenses × 2 skeptics, Opus) confirmed 4 findings, all fixed: the teach verdict card was being wiped ~4ms after rendering (its target sat inside the `grow`-reswapped #rubric — reproduced in a real browser; intake now lives in its own panel outside the swap region); the real `_teach_live` gate+persist body had zero test execution (now seam-tested both directions); duplicate re-teach double-counted the value strip (record_requirement now de-dupes like record_growth); and the receipt's "hit Verify" line pointed at a button that doesn't exist on the mock box (now real-mints-only). Suite 160 → 175 green keyless + 16 node tests. Increments 3–4 (answer-key manager, screen-an-output real path, cheat station, hero-flip layout, second example workspace) are specced but unbuilt.
- [ ] **Prove it once, on camera.** Run the full loop live end to end one time (catch → cluster → mint → gate → receipt recompute) and record it. One honest recording beats any amount of narrative.
- [ ] **Extract the one novel idea (2-3 days).** Pull `test_honesty_gate.py` plus the Wilson-CI receipt into a small framework-agnostic pytest plugin, and write the ~1,500-word essay ("honesty gates for self-improving eval suites"), citing the verifier-gaming literature, with Bonsai as the now-true reference implementation. Publish publicly; no cold DMs.
- [ ] **Banner the repo.** README status line: "capstone / stable reference implementation." Keep it public (portfolio value; check Discord for Gemini/MongoDB sponsor-prize results before any visibility change).

**Tripwire:** if the wire-grow() step blows past two weeks of evenings, that is the documented design-exceeds-build pattern recurring. Stop, ship the essay against the lineage-route path instead, and banner the repo as-is.

---

## 4. How it's useful, and how to make that legible at the same time

The lesson of the hackathon was that these are the same problem: the parts that were hard to explain (mint/grow/prune) are the parts the market already ships under simpler names, and the part that is easy to explain (the answer-key sentence) is the only novel part. So usefulness and legibility now point at the same three targets:

1. **A citable idea with my name on it.** The essay + plugin is the artifact people can use (drop the plugin into any eval repo) and understand in one sentence. This is the public payoff.
2. **The method for the day job.** Bonsai's real enterprise idea (tribal knowledge → labeled golden set → calibrated judge → agreement gate, reported as direction + CI) transfers as people/process into the judge-calibration workshop at work. Ideas and specs transfer; this codebase never enters the bank, and bank specifics never enter this repo.
3. **A finished portfolio proof.** "Built, deployed, and made every claim true, solo" is the story. The recording plus the green CI badge is the evidence.

What Bonsai is **not**: a product. Anyone needing the failure-to-eval loop should use Braintrust or LangSmith; anyone needing an open stack should use Langfuse + DeepEval. Say this out loud when showing it; conceding the category is what makes the remnant credible.

---

## 5. Wrap criteria

Done means: CI green with the honesty gate in it, the live loop recorded once, the essay and plugin published, the README bannered. After that, no more feature work. Thirty days after wrap, review against the standing bar: it either compounded (essay read, plugin used, workshop material reused, or ~3 hours/month saved) or it's closed for good with the learnings banked. Either outcome is a win; the only losing move is an unfinished repo whose README overclaims.

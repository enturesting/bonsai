# Bonsai — hackathon lessons & forward plan
*AI Engineer World's Fair Hackathon 2026 · solo build · didn't place top-6 · written 2026-06-28*

## What actually happened (don't let the result erase it)
In ~24h, solo, you built and **deployed** a self-improving eval *harness* with a genuinely novel wedge (a build-checked separation between the check-minting loop and the gold it's graded against), real Gemini 3.5 + Atlas $vectorSearch + Voyage, a live public URL, a polished README/diagrams, 93 green tests, and a working on-stage demo. Most teams don't ship that. **Placement ≠ value created.**

## Why it didn't place (honest)
1. **Solo = one brain doing build AND pitch.** The winners were ≥2 people. The real advantage of a second person isn't more code — it's a **split brain**: one person can obsess over the *narrative/legibility* while the other goes deep on the *product*. Solo, you (correctly) chose depth, and the pitch got the leftover cycles.
2. **You built it so big it got hard to *hold in your head* — and to narrate.** Depth is a strength that becomes a liability at pitch time: more surface area = more places to wander. On stage you jumped around the run-of-show (`demo-day/3-DEMO--runofshow-and-qa.md`) instead of riding one thru-line.
3. **Under-rehearsed the *spoken* delivery.** You had the doc; reading-while-presenting ≠ rehearsed. Live Demo is 20% of the score and Q&A feeds the 40% Technicality — both reward a smooth, confident verbal performance, which only comes from saying it out loud 3-5×.
4. **Legibility, not capability, was the gap.** The substance was there; a judge in 3 minutes buys what they can *follow*, not what's *true*.

## The transferable lessons (for next time)
- **Pick a build-to-pitch ratio up front.** For a judged hackathon, reserve the last ~2 hours for *nothing but* rehearsing the spoken demo + Q&A. Treat the pitch as a deliverable, not a wrap-up.
- **One thru-line, memorized.** The arc you landed on is strong — *fear → "evals are broken" → watch it catch + write its own check + show it didn't cheat → only now name it "eval harness."* Memorize THAT spine; everything else is optional depth you deploy only if asked.
- **Rehearse out loud, with a timer, ideally to a person.** If solo, record yourself once and watch it back — you'd have caught the jumping-around instantly.
- **Depth is for Q&A, not the demo.** Keep the 3-min ruthlessly simple; let the deep stuff (the positioning, the honesty-rail nuance, the future-state) live in the back pocket for "tell me more."
- **The solo move was still right *for you*.** You optimized for learning + a real product over a polished 3 minutes. That compounds; a trophy doesn't. Just go in eyes-open next time about the tradeoff.

## What's genuinely yours to keep (regardless of placement)
- A **working, deployed, novel system** + a deep competitive/positioning map (`demo-day/3-DEMO--positioning.md`) + a vision pack + ELID/diagrams + the enterprise-demo fixture sets (bank + healthcare). These are portfolio- and work-grade assets.
- A real **point of view**: trust/verification as the bottleneck on autonomous AI, and a build-checked honesty rail as the mechanism. That's a thesis you can carry into conversations, work, and future builds.
- The **skill** of going 0→deployed→demoed solo in a day. That's rare and hireable.

## Forward plan
**Repo public vs private:**
- **Keep it PUBLIC until the sponsor prizes are announced on Discord** (Gemini / MongoDB) — going private now could cost you a $5k shot for no reason.
- **After that, decide by intent:**
  - *Portfolio / credibility / open exploration* → keep public. It's polished and deployed; it's a strong "here's what I ship" artifact for hallway convos, recruiters, and your own brand.
  - *Serious product / commercialize / repurpose for work* → go private, keep iterating "in the dark." (Honest caveat from the research: the moat is thin/combinational — a few-day feature others could replicate — so privacy buys *focus*, not a hard moat.)
  - Default for a solo builder: **public is probably the higher-EV move** unless you have concrete plans to build it as a product or use it at work.
- Either way: the learnings, docs, and assets are yours regardless of repo visibility — capture them now (this file + `demo-day/`).

**Driving it forward:**
- Tighten the spoken pitch (you already have the materials) and reuse it in hallway convos this week — low stakes, high reps.
- Pick ONE rough edge to round out (e.g., harden the honesty rail from a lint toward real isolation, or run the full live loop end-to-end) — a concrete next milestone keeps momentum.
- Consider a short write-up ("I built a self-improving eval harness in 24h — here's the honesty-rail idea") — turns the work into reach + feedback.

## Code-truth gaps (from the pre-demo audit; the most honest lessons)
A deeper code audit (a separate prep session) found the *live* path had drifted from the *narrative* — the deepest "built it so big it got hard to hold" lesson, made concrete. **Confirmed this session:**
- **Clicking "Improve" does NOT mint a new gated check.** `loop/engine.eval_stream` only rewrites the seed check's `property` string in-memory and re-checks one claim. The real `grow()` / `mint_check` / `is_general` / `$vectorSearch` path runs only in the `/tree/{claim_id}` lineage route + unit tests. (Biggest claim-vs-code gap.)
- **The "9 → 14 / 15" receipt is precomputed** — loaded from `eval/gold_result.json` (`web/routes.py:66`), rendered on page load. On-stage clicks don't recompute it.
- **The honesty rail is NOT "build-failing CI" today.** `test_honesty_gate.py` passes when run directly, but `pytest.ini` testpaths = `store/tests web/tests` (excludes `eval/tests`) and there's **no `.github/workflows`** — nothing runs it automatically. README / DIAGRAM / about **overstate** it ("a build-failing test"). It's a real, valuable *static grep* of `/loop`, but it's not wired to fail any build. *(My mid-build README softening fixed "build-provably" but missed this — lesson: verify the claim against the actual test wiring, not the test's existence.)*
- **`prune`, `skeptic`, and the autonomous catch→cluster→mint→grow→prune cycle have no live runtime caller** — they exist + are tested, but nothing drives them at runtime.

**Why this is the best lesson, not a gotcha:**
1. **Founder-fluency:** knowing *exactly* what's live vs mock vs precomputed makes you bulletproof in Q&A — you concede cleanly ("the receipt's precomputed; the real minting runs in the lineage path + tests") instead of getting caught. That composure is half of what top-6 had.
2. **The most satisfying next build is making the pitch literally true.** Each gap above is a crisp, high-leverage fix.

## Ranked next build (when you iterate — from the handoff's §7/§8)
1. **"Make the central pitch literally true in the live path"** (biggest claim-vs-code closer): wire `grow()` into `eval_stream` so a click births a genuinely new gated check; recompute the gold receipt live; surface the **two-score gap** (gameable working score vs frozen-gold + Wilson CI it can't read) as the hero UI.
2. **"Harden the honesty rail: lint → real CI → boundary"**: add `eval/tests` to `pytest.ini` + a CI workflow (now "build-failing" is *true*), then import-linter contract → gold behind a separate process → hash-attested signed receipt.
3. **"Founder-fluency drill"**: a runnable mechanism notebook (Wilson CI vs k/n; one real `save_failure → embed → $vectorSearch → is_general` walkthrough; the p=0.031 derivation) + a concession-first "hardest questions" drill, recorded + self-graded.

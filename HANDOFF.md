# HANDOFF — Bonsai → orchestrator session (written 2026-07-03, session closing)

*Audience: the Fable orchestrator reviewing ALL of Nic's workstreams to plan
parallel waves + factory (funisfactory) fan-out. This is the complete bonsai
context; nothing else is needed to schedule it.*

## What this is, in one breath

Bonsai = a self-improving eval harness whose one defensible idea is the
**honesty gate** (CI test proving the self-improving loop can't read the
held-out human answer key, improvement reported as direction + Wilson CI,
calibrated to a named domain owner's labels). Verdict from last night's
skeptic-tested research: **continue, narrowly** — the payoff is an essay +
pytest plugin that *names* the pattern (first-to-name decays), plus making the
owner's taught rules *actually catch things*. It is NOT a product; do not let
any wave inflate it into one.

## State

- Repo `~/dev/bonsai`, ALL work uncommitted in the working tree by design
  (freeze gate = Q10 sponsor-prize decision; do NOT commit/push).
- Suite: 175 pytest green KEYLESS (`mv .env /tmp/e; pytest -q; mv /tmp/e .env`)
  + 16 node tests (`node --test web/tests/main.test.js`). Keep it that way.
- Demo: `WEB_MOCK_STREAM=1 MOCK_AUT=1 .venv/bin/python -m uvicorn main:app
  --port 8000`. A stray server may still be running: `pkill -f "uvicorn main:app"`.
- Public repo + deployed DigitalOcean app still run PRE-wrap code until Q10.

## Read-first (in order)

1. `~/dev/bonsai/NEXT.md` — the authoritative queue (Q/M ids used below).
2. `~/dev/bonsai/WRAP-UP.md` — goals, honest state, the tripwire.
3. Vault `private/projects/bonsai/16-where-it-plugs-in-continue-stop.md`
   (+ addendum) — the continue/stop verdict, lane strategy vs auto-harness,
   factory-fit analysis. Spec/plan: `~/dev/bonsai/docs/superpowers/`.

## Dependency & parallelism map (the part you're here for)

**Track A — owner visibility (the #1 bar: a taught rule really catches a claim)**
`Q6 → M4 → Q9(record)`, then `M1` (intake skill).
- Q6 is CODE (real screening path) but its VALIDATION needs a keyed box
  (Atlas + Vertex creds) and Q9 needs Nic on camera → **front-load Q6 coding,
  schedule its live validation as a Nic-attended slot.**

**Track B — public payoff (time-sensitive, fully parallel with A, zero creds)**
`Q11 = essay (evening 1) + honesty-gate pytest plugin extraction (evening 2)`.
- Needs NO new engine work; must NOT wait for Track A. Essay = Nic's voice
  (human/attended); plugin extraction = mechanical, well-specified.

**Track C — small independents (parallel any time, keyless, well-specified)**
`Q3` (teach-form expectations), `Q1` (demo-mode banner + mock-lineage honesty,
Q2 folded in), `Q4` ("try to cheat it" station), `Q5` (answer-key manager).

**Track D — gated (do not schedule until their gates open)**
- `Q10` (Nic checks Discord for sponsor-prize result) → unblocks `Q12` (banner)
  + all commits/pushes/redeploys.
- `M3` (factory dogfood probe, ≤1 evening, ADVISORY-ONLY) — **blocked by the
  factory's own g1/g2** (no bead has ever round-tripped; no sweeper). Do not
  seed it before those close; a FLOOR verdict column is its 80% substitute.

**Cut — do not resurrect:** Q7 hero-flip, Q8 second scenario, any enterprise
sidecar/product (Anthropic Outcomes ships that primitive).

## Factory-feed assessment (which items make good beads)

GOOD beads (isolated, testable, accept-criteria in NEXT.md, keyless):
**Q3, Q1, Q4, Q5, plugin-extraction half of Q11.** Each is one bead;
acceptance = suite stays green keyless + the item's accept line.
NEEDS HUMAN/ATTENDED: essay half of Q11 (voice), Q6 live validation, M4/Q9
(owner ritual + recording), Q10 (decision), M1 (run WITH the owner).
META: these beads are deliberately good factory-tuning fodder — small, typed,
verifiable. If the factory mints them, keep bead ids mirrored in NEXT.md.

## Constraints any wave must respect

1. **No commits/pushes** until Q10. Work in the working tree.
2. **Honesty invariants:** no UI sentence may overclaim; scripted things say
   "scripted"; gate verdicts shown are always the real `is_general` outcome;
   /loop never references /eval or gold (CI-linted — don't break the lint).
3. **Tripwire:** anything blowing past ~2 weeks of evenings → stop, ship Q11.
4. Tests must pass with `.env` REMOVED (a real .env with live keys sits in the
   repo — never let a test path reach it).
5. Wilson/direction reporting: never introduce a bare-% claim anywhere.

## Reframes worth considering (orchestrator's call)

- Q11-essay is the single highest leverage/effort item across ALL bonsai work
  and competes only for Nic-attention, not compute — consider it for the very
  first attended slot.
- Q6 + Q11 + Track C are three independent lanes → bonsai can absorb a wide
  first wave without internal conflicts (different files; Track C touches
  templates/CSS, Q6 touches routes/streams, Q11 creates a new package dir).
- If the factory needs a first END-TO-END rehearsal bead, Q3 is the safest
  candidate in this repo (small, copy-level, crisp acceptance, zero risk).

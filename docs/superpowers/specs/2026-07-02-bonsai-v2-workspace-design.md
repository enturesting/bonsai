# Bonsai v2 — "a workspace with a visible owner" (design spec)

*2026-07-02. Approved direction from a 3-design × 3-judge panel (raw output:
vault `bonsai-hackathon/v2-design-panel-raw-2026-07-02.json`). Engine unchanged;
this is a surface redesign. Repo commits remain gated on the sponsor-prize /
freeze decision — build in the working tree.*

## The problem being solved

The app shows a self-improving loop with no owner on stage. "Improve" is an
ambiguous verb; the payoff is a flipped pill + a Wilson CI that reads as noise;
the red→green flip implies the *answer* got fixed when only the *harness*
improved. Nobody can tell whether anything improved, or how.

**Acceptance bar (user's words):** someone looking at it can tell how it
improved. Every meaningful action must end in a plain-English, on-screen
statement of what changed (and honest labels for what is scripted).

## One job

An AI-enablement engineer standing up a cited-answer agent uses Bonsai to
bootstrap a calibrated, honesty-gated eval harness: the domain owner's
plain-English requirements + a few labeled examples become gated executable
checks, which then grow from real catches. Northbeam/Verity stays the
pre-loaded worked example (its 9→14 gold receipt is real — never discard it;
no scenario reskin).

## Increment 1 — the legibility floor (zero engine changes)

Ships standalone; stopping here still fixes the core complaint.

1. **Verb + pill semantics.** Button becomes "Check this answer →". Pill labels
   change from GREEN/RED to SUPPORTED / CAUGHT (the pill judges the *answer*).
   A separate harness stamp under the stream states the harness outcome:
   "the answer stays wrong — the harness now catches this pattern ✓" (red path)
   or "cleared — false alarm removed ✓" (green path).
2. **The receipt card** (the payoff, replaces the bare mint-note). Rendered by
   main.js from the score event (mint data already rides it). Written like a
   commit message:
   - caught + gated: "✓ New check admitted: «property» · born from this catch ·
     caught M sibling failures, passed all N known-good · Rubric 6 → 7 checks ·
     the loop that wrote it can't read the answer key."
   - caught + rejected: "✕ Candidate check rejected by the generality gate
     (caught only 1 lookalike) — nothing added. That's the gate working."
   - caught + seam error: the actual error, and what the score then counts.
   - cleared: "✓ Well-supported — false alarm removed. No check minted
     (nothing to learn from a good answer)."
   - mock runs append "· scripted offline demo".
3. **Value strip** above the two-score band: three stat tiles — Rubric (N
   checks) · Coverage (x of 5 failure families) · Honesty receipt (14/15 ·
   CI) — each a jump-link; refreshed on the same `grow` event as the rubric
   panel (`/fragment/value-strip`). The receipt card's "6 → 7" delta must match
   these tiles.
4. **Provenance badges** on rubric rows: 🌱 "grown from catch" (+ contributing
   claim count). The seed check is labeled as the contract you started from.
   (◆ "from owner requirement" arrives with Increment 2.)
5. **Owner on stage.** Scenario strip gains the owner persona + stakes line:
   Priya, Northbeam's security lead, owns what Verity may promise; "a security
   reviewer's deadliest question: *show me where it says that*."
6. **Method ribbon** (thin, static orientation strip, NOT a wizard): Capture
   the rules → Build the answer key → Calibrate → Try to cheat it → Grow from
   failures.
7. **Demote the tree.** Rubric panel first in the sidebar; bonsai below it,
   shorter; caption reads as a growth timeline. Lineage stays (one layer down).
8. **Rebrand the live-claim box** as "Screen an output" (it already is that,
   in mock form).

## Increment 2 — owner intake ("+ Add a requirement")

The lane's centerpiece (old roadmap Move 2). Never ships without the gate
firing visibly.

- `loop/grower.py: mint_check_from_standard(text) -> Check` — structured LLM
  call turning a plain-English standard into the Check schema (sibling of
  `mint_check`).
- `POST /teach` + `_teach.html`: form in the rubric panel. Response = the
  structured check + a visible gate verdict + a receipt card; triggers rubric/
  value-strip refresh.
- **Keyed box:** real mint + real `is_general` gate (known-good sample +
  nearest failures). ADMITTED persists via `upsert_check`.
- **Keyless/mock box (honest degradation):** one scripted worked example via a
  pre-fill chip (streamed transformation + scripted gate verdict, labeled
  "scripted offline demo"). Arbitrary typed text is accepted as a
  display-only ◆ requirement with status "unverified — a live box runs the
  generality gate", never a fake ADMITTED.
- Display state: `web/state.py` gains owner-requirement rows (◆ badge),
  merged into `RUBRIC.checks()` and counted in the value strip.

## Increment 3 (sketch — later)

Answer-key manager (owner adds labeled gold examples from /web — honesty-safe:
the rail only forbids /loop); real "screen an output" against the current
rubric on a keyed box; "try to cheat it" expander in the honesty band that runs
the actual honesty-gate lint keyless, labeled "a lint, not a sandbox".

## Increment 4 (sketch — later)

Full hero-flip layout (Rubric as left hero column, Evidence right), workspace
switcher ("New workspace / Open example"), CoverPilot as second example
workspace (fixtures only; never touches the Northbeam gold receipt).

## Guardrails (from the judge panel — binding)

- No "real tool" copy on the keyless public box; scripted things say scripted;
  a scripted flip must be distinguishable from a real run.
- Owner intake without a visible gate = "an LLM wrote you an eval" — forbidden.
- No scenario reskin of the default corpus; the real 9→14 Northbeam receipt is
  the trust anchor.
- The token stream never owns the payoff — the receipt card does.
- Tripwire: any increment blowing past ~2 weeks of evenings → stop, ship the
  floor, banner.

## Testing

Every new fragment/route gets keyless tests (existing conftest pattern);
receipt rendering gets node tests beside renderScore/renderMintNote; pill-label
changes update engine/mock/sse tests; the suite stays green with `.env`
removed. Visual check via headless-Chrome screenshot before declaring done.

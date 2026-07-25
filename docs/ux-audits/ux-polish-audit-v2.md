# Bonsai — Apple-grade UX polish audit (v2)

The dashboard already has real taste: a coherent paper / forest / gold palette, a
genuine serif voice, and a live moment — pill flip → score bump → branch sprout —
that most "dashboards" never earn. v2 isn't more design. It's **restraint, rhythm,
and correctness**: make the honesty receipt the one loud thing, fix the contrast and
keyboard paths so the polish holds up under scrutiny, and let the live moment land
where the eye already is — then go still. Most of this list is still *subtraction*.

Every selector and line below was re-verified against the current tree. Note: the
file is mid-edit — a new scenario strip pushed `style.css` to 669 lines and shifted
everything below line 143 by **+22**, so these numbers supersede v1's. Two things are
**already fixed in your working copy** and are *not* re-flagged: the "AUT" acronym is
gone (`index.html:34` now reads "Athena's answers… each a cited reply to staff"), and
the scenario strip is fully styled. One v1-style instinct is **refuted** below (don't
dedupe `--green`/`--forest-bright`).

Ranked by impact, then effort. `H/M/S` = High/Med impact, Med/Small effort.

> **Post-audit verification (4 fixes landed + 1 finding retracted).** A follow-up pass
> implemented and verified the genuine *defects* (not just polish): **#2 console placement**
> — the streaming rewrite console now breaks to a full-width row below the pill instead of
> cramming into a content-sized header cell (verified in a rendered capture); the **score-bump
> false-celebration** (`main.js` — `.score-bump` was firing on `before == after`) now gates on
> a real change; and the **reduced-motion branch-draw trap** (`animation:none` would freeze the
> branch at `stroke-dashoffset:70` → invisible) now forces it fully drawn. All 69 tests stay
> green. **#4 (mobile overflow) was retracted as a false positive** — see below; it was a
> headless-screenshot canvas artifact, not a real bug.

---

## The top 10

### 1. Make the honesty receipt the *one* hero — twin 2.4rem numbers can't both be the proof
**Impact: H · Effort: M · Confidence: verified-in-code + live-confirmed**

- **What's off:** The Score (working pool) and Honesty-receipt (vs frozen gold) panels
  emit the *same* `.score-counts` markup at the *same* 2.4rem serif. The live render
  confirms it bluntly: the two panels read as **siblings** — same white card, same
  dark-green serif heading, same gold eyebrow, same big number — "distinguishable only
  by their heading words, not by visual weight or color." The gold receipt, which *is*
  the moat and the whole pitch, does not read as elevated. v1 proposed separating them
  with chrome (border width, tint, shadow); but two identical 2.4rem numerals keep
  reading as "which do I trust?" because the numeral weight is the dominant signal and
  stays equal. Meanwhile the CSS literally names the *pill* the "star," yet it renders
  at 0.74rem while these twin numbers and a 240px swaying tree out-shout everything.
- **The fix:** Break the tie at the glyph + word level, not the container.
  - Demote the working-pool figure so only the gold one is biggest:
    `.score-panel .score-counts { font-size: 1.5rem; color: var(--muted); }` (keep
    `.gold-panel` at 2.4rem). Specificity `(0,2,0)` cleanly overrides the shared rule
    and survives the htmx score swap.
  - Seal the gold panel: `.gold-panel h2::before { content: "✓ "; color: var(--forest-bright); }`
    (the h2 is already `display:flex; align-items:baseline`, so this drops in cleanly).
  - Relabel the eyebrows so the *kind* of number is the legible difference: working-pool
    → "self-graded · what the loop optimizes"; gold → "independently verified · the loop
    can't read this."
  - Keep the tree → score → gold **order** (do *not* hoist gold above score — `_score.html:14`'s
    copy forward-references the frozen gold, so the cause→proof reveal breaks if reversed).
- **Where:** `style.css` `.score-counts` (477), `.gold-panel` (176), `.panel h2` (201);
  `_score.html:3`, `_gold.html:4` (eyebrows); `index.html:40–42` (keep order).

---

### 2. The live moment: get the console out of the header, and give it a calm finish
**Impact: H · Effort: M · Confidence: verified-in-code**

- **What's off:** Four faults in the demo's money beat.
  1. **Wrong place.** The Improve button targets `#improve-{{c.id}}`, which lives *inside*
     `.claim-head` (`display:flex; justify-content:space-between`). So the dark streaming
     `.rule-box` console swaps into the **right cell of the header strip** — beside the
     category chip and *above* the claim text it's rewriting. Reading order is inverted
     and the centerpiece renders cramped in a content-sized flex cell, top-right.
  2. **Caret never stops.** `.rule-stream::after` blinks `▋` forever; nothing stills it,
     so a *finished* rewrite still reads as "still typing."
  3. **CTA never resolves.** The Improve button has no `hx-indicator`, isn't disabled
     during its stream, and stays "Improve →" after the flip — a second click mid-stream
     re-swaps the slot and **restarts** the whole red→green animation from scratch.
  4. **Bump on a non-event.** `renderScore()` re-triggers `.score-bump` *unconditionally*,
     but `mock_stream.py` sends `before == after` on a confirmed failure — so the score
     panel **celebrates (scale 1.05) when nothing changed**, signalling a win where there
     was none. For an *honesty* harness, that's the worst possible false positive.
- **The fix:**
  - In `_claims.html` move `<div id="improve-{{c.id}}" class="improve-slot">` out of
    `.claim-head` to a full-width block *after* `.claim-by`; add `.improve-slot{display:block}`
    and bump `.improve{margin-top:0.85rem}`. Result: chip+pill in head, claim text, then
    the console below — a top-to-bottom read.
  - Toggle the caret off: in the `htmx:sseClose` handler add `rule-stream--done` to the
    closing `#rule-stream` and add `.rule-stream--done::after { display:none }`.
  - Gate the bump: wrap the add in `if (data.after !== data.before)` (main.js:48–51).
  - On `sseClose`, set the button to a quiet resting state ("Improved ✓", swap to
    `.btn--ghost`) and disable it for the stream's duration so a re-click can't restart it.
- **Where:** `_claims.html:5–7` (slot) & `:15–18` (button); `style.css` `.claim-head` (285),
  `.improve` (400), `.rule-stream::after` (448); `main.js` `renderScore` bump (45–52) &
  `htmx:sseClose` (78–87).

---

### 3. Split the "text-safe" gold — it fails AA everywhere, worst on the moat's own proof numbers
**Impact: H · Effort: M · Confidence: verified-in-code**

- **What's off:** `--gold #b8862f` carries the inline comment `text-safe` (line 22) — it
  is not. As text it scores **3.18:1** on paper-2 (the gold eyebrows, `.score-arrow`,
  `.receipt-moat em`) and only **2.54:1** for `.lin-sim` — the `$vectorSearch` cosine-
  similarity numbers, i.e. the literal proof of the moat is the *least legible text on the
  page*. AA's normal-text floor is 4.5:1; none clear 3.2. The newly-added `.scenario-tag`
  (gold on cream paper) is a fresh instance of the same failure.
- **The fix:** Split fill from ink. Keep `--gold` for dots/rings/dashes; add
  `--gold-ink: #7d5a16` (verified **6.17:1** on paper-2, **4.93:1** on gold-soft) and point
  every gold-as-*text* use at it. Fix the false comment on line 22.
- **Where:** `style.css` decl (22) + all six text uses — `.receipt-moat em` (173),
  `.receipt-eyebrow` color (464), `.score-arrow` (488), `.lin-meta code` (609), `.lin-sim`
  (614), `.flow-arrow` (651) — **plus the new `.scenario-tag` color (160)** that v1's list
  predates. (v1 named only four; these eight are the full set.)

---

### 4. ~~Mobile: the claim header overflows at 390px — the star pill is clipped to "RE"~~ — **WITHDRAWN (false positive)**
**Status after verification: NOT A BUG · Confidence: code-verified (deterministic measurement)**

- **What it claimed:** the live 390px capture showed the `● RED` pill clipped to "RE" and
  the page scrolling sideways — flagged as the single most clearly broken thing.
- **Why it's wrong:** this was a **screenshot-tool artifact**, not a layout bug. The
  headless Chrome used for grounding (and for this verification pass) *clamps its layout
  viewport to a 500px minimum* and ignores smaller `--window-size` values for layout — while
  still cropping the capture canvas at the requested 390/360px. So the right ~110px gets
  cropped off the *image*, which reads as "overflow." A diagnostic injected at the rendered
  width reports `clientWidth == scrollWidth == 500` with **zero** elements exceeding the
  viewport. A deterministic test rendering the real card CSS into fixed 360/320/280/240px
  containers shows `OVERFLOW=false` and the chip+pill comfortably on one line at *every*
  width — **with or without** any `flex-wrap` change. There is no horizontal overflow.
- **What was kept anyway:** `.claim-head { flex-wrap: wrap; gap: 0.5rem 0.85rem; }` plus
  `.improve-slot:has(.improve) { flex-basis: 100%; }` *were* applied — but they earn their
  place under **#2 (console placement)**, letting the streaming console break to a full-width
  row. They are defensively correct for a genuine sub-500px browser too, just not fixing an
  observed bug.
- **Lesson for the audit:** any finding tagged `needs-visual` that came only from a headless
  screenshot at a narrow width is suspect — verify narrow-viewport claims with JS measurement
  (`scrollWidth`/`getBoundingClientRect`), not a capture whose canvas the engine clamps.

---

### 5. Cap the claim reading measure — and stop it being the tightest leading at the longest line
**Impact: M · Effort: S · Confidence: verified-in-code + live-confirmed**

- **What's off:** The live render calls this "the most un-Apple-clean thing on desktop":
  `.claim-text` has no `max-width`, sits in a ~950px column, and runs **~95–100 characters
  on one line** (v1 guessed ~110ch; the real measure is high-90s — still far past the
  comfortable 66–75ch). Worse, the primary reading copy has the *tightest* leading on the
  page (1.42), tighter even than the body default (1.5) it overrides — long measure + tight
  leading is the exact combination that loses the eye on line return. Reading leadings are
  improvised with no system (1.42 / 1.5 / 1.55 / 1.6).
- **The fix:** Cap the measure and relax the leading together:
  `.claim-text, .claim-q { max-width: 64ch; }` and bump `.claim-text` line-height **1.42 → 1.55**.
  Tokenize once (`--lh-body: 1.55`) and apply to the other reading copy (`.about-block p`,
  `.about-sub`); leave the mono `.rule-stream` alone.
- **Where:** `style.css` `.claim-text` (305, line-height 310), `.claim-q` (299).

---

### 6. Make the verdict pill state *meaning*, not its own color
**Impact: M · Effort: S · Confidence: verified-in-code**

- **What's off:** The "star" element flips through the literal words **RED → CHECKING… →
  GREEN**. The text just names the pill's color — redundant for sighted users (the pill is
  already red with a red dot) and **meaningless to a screen reader or color-blind user**,
  who hears "RED" with zero verdict content. It's internal QA color-jargon on the most
  prominent element, and it undersells the product's own thesis ("the answers are backed").
- **The fix:** Make the label state the verdict. Initial → "Not backed"; server emits
  "Checking…" / "Backed" / "Not backed". Keep `.pill { min-width: 6.4rem }` so the chip
  width is stable across the three words.
- **Where:** `_claims.html:6` & `_improve.html:5` (initial label); `mock_stream.py:68/78`,
  `sse.py:86`, **and the real backend `loop/engine.py:147/160/174`** (the finding's list
  missed engine.py — change it or the deploy path still says RED/GREEN). Update the string
  assertions in `test_engine.py:125/127/175` and `test_stream.py:40` in the same commit.

---

### 7. Clear the remaining AA misses — the pulsing "star" pill and all secondary text
**Impact: M · Effort: S · Confidence: verified-in-code**

- **What's off:** Two more real WCAG-AA failures on visible UI. `.pill--yellow` —
  the *actively pulsing* in-progress state users watch during the whole stream — is the
  **worst-contrast verdict at 3.28:1**; `.pill--red`, the resting state you see on load,
  is a marginal **4.41:1**. Separately, `--muted #6a7c70` fails AA on *every* paper at
  *every* size (3.84–4.44:1) across ~13 elements (tagline, hint, claim-cat, score-of,
  ghost button, topbar link…) — not just "below ~14px / 3 elements" as v1 had it.
- **The fix:** Darken text only, keep the soft fills and the hues:
  `.pill--yellow → #8a5d0e` (4.75:1), `.pill--red → #b5362a` (4.83:1), and the single token
  `--muted → #52685a` (verified 5.21 / 5.92 / 5.54 / 6.02 across the papers; v1's `#5c6e62`
  was borderline at 4.70:1). All keep the existing visual hierarchy.
- **Where:** `style.css` `.pill--yellow` color (379), `.pill--red` color (375), `--muted` (16).

---

### 8. Calm the voice — drop the hype, the codebase-speak, and the three names for one thing
**Impact: M · Effort: S · Confidence: verified-in-code**

- **What's off:** The copy keeps breaking the calm-confident register.
  - Hero (`index.html:29`): bold **"QA on steroids"** + **"…proof we didn't cheat to say so."**
    "on steroids" is gym-hype Apple never uses; "didn't cheat" is self-incriminating and
    plants the word *cheat*. (The live render shows the strip itself is visually understated
    — so this is a **copy** fix, not the banner-styling fix v1 implied.)
  - Receipt fine-print (`_score.html:14`, `_gold.html:14`): "code path", "build-failing test",
    "working-pool", "held-out" — engineering jargon a buyer won't parse — and both panels say
    the same idea twice.
  - One mechanism, three names: "Honesty receipt" (dashboard) vs **"The honesty rail"**
    (`about.html:45`) vs "moat" (CSS). Pick one noun.
  - Leaks: `_rule.html:2` "**grower** is rewriting the rule…" (internal module name);
    `_tree.html:6` exposes the raw "**$vectorSearch**" operator in prose; `about.html:54`
    "Watch a check get **born**" (cutesy).
- **The fix:** Rewrite to plain language; say the moat once. Hero → one calm bold claim, no
  "steroids"/"cheat". Receipt → translate the jargon but **keep the dynamic `{{count}}` and
  the `<strong>`/`<em>` accents**, and keep the working-pool-vs-answer-key distinction (don't
  call the working pool "the answers"). `about.html:45` → "Honesty receipt". `_rule.html:2`
  → "Rewriting the check…". `_tree.html:6` → drop "$vectorSearch" (keep it on the lineage
  card where it reads as proof). `about.html:54` → "See a check get created →".
- **Where:** `index.html:29`; `_score.html:14`, `_gold.html:14` (and `about.html:46`,
  same jargon); `about.html:45,54`; `_rule.html:2`; `_tree.html:6`.

---

### 9. Make the tree and focus states actually usable by keyboard and screen reader
**Impact: M · Effort: S · Confidence: verified-in-code**

- **What's off:** The custom UI is invisible/dead to assistive tech in four ways.
  1. The bonsai `<svg role="img">` makes its **entire subtree presentational** — the
     `role="button"` lineage leaves are pruned from the a11y tree (`tabindex` can't override
     it).
  2. Those leaves are focusable but **not operable**: htmx defaults to `click`, which
     browsers don't synthesize from Enter/Space on a generic `<circle>` — a dead focus stop
     (WCAG 2.1.1).
  3. **Zero `:focus-visible` rules** exist anywhere — and v1's `box-shadow` ring would be
     *invisible* on the SVG leaf (a `<circle>` isn't a CSS box; v1's `--ring` token doesn't
     even exist).
  4. The live pill flip / score change is announced to **no live region** (WCAG 4.1.3).
- **The fix:**
  - `_treesvg.html:2` `role="img"` → `role="group"` (keep the aria-label); `aria-hidden` the
    cosmetic leaf-pad/leaf-b/leaf-c circles.
  - `_treesvg.html:44` add `hx-trigger="click, keyup[key=='Enter'], keyup[key==' ']"` + a tiny
    `main.js` keydown that `preventDefault()`s Space.
  - `.btn:focus-visible, .topbar-link:focus-visible { box-shadow: 0 0 0 3px rgba(202,166,79,.45); }`
    **plus a separate SVG-safe** `.leaf--clickable:focus-visible { outline: 2px solid var(--gold-bright);
    outline-offset: 2px; }` (outline paints on SVG; box-shadow doesn't).
  - Live region: add `aria-live="polite"` to `#score-display` (`_score.html:4`) — it's mutated
    in place, so it announces cleanly. For the pill, update a **dedicated visually-hidden
    `aria-live` element** with just "Backed"/"Not backed"; do **not** put the live region on
    `.improve-slot` (it wraps the token-streaming console and would flood the reader).
  - While here, the lineage hit target is an **11px leaf** (`r="5.5"`, far below WCAG 24px):
    add a transparent `<circle r="18" pointer-events="all">` hit area without changing the art.
- **Where:** `_treesvg.html:2, 42–47`; `_score.html:4`; `style.css` `.btn` (222),
  `.topbar-link` (629), `.leaf--clickable` (576).

---

### 10. Motion: purposeful, then still
**Impact: M · Effort: S · Confidence: verified-in-code (+ live for the /about white-box)**

- **What's off:** Continuous idle motion is the most un-Apple thing on the page, and the
  reduced-motion path is both incomplete and self-defeating.
  - `.tree-panel .bonsai` sways **forever** (`sway 7s infinite`); `about.html`'s hero video
    `loop`s the logo forever with **zero reduced-motion handling** — the same perpetual-idle
    sin on the marketing page (and a WCAG 2.2.2 issue: auto-motion >5s, no pause).
  - The `prefers-reduced-motion` block silences only 4 selectors; the sprout, leaf pops,
    lineage and score-bump still run. Worse, naively adding `.branch--new` would leave it
    **invisible** — `animation:none` freezes `stroke-dashoffset:70`, so the branch draws to
    nothing. The centerpiece silently disappears under reduced motion.
  - The leaf `pop` overshoots to **scale(1.4)** — bouncy/toy-like, not Apple's restrained
    ~1.05–1.1 spring.
  - On stream close, the sprout (~1.2s) and the lineage fade (0.45s) fire **simultaneously**,
    so the lineage finishes first and the "branch then its cluster" order inverts into a flash.
  - **/about white-box** (live-confirmed): `.hero-mark` forces `background:#fff` around the
    video, whose poster is white — so the logo sits in a white card that *doesn't match the
    cream page*, with a larger bonsai sketch bleeding past its edges. Reads as an unintended
    letterbox.
- **The fix:**
  - Delete `animation: sway…` from `.bonsai` (and shrink `height: 240px → 200px`); reserve
    motion for the sprout.
  - Extend the reduced-motion list to `.branch--new, .leaf--new, .leaf-pad--new, .lineage,
    .rule-stream span, .score-bump` **and** add `.branch--new { stroke-dashoffset: 0 !important; }`
    so the branch renders fully drawn.
  - `@keyframes pop`: 70% `scale(1.4) → scale(1.12)`; shorten `.leaf--new` to `pop 0.4s`.
  - Defer the lineage ajax: wrap `main.js`'s `htmx.ajax` in `setTimeout(…, 700)` so it follows
    the draw — pill → branch → lineage, a 1-2-3 beat.
  - `about.html:24` drop `loop`; add a 3-line reduced-motion script (pause + `load()` to the
    poster). Set `.hero-mark { background: transparent; }` (or cream) so it stops reading as a
    white card.
- **Where:** `style.css` `.tree-panel .bonsai` (509–516), reduced-motion block (571–573),
  `.branch--new` (551), `@keyframes pop` (565), `.hero-mark` (635); `main.js:84`; `about.html:24`.

---

## Quick wins (each < 5 min, same pass)

- **Delete dead code that pretends to be polish.** `.score-after { transition: color 0.3s }`
  (style.css:489) never fires — the node is recreated on every score swap, so it snaps. And
  the `0 1px 0 rgba(255,255,255,0.7) inset` highlight in `--shadow` (style.css:41) renders
  ~#fffefd over a near-white panel — a no-op bevel. Remove both.
- **One header rhythm.** Delete `.claims-panel > h2 { margin-bottom: 1.1rem }` (style.css:269)
  so every panel heading shares the base `.panel h2` gap.
- **Ease the one SVG affordance.** Add `transition: stroke .15s, stroke-width .15s` to
  `.leaf--clickable` (style.css:576) so the hover outline fades instead of snapping like
  every other interactive element eases.
- **Tighten display type, loosen caps.** `.wordmark` letter-spacing `+0.2px → -0.01em`
  (style.css:106; a logotype should never track *looser*); add `-0.01em` to `.score-counts`
  (477) and `-0.015em` to `.about-motto` (639). For the real caps labels only — `.claim-cat`
  (291), `.receipt-eyebrow` (462), `.lin-kind` (594), `.pill` (357) — switch tracking to
  `0.06em` so it scales with size (your new `.scenario-tag` already does this). Leave
  lowercase labels alone.
- **Stop the sticky rail clipping.** `.side` (style.css:192) has no overflow, so a tall
  tree+score+gold stack clips while stuck. Add `max-height: calc(100vh - 6rem); overflow: auto;`
  — use literals, the `--topbar-h`/`--space-4` tokens the original fix referenced don't exist.
- **Align the masthead gutter to the grid.** The topbar, hero-line and scenario-line are
  full-bleed while `.grid` is centered at 1380px, so brand-left and card-left diverge on wide
  screens. One line each: `padding-inline: max(1.6rem, calc((100% - 1380px)/2 + 1.6rem))`.
- **Collapse the radius zoo.** Seven non-circular radii (16/14/12/11/9/6/5) → two tokens:
  `--radius-card: 14px`, `--radius-control: 8px`; keep `999px` for pills/dots
  (style.css:197/274/342/403/225/584/593/616).

---

## What changed from v1

**Corrected or refuted (v1 over-claimed or got it wrong):**
- **"Put everything on an 8px scale" referenced tokens that don't exist.** There is *no*
  `--space-*` scale in the file — paddings are literals — so v1 #1's `var(--space-5)` fix
  wouldn't apply, and it set `.grid gap` == `.panel padding`, which would *re-flatten* the
  hierarchy it tried to fix. (Spacing-token hygiene is still worth doing, but it's L-impact:
  the live render shows cards already read clearly via surface + shadow.)
- **"16.5 → 17px on body" is the wrong knob.** The rem scale is anchored to the **16px root**
  (`html` has no font-size; only `body` is 16.5px), so bumping body alone moves almost nothing
  and *widens* the base-vs-scale split. Set the size on `html` instead (`html { font-size: 16.5px }`,
  `body { font-size: 1rem }`).
- **`--muted` is worse than v1 said.** Not "fails below ~14px / 3 elements" — it fails AA at
  *every* size on *every* paper (3.84–4.44:1), ~13 elements; and v1's proposed `#5c6e62` is
  itself borderline (4.70:1). Use `#52685a`.
- **The reading measure is ~95–100ch, not ~110ch** (live-measured) — still well over, and
  confirmed as the most un-Apple thing on desktop.
- **v1's focus-ring fix would silently fail on the SVG leaf** (`box-shadow` doesn't paint on a
  `<circle>`; v1's `--ring` token doesn't exist), and v1 #10's "give the leaf a tabindex/role"
  was already done — the real gaps are `role="img"` pruning and missing keyboard activation.
- **v1 #5 told you to *keep* "frozen gold set / no code path."** From an Apple-voice lens that
  phrase *is* the defect.
- **v1 #7 listed 5 radii; there are 7** (it missed 5px, 9px, 14px).
- **Don't dedupe `--green`/`--forest-bright`.** They're byte-identical today, but keeping them
  as two tokens is exactly what lets you tune brand vs verdict independently — collapsing them
  *couples* the two. Refuted.

**New in v2 (v1 missed these):**
- ~~**Mobile claim-head overflow at 390px** — the star pill clipped to "RE", page scrolls sideways.~~ **Retracted on verification: false positive** (headless-capture artifact — the layout viewport clamps to 500px; deterministic measurement shows no overflow at any width down to 240px).
- **The "text-safe" gold comment is literally false** — AA fails on all six text uses, worst
  (2.54:1) on the `$vectorSearch` similarity numbers that *are* the moat's proof; the new
  `.scenario-tag` adds a seventh.
- **The yellow "star" pill is the lowest-contrast verdict (3.28:1)**; red resting is 4.41:1.
- **The live rule console injects into the claim-head flex row** (inverted reading order).
- **The reduced-motion branch-draw trap** (`animation:none` → branch invisible).
- **The score bump fires on a non-event** (`before==after` on a confirmed failure) — a false
  celebration in an *honesty* harness.
- **The caret never stops, the Improve CTA never resolves, the error label stays "rewriting…"
  forever** — the live moment never reaches a calm "done" state.
- **`role="img"` hides the leaf buttons; leaves aren't keyboard-operable; no live region; 11px
  hit target** — the whole keyboard/SR path.
- **RED/GREEN labels by color, not meaning.**
- **The /about hero video loops forever** ignoring reduced-motion.
- **Three names for one mechanism** (receipt / rail / moat); **module/DB-operator leaks**
  (grower, `$vectorSearch`) in user copy.

**Confirmed by the live render:**
- **v1 #2 (look-alike receipts):** confirmed — the two panels blur into siblings; the gold
  receipt does *not* read as elevated.
- **v1 #9 (measure too long):** confirmed and elevated — the standout desktop flaw.
- **v1 #3 (perpetual sway is un-Apple):** confirmed conceptually — the same sin recurs as the
  /about video loop.
- **v1's "about hero video box letterboxes" quick win:** confirmed as a real **white-box**, not
  a hypothetical.
- **v1 #6 nuance:** the hero strip is actually visually *understated* (a faint centered band),
  so the fix is the **copy**, not the banner styling v1 described.

*Already resolved in your working tree — not re-flagged:* the "AUT" acronym is gone
(`index.html:34`), and the new scenario strip is fully styled.

---

## The one-line summary for the founder

Let the **honesty receipt** be the single loudest, most legible thing — one big verified
number, real contrast on the gold and the pills, and a live moment that lands under the claim
and then goes still. Almost all of it is subtraction.

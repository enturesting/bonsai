# Bonsai — Apple-grade UX polish audit

The dashboard already has taste: a coherent paper/forest/gold palette, a real
typographic voice, and a genuinely good live moment (the pill flip → score bump →
branch sprout). The gap to "Apple-grade" isn't more design — it's **restraint and
rhythm**. Right now the surface is busy: ad-hoc spacing, perpetual motion, two
look-alike receipts, and a thicket of tiny uppercase mono labels all compete for
the eye. Apple-clean = fewer things moving, one obvious hierarchy, a single spacing
grid, and breathing room around the one thing that matters (the flip + the honesty
receipt).

Files in scope: `web/templates/*.html`, `web/static/style.css`, `web/static/main.js`.

Ranked by impact, then effort. Each fix names the selector and concrete values.

---

## The top 10

### 1. Put everything on one spacing scale
**Impact: H · Effort: M**

- **What's off:** Spacing is improvised — `1.15rem 1.3rem`, `0.95rem`, `0.85rem`,
  `0.7rem`, `1.05rem`, `0.82rem` appear all over with no shared rhythm. The page
  reads slightly "off" everywhere without any single thing being wrong. This is the
  #1 reason it feels homemade rather than Apple-calm.
- **The fix:** Define an 8px-based scale in `:root` and replace the one-off values:
  ```css
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
  --space-4: 16px; --space-5: 24px; --space-6: 32px; --space-7: 48px;
  ```
  Map the big offenders to it: `.panel { padding: var(--space-5) var(--space-5); }`
  (was `1.15rem 1.3rem`), `.grid { gap: var(--space-5); padding: var(--space-5)
  var(--space-5) var(--space-7); }`, `.side { gap: var(--space-5); }`,
  `.claim { padding: var(--space-4) var(--space-4); margin-bottom: var(--space-4); }`
  (kill the asymmetric `1rem 1.15rem 1.05rem`).
- **Where:** `style.css` `:root`, `.panel` (172), `.grid` (161), `.side` (170),
  `.claim` (248).

---

### 2. Make the honesty receipt outrank the working-pool score
**Impact: H · Effort: M**

- **What's off:** `.score-panel` (working pool) and `.gold-panel` (honesty receipt
  vs frozen gold) are nearly identical: same `.score-counts` at 2.4rem, same eyebrow,
  same dense `.receipt-moat`. The honesty receipt *is the moat* — the whole pitch —
  but it sits as a visual sibling, third in the stack, easy to miss. Two big
  before→after numbers also read as "which one do I trust?"
- **The fix:** Demote the working-pool score and elevate the gold receipt.
  - Shrink working-pool counts: `.score-panel .score-counts { font-size: 1.7rem; }`
    so the gold one (keep 2.4rem) clearly wins.
  - Give the gold panel real prominence: thicker accent + tint, not just a 3px rule.
    `.gold-panel { border-left-width: 4px; background:
    linear-gradient(180deg, var(--paper-2), var(--gold-soft) 280%); box-shadow:
    var(--shadow-lg); }`
  - Add a small "✓ verified" affordance on the gold eyebrow so it reads as the
    proof, e.g. prepend a forest checkmark to `.gold-eyebrow`.
  - Consider reordering the `<aside>` so the honesty receipt sits directly under the
    tree, above the working-pool score (`index.html:39–43`).
- **Where:** `style.css` `.gold-panel` (154), `.score-panel` (435),
  `.score-counts` (455); optionally `index.html` aside order.

---

### 3. Stop the perpetual tree sway — let the eye rest
**Impact: H · Effort: S**

- **What's off:** `.bonsai { animation: sway 7s ease-in-out infinite; }` rotates the
  whole tree forever. Apple motion is *purposeful then still* — continuous idle
  movement is the single most un-Apple thing on the page and quietly fights every
  other element for attention.
- **The fix:** Remove the infinite idle sway. Reserve motion for the meaningful
  beat — the branch sprout (`.branch--new` draw + `.leaf--new` pop already exist and
  are great). If you want a touch of life, make it a *one-shot settle* on `grow`:
  trigger a single 1.2s damped sway when `main.js` dispatches the `grow` event,
  rather than a 24/7 loop. Quickest version: just delete `animation: sway …` from
  `.bonsai` (490) and the `@keyframes sway` (494).
- **Where:** `style.css` `.tree-panel .bonsai` (487–493), `@keyframes sway` (494);
  optional hook in `main.js:80` (the `grow` dispatch).

---

### 4. Thin out the uppercase-mono micro-label thicket
**Impact: M · Effort: M**

- **What's off:** Wide-tracked uppercase mono labels are everywhere —
  `.claim-cat`, `.receipt-eyebrow` (1.4px tracking), `.gold-eyebrow`, `.lin-kind`,
  `.rule-label`, `.cite`. Each one shouts. Stacked, they create constant low-level
  visual noise that reads as "dashboard," the opposite of calm.
- **The fix:** Pick **one** uppercase eyebrow style and let everything else be
  sentence-case body type.
  - Unify tracking to a single token `--track-caps: 0.6px` and drop the 1.4px on
    `.receipt-eyebrow` (440).
  - Make `.claim-cat` lowercase/sentence-case and quieter (it's metadata, not a
    headline): drop `text-transform: uppercase`, reduce weight to 500.
  - Let `.lin-kind` be plain muted body text, not uppercase mono.
- **Where:** `style.css` `.claim-cat` (264), `.receipt-eyebrow` (436),
  `.lin-kind` (572), `.gold-eyebrow` (155).

---

### 5. Cut the fine-print density under the scores
**Impact: M · Effort: S**

- **What's off:** `.receipt-moat` is a two-sentence, 0.72rem grey paragraph under
  *both* score panels. That's a wall of legal-feeling small text in the calmest part
  of the layout — and at `--muted` #6a7c70 / 0.72rem it's also below comfortable
  contrast.
- **The fix:** Trim to one sentence and give it air:
  `.receipt-moat { font-size: 0.8rem; line-height: 1.55; margin-top: var(--space-4);
  color: var(--ink-soft); }`. Keep the bold "frozen gold set / no code path" phrase;
  drop the redundant second clause (the About page already carries the long form).
  One moat line, not two stacked.
- **Where:** `style.css` `.receipt-moat` (144), `_score.html:14`, `_gold.html:14`.

---

### 6. Calm the hero strip — it reads like a banner ad
**Impact: M · Effort: S**

- **What's off:** `.hero-line` is a full-bleed centered strip with a hard bottom
  border and **bold "QA on steroids"** leading. The full-width band + centered bold
  hype is the least Apple element above the fold; Apple leads with a calm, confident
  single line, generous space, left-aligned to the content grid.
- **The fix:** Drop the full-bleed band styling and the border; let it breathe inside
  the content measure:
  `.hero-line { max-width: 1380px; margin: var(--space-5) auto 0; padding: 0 var(--space-5);
  background: none; border: 0; text-align: left; font-size: 1.05rem; color: var(--ink-soft);
  max-width: 64ch; }`. Soften "QA on steroids" to something quieter (copy call —
  e.g. lead with the proof, not the hype), keeping one bold phrase max.
- **Where:** `style.css` `.hero-line` (132), `index.html:29`.

---

### 7. Unify radii and shadows to two tiers
**Impact: M · Effort: S**

- **What's off:** Corner radii are scattered — panels 16px, claims 12px, buttons
  11px, rule-box 11px, lineage 12px, cite 6px, pills 999px. Shadows mix
  `--shadow-sm` and `--shadow` semi-randomly. Inconsistent geometry is a subtle but
  real "not premium" tell.
- **The fix:** Two radius tiers only: `--radius-card: 16px` (panels, claims,
  lineage, rule-box) and `--radius-control: 10px` (buttons, cite, badges); keep
  `999px` for pills/dots. Cards get `--shadow`, controls get `--shadow-sm`, nothing
  else. Search-replace the literal `border-radius` values.
- **Where:** `style.css` `.panel` (176), `.claim` (252), `.btn` (203),
  `.rule-box` (381), `.lineage` (563), `.cite` (320).

---

### 8. Keep the green pill from breaking the claim-head row
**Impact: M · Effort: S**

- **What's off:** `.pill--green` applies `transform: translateY(-1px)` plus a big
  dual glow, so when a pill flips green it physically jumps and its halo overlaps the
  category chip on the same `.claim-head` baseline. On a card grid, one row lifting
  out of alignment looks like a bug, not a flourish. Also `min-width: 6.4rem` makes
  every pill a wide chip regardless of label.
- **The fix:** Remove the `translateY` on the resting green state (let the *flip
  transition*, not the steady state, carry the lift), and soften the glow:
  `.pill--green { box-shadow: 0 0 0 2px rgba(202,166,79,0.30); transform: none; }`.
  Tighten sizing: `min-width: 5.4rem`. Keep the gold dot — that's the payoff.
- **Where:** `style.css` `.pill--green` (362), `.pill` `min-width` (330).

---

### 9. Cap the claim text measure — lines are too long
**Impact: M · Effort: S**

- **What's off:** At `max-width: 1380px` with a `360px` side, the claims column runs
  ~950px wide. `.claim-text` at 1.08rem then sets ~110-character lines — well past the
  comfortable 55–75ch reading measure. Long measure makes dense content feel heavier
  than it is.
- **The fix:** Constrain the reading measure inside the card:
  `.claim-text, .claim-q { max-width: 64ch; }`. Optionally narrow the whole grid a
  touch (`--max: 1240px`) or widen the side rail so the claim column isn't so wide.
- **Where:** `style.css` `.claim-text` (283), `.claim-q` (277), `.grid` (161).

---

### 10. Add visible focus rings (keyboard a11y is part of polish)
**Impact: M · Effort: S**

- **What's off:** Buttons and links style `:hover` only — there is no
  `:focus-visible` treatment anywhere. Tab through the page and the focus state is
  the browser default (or nothing). Apple-grade means the keyboard path looks as
  considered as the mouse path.
- **The fix:** One consistent ring token:
  ```css
  --ring: 0 0 0 3px rgba(202,166,79,0.45);
  .btn:focus-visible, .topbar-link:focus-visible,
  .leaf--clickable:focus-visible { outline: none; box-shadow: var(--ring); }
  ```
  Also give `.leaf--clickable` a `tabindex`/role in `_treesvg.html` so grown
  branches are reachable, matching their click affordance.
- **Where:** `style.css` `.btn` (200), `.topbar-link` (607),
  `.leaf--clickable` (554); `_treesvg.html`.

---

## Quick wins (do these in the same pass — each < 5 min)

- **Two blinking things at once.** `.rule-label::before` blinks *and*
  `.rule-stream::after` caret blinks (lines 401, 429) during a stream — pick one.
  Keep the caret (it reads as "typing"); make the label dot steady. (M/S)
- **Base font size.** `16.5px` (line 62) is an odd value; `17px` is the Apple body
  size and renders cleaner. (M/S)
- **Muted contrast.** `--muted: #6a7c70` (16) on paper fails WCAG AA below ~14px.
  Darken to ~`#5c6e62` for the small `.tagline`, `.hint`, `.lin-why` text. (M/S)
- **Claim hover lift on every card.** `.claim:hover { transform: translateY(-1px) }`
  (259) on a long list makes the whole page feel twitchy on mouse-over. Keep the
  shadow change, drop the transform. (M/S)
- **About hero video box.** `.hero-mark` (613) forces `background:#fff` + radius
  around the `bonsai-loop.mp4`; if the video isn't exactly square it letterboxes on
  white. Match the box aspect to the asset or use `object-fit: cover`. (M/S)
- **Reduced-motion gaps.** The `prefers-reduced-motion` block (549) covers the
  bonsai/pill/caret but not `.lineage` fade-in, `.leaf--new` pop, or `.score-bump`.
  Add them so the reduced-motion path is actually still. (M/S)

---

## The one-line summary for the founder

Remove motion that doesn't mean anything (the sway), put everything on one 8px grid,
and let the **honesty receipt** be the single loudest thing on the page. Most of the
list is *subtraction* — that's what makes it feel Apple.

// Pure-logic tests for web/static/main.js (run with: node --test web/tests/).
// The DOM wiring is guarded behind `typeof document`, so requiring the module
// under node exercises only the pure formatters.
const assert = require("node:assert");
const test = require("node:test");
const { renderScore, renderMintNote, renderReceipt, pct } = require("../static/main.js");

test("pct formats a 0..1 float as a one-decimal percent", () => {
  assert.strictEqual(pct(0.575), "57.5%");
  assert.strictEqual(pct(1), "100.0%");
  assert.strictEqual(pct(0), "0.0%");
});

test("renderScore shows before→after / n green and the Wilson CI", () => {
  const html = renderScore({ passed: true, before: 2, after: 3, n: 9, ci: [0.12, 0.646] });
  assert.match(html, /class="score-before">2</);
  assert.match(html, /class="score-after[^"]*">3</);
  assert.match(html, /\/ 9 green/);
  assert.match(html, /95% CI \[12\.0%, 64\.6%\]/);
});

test("renderScore marks an improvement (after>before) as up", () => {
  const html = renderScore({ passed: true, before: 2, after: 3, n: 9, ci: [0, 1] });
  assert.match(html, /score-after up/);
});

test("renderScore does not mark up when the count is flat", () => {
  const html = renderScore({ passed: false, before: 3, after: 3, n: 9, ci: [0, 1] });
  assert.doesNotMatch(html, /score-after up/);
});

test("renderScore marks a real drop (minted check tightened the pool) as down", () => {
  const html = renderScore({ passed: false, before: 3, after: 2, n: 9, ci: [0, 1] });
  assert.match(html, /score-after down/);
});

// ---- renderMintNote: the mint story is honesty-critical copy ---------------
function mint(overrides) {
  return Object.assign({
    attempted: true, gated: true, id: "minted-x",
    property: "Every numeric claim must cite a source containing that figure.",
    cluster_size: 3, caught_siblings: 3, n_known_good: 2,
    error: null, source: "loop",
  }, overrides);
}

test("renderMintNote is null when there was nothing to mint (green flip)", () => {
  assert.strictEqual(renderMintNote(null), null);
  assert.strictEqual(renderMintNote(undefined), null);
});

test("renderMintNote gated real mint shows property + gate counts, no scripted label", () => {
  const note = renderMintNote(mint({}));
  assert.match(note.text, /minted & passed the generality gate/);
  assert.match(note.text, /caught 3 sibling failures/);
  assert.match(note.text, /passed all 2 known-good/);
  assert.match(note.text, /Every numeric claim/);
  assert.doesNotMatch(note.text, /scripted/);
  assert.match(note.cls, /mint-note--gated/);
});

test("renderMintNote labels a mock mint as scripted — never reads as a real mint", () => {
  const note = renderMintNote(mint({ source: "mock" }));
  assert.match(note.text, /scripted offline demo/);
});

test("renderMintNote shows a gate rejection honestly", () => {
  const note = renderMintNote(mint({ gated: false, caught_siblings: 1 }));
  assert.match(note.text, /failed the generality gate/);
  assert.match(note.text, /not added/);
  assert.match(note.cls, /mint-note--rejected/);
});

test("renderMintNote surfaces the actual seam error, not a canned cause", () => {
  const note = renderMintNote(mint({ error: "Vertex quota exceeded for gemini-3.5-flash" }));
  assert.match(note.text, /Vertex quota exceeded/);
  assert.match(note.cls, /mint-note--error/);
});

// ---- renderReceipt: the plain-English payoff of every click ----------------
test("renderReceipt narrates a caught+gated mint like a commit message", () => {
  const r = renderReceipt({ passed: false, before: 3, after: 3, n: 9, ci: [0.1, 0.6], mint: mint({}) });
  assert.match(r.html, /the answer stays wrong/i);
  assert.match(r.html, /minted &amp; passed the generality gate|minted/);
  assert.match(r.html, /caught 3 sibling/);
  assert.match(r.html, /can&#39;t read the answer key/);
  assert.match(r.html, /Working score 3 → 3 \/ 9/);
});

test("renderReceipt narrates a cleared false alarm with no mint", () => {
  const r = renderReceipt({ passed: true, before: 2, after: 3, n: 9, ci: [0.1, 0.6], mint: null });
  assert.match(r.html, /Well-supported — false alarm removed/);
  assert.match(r.html, /No check minted/);
  assert.match(r.html, /2 → 3 \/ 9/);
});

test("renderReceipt never points a scripted mint at the missing Verify button", () => {
  const r = renderReceipt({ passed: false, before: 3, after: 3, n: 9, ci: [0.1, 0.6],
                            mint: mint({ source: "mock" }) });
  assert.doesNotMatch(r.html, /hit Verify/);
  assert.match(r.html, /scripted offline demo/);
});

test("renderReceipt shows a gate rejection without the honesty flourish", () => {
  const r = renderReceipt({ passed: false, before: 3, after: 3, n: 9, ci: [0.1, 0.6],
                            mint: mint({ gated: false, caught_siblings: 1 }) });
  assert.match(r.html, /failed the generality gate/);
  assert.doesNotMatch(r.html, /can&#39;t read the answer key/);
});

test("renderReceipt escapes HTML riding in the minted property", () => {
  const r = renderReceipt({ passed: false, before: 1, after: 1, n: 3, ci: [0, 1],
                            mint: mint({ property: '<img src=x onerror=alert(1)>' }) });
  assert.doesNotMatch(r.html, /<img/);
});

test("renderMintNote reports an empty cluster as nothing-to-mint", () => {
  const note = renderMintNote({ attempted: false, gated: false, id: null, property: null,
                                cluster_size: 0, caught_siblings: 0, n_known_good: null,
                                error: null, source: "loop" });
  assert.match(note.text, /no similar past failures/);
  assert.match(note.cls, /mint-note--empty/);
});

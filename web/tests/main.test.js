// Pure-logic tests for web/static/main.js (run with: node --test web/tests/).
// The DOM wiring is guarded behind `typeof document`, so requiring the module
// under node exercises only the pure formatters.
const assert = require("node:assert");
const test = require("node:test");
const { renderScore, pct } = require("../static/main.js");

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

// Bonsai harness — client glue.
//
// The score event arrives as a JSON string swapped into the hidden #score-raw
// (contract §2). main.js parses it and formats the running score (counts +
// Wilson CI, never a bare %) into the visible #score-display. On stream close
// (done) it nudges the bonsai tree to sprout a branch.
"use strict";

// ---- pure formatters (unit-tested under node) ----------------------------
function pct(x) {
  return (Number(x) * 100).toFixed(1) + "%";
}

function renderScore(data) {
  const before = data.before;
  const after = data.after;
  const up = after > before ? " up" : "";
  const lo = pct(data.ci[0]);
  const hi = pct(data.ci[1]);
  return (
    '<div class="score-counts">' +
    '<span class="score-before">' + before + "</span>" +
    '<span class="score-arrow">→</span>' +
    '<span class="score-after' + up + '">' + after + "</span>" +
    '<span class="score-of">/ ' + data.n + " green</span>" +
    "</div>" +
    '<div class="score-ci">95% CI [' + lo + ", " + hi + "]</div>"
  );
}

// ---- DOM wiring (skipped under node) -------------------------------------
if (typeof document !== "undefined") {
  // 1. score JSON -> formatted running score.
  document.body.addEventListener("htmx:afterSwap", function (evt) {
    const t = evt.target;
    if (!t || t.id !== "score-raw") return;
    const raw = (t.textContent || "").trim();
    if (!raw) return;
    let data;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      return;
    }
    const display = document.getElementById("score-display");
    if (display) {
      display.innerHTML = renderScore(data);
      display.classList.remove("score-bump");
      // reflow so the animation re-triggers on every update
      void display.offsetWidth;
      display.classList.add("score-bump");
    }
  });

  // 2. keep the streaming rule console scrolled to the newest token.
  document.body.addEventListener("htmx:sseMessage", function (evt) {
    const rule = document.getElementById("rule-stream");
    if (rule) rule.scrollTop = rule.scrollHeight;
  });

  // 3. when an improve stream closes, sprout a branch on the bonsai tree.
  document.body.addEventListener("htmx:sseClose", function () {
    document.body.dispatchEvent(new Event("grow"));
  });
}

// ---- node export (no-op in the browser) ----------------------------------
if (typeof module !== "undefined" && module.exports) {
  module.exports = { renderScore, pct };
}

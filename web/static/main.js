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

    // flip the rule heading out of its "rewriting…" state once the verdict lands,
    // so it reads as finished (the green/red pill is the verdict; this confirms it).
    const improve = t.closest(".improve");
    const label = improve && improve.querySelector(".rule-label");
    if (label) {
      label.textContent = data.passed
        ? "✓ check rewritten — it passes now"
        : "✓ check rewritten — still catches this";
      label.classList.add("rule-label--done");
    }
  });

  // 2. keep the streaming rule console scrolled to the newest token.
  document.body.addEventListener("htmx:sseMessage", function (evt) {
    const rule = document.getElementById("rule-stream");
    if (rule) rule.scrollTop = rule.scrollHeight;
  });

  // 3. when an improve stream closes via the `done` event: sprout a branch AND
  // auto-reveal the cluster->mint->is_general lineage for that claim, so the moat
  // mechanism (Atlas $vectorSearch cluster -> minted general check -> gate) is the
  // DEFAULT surface right after the flip — not a hidden second click.
  // htmx:sseClose also fires on nodeReplaced/nodeMissing; only type:'message' is
  // the real done-driven close, so gate on it.
  document.body.addEventListener("htmx:sseClose", function (evt) {
    if (!evt.detail || evt.detail.type !== "message") return;
    document.body.dispatchEvent(new Event("grow"));
    var imp = evt.target && evt.target.closest ? evt.target.closest(".improve") : evt.target;
    var cid = imp && imp.getAttribute && imp.getAttribute("data-claim-id");
    if (cid && window.htmx) {
      window.htmx.ajax("GET", "/tree/" + encodeURIComponent(cid),
        { target: "#lineage", swap: "innerHTML" });
    }
  });
}

// ---- node export (no-op in the browser) ----------------------------------
if (typeof module !== "undefined" && module.exports) {
  module.exports = { renderScore, pct };
}

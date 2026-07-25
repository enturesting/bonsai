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

// The mint story riding the score event (data.mint; null when nothing to mint).
// Returns {text, cls} or null. Honest by construction: a scripted (mock) mint is
// labeled, a gate rejection is shown, a seam failure is reported — never hidden.
function renderMintNote(mint) {
  if (!mint) return null;
  var scripted = mint.source === "mock" ? " · scripted offline demo" : "";
  if (mint.error) {
    // show the actual seam error (store OR model) — never mislabel the cause
    return {
      text: "mint skipped (" + String(mint.error).slice(0, 140) + ") — score counts the rewritten check only",
      cls: "mint-note mint-note--error",
    };
  }
  if (mint.gated) {
    return {
      text:
        "✚ new check minted & passed the generality gate (caught " +
        mint.caught_siblings + " sibling failure" + (mint.caught_siblings === 1 ? "" : "s") +
        (mint.n_known_good != null ? ", passed all " + mint.n_known_good + " known-good" : "") +
        "): “" + mint.property + "”" + scripted,
      cls: "mint-note mint-note--gated",
    };
  }
  if (mint.attempted && mint.property) {
    return {
      text:
        "✕ candidate check failed the generality gate (caught " + mint.caught_siblings +
        " sibling" + (mint.caught_siblings === 1 ? "" : "s") + ", needs ≥2) — not added" + scripted,
      cls: "mint-note mint-note--rejected",
    };
  }
  return {
    text: "no similar past failures to mint a general check from yet" + scripted,
    cls: "mint-note mint-note--empty",
  };
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

// The plain-English payoff card for a finished check run — the answer's verdict
// first, then what the harness gained (or honestly didn't). Built ONLY from
// escaped text; the mint property is model-generated and untrusted.
function renderReceipt(data) {
  if (!data) return null;
  var lines = [];
  var scoreLine = "Working score " + data.before + " → " + data.after + " / " + data.n;
  if (data.passed) {
    lines.push('<div class="receipt-verdict receipt-verdict--clear">✓ Well-supported — false alarm removed.</div>');
    lines.push('<div class="receipt-line">No check minted — nothing to learn from a good answer. ' +
      esc(scoreLine) + ".</div>");
  } else {
    lines.push('<div class="receipt-verdict receipt-verdict--caught">✗ Caught — the answer stays wrong; the harness is what improves.</div>');
    var m = renderMintNote(data.mint);
    if (m) lines.push('<div class="receipt-line ' + m.cls + '">' + esc(m.text) + "</div>");
    if (data.mint && data.mint.gated && data.mint.source !== "mock") {
      // only for a REAL mint: the mock box has no Verify affordance, and a
      // scripted mint's "gain" must never be presented as confirmable.
      lines.push('<div class="receipt-line receipt-honesty">The loop that wrote it can' + "&#39;" +
        "t read the answer key — hit Verify on the honesty receipt to confirm the gain is real.</div>");
    }
    lines.push('<div class="receipt-line receipt-score">' + esc(scoreLine) +
      " (a stricter rubric can lower this — that's honest).</div>");
  }
  return { html: lines.join(""), cls: "receipt" };
}

function renderScore(data) {
  const before = data.before;
  const after = data.after;
  const up = after > before ? " up" : after < before ? " down" : "";
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
      // only animate a real change — an improve that moved nothing sends
      // before == after, and an honesty harness must not bump when nothing moved.
      // (On the wired path a confirmed failure can DROP the count: the minted
      // check tightens the pool — that change is real and should register.)
      if (data.after !== data.before) {
        void display.offsetWidth; // reflow so the animation re-triggers each time
        display.classList.add("score-bump");
      }
    }

    // flip the rule heading out of its "rewriting…" state once the verdict lands,
    // so it reads as finished (the green/red pill is the verdict; this confirms it).
    const improve = t.closest(".improve");
    const label = improve && improve.querySelector(".rule-label");
    if (label) {
      label.textContent = data.passed
        ? "✓ well-supported — false alarm cleared"
        : "✓ caught — a check now polices this pattern";
      label.classList.add("rule-label--done");
    }

    // the receipt: the plain-English payoff — verdict, the mint story, and the
    // score delta — right under the rewrite console. THIS owns the payoff, not
    // the token stream.
    const slot = improve && improve.querySelector(".receipt");
    const receipt = renderReceipt(data);
    if (slot && receipt) {
      slot.innerHTML = receipt.html;
      slot.className = receipt.cls;
      slot.hidden = false;
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

  // 4. example chips: one click fills the Live Claim form (claim + source + class)
  // so the on-stage "now you type one" beat never has to improvise a fitting claim.
  document.body.addEventListener("click", function (evt) {
    var chip = evt.target && evt.target.closest ? evt.target.closest(".ex-chip") : null;
    if (!chip) return;
    var form = chip.closest(".live-claim");
    if (!form) return;
    var claim = form.querySelector('[name="claim"]');
    var source = form.querySelector('[name="source"]');
    var cat = form.querySelector('[name="category"]');
    if (claim) claim.value = chip.getAttribute("data-claim") || "";
    if (source) source.value = chip.getAttribute("data-source") || "";
    if (cat) cat.value = chip.getAttribute("data-cat") || cat.value;
    if (claim) claim.focus();
  });
}

// ---- node export (no-op in the browser) ----------------------------------
if (typeof module !== "undefined" && module.exports) {
  module.exports = { renderScore, renderMintNote, renderReceipt, pct };
}

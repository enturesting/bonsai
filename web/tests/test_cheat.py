"""The "try to cheat it" station: the honesty band's expander + POST /cheat.

The claim under test is literal: the station runs the SAME checker CI's
honesty gate runs (eval.honesty — imported, never a re-implementation, never
a shell-out to pytest), keyless, against this box's real loop/ source; canned
"cheat attempt" snippets are linted AS TEXT through the same functions and
labeled as examples, not repo modifications. Copy discipline: "a lint, not a
sandbox", and no sentence may claim cheating is impossible.
"""
from __future__ import annotations

from eval.honesty import run_honesty_lint

from web import routes as web_routes


# ── the station on the dashboard (inside the honesty band) ───────────────────
def test_station_runs_the_real_ci_checker_and_shows_a_real_pass(client):
    real = run_honesty_lint()  # the exact function the route (and CI) calls
    assert real["clean"] and real["files_scanned"] > 0
    body = client.get("/").text
    assert "Try to cheat it" in body
    assert "the exact check CI runs, running now" in body
    # the rendered scan count is the real one — the verdict came from the checker
    assert f"scanned {real['files_scanned']} <code>loop/</code> source files" in body
    assert "PASSING" in body


def test_station_is_labeled_a_lint_not_a_sandbox_and_never_overclaims(client):
    body = client.get("/").text
    assert "a lint, not a sandbox" in body
    # scoped claim: what the gate proves, and its limit — never "cheat-proof"
    assert "nothing more" in body
    assert "guardrail check, not an unbreakable wall" in body
    assert "impossible" not in body.lower() and "cheat-proof" not in body.lower()


def test_station_would_report_a_real_leak_never_a_staged_pass(client, monkeypatch):
    """The verdict shown is always the real lint outcome: if the checker ever
    found offenders, the station must say LEAK — not render a green pass."""
    monkeypatch.setattr(
        web_routes,
        "run_honesty_lint",
        lambda: {"clean": False, "files_scanned": 7,
                 "offenders": [("grower.py", ["eval/gold"])]},
    )
    body = client.get("/").text
    assert "LEAK" in body and "grower.py" in body
    assert "in CI this fails the build" in body
    assert "PASSING" not in body


# ── POST /cheat: snippets linted as text through the same checker ────────────
def test_canned_cheat_snippet_is_caught_by_the_real_checker(client):
    body = client.post("/cheat", data={"canned": "import-gold"}).text
    assert "CAUGHT" in body and "would fail the CI build" in body
    assert "load_gold" in body  # the matched forbidden pattern is shown
    # labeled an example run through the real lint — NOT a repo modification
    assert "linted as text" in body and "was not modified" in body


def test_canned_comment_leak_is_caught_raw_text_scan(client):
    body = client.post("/cheat", data={"canned": "comment-leak"}).text
    assert "CAUGHT" in body and "eval/gold" in body


def test_innocent_lookalike_passes_the_same_lint(client):
    """The station shows real precision, not a hardcoded CAUGHT: names that
    merely contain 'eval' pass — and the pass copy stays scoped."""
    body = client.post("/cheat", data={"canned": "innocent"}).text
    assert "CAUGHT" not in body
    assert "passes the lint" in body
    assert "can pass it and still be wrong in other ways" in body


def test_typed_snippet_is_linted_for_real_both_directions(client):
    caught = client.post("/cheat", data={"snippet": "from eval.scoring import load_gold"}).text
    assert "CAUGHT" in caught
    clean = client.post("/cheat", data={"snippet": "from loop.engine import eval_stream"}).text
    assert "CAUGHT" not in clean and "passes the lint" in clean


def test_empty_submit_is_a_noop(client):
    assert client.post("/cheat", data={}).text == ""


def test_gold_verify_rerender_keeps_the_station(client):
    """POST /gold/verify outerHTML-swaps #gold-panel — the station must survive
    the swap (the mock/keyless path re-renders _gold.html with the lint rerun)."""
    body = client.post("/gold/verify").text
    assert "Try to cheat it" in body
    assert "a lint, not a sandbox" in body

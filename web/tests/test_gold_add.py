"""The answer-key manager: web.gold's add path + POST /gold/add + _goldkey.html.

The rail nuance: only /loop is barred from gold — /web writes it on the owner's
behalf (their labels, not just their rules). Disciplines under test:
  * copy-verify — success is only reported after the item is read back off disk
    intact; a failed verify removes the file and is reported, never swallowed;
  * path safety — ids are rejected (not repaired) on traversal/malformed input,
    writes are confined to the gold dir, existing files are never overwritten;
  * provenance honesty — owner-added is labeled owner-added in storage AND in the
    rendered fragment, and the receipt copy stays tied to the set it was computed
    on (a stored frozen-set receipt says owner-added items are not in it).
"""
from __future__ import annotations

import json

import pytest

from web import gold as web_gold
from web import routes as web_routes

FROZEN_FIXTURE = {
    "gold_id": "g-clean-fixture",
    "question": "Is the fixture frozen?",
    "reference_answer": "Yes [S1].",
    "must_support": [{"claim": "Yes.", "claim_type": "judgment",
                      "supporting_quote": "Yes.", "source_url": "S1",
                      "category_relevant": "clean"}],
    "must_not_assert": [],
    "expected_verdict": "pass",
    "frozen": True,
}

ADD_FORM = {
    "question": "How often are access reviews performed?",
    "claim": "Access reviews are performed quarterly.",
    "supporting_quote": "Access reviews are performed quarterly by the security team.",
    "category": "clean",
    "claim_type": "judgment",
    "expected_verdict": "pass",
}


@pytest.fixture
def gold_dir(tmp_path, monkeypatch):
    """Redirect web.gold's ONE read/write dir to a sandbox seeded with a frozen
    item — tests must never write into the real eval/gold/ set."""
    d = tmp_path / "gold"
    d.mkdir()
    (d / "g-clean-fixture.json").write_text(json.dumps(FROZEN_FIXTURE), encoding="utf-8")
    monkeypatch.setattr(web_gold, "GOLD_DIR", str(d))
    return d


def _sandbox_files(gold_dir):
    return sorted(p.name for p in gold_dir.iterdir())


# ── add + list round-trip (keyless: a file write, no model) ──────────────────
def test_add_and_list_round_trip_mirrors_frozen_schema(gold_dir):
    item = web_gold.add_gold_item(**{k: v for k, v in ADD_FORM.items()})
    assert item["gold_id"] == "g-owner-access-reviews-are-performed-quarterly"
    stored = json.loads((gold_dir / (item["gold_id"] + ".json")).read_text(encoding="utf-8"))
    assert stored == item
    # schema mirrors the frozen items exactly, plus explicit provenance in storage
    assert set(FROZEN_FIXTURE) <= set(stored)
    assert set(stored["must_support"][0]) == set(FROZEN_FIXTURE["must_support"][0])
    assert stored["frozen"] is False
    assert stored["provenance"] == "owner-added"
    # listed as owner-added; the frozen item never shows up as owner
    assert [it["gold_id"] for it in web_gold.list_owner_items()] == [item["gold_id"]]
    prov = web_gold.gold_provenance()
    assert [it["gold_id"] for it in prov["frozen"]] == ["g-clean-fixture"]


def test_fail_label_mirrors_the_frozen_must_not_assert_convention(gold_dir):
    item = web_gold.add_gold_item(question="q?", claim="Northbeam never stores data.",
                                  category="fabricated-quote", expected_verdict="fail")
    assert item["expected_verdict"] == "fail"
    assert item["must_not_assert"] == ["Northbeam never stores data."]


def test_duplicate_id_is_rejected_never_overwritten(gold_dir):
    web_gold.add_gold_item(question="q?", claim="Same claim twice.")
    before = _sandbox_files(gold_dir)
    with pytest.raises(ValueError, match="never overwritten"):
        web_gold.add_gold_item(question="other q?", claim="Same claim twice.")
    assert _sandbox_files(gold_dir) == before


def test_invalid_label_category_or_empty_fields_are_rejected(gold_dir):
    with pytest.raises(ValueError, match="'pass' or 'fail'"):
        web_gold.add_gold_item(question="q", claim="c", expected_verdict="maybe")
    with pytest.raises(ValueError, match="unknown category"):
        web_gold.add_gold_item(question="q", claim="c", category="not-a-family")
    with pytest.raises(ValueError, match="claim_type"):
        web_gold.add_gold_item(question="q", claim="c", claim_type="vibes")
    with pytest.raises(ValueError, match="required"):
        web_gold.add_gold_item(question="", claim="c")
    assert _sandbox_files(gold_dir) == ["g-clean-fixture.json"]  # nothing written


# ── path safety: rejected, not repaired; confined to the gold dir ────────────
@pytest.mark.parametrize("bad_id", [
    "../pwn", "..", "a/../../b", "g-owner-../x", "/etc/passwd",
    "x.json", ".hidden", "UPPER-CASE", "spaced id", "-leading-hyphen",
])
def test_unsafe_ids_are_rejected_and_nothing_is_written(gold_dir, tmp_path, bad_id):
    with pytest.raises(ValueError, match="unsafe id"):
        web_gold.add_gold_item(question="q", claim="c", gold_id=bad_id)
    assert _sandbox_files(gold_dir) == ["g-clean-fixture.json"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["gold"]  # nothing escaped


def test_route_reports_traversal_id_as_a_refusal(client, gold_dir):
    body = client.post("/gold/add", data=ADD_FORM | {"gold_id": "../../evil"}).text
    assert "not added" in body and "unsafe id" in body
    assert "goldkey-card--added" not in body
    assert _sandbox_files(gold_dir) == ["g-clean-fixture.json"]


# ── copy-verify: no silent partial writes ────────────────────────────────────
def test_copy_verify_mismatch_removes_the_file_and_raises(gold_dir, monkeypatch):
    monkeypatch.setattr(web_gold, "_read_back_item", lambda path: {"gold_id": "tampered"})
    with pytest.raises(RuntimeError, match="copy-verify failed"):
        web_gold.add_gold_item(**{k: v for k, v in ADD_FORM.items()})
    assert _sandbox_files(gold_dir) == ["g-clean-fixture.json"]
    assert web_gold.list_owner_items() == []


def test_route_reports_copy_verify_failure_never_a_fake_success(client, gold_dir, monkeypatch):
    monkeypatch.setattr(web_gold, "_read_back_item", lambda path: {})
    body = client.post("/gold/add", data=ADD_FORM).text
    assert "goldkey-card--failed" in body
    assert "not added" in body and "copy-verify failed" in body
    assert "nothing was kept" in body
    assert "goldkey-card--added" not in body
    assert _sandbox_files(gold_dir) == ["g-clean-fixture.json"]


# ── route round-trip + provenance labeling in the rendered fragment ──────────
def test_route_add_lists_item_with_owner_provenance(client, gold_dir):
    body = client.post("/gold/add", data=ADD_FORM).text
    assert "goldkey-card--added" in body
    assert "written and read back intact" in body
    assert "owner-added, not frozen" in body
    assert "g-owner-access-reviews-are-performed-quarterly" in body
    # provenance chips: the new item is owner-added; frozen stays a read-only count
    assert "prov--owner" in body and "owner-added" in body
    assert "prov--frozen" in body and "authored offline, read-only here" in body
    # the dashboard's copy of the fragment lists it too (add → list round-trip)
    dash = client.get("/").text
    assert "g-owner-access-reviews-are-performed-quarterly" in dash


def test_dashboard_fragment_without_owner_items_shows_only_the_frozen_count(client):
    # unpatched GOLD_DIR: the real eval/gold/ (frozen-only) — read, never written
    body = client.get("/").text
    assert 'id="goldkey-panel"' in body
    assert "prov--frozen" in body
    assert "prov--owner" not in body.split('id="goldkey-panel"')[1].split("</section>")[0]
    assert "not in this receipt" not in body          # no owner items → no receipt caveat
    assert "frozen gold" in body                      # stored receipt copy unchanged


# ── receipt provenance: owner adds never silently change a receipt's claim ───
def test_stored_receipt_says_owner_items_are_not_in_it(client, gold_dir):
    client.post("/gold/add", data=ADD_FORM)
    body = client.get("/").text
    assert "not in this receipt" in body
    assert "computed on the frozen set only" in body
    # the stored numbers keep their frozen-set eyebrow — the set they were computed on
    assert "frozen gold" in body and "precomputed, fixed" in body


def test_live_rescore_that_included_owner_items_says_so(client, monkeypatch):
    async def fake_recompute():
        return {"before": 9, "after": 14, "n": 16, "ci": [0.65, 0.96],
                "sign_test": {"helped": 5, "hurt": 0, "n": 5, "p": 0.03125},
                "checks_before": 1, "checks_after": 6, "live": True,
                "n_frozen": 15, "n_owner": 1}

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "recompute_gold_result", fake_recompute)
    body = client.post("/gold/verify").text
    assert "15 frozen + 1 owner-added item" in body
    assert "recomputed live just now" in body
    assert "not in this receipt" not in body          # these numbers DO include them


async def test_recompute_reports_the_provenance_split_of_the_scored_set(monkeypatch):
    import store as store_pkg
    import eval.scoring as scoring
    from store.models import Check

    rubric = [Check(id="numeric-cites-source", property="p", rationale="r",
                    positive_example="p", negative_example="n", overfit_risk="o")]
    gold = [{"gold_id": "g-a", "frozen": True}, {"gold_id": "g-b", "frozen": True},
            {"gold_id": "g-owner-c", "frozen": False, "provenance": "owner-added"}]

    async def fake_checks(db):
        return rubric

    monkeypatch.setattr(store_pkg, "get_db", lambda: object())
    monkeypatch.setattr(store_pkg, "get_checks", fake_checks, raising=False)
    monkeypatch.setattr(scoring, "load_gold", lambda: gold)
    monkeypatch.setattr(scoring, "score_rubric", lambda checks, items: [True for _ in items])

    res = await web_gold.recompute_gold_result()
    assert res["n"] == 3 and res["n_frozen"] == 2 and res["n_owner"] == 1

"""Tests for the DEV fixture-question loader (fixtures.questions)."""
from __future__ import annotations

import fixtures
from fixtures.questions import FAILURE_CATEGORIES, load_fixture_questions


def test_loads_at_least_eight_fixtures():
    qs = load_fixture_questions()
    assert isinstance(qs, list)
    assert len(qs) >= 8


def test_public_loader_reexported_from_package():
    # /web imports `fixtures.load_fixture_questions`
    assert fixtures.load_fixture_questions is load_fixture_questions


def test_every_fixture_has_required_shape():
    for q in load_fixture_questions():
        assert q["id"], q
        assert q["question"]
        assert q["category"] in set(FAILURE_CATEGORIES) | {"clean"}
        assert isinstance(q["sources"], list) and q["sources"]
        for s in q["sources"]:
            assert s["id"] and s["text"]
        mock = q["mock"]
        assert mock["claim"] and mock["output"]
        assert isinstance(mock["cite_ids"], list) and mock["cite_ids"]
        # cited ids must reference real candidate sources
        cand_ids = {s["id"] for s in q["sources"]}
        assert set(mock["cite_ids"]) <= cand_ids


def test_all_five_failure_categories_are_covered():
    cats = {q["category"] for q in load_fixture_questions()}
    for c in FAILURE_CATEGORIES:
        assert c in cats, f"missing fixture for category {c}"
    assert "clean" in cats


def test_failure_fixtures_carry_diagnosis_metadata():
    for q in load_fixture_questions():
        if q["category"] == "clean":
            continue
        assert q["expected"], q["id"]
        assert q["why"], q["id"]


def test_fixture_ids_are_unique():
    ids = [q["id"] for q in load_fixture_questions()]
    assert len(ids) == len(set(ids))

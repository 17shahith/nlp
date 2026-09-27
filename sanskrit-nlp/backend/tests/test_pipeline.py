"""Tests for modules/pipeline.py end-to-end, against the seeded test cases."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from db import get_db
from modules import pipeline

CASES_PATH = Path(__file__).resolve().parent.parent / "seed" / "test_cases.json"


def _load_cases():
    with open(CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", [c for c in _load_cases() if c["type"] == "valid"], ids=lambda c: c["input"])
async def test_valid_cases_produce_expected_sentence(case):
    db = get_db()
    trace = await pipeline.run(db, case["input"])
    assert trace["success"] is True
    output = trace["steps"]["6_output"]
    assert output is not None
    assert output["sanskrit"] == case["expected_sanskrit"]
    assert output["english"] == case["expected_english"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [c for c in _load_cases() if c["type"] in ("invalid", "incomplete") and "expected_failure" in c],
    ids=lambda c: c["input"] or "(empty)",
)
async def test_invalid_and_incomplete_cases_fail_expected_rule(case):
    db = get_db()
    trace = await pipeline.run(db, case["input"])
    assert trace["success"] is False
    failed_ids = [r["id"] for r in trace["steps"]["4_rules"] if not r["passed"]]
    assert case["expected_failure"] in failed_ids


@pytest.mark.asyncio
async def test_empty_input_gives_friendly_message():
    db = get_db()
    trace = await pipeline.run(db, "")
    assert trace["success"] is False
    assert "Please enter at least two words" in trace["errors"]

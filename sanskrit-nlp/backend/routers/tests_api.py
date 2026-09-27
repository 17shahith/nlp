"""POST /api/run-tests -- run seed/test_cases.json through the live pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from db import get_db
from modules import pipeline

router = APIRouter(prefix="/api", tags=["tests"])

_TEST_CASES_PATH = Path(__file__).resolve().parent.parent / "seed" / "test_cases.json"


def _load_cases() -> list[dict[str, Any]]:
    with open(_TEST_CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _evaluate(case: dict[str, Any], trace: dict[str, Any]) -> tuple[bool, str]:
    """Compare a pipeline trace against one test case's expectation. Returns (passed, actual)."""
    if case["type"] == "valid":
        output = trace["steps"]["6_output"]
        if not trace["success"] or output is None:
            return False, "; ".join(trace["errors"]) or "generation failed"
        actual = output["sanskrit"]
        passed = actual == case["expected_sanskrit"]
        return passed, actual

    if case["type"] == "incomplete" and "expected_message" in case:
        actual = "; ".join(trace["errors"])
        passed = case["expected_message"] in actual
        return passed, actual

    # invalid / incomplete cases with an expected failing rule id
    expected_rule = case.get("expected_failure")
    failed_rule_ids = [r["id"] for r in trace["steps"]["4_rules"] if not r["passed"]]
    actual = ", ".join(failed_rule_ids) if failed_rule_ids else "; ".join(trace["errors"])
    passed = (not trace["success"]) and (expected_rule in failed_rule_ids)
    return passed, actual


@router.post("/run-tests")
async def run_tests():
    """Run every seeded test case through the pipeline and report pass/fail."""
    db = get_db()
    cases = _load_cases()
    results = []
    passed_count = 0

    for case in cases:
        trace = await pipeline.run(db, case["input"])
        passed, actual = _evaluate(case, trace)
        passed_count += int(passed)
        results.append({
            "id": case["id"],
            "type": case["type"],
            "input": case["input"],
            "expected": case.get("expected_sanskrit") or case.get("expected_failure") or case.get("expected_message"),
            "actual": actual,
            "status": "PASS" if passed else "FAIL",
        })

    return {
        "total": len(cases),
        "passed": passed_count,
        "failed": len(cases) - passed_count,
        "results": results,
    }

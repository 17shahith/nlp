"""Tests for the HTTP API layer (routers/*.py), using httpx against the FastAPI app."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["db"] == "ok"
    assert body["groq"] in ("enabled", "disabled")


@pytest.mark.asyncio
async def test_generate_valid_sentence(client):
    resp = await client.post("/api/generate", json={"words": "Rama, fruit, eats"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["steps"]["6_output"]["sanskrit"] == "रामः फलम् खादति।"


@pytest.mark.asyncio
async def test_generate_unknown_word_fails_with_r10(client):
    resp = await client.post("/api/generate", json={"words": "Rama, xyzabc, eats"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    failed_ids = [r["id"] for r in body["steps"]["4_rules"] if not r["passed"]]
    assert "R10" in failed_ids


@pytest.mark.asyncio
async def test_lookup_endpoint(client):
    resp = await client.get("/api/lookup", params={"q": "फलम्"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["english"] == "fruit"
    assert body["category"] == "Noun"


@pytest.mark.asyncio
async def test_lookup_unknown_returns_404(client):
    resp = await client.get("/api/lookup", params={"q": "xyzabc"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rules_endpoint_lists_ten_rules(client):
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 10
    assert {i["id"] for i in items} == {f"R{n}" for n in range(1, 11)}


@pytest.mark.asyncio
async def test_run_tests_endpoint_reports_results(client):
    resp = await client.post("/api/run-tests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(body["results"])
    assert body["passed"] + body["failed"] == body["total"]


@pytest.mark.asyncio
async def test_add_and_delete_word(client):
    payload = {
        "lemma": "परीक्षा-शब्द",
        "iast": "parīkṣā-śabda",
        "english": "testword",
        "english_aliases": ["testword"],
        "category": "Noun",
        "gender": "neuter",
        "animate": False,
        "forms": [
            {"form": "परीक्षा-शब्दम्", "case": "nominative", "vibhakti": "prathama", "number": "singular"}
        ],
    }
    resp = await client.post("/api/words", json=payload)
    assert resp.status_code == 201

    resp = await client.delete(f"/api/words/{payload['lemma']}")
    assert resp.status_code == 200

"""Tests for modules/vocabulary.py (sub-task 1: meaning lookup)."""
from __future__ import annotations

import pytest

from db import get_db
from modules.vocabulary import lookup


@pytest.mark.asyncio
async def test_lookup_devanagari_exact_form():
    db = get_db()
    match = await lookup(db, "रामः", "devanagari")
    assert match is not None
    assert match.lemma == "राम"
    assert match.english == "Rama"
    assert match.matched_form["case"] == "nominative"


@pytest.mark.asyncio
async def test_lookup_devanagari_lemma_fallback():
    db = get_db()
    match = await lookup(db, "राम", "devanagari")
    assert match is not None
    assert match.matched_form is None
    assert match.lemma == "राम"


@pytest.mark.asyncio
async def test_lookup_english_alias():
    db = get_db()
    match = await lookup(db, "fruit", "latin")
    assert match is not None
    assert match.lemma == "फल"
    assert match.direction == "en2sa"


@pytest.mark.asyncio
async def test_lookup_english_verb_conjugation():
    db = get_db()
    match = await lookup(db, "eats", "latin")
    assert match is not None
    assert match.lemma == "खाद्"


@pytest.mark.asyncio
async def test_lookup_plural_hint():
    db = get_db()
    match = await lookup(db, "boys", "latin")
    assert match is not None
    assert match.number_hint == "plural"


@pytest.mark.asyncio
async def test_lookup_unknown_word_returns_none():
    db = get_db()
    match = await lookup(db, "xyzabc", "latin")
    assert match is None

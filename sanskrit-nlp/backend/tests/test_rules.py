"""Tests for modules/rules.py (sub-task 4: grammar rule engine)."""
from __future__ import annotations

import pytest

from db import get_db
from modules import grammar_info, inflector, role_assigner
from modules.role_assigner import WordSlot
from modules.rules import RuleContext, hard_failures, run_all
from modules.vocabulary import lookup


async def _slots_for(tokens_and_scripts):
    db = get_db()
    slots = []
    for i, (text, script) in enumerate(tokens_and_scripts):
        match = await lookup(db, text, script)
        assert match is not None, f"expected '{text}' to resolve"
        gi = grammar_info.get_grammar_info(match)
        slots.append(WordSlot(index=i, token=text, match=match, grammar=gi))
    role_assigner.assign_roles(slots)
    inflector.inflect(slots)
    return slots


@pytest.mark.asyncio
async def test_r5_fails_on_number_mismatch():
    slots = await _slots_for([("रामः", "devanagari"), ("फलम्", "devanagari"), ("खादन्ति", "devanagari")])
    ctx = RuleContext(slots=slots, unknown_tokens=[])
    results = run_all(ctx)
    failures = {r.id for r in hard_failures(results)}
    assert "R5" in failures


@pytest.mark.asyncio
async def test_r6_fails_on_person_mismatch():
    slots = await _slots_for([("अहम्", "devanagari"), ("फलम्", "devanagari"), ("खादति", "devanagari")])
    ctx = RuleContext(slots=slots, unknown_tokens=[])
    results = run_all(ctx)
    failures = {r.id for r in hard_failures(results)}
    assert "R6" in failures


@pytest.mark.asyncio
async def test_r7_fails_intransitive_with_object():
    slots = await _slots_for([("boy", "latin"), ("fruit", "latin"), ("runs", "latin")])
    ctx = RuleContext(slots=slots, unknown_tokens=[])
    results = run_all(ctx)
    failures = {r.id for r in hard_failures(results)}
    assert "R7" in failures


@pytest.mark.asyncio
async def test_r8_fails_on_gender_mismatch():
    slots = await _slots_for([
        ("बालकः", "devanagari"), ("सुन्दरी", "devanagari"),
        ("खादति", "devanagari"), ("फलम्", "devanagari"),
    ])
    ctx = RuleContext(slots=slots, unknown_tokens=[])
    results = run_all(ctx)
    failures = {r.id for r in hard_failures(results)}
    assert "R8" in failures


@pytest.mark.asyncio
async def test_r10_fails_on_unknown_word():
    ctx = RuleContext(slots=[], unknown_tokens=["xyzabc"])
    results = run_all(ctx)
    failures = {r.id for r in hard_failures(results)}
    assert "R10" in failures


@pytest.mark.asyncio
async def test_valid_sentence_passes_all_hard_rules():
    slots = await _slots_for([("रामः", "devanagari"), ("फलम्", "devanagari"), ("खादति", "devanagari")])
    ctx = RuleContext(slots=slots, unknown_tokens=[])
    results = run_all(ctx)
    assert hard_failures(results) == []

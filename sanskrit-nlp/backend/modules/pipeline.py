"""
Pipeline orchestrator.

Runs sub-tasks 1 through 5 in order (vocabulary lookup, classification,
grammar info, role assignment + inflection, rule checking, template
application) and assembles the step-by-step trace that both the API and
the frontend display, matching the assignment's example shape.

Sentence generation itself never calls Groq or any other LLM: every field
in the trace is produced by deterministic lookups and the rule engine in
rules.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from modules import classifier, grammar_info, inflector, normalizer, role_assigner, rules, sentence_builder
from modules.role_assigner import WordSlot
from modules.rules import RuleContext
from modules.vocabulary import lookup as vocab_lookup

EMPTY_INPUT_MESSAGE = "Please enter at least two words"


async def _build_slots(
    db: AsyncIOMotorDatabase, tokens: list[normalizer.Token]
) -> tuple[list[WordSlot], list[str], list[dict[str, Any]]]:
    """Look up every token; return (resolved slots, unknown token texts, meaning rows)."""
    slots: list[WordSlot] = []
    unknown: list[str] = []
    meaning_rows: list[dict[str, Any]] = []

    for i, tok in enumerate(tokens):
        match = await vocab_lookup(db, tok.text, tok.script)
        if match is None:
            unknown.append(tok.text)
            meaning_rows.append({
                "input": tok.raw, "sanskrit": None, "english": None,
                "found": False, "reason": f"'{tok.text}' was not found in the vocabulary.",
            })
            continue

        gi = grammar_info.get_grammar_info(match)
        slot = WordSlot(index=i, token=tok.text, match=match, grammar=gi)
        slots.append(slot)
        meaning_rows.append({
            "input": tok.raw,
            "sanskrit": match.matched_form["form"] if match.matched_form else match.lemma,
            "english": match.english,
            "found": True,
        })

    return slots, unknown, meaning_rows


def _errors_from(rule_results: list, slots: list[WordSlot]) -> list[str]:
    errors = []
    for r in rules.hard_failures(rule_results):
        errors.append(f"{r.message} (Rule {r.id})")
    for s in slots:
        if s.error:
            errors.append(f"{s.error} (word: '{s.token}')")
    return errors


async def run(db: AsyncIOMotorDatabase, raw_input: str) -> dict[str, Any]:
    """Run the full pipeline for one input string and return the trace dict."""
    tokens = normalizer.normalize(raw_input)

    if not tokens:
        trace = {
            "input": raw_input,
            "steps": {
                "1_meaning": [], "2_classification": [], "3_grammar": [],
                "4_rules": [], "5_template": None, "6_output": None,
            },
            "success": False,
            "errors": [EMPTY_INPUT_MESSAGE],
        }
        await _log(db, raw_input, trace)
        return trace

    slots, unknown, meaning_rows = await _build_slots(db, tokens)

    role_assigner.assign_roles(slots)
    inflector.inflect(slots)

    ctx = RuleContext(slots=slots, unknown_tokens=unknown)
    rule_results = rules.run_all(ctx)

    hard_fail = bool(rules.hard_failures(rule_results)) or any(s.error for s in slots)
    success = not hard_fail

    output = None
    template_name = None
    if success:
        built = sentence_builder.build_sentence(slots)
        output = {"sanskrit": built.sanskrit, "iast": built.iast, "english": built.english}
        template_name = built.template

    classification_rows = [
        {"word": s.chosen_form or s.token, "category": classifier.classify(s.match.word_doc)}
        for s in slots
    ]
    grammar_rows = [
        {
            "word": s.chosen_form or s.token,
            "role": s.role,
            "gender": s.chosen_gender,
            "number": s.chosen_number,
            "case": s.chosen_case,
            "person": s.chosen_person,
            "tense": s.grammar.tense if s.category == "Verb" else None,
        }
        for s in slots
    ]

    trace: dict[str, Any] = {
        "input": raw_input,
        "steps": {
            "1_meaning": meaning_rows,
            "2_classification": classification_rows,
            "3_grammar": grammar_rows,
            "4_rules": [r.model_dump() for r in rule_results],
            "5_template": template_name,
            "6_output": output,
        },
        "success": success,
        "errors": [] if success else _errors_from(rule_results, slots),
    }

    await _log(db, raw_input, trace)
    return trace


async def _log(db: AsyncIOMotorDatabase, raw_input: str, trace: dict[str, Any]) -> None:
    """Best-effort write to generation_logs; failures here never break the API."""
    try:
        output = trace["steps"]["6_output"]
        failed_rules = [
            r["id"] for r in trace["steps"]["4_rules"] if not r["passed"] and r.get("hard", True)
        ]
        await db.generation_logs.insert_one({
            "input": raw_input,
            "output_sanskrit": output["sanskrit"] if output else None,
            "output_english": output["english"] if output else None,
            "success": trace["success"],
            "failed_rules": failed_rules,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception:
        pass

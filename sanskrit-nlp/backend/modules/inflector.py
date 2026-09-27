"""
# SUB-TASK 5b: Inflection (Correct Stored Form Selection)

Once role_assigner.py has decided *what* each word is doing (Subject,
Object, Verb, Adjective), this module decides *which stored form* of that
word actually expresses it:

- Subject -> nominative form (singular unless the input indicated plural)
- Object -> accusative form (singular unless the input indicated plural)
- Verb -> the form matching the Subject's person + number, present tense
- Adjective -> the form matching its noun's gender + case + number

When the user gave an explicit Devanagari form, that exact form is used
as-is and is never silently replaced -- if it breaks an agreement rule,
the rule engine (rules.py) reports the violation instead of "fixing" it.
When the user gave an English word, this module chooses the grammatically
correct form on their behalf. If no matching form exists in the
vocabulary, the slot is marked with a clear error instead of guessing.
"""
from __future__ import annotations

from typing import Any, Optional

from modules.role_assigner import WordSlot

NO_FORM_ERROR = "Form not available in vocabulary"


def _find_noun_form(forms: list[dict[str, Any]], case: str, number: str) -> Optional[dict[str, Any]]:
    for f in forms:
        if f.get("case") == case and f.get("number") == number:
            return f
    return None


def _find_verb_form(forms: list[dict[str, Any]], person: int, number: str) -> Optional[dict[str, Any]]:
    for f in forms:
        if f.get("person") == person and f.get("number") == number:
            return f
    return None


def _find_adjective_form(
    forms: list[dict[str, Any]], gender: str, case: str, number: str
) -> Optional[dict[str, Any]]:
    for f in forms:
        if f.get("gender") == gender and f.get("case") == case and f.get("number") == number:
            return f
    return None


def _use_explicit_form(slot: WordSlot) -> None:
    """Copy an explicitly-given Devanagari form's attributes onto the slot verbatim.

    When the stored text is case-ambiguous (neuter nom/acc are identical),
    grammar_info leaves case/vibhakti unset; role_assigner then decided the
    role from animacy instead, so we resolve the display case from that
    role here rather than reporting "unknown".
    """
    slot.chosen_form = slot.match.matched_form["form"]
    if slot.grammar.case is not None:
        slot.chosen_case = slot.grammar.case
        slot.chosen_vibhakti = slot.grammar.vibhakti
    elif slot.role == "Subject":
        slot.chosen_case = "nominative"
        slot.chosen_vibhakti = "prathama"
    elif slot.role == "Object":
        slot.chosen_case = "accusative"
        slot.chosen_vibhakti = "dvitiya"
    slot.chosen_number = slot.grammar.number
    slot.chosen_gender = slot.grammar.gender
    slot.chosen_person = slot.grammar.person


def _resolved_number(slot: WordSlot) -> str:
    number = slot.grammar.number
    return number if number in ("singular", "dual", "plural") else "singular"


def _inflect_noun_or_pronoun(slot: WordSlot) -> None:
    if slot.match.direction == "sa2en":
        _use_explicit_form(slot)
        return

    number = _resolved_number(slot)
    case = "nominative" if slot.role == "Subject" else "accusative"
    vibhakti = "prathama" if case == "nominative" else "dvitiya"
    form = _find_noun_form(slot.match.word_doc.get("forms", []), case, number)
    if form is None:
        slot.error = f"{NO_FORM_ERROR}: no {case} {number} form for '{slot.token}'"
        return

    slot.chosen_form = form["form"]
    slot.chosen_case = case
    slot.chosen_vibhakti = vibhakti
    slot.chosen_number = number
    slot.chosen_gender = slot.grammar.gender
    slot.chosen_person = slot.grammar.person


def _inflect_adjective(slot: WordSlot, slots_by_index: dict[int, WordSlot]) -> None:
    if slot.match.direction == "sa2en":
        _use_explicit_form(slot)
        return

    target = slots_by_index.get(slot.modifies) if slot.modifies is not None else None
    if target is None or target.chosen_gender is None:
        slot.error = f"{NO_FORM_ERROR}: adjective '{slot.token}' has no noun to agree with"
        return

    gender, case, number = target.chosen_gender, target.chosen_case, target.chosen_number
    form = _find_adjective_form(slot.match.word_doc.get("forms", []), gender, case, number)
    if form is None:
        slot.error = f"{NO_FORM_ERROR}: no {gender} {case} {number} form for '{slot.token}'"
        return

    slot.chosen_form = form["form"]
    slot.chosen_case = case
    slot.chosen_number = number
    slot.chosen_gender = gender


def _inflect_verb(slot: WordSlot, subject: Optional[WordSlot]) -> None:
    if slot.match.direction == "sa2en":
        _use_explicit_form(slot)
        return

    if subject is None:
        slot.error = "No subject available to determine verb agreement"
        return

    person = subject.chosen_person if subject.chosen_person else 3
    number = subject.chosen_number or "singular"
    form = _find_verb_form(slot.match.word_doc.get("forms", []), person, number)
    if form is None:
        slot.error = f"{NO_FORM_ERROR}: no person {person} {number} present-tense form for '{slot.token}'"
        return

    slot.chosen_form = form["form"]
    slot.chosen_number = number
    slot.chosen_person = person


def inflect(slots: list[WordSlot]) -> None:
    """Resolve `.chosen_form` (and related attributes) for every slot, in place."""
    slots_by_index = {s.index: s for s in slots}

    for slot in slots:
        if slot.category in ("Noun", "Pronoun"):
            _inflect_noun_or_pronoun(slot)

    for slot in slots:
        if slot.category == "Adjective":
            _inflect_adjective(slot, slots_by_index)

    subject = next((s for s in slots if s.role == "Subject"), None)
    for slot in slots:
        if slot.category == "Verb":
            _inflect_verb(slot, subject)

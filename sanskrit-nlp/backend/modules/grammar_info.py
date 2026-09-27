"""
# SUB-TASK 3: Grammatical Information Retrieval

Given a resolved vocabulary match (from vocabulary.py), extracts the
grammatical attributes needed by the rule engine and the inflector:
gender, number, case/vibhakti (nouns, pronouns, adjectives), and
person/tense/lakara (verbs).

When the user supplied an explicit Devanagari form, these attributes come
directly from that stored form (they are grammatical facts, not guesses).
When the user supplied an English word, no specific form was chosen yet,
so number is reported as the vocabulary layer's best hint, or
"unspecified" if none is available -- the inflector (sub-task 5b) is
responsible for picking the actual form later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from modules.vocabulary import WordMatch


@dataclass
class GrammarInfo:
    """Grammatical attributes resolved for one word/token."""

    gender: Optional[str] = None
    number: str = "unspecified"
    case: Optional[str] = None
    vibhakti: Optional[str] = None
    person: Optional[int] = None
    tense: Optional[str] = None
    lakara: Optional[str] = None


def get_grammar_info(match: WordMatch) -> GrammarInfo:
    """Resolve grammatical attributes for a single vocabulary match."""
    doc: dict[str, Any] = match.word_doc
    category = doc.get("category")

    if match.matched_form is not None:
        form = match.matched_form
        if category == "Verb":
            return GrammarInfo(
                number=form.get("number", "unspecified"),
                person=form.get("person"),
                tense=form.get("tense"),
                lakara=form.get("lakara"),
            )
        # Noun / Pronoun / Adjective stored form.
        # When the same Devanagari text stores more than one case (true for
        # every neuter noun: nominative and accusative singular/dual/plural
        # are written identically), the case is not actually determined by
        # the text alone -- leave it unset so role_assigner falls back to
        # the animacy heuristic instead of "deciding" an arbitrary case.
        case = None if match.case_ambiguous else form.get("case")
        vibhakti = None if match.case_ambiguous else form.get("vibhakti")
        return GrammarInfo(
            gender=form.get("gender") or doc.get("gender"),
            number=form.get("number", "unspecified"),
            case=case,
            vibhakti=vibhakti,
            person=doc.get("person"),
        )

    # English input: no specific form chosen yet.
    if category == "Verb":
        return GrammarInfo(number=match.number_hint or "unspecified")

    return GrammarInfo(
        gender=doc.get("gender"),
        number=match.number_hint or "unspecified",
        person=doc.get("person"),
    )

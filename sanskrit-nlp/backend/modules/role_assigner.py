"""
# SUB-TASK 5a: Semantic Role Assignment

Decides which word plays which sentence role -- Subject, Object, Verb, or
Adjective -- from the category, animacy, and (when available) explicit
case of each resolved word. This runs before inflection: it decides *what*
each word is doing in the sentence, and inflector.py (5b) later decides
*which stored form* expresses that role.

Rules, in order:
1. Exactly one Verb category word -> role "Verb".
2. Pronoun category -> role "Subject".
3. Noun category: if the user gave an explicit Devanagari form, its case
   decides the role (nominative -> Subject, accusative -> Object) and
   overrides the animacy heuristic below. Otherwise: animate -> Subject,
   inanimate -> Object. With two animate nouns and no explicit case, the
   first in input order is Subject, the second is Object.
4. Adjective category -> role "Adjective", attached to the nearest noun:
   the nearest *following* noun by index, falling back to the nearest
   preceding noun if none follows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.grammar_info import GrammarInfo
from modules.vocabulary import WordMatch


@dataclass
class WordSlot:
    """One resolved input word, carrying it through the whole pipeline."""

    index: int
    token: str
    match: WordMatch
    grammar: GrammarInfo
    role: Optional[str] = None          # "Subject" | "Object" | "Verb" | "Adjective"
    modifies: Optional[int] = None      # index of the noun/pronoun this adjective modifies
    chosen_form: Optional[str] = None   # Devanagari form picked by the inflector
    chosen_case: Optional[str] = None
    chosen_vibhakti: Optional[str] = None
    chosen_number: Optional[str] = None
    chosen_gender: Optional[str] = None
    chosen_person: Optional[int] = None
    error: Optional[str] = None         # set by the inflector if no form is available

    @property
    def category(self) -> str:
        return self.match.word_doc["category"]


def assign_roles(slots: list[WordSlot]) -> None:
    """Mutate `slots` in place, setting `.role` (and `.modifies` for adjectives)."""
    for slot in slots:
        if slot.category == "Verb":
            slot.role = "Verb"

    noun_like_indices = [s.index for s in slots if s.category in ("Noun", "Pronoun")]
    assigned_subject = False

    for slot in slots:
        if slot.category != "Pronoun":
            continue
        slot.role = "Subject"
        assigned_subject = True

    for slot in slots:
        if slot.category != "Noun":
            continue

        explicit_case = slot.grammar.case  # set only when a Devanagari form was given
        if explicit_case == "nominative":
            slot.role = "Subject"
            assigned_subject = True
            continue
        if explicit_case == "accusative":
            slot.role = "Object"
            continue

        # No explicit case: use the animacy heuristic.
        animate = bool(slot.match.word_doc.get("animate"))
        if animate and not assigned_subject:
            slot.role = "Subject"
            assigned_subject = True
        elif animate:
            slot.role = "Object"
        else:
            slot.role = "Object"

    for slot in slots:
        if slot.category != "Adjective":
            continue
        slot.role = "Adjective"
        slot.modifies = _nearest_noun(slot.index, noun_like_indices)


def _nearest_noun(adj_index: int, noun_indices: list[int]) -> Optional[int]:
    """Find the nearest following noun index, or the nearest preceding one."""
    following = [i for i in noun_indices if i > adj_index]
    if following:
        return min(following)
    preceding = [i for i in noun_indices if i < adj_index]
    if preceding:
        return max(preceding)
    return None

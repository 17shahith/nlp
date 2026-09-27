"""
# SUB-TASK 1: Word Meaning Lookup (Sanskrit <-> English)

Given a single normalized token (Devanagari or English), finds the
vocabulary entry (lemma document) it belongs to, the specific inflected
form that matched (if the token was an exact Devanagari form), and the
English gloss. Never guesses: an unrecognized token returns `None`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

# English words that signal a plural noun/pronoun even though the matched
# lemma's stored alias is singular (e.g. "boys" -> lemma "बालक").
PLURAL_HINTS: set[str] = {
    "we", "us", "they", "them",
    "boys", "girls", "books", "fruits", "students", "teachers",
    "horses", "kings", "houses", "forests", "letters", "schools",
}


@dataclass
class WordMatch:
    """Result of a successful vocabulary lookup for one input token."""

    token: str
    lemma: str
    word_doc: dict[str, Any]
    matched_form: Optional[dict[str, Any]]  # exact stored form, if Devanagari input
    english: str
    direction: str  # "sa2en" (Devanagari given) or "en2sa" (English given)
    number_hint: Optional[str] = None  # "singular" | "plural", for English input
    case_ambiguous: bool = False  # True when the same Devanagari text stores >1 case
    # (e.g. neuter nouns: nominative and accusative singular are the same string)


async def _find_by_devanagari(db: AsyncIOMotorDatabase, text: str) -> Optional[WordMatch]:
    """Match a Devanagari token against stored inflected forms, then lemma text."""
    doc = await db.words.find_one({"verified": True, "forms.form": text})
    if doc:
        matching = [f for f in doc["forms"] if f["form"] == text]
        matched_form = matching[0] if matching else None
        distinct_cases = {f.get("case") for f in matching if f.get("case")}
        case_ambiguous = len(distinct_cases) > 1
        return WordMatch(
            token=text, lemma=doc["lemma"], word_doc=doc,
            matched_form=matched_form, english=doc["english"], direction="sa2en",
            case_ambiguous=case_ambiguous,
        )

    doc = await db.words.find_one({"verified": True, "lemma": text})
    if doc:
        return WordMatch(
            token=text, lemma=doc["lemma"], word_doc=doc,
            matched_form=None, english=doc["english"], direction="sa2en",
        )
    return None


async def _find_by_english(db: AsyncIOMotorDatabase, text: str) -> Optional[WordMatch]:
    """Match an English token against english_aliases, then verb conjugations."""
    doc = await db.words.find_one({"verified": True, "english_aliases": text})
    if doc:
        number_hint = "plural" if text in PLURAL_HINTS else "singular"
        return WordMatch(
            token=text, lemma=doc["lemma"], word_doc=doc,
            matched_form=None, english=doc["english"], direction="en2sa",
            number_hint=number_hint,
        )

    # verbs: also allow matching english_verb.base / .3sg / .pl directly
    doc = await db.words.find_one({
        "verified": True,
        "category": "Verb",
        "$or": [
            {"english_verb.base": text},
            {"english_verb.3sg": text},
            {"english_verb.pl": text},
        ],
    })
    if doc:
        return WordMatch(
            token=text, lemma=doc["lemma"], word_doc=doc,
            matched_form=None, english=doc["english"], direction="en2sa",
        )
    return None


async def lookup(db: AsyncIOMotorDatabase, token: str, script: str) -> Optional[WordMatch]:
    """
    Look up a single normalized token.

    `script` must be "devanagari" or "latin" (as produced by normalizer.py).
    Returns `None` if the token is not a known, verified vocabulary entry.
    """
    if script == "devanagari":
        return await _find_by_devanagari(db, token)
    return await _find_by_english(db, token)

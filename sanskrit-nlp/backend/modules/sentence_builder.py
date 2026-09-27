"""
# SUB-TASK 5c: Template Application and Sentence Construction

Arranges the inflected words (from role_assigner.py + inflector.py) into
a final Sanskrit sentence using one of two fixed templates, transliterates
it to IAST, and builds the English gloss deterministically -- by template
and lookup, never by an LLM.

Templates:
  T1: [Adjective?] Subject + [Adjective?] Object + Verb
  T2: [Adjective?] Subject + Verb                        (no object)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from modules.role_assigner import WordSlot

# --- Devanagari -> IAST transliteration -------------------------------------

_INDEP_VOWELS = {
    "अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū",
    "ऋ": "ṛ", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
}
_MATRAS = {
    "ा": "ā", "ि": "i", "ी": "ī", "ु": "u", "ू": "ū",
    "ृ": "ṛ", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
}
_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ṅ",
    "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ञ": "ñ",
    "ट": "ṭ", "ठ": "ṭh", "ड": "ḍ", "ढ": "ḍh", "ण": "ṇ",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "ś", "ष": "ṣ", "स": "s", "ह": "h",
}
_VIRAMA = "्"
_ANUSVARA = "ं"
_VISARGA = "ः"
_DANDA = "।"
_DOUBLE_DANDA = "॥"


def devanagari_to_iast(text: str) -> str:
    """Transliterate a Devanagari string into IAST, character by character."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in _CONSONANTS:
            base = _CONSONANTS[ch]
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt == _VIRAMA:
                out.append(base)
                i += 2
                continue
            if nxt in _MATRAS:
                out.append(base + _MATRAS[nxt])
                i += 2
                continue
            out.append(base + "a")
            i += 1
            continue
        if ch in _INDEP_VOWELS:
            out.append(_INDEP_VOWELS[ch])
            i += 1
            continue
        if ch == _ANUSVARA:
            out.append("ṃ")
            i += 1
            continue
        if ch == _VISARGA:
            out.append("ḥ")
            i += 1
            continue
        if ch in (_DANDA, _DOUBLE_DANDA):
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# --- English gloss construction ---------------------------------------------

_PRONOUN_ENGLISH = {
    (1, "singular"): "I", (1, "plural"): "We", (1, "dual"): "We",
    (2, "singular"): "You", (2, "plural"): "You", (2, "dual"): "You",
}


def _subject_english(slot: WordSlot) -> str:
    doc = slot.match.word_doc
    person = slot.chosen_person or doc.get("person") or 3
    number = slot.chosen_number or "singular"

    if doc["category"] == "Pronoun":
        if (person, number) in _PRONOUN_ENGLISH:
            return _PRONOUN_ENGLISH[(person, number)]
        if number in ("plural", "dual"):
            return "They"
        gender = doc.get("gender")
        return {"masculine": "He", "feminine": "She", "neuter": "It"}.get(gender, "He")

    return _noun_phrase(doc, number)


def _noun_phrase(doc: dict, number: str, adjective_english: Optional[str] = None) -> str:
    """Build 'Rama' / 'the fruit' / 'the sweet fruit' / 'the boys'."""
    base = doc["english"]
    is_proper = base[:1].isupper()
    if number == "plural" and not is_proper:
        base = base if base.endswith("s") else base + "s"
    if adjective_english:
        base = f"{adjective_english} {base}"
    if is_proper:
        return base
    return f"the {base}"


def _verb_english(verb_slot: WordSlot, subject_slot: WordSlot) -> str:
    ev = verb_slot.match.word_doc.get("english_verb") or {}
    base = ev.get("base", verb_slot.match.english)
    third_sg = ev.get("3sg", base)
    person = subject_slot.chosen_person or subject_slot.match.word_doc.get("person") or 3
    number = subject_slot.chosen_number or "singular"
    if person == 3 and number == "singular":
        return third_sg
    return base


@dataclass
class BuiltSentence:
    template: str
    sanskrit: str
    iast: str
    english: str


def build_sentence(slots: list[WordSlot]) -> BuiltSentence:
    """Apply the correct template and produce Sanskrit + IAST + English output."""
    subject = next(s for s in slots if s.role == "Subject")
    verb = next(s for s in slots if s.role == "Verb")
    objects = [s for s in slots if s.role == "Object"]
    obj = objects[0] if objects else None
    adjectives = {s.modifies: s for s in slots if s.role == "Adjective"}

    subj_adj = adjectives.get(subject.index)
    obj_adj = adjectives.get(obj.index) if obj else None

    parts: list[str] = []
    if subj_adj:
        parts.append(subj_adj.chosen_form)
    parts.append(subject.chosen_form)
    if obj is not None:
        if obj_adj:
            parts.append(obj_adj.chosen_form)
        parts.append(obj.chosen_form)
    parts.append(verb.chosen_form)

    sanskrit = " ".join(parts) + "।"
    iast = " ".join(devanagari_to_iast(p) for p in parts)
    template = "Subject + Object + Verb" if obj is not None else "Subject + Verb"

    subject_phrase = _subject_english(subject)
    verb_phrase = _verb_english(verb, subject)

    verb_doc = verb.match.word_doc
    is_motion_verb = (verb_doc.get("english_verb") or {}).get("base") == "go"

    if obj is not None:
        obj_adj_english = obj_adj.match.word_doc["english"] if obj_adj else None
        object_phrase = _noun_phrase(obj.match.word_doc, obj.chosen_number or "singular", obj_adj_english)
        if is_motion_verb:
            english = f"{subject_phrase} {verb_phrase} to {object_phrase}."
        else:
            english = f"{subject_phrase} {verb_phrase} {object_phrase}."
    else:
        english = f"{subject_phrase} {verb_phrase}."

    english = english[0].upper() + english[1:] if english else english

    return BuiltSentence(template=template, sanskrit=sanskrit, iast=iast, english=english)

"""
Input normalization.

Splits the raw comma-separated input string into clean tokens: trims
whitespace, applies Unicode NFC normalization, strips trailing danda
punctuation ("।", "॥") and periods, lowercases English tokens (Devanagari
has no case so it is left as-is), and tags each token with the script it
was written in.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

DEVANAGARI_RANGE = re.compile(r"[ऀ-ॿ]")
PUNCTUATION_STRIP = re.compile(r"[।॥.!?]+$")


@dataclass
class Token:
    """A single normalized input token."""

    raw: str          # the original text as typed (before cleanup)
    text: str         # cleaned token: NFC-normalized, punctuation stripped
    script: str       # "devanagari" or "latin"


def detect_script(text: str) -> str:
    """Return "devanagari" if the token contains any Devanagari codepoint, else "latin"."""
    return "devanagari" if DEVANAGARI_RANGE.search(text) else "latin"


def _clean(token: str) -> str:
    """NFC-normalize, strip surrounding whitespace and trailing punctuation."""
    token = unicodedata.normalize("NFC", token).strip()
    token = PUNCTUATION_STRIP.sub("", token)
    return token.strip()


def normalize(raw_input: str) -> list[Token]:
    """
    Split raw comma-separated input into a list of `Token` objects.

    Empty tokens (from stray commas or leading/trailing whitespace) are
    dropped. English tokens are lowercased; Devanagari tokens are left in
    their original case-insensitive script but still NFC-normalized.
    """
    if not raw_input or not raw_input.strip():
        return []

    pieces = [p for p in raw_input.split(",")]
    tokens: list[Token] = []
    for piece in pieces:
        raw = piece
        cleaned = _clean(piece)
        if not cleaned:
            continue
        script = detect_script(cleaned)
        text = cleaned if script == "devanagari" else cleaned.lower()
        tokens.append(Token(raw=raw.strip(), text=text, script=script))
    return tokens

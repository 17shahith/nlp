"""
# SUB-TASK 2: Word Category Classification

Trivial by design: category is stored directly on the vocabulary entry
(Noun, Verb, Adjective, Pronoun), so classification is a lookup, not an
inference. This module exists as its own step so the pipeline trace can
report it separately, matching the assignment's five sub-tasks.
"""
from __future__ import annotations

from typing import Any


def classify(word_doc: dict[str, Any]) -> str:
    """Return the grammatical category stored on a vocabulary entry."""
    return word_doc["category"]

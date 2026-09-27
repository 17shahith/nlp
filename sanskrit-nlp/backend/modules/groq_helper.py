"""
Optional Groq (LLM) helper.

Strictly limited to two jobs, neither of which ever touches the generated
Sanskrit sentence or its English meaning:

1. explain_trace(): given an already-successful pipeline trace, ask Groq
   for a short, beginner-friendly explanation of *why* the sentence is
   grammatically correct. The prompt explicitly forbids changing the
   sentence.
2. suggest_word(): given an unknown word, ask Groq to propose a
   vocabulary entry in the `words` schema. The result is validated with
   Pydantic and stored with verified=False -- it is never used by the
   deterministic pipeline until a human approves it from the Dictionary
   page.

If GROQ_API_KEY is not set, or the Groq API call fails for any reason,
both functions return a graceful fallback message/result instead of
raising, so the rest of the app keeps working.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from config import settings

_TIMEOUT_SECONDS = 15.0


def _client():
    """Lazily construct a Groq client, or return None if unavailable."""
    if not settings.groq_enabled:
        return None
    try:
        from groq import Groq  # imported lazily so the app works without the package too
        return Groq(api_key=settings.groq_api_key)
    except Exception:
        return None


async def explain_trace(trace: dict[str, Any]) -> str:
    """Return a short explanation of a successful trace, or a fallback message."""
    client = _client()
    if client is None:
        return "AI explanations are disabled (no GROQ_API_KEY configured)."
    if not trace.get("success"):
        return "Only a successful sentence can be explained."

    prompt = (
        "You are a Sanskrit grammar tutor. You will be given the JSON trace of a "
        "rule-based Sanskrit sentence generator. Explain in 3-5 short, beginner-"
        "friendly sentences WHY the generated sentence is grammatically correct "
        "(refer to vibhakti/case, gender, number, and person agreement as shown "
        "in the trace). Do not change the sentence. Explain only.\n\n"
        f"TRACE:\n{json.dumps(trace, ensure_ascii=False)}"
    )
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return f"AI explanation unavailable right now ({exc.__class__.__name__})."


async def suggest_word(unknown_word: str) -> Optional[dict[str, Any]]:
    """Ask Groq for a candidate vocabulary entry for an unknown word.

    Returns a dict matching the `words` schema (verified=False, source="groq"),
    or None if Groq is disabled/unavailable/returned something unusable.
    """
    client = _client()
    if client is None:
        return None

    schema_hint = (
        '{"lemma": "<Devanagari lemma>", "iast": "<IAST>", "english": "<English gloss>", '
        '"english_aliases": ["..."], "category": "Noun|Verb|Adjective|Pronoun", '
        '"gender": "masculine|feminine|neuter|null", "animate": true|false, '
        '"person": 1|2|3|null, "transitive": true|false|null, '
        '"english_verb": {"base": "...", "3sg": "...", "pl": "..."} or null, '
        '"forms": [{"form": "...", "case": "...", "vibhakti": "...", "number": "..."}]}'
    )
    prompt = (
        "You are a Sanskrit lexicon assistant. The word "
        f'"{unknown_word}" is not in a small rule-based Sanskrit generator\'s vocabulary. '
        "Propose a single vocabulary entry for it as a JSON object matching exactly this "
        f"shape (respond with ONLY the JSON object, no commentary): {schema_hint}"
    )
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=_TIMEOUT_SECONDS,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        data["verified"] = False
        data["source"] = "groq"
        return data
    except Exception:
        return None

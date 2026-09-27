"""
POST /api/explain        -- optional Groq explanation of a successful trace
POST /api/suggest-word   -- optional Groq suggestion for an unknown word

Both are pure add-ons: the deterministic pipeline in modules/pipeline.py
never calls either of these, and the app works fully without GROQ_API_KEY.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from db import get_db
from modules import groq_helper

router = APIRouter(prefix="/api", tags=["assist"])


class ExplainRequest(BaseModel):
    trace: dict[str, Any]


class SuggestRequest(BaseModel):
    word: str


@router.post("/explain")
async def explain(body: ExplainRequest):
    """Return a beginner-friendly explanation of a successful trace, via Groq."""
    if not settings.openai_enabled:
        raise HTTPException(status_code=503, detail="AI Assistant is not configured on this server.")
    text = await groq_helper.explain_trace(body.trace)
    return {"explanation": text}


@router.post("/suggest-word")
async def suggest_word(body: SuggestRequest):
    """Ask Groq to propose a vocabulary entry for an unknown word; store as unverified."""
    if not settings.openai_enabled:
        raise HTTPException(status_code=503, detail="AI Assistant is not configured on this server.")

    suggestion = await groq_helper.suggest_word(body.word)
    if suggestion is None:
        raise HTTPException(status_code=502, detail="Groq could not produce a usable suggestion.")

    db = get_db()
    await db.words.update_one(
        {"lemma": suggestion.get("lemma", body.word)},
        {"$set": suggestion},
        upsert=True,
    )
    return {"suggestion": suggestion}

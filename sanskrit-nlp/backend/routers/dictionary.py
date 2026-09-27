"""
Dictionary endpoints: lookup, browse, add, and manage Groq-suggested words.

GET  /api/lookup           -- meaning + category + grammar info for one word
GET  /api/words             -- paginated vocabulary listing (optional category filter)
POST /api/words             -- add a word manually (validated, verified=true)
GET  /api/words/pending      -- Groq-suggested words awaiting approval
POST /api/words/{lemma}/approve -- mark a Groq suggestion verified=true
DELETE /api/words/{lemma}   -- remove a word (used to reject a suggestion)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import get_db
from models import Word
from modules import classifier, grammar_info, normalizer
from modules.vocabulary import lookup as vocab_lookup

router = APIRouter(prefix="/api", tags=["dictionary"])


@router.get("/lookup")
async def lookup_word(q: str = Query(..., min_length=1)):
    """Look up a single Sanskrit or English word and return its full grammar info."""
    db = get_db()
    tokens = normalizer.normalize(q)
    if not tokens:
        raise HTTPException(status_code=400, detail="Empty query.")
    token = tokens[0]

    match = await vocab_lookup(db, token.text, token.script)
    if match is None:
        raise HTTPException(status_code=404, detail=f"'{token.text}' was not found in the vocabulary.")

    gi = grammar_info.get_grammar_info(match)
    word_doc = {k: v for k, v in match.word_doc.items() if k != "_id"}
    return {
        "query": q,
        "lemma": match.lemma,
        "matched_form": match.matched_form["form"] if match.matched_form else None,
        "english": match.english,
        "category": classifier.classify(match.word_doc),
        "gender": gi.gender,
        "number": gi.number,
        "case": gi.case,
        "vibhakti": gi.vibhakti,
        "person": gi.person,
        "word": word_doc,
    }


@router.get("/words")
async def list_words(
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Paginated vocabulary listing, optionally filtered by category."""
    db = get_db()
    query: dict = {"verified": True}
    if category:
        query["category"] = category

    total = await db.words.count_documents(query)
    cursor = (
        db.words.find(query, {"_id": 0})
        .sort("lemma", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [doc async for doc in cursor]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/words", status_code=201)
async def add_word(word: Word):
    """Manually add a new, immediately-verified vocabulary entry."""
    db = get_db()
    existing = await db.words.find_one({"lemma": word.lemma})
    if existing:
        raise HTTPException(status_code=409, detail=f"Lemma '{word.lemma}' already exists.")

    doc = word.model_dump()
    doc["verified"] = True
    doc["source"] = "manual"
    await db.words.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/words/{lemma}")
async def update_word(lemma: str, word: Word):
    """Update an existing vocabulary entry."""
    db = get_db()
    existing = await db.words.find_one({"lemma": lemma})
    if not existing:
        raise HTTPException(status_code=404, detail=f"No word with lemma '{lemma}'.")
    
    if lemma != word.lemma:
        conflict = await db.words.find_one({"lemma": word.lemma})
        if conflict:
            raise HTTPException(status_code=409, detail=f"Lemma '{word.lemma}' already exists.")

    doc = word.model_dump()
    doc["verified"] = True
    if "source" not in doc or not doc["source"]:
        doc["source"] = existing.get("source", "manual")
        
    await db.words.replace_one({"lemma": lemma}, doc)
    doc.pop("_id", None)
    return doc


@router.get("/words/pending")
async def list_pending_words():
    """List Groq-suggested words awaiting human approval."""
    db = get_db()
    cursor = db.words.find({"verified": False, "source": "groq"}, {"_id": 0})
    return {"items": [doc async for doc in cursor]}


@router.post("/words/{lemma}/approve")
async def approve_word(lemma: str):
    """Approve a pending Groq suggestion, making it usable by the pipeline."""
    db = get_db()
    result = await db.words.update_one({"lemma": lemma}, {"$set": {"verified": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"No word with lemma '{lemma}'.")
    return {"lemma": lemma, "verified": True}


@router.delete("/words/{lemma}")
async def delete_word(lemma: str):
    """Delete a word entry (used to reject a Groq suggestion or remove a manual entry)."""
    db = get_db()
    result = await db.words.delete_one({"lemma": lemma})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No word with lemma '{lemma}'.")
    return {"lemma": lemma, "deleted": True}

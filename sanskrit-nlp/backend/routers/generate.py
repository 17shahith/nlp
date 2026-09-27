"""POST /api/generate -- run the deterministic pipeline on user input."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from db import get_db
from models import GenerateRequest
from modules import pipeline

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate")
async def generate(body: GenerateRequest):
    """Run the full sub-task 1-6 pipeline and return the step-by-step trace."""
    db = get_db()
    trace = await pipeline.run(db, body.words)
    return trace

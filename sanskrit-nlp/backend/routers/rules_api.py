"""GET /api/rules -- list every rule the engine applies, for the Rules page."""
from __future__ import annotations

from fastapi import APIRouter

from modules.rules import RULES

router = APIRouter(prefix="/api", tags=["rules"])

_EXAMPLES = {
    "R1": "'Rama, fruit' (no verb) fails: no verb found.",
    "R2": "'play' alone fails: Subject is required. Please provide a subject, e.g., boy, play.",
    "R3": "An accusative word placed as Subject would fail this rule.",
    "R4": "An object given in the wrong case would fail this rule.",
    "R5": "'रामः, फलम्, खादन्ति' fails: singular subject, plural verb.",
    "R6": "'अहम्, फलम्, खादति' fails: 1st person subject, 3rd person verb.",
    "R7": "'boy, fruit, runs' fails: 'runs' (धाव्) is intransitive but has an object.",
    "R8": "'बालकः, सुन्दरी, खादति, फलम्' fails: feminine adjective, masculine subject.",
    "R9": "The same word cannot be both the Subject and the Object.",
    "R10": "'Rama, xyzabc, eats' fails: 'xyzabc' is not in the vocabulary.",
}


@router.get("/rules")
async def get_rules():
    """Return every rule's id, name, description, active flag, and a short example."""
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "hard": r.hard,
                "active": True,
                "example": _EXAMPLES.get(r.id, ""),
            }
            for r in RULES
        ]
    }

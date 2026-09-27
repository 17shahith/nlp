"""
Pydantic data models shared across the backend.

These models describe the vocabulary schema stored in MongoDB (Word, Form),
the public API request/response bodies (GenerateRequest, GenerateResponse),
and the internal rule-engine result type (RuleResult).
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Category = Literal["Noun", "Verb", "Adjective", "Pronoun"]
Gender = Literal["masculine", "feminine", "neuter"]
CaseName = Literal[
    "nominative", "accusative", "instrumental", "dative",
    "ablative", "genitive", "locative", "vocative",
]
Vibhakti = Literal[
    "prathama", "dvitiya", "tritiya", "chaturthi",
    "panchami", "shashthi", "saptami", "sambodhana",
]
NumberName = Literal["singular", "dual", "plural", "unspecified"]
Tense = Literal["present"]
Lakara = Literal["lat"]


class NounAdjForm(BaseModel):
    """One inflected form of a noun, pronoun, or adjective."""

    form: str
    case: CaseName
    vibhakti: Vibhakti
    number: NumberName
    gender: Optional[Gender] = None


class VerbForm(BaseModel):
    """One inflected form of a verb (present tense, lat lakara)."""

    form: str
    person: int = Field(ge=1, le=3)
    number: NumberName
    tense: Tense = "present"
    lakara: Lakara = "lat"


class EnglishVerb(BaseModel):
    """English conjugations used to build the English gloss for a verb."""

    base: str
    third_sg: str = Field(alias="3sg")
    plural: str = Field(alias="pl")

    class Config:
        populate_by_name = True


class Word(BaseModel):
    """A single vocabulary entry (lemma) with all of its stored forms."""

    lemma: str
    iast: str
    english: str
    english_aliases: list[str] = Field(default_factory=list)
    category: Category
    gender: Optional[Gender] = None
    animate: bool = False
    person: Optional[int] = None
    transitive: Optional[bool] = None
    english_verb: Optional[EnglishVerb] = None
    forms: list[dict[str, Any]] = Field(default_factory=list)
    verified: bool = True
    source: Literal["seed", "manual", "groq"] = "seed"


class GenerateRequest(BaseModel):
    """Body of POST /api/generate."""

    words: str

    @field_validator("words")
    @classmethod
    def not_none(cls, v: str) -> str:
        return v if v is not None else ""


class RuleResult(BaseModel):
    """Outcome of running a single grammar rule against the sentence context."""

    id: str
    name: str
    passed: bool
    message: str
    hard: bool = True  # hard rule failure blocks generation; soft = warning only


class MeaningStep(BaseModel):
    input: str
    sanskrit: Optional[str] = None
    english: Optional[str] = None
    found: bool = True
    reason: Optional[str] = None


class ClassificationStep(BaseModel):
    word: str
    category: Optional[str] = None


class GrammarStep(BaseModel):
    word: str
    role: Optional[str] = None
    gender: Optional[str] = None
    number: Optional[str] = None
    case: Optional[str] = None
    person: Optional[int] = None
    tense: Optional[str] = None


class OutputInfo(BaseModel):
    sanskrit: str
    iast: str
    english: str


class PipelineTrace(BaseModel):
    """Full step-by-step trace returned by POST /api/generate."""

    input: str
    steps: dict[str, Any]
    success: bool
    errors: list[str] = Field(default_factory=list)


class GenerateResponse(PipelineTrace):
    """Alias kept for API-doc clarity; identical shape to PipelineTrace."""
    pass

"""
Configuration loader.

Reads all runtime configuration from environment variables (via a local
.env file during development) and exposes it as a single, typed `Settings`
instance that the rest of the backend imports.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load variables from a .env file in the current working directory (if any).
# This must happen before we read os.environ below.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable application settings, populated once at import time."""

    mongodb_uri: str
    db_name: str
    openai_api_key: str | None
    openai_model: str
    testing: bool

    @property
    def openai_enabled(self) -> bool:
        """Whether an OpenAI API key has been configured."""
        return bool(self.openai_api_key)


def _load_settings() -> Settings:
    """Build a `Settings` object from the current process environment."""
    testing = os.getenv("TESTING", "false").lower() in {"1", "true", "yes"}
    db_name = os.getenv("DB_NAME", "sanskrit_nlp")
    if testing and not db_name.endswith("_test"):
        db_name = f"{db_name}_test"

    return Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        db_name=db_name,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        testing=testing,
    )


settings = _load_settings()

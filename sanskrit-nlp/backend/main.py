"""
FastAPI application entry point.

Mounts every router under /api, serves the plain-HTML/CSS/JS frontend as
static files, wires up CORS for local development, creates MongoDB
indexes on startup, and installs a global JSON error handler.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from config import settings
from db import close_client, ensure_indexes, get_db
from routers import assist, dictionary, generate, rules_api, tests_api

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    yield
    await close_client()


app = FastAPI(
    title="Sanskrit Vakya Nirmata",
    description="A rule-based Sanskrit sentence generation system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(dictionary.router)
app.include_router(rules_api.router)
app.include_router(tests_api.router)
app.include_router(assist.router)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})


@app.get("/api/health")
async def health():
    """Report DB reachability and whether Groq is enabled."""
    db_status = "ok"
    try:
        db = get_db()
        await db.command("ping")
    except Exception:
        db_status = "unreachable"
    return {"db": db_status, "groq": "enabled" if settings.openai_enabled else "disabled"}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

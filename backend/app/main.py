"""
OnboardAI — FastAPI application entry point.

Start the server:
    uvicorn app.main:app --reload

Interactive API docs:
    http://localhost:8000/docs
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import documents, query, topics, viewer

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure required directories exist and log resolved paths at startup."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    logging.getLogger(__name__).info(
        "startup: CHROMA_PERSIST_DIR=%s", settings.CHROMA_PERSIST_DIR,
    )
    yield


app = FastAPI(
    title="OnboardAI API",
    description="Multi-topic RAG assistant — query pre-loaded knowledge bases.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
origins = [
    "http://localhost:5173",          # Vite dev server
    "http://localhost:3000",
    "https://onboard-ai.vercel.app",  # update with your Vercel URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────
app.include_router(topics.router,    prefix="/api", tags=["Topics"])
app.include_router(query.router,     prefix="/api", tags=["Query"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(viewer.router,    prefix="/api", tags=["Viewer"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "OnboardAI API is running", "docs": "/docs", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}

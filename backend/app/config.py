"""
Config - Loads settings from .env file

Single source of truth for all configuration.  Every other module imports
`settings` from here.  TOPICS is the canonical registry of knowledge-base
topics that the app supports.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Resolve paths relative to the backend root so uvicorn and scripts always
# share the same chroma_data/ directory regardless of CWD.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _resolve_dir(env_var: str, default: str) -> str:
    """Return an absolute path for a directory setting."""
    raw = os.getenv(env_var, default)
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str((_BACKEND_ROOT / p).resolve())


# ── Knowledge-base topic registry ────────────────────────────
# Each key is the topic ID used in API requests and as the ChromaDB
# collection name.  Keep IDs lowercase-kebab-case.

TOPICS: dict[str, dict] = {
    "employee-handbook": {
        "name":        "GitLab Employee Handbook",
        "icon":        "📋",
        "description": "GitLab's public company handbook — PTO, benefits, values, spending policies, onboarding",
    },
    "franchise-ops": {
        "name":        "Chick-fil-A Franchise Manual",
        "icon":        "🏪",
        "description": "Chick-fil-A's 2022 franchise operations manual — daily procedures, food safety, customer service, training",
    },
    "real-estate": {
        "name":        "HUD Fair Housing Act Manual",
        "icon":        "🏠",
        "description": "HUD's Fair Housing Act design manual — protected classes, accessibility standards, compliance requirements",
    },
    "sba-tax": {
        "name":        "SBA Small Business Tax Guide",
        "icon":        "💼",
        "description": "SBA.gov guides on small business taxes — structures, deductions, deadlines, filing requirements",
    },
    "supabase-docs": {
        "name":        "Supabase Developer Docs",
        "icon":        "⚡",
        "description": "Supabase official docs — database, auth, storage, edge functions, migrations",
    },
}


class Settings:
    # OpenAI
    OPENAI_API_KEY: str  = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL: str       = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # ChromaDB — always absolute so server + scripts share the same store.
    # Each topic maps to a collection of the same name inside this directory.
    CHROMA_PERSIST_DIR: str = _resolve_dir("CHROMA_PERSIST_DIR", "chroma_data")

    # Chunking
    CHUNK_SIZE: int    = int(os.getenv("CHUNK_SIZE",    "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # Retrieval
    TOP_K: int                  = int(os.getenv("TOP_K",                "5"))
    RELEVANCE_THRESHOLD: float  = float(os.getenv("RELEVANCE_THRESHOLD", "0.2"))

    # File upload — always absolute
    UPLOAD_DIR: str       = _resolve_dir("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

    # Topic registry (convenience alias)
    TOPICS: dict[str, dict] = TOPICS


settings = Settings()

#!/usr/bin/env python3
"""
Ingest Supabase documentation pages into the 'supabase-docs' ChromaDB collection.

Can be run standalone or imported and called via run().

Usage (from the backend/ directory):
    python scripts/ingest_supabase_docs.py [--force]

Environment:
    Requires OPENAI_API_KEY in .env
"""

import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.config import settings
from app.services.chunker import chunk_document
from app.services.document_processor import ProcessedDocument
from app.services.embeddings import embed_texts
from app.services.vector_store import add_chunks, delete_by_filename, get_collection_stats

COLLECTION = "supabase-docs"

_GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/supabase/supabase/master/apps/docs/content/"
)

SOURCE_DOCS_DIR = BACKEND_DIR / "source_docs" / COLLECTION

SUPABASE_DOCS: list[dict] = [
    {"filename": "supabase_overview.md",             "path": "guides/getting-started/features.mdx",                       "section": "Overview & Features"},
    {"filename": "supabase_database.md",             "path": "guides/database/overview.mdx",                              "section": "Database"},
    {"filename": "supabase_auth.md",                 "path": "guides/auth/overview.mdx",                                  "section": "Authentication"},
    {"filename": "supabase_storage.md",              "path": "guides/storage/overview.mdx",                               "section": "Storage"},
    {"filename": "supabase_edge_functions.md",       "path": "guides/functions/overview.mdx",                             "section": "Edge Functions"},
    {"filename": "supabase_realtime.md",             "path": "guides/realtime/overview.mdx",                              "section": "Realtime"},
    {"filename": "supabase_cli.md",                  "path": "guides/cli/getting-started.mdx",                            "section": "CLI"},
    {"filename": "supabase_self_hosting.md",         "path": "guides/self-hosting/overview.mdx",                          "section": "Self-Hosting"},
    {"filename": "supabase_row_level_security.md",   "path": "guides/database/postgres/row-level-security.mdx",           "section": "Row Level Security"},
    {"filename": "supabase_migrations.md",           "path": "guides/deployment/database-migrations.mdx",                 "section": "Database Migrations"},
]


def fetch_url(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OnboardAI-Ingestor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def clean_mdx(raw: str) -> str:
    """Strip MDX frontmatter, imports, and JSX tags."""
    raw = re.sub(r"^---\s*\n.*?\n---\s*\n", "", raw, flags=re.DOTALL)
    raw = re.sub(r"^\s*(import|export)\s+.*$", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"<[A-Z][^>]*/\s*>", "", raw)
    raw = re.sub(r"<([A-Z][A-Za-z]*)[^>]*>", "", raw)
    raw = re.sub(r"</[A-Z][A-Za-z]*>", "", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def ingest_doc(filename: str, text: str, section: str, source_path: str = "") -> dict:
    """Chunk, embed, and store one document into COLLECTION."""
    import hashlib
    delete_by_filename(filename, collection_name=COLLECTION)
    doc_id = hashlib.md5(f"{COLLECTION}:{filename}".encode()).hexdigest()[:8]
    uploaded_at = datetime.now(timezone.utc).isoformat()
    word_count = len(text.split())

    processed = ProcessedDocument(
        text=text,
        metadata={
            "filename":   filename,
            "file_type":  ".md",
            "char_count": len(text),
            "word_count": word_count,
        },
    )
    chunks = chunk_document(
        processed,
        doc_id=doc_id,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
        uploaded_at=uploaded_at,
        source_path=source_path,
    )
    if not chunks:
        return {"filename": filename, "chunk_count": 0, "word_count": word_count, "status": "empty"}

    embeddings = embed_texts([c.text for c in chunks])
    add_chunks(chunks, embeddings, collection_name=COLLECTION)
    return {"filename": filename, "chunk_count": len(chunks), "word_count": word_count, "status": "ok"}


def run(force: bool = False) -> dict:
    """
    Ingest all SUPABASE_DOCS into the 'supabase-docs' collection.

    Returns a result dict with status, files ingested, total_chunks, and failures.
    Skips if the collection already has data unless force=True.
    """
    stats = get_collection_stats(COLLECTION)
    if stats["doc_count"] > 0 and not force:
        return {"topic": COLLECTION, "status": "skipped",
                "reason": f"already has {stats['doc_count']} docs"}

    results: list[dict] = []
    failed: list[str] = []

    os.makedirs(SOURCE_DOCS_DIR, exist_ok=True)

    for doc in SUPABASE_DOCS:
        url = _GITHUB_RAW_BASE + doc["path"]
        print(f"  Fetching  {doc['filename']} …", end=" ", flush=True)
        try:
            raw  = fetch_url(url)
            text = clean_mdx(raw)
            if len(text.split()) < 30:
                print("SKIPPED (too little text after cleaning)")
                failed.append(doc["filename"])
                continue
            # Save the cleaned markdown so the viewer can serve it
            dest = SOURCE_DOCS_DIR / doc["filename"]
            dest.write_text(text, encoding="utf-8")
            r = ingest_doc(doc["filename"], text, doc["section"], source_path=str(dest))
            print(f"OK — {r['chunk_count']} chunks")
            results.append(r)
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code} — skipping")
            failed.append(doc["filename"])
        except Exception as exc:
            print(f"ERROR: {exc} — skipping")
            failed.append(doc["filename"])

    total_chunks = sum(r["chunk_count"] for r in results)
    return {
        "topic":        COLLECTION,
        "status":       "ok" if results else "error",
        "files":        len(results),
        "total_chunks": total_chunks,
        "failed":       len(failed),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Ingest Supabase docs into ChromaDB.")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if collection has data")
    args = parser.parse_args()

    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set. Add it to backend/.env.")
        sys.exit(1)

    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    print(f"Ingesting {len(SUPABASE_DOCS)} Supabase docs → collection '{COLLECTION}'\n")

    result = run(force=args.force)
    print(f"\n── Result ───────────────────────────")
    if result["status"] == "skipped":
        print(f"  Skipped — {result['reason']}.  Use --force to re-ingest.")
    elif result["status"] == "ok":
        print(f"  Ingested {result['files']} files, {result['total_chunks']} total chunks")
        if result.get("failed"):
            print(f"  {result['failed']} file(s) skipped (see errors above)")
    else:
        print(f"  ERROR — no files ingested")


if __name__ == "__main__":
    main()

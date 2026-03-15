#!/usr/bin/env python3
"""
Ingest all pre-loaded demo topics into their respective ChromaDB collections.

Usage (from the backend/ directory):
    python scripts/ingest_demos.py --all [--force]
    python scripts/ingest_demos.py --topic supabase-docs [--force]
    python scripts/ingest_demos.py --topic employee-handbook --force

Topics:
    employee-handbook   GitLab Employee Handbook (sparse git clone)
    franchise-ops       Chick-Fil-A 2022 PDF (test_docs/)
    real-estate         NAR Fair Housing PDF (test_docs/)
    sba-tax             SBA.gov Small Business Tax Guide (HTTP)
    supabase-docs       Supabase GitHub docs (HTTP)

Environment:
    Requires OPENAI_API_KEY in .env
"""

import argparse
import hashlib
import html.parser
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
from app.services.document_processor import ProcessedDocument, process_file
from app.services.embeddings import embed_texts
from app.services.vector_store import (
    add_chunks,
    delete_by_filename,
    get_collection_stats,
)

TEST_DOCS_DIR  = BACKEND_DIR / "test_docs"
SOURCE_DOCS_DIR = BACKEND_DIR / "source_docs"

# ── Common utilities ──────────────────────────────────────────


def _already_has_data(collection: str) -> bool:
    stats = get_collection_stats(collection)
    return stats["doc_count"] > 0


def _embed_and_store(chunks: list, collection: str) -> int:
    """Embed chunks in batches of 50, store each batch, return total stored."""
    total = 0
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = embed_texts([c.text for c in batch])
        add_chunks(batch, embeddings, collection_name=collection)
        total += len(batch)
        if len(chunks) > batch_size:
            print(f"    … {total}/{len(chunks)} chunks embedded", flush=True)
    return total


def _save_source_text(text: str, collection: str, filename: str) -> str:
    """
    Write `text` to source_docs/{collection}/{filename} and return the path.
    The filename is used as-is (caller is responsible for the extension).
    """
    dest = SOURCE_DOCS_DIR / collection / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return str(dest)


def _ingest_text(
    text: str,
    filename: str,
    collection: str,
    file_type: str = ".md",
    source_path: str = "",
) -> dict:
    """Chunk, embed, and store a plain text string. Returns result dict."""
    delete_by_filename(filename, collection_name=collection)
    doc_id = hashlib.md5(f"{collection}:{filename}".encode()).hexdigest()[:8]
    uploaded_at = datetime.now(timezone.utc).isoformat()
    word_count = len(text.split())

    processed = ProcessedDocument(
        text=text,
        metadata={
            "filename": filename,
            "file_type": file_type,
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

    stored = _embed_and_store(chunks, collection)
    return {"filename": filename, "chunk_count": stored, "word_count": word_count, "status": "ok"}


def _ingest_file(file_path: Path, collection: str) -> dict:
    """Extract text from a file on disk, copy to source_docs/, chunk, embed, and store."""
    filename = file_path.name

    # Copy to source_docs so the viewer can serve it later
    dest = SOURCE_DOCS_DIR / collection / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(file_path), str(dest))
    source_path = str(dest)

    delete_by_filename(filename, collection_name=collection)
    doc_id = hashlib.md5(f"{collection}:{filename}".encode()).hexdigest()[:8]
    uploaded_at = datetime.now(timezone.utc).isoformat()

    processed = process_file(str(file_path))
    if len(processed.text.split()) < 50:
        return {"filename": filename, "chunk_count": 0, "word_count": 0, "status": "empty"}

    chunks = chunk_document(
        processed,
        doc_id=doc_id,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
        uploaded_at=uploaded_at,
        source_path=source_path,
    )
    if not chunks:
        return {"filename": filename, "chunk_count": 0, "word_count": len(processed.text.split()), "status": "empty"}

    print(f"    {len(chunks)} chunks to embed …", flush=True)
    stored = _embed_and_store(chunks, collection)
    return {
        "filename": filename,
        "chunk_count": stored,
        "word_count": len(processed.text.split()),
        "status": "ok",
    }


def _fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OnboardAI-Ingestor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ── HTML stripping ────────────────────────────────────────────


class _TextExtractor(html.parser.HTMLParser):
    """Minimal HTML → plain text extractor using stdlib only."""

    _SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        raw = "\n".join(self._parts)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _strip_html(html_text: str) -> str:
    parser = _TextExtractor()
    parser.feed(html_text)
    return parser.get_text()


# ── Topic: employee-handbook ──────────────────────────────────

_GITLAB_HANDBOOK_BASE = "https://gitlab.com/gitlab-com/content-sites/handbook.git"

_HANDBOOK_SECTIONS = [
    "content/handbook/values",
    "content/handbook/communication",
    "content/handbook/paid-time-off",
    "content/handbook/benefits",
    "content/handbook/people-group/onboarding",
    "content/handbook/people-group/code-of-conduct",
    "content/handbook/finance/travel",
    "content/handbook/spending-company-money",
]

_HANDBOOK_COLLECTION = "employee-handbook"


def _strip_hugo_frontmatter(text: str) -> str:
    """Remove TOML/YAML frontmatter and Hugo shortcodes."""
    # YAML frontmatter (--- ... ---)
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    # TOML frontmatter (+++ ... +++)
    text = re.sub(r"^\+\+\+\s*\n.*?\n\+\+\+\s*\n", "", text, flags=re.DOTALL)
    # Hugo shortcodes {{< ... >}} and {{% ... %}}
    text = re.sub(r"\{\{[<%].*?[>%]\}\}", "", text, flags=re.DOTALL)
    # Excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ingest_employee_handbook(force: bool = False) -> dict:
    collection = _HANDBOOK_COLLECTION
    if _already_has_data(collection) and not force:
        return {"topic": collection, "status": "skipped", "reason": "already has data"}

    if not shutil.which("git"):
        return {"topic": collection, "status": "error", "reason": "git not found on PATH"}

    tmpdir = tempfile.mkdtemp(prefix="onboardai-handbook-")
    try:
        print(f"  Cloning GitLab handbook (sparse) …", flush=True)
        result = subprocess.run(
            [
                "git", "clone",
                "--no-checkout",
                "--depth=1",
                "--filter=blob:none",
                _GITLAB_HANDBOOK_BASE,
                tmpdir,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip()
            return {"topic": collection, "status": "error", "reason": f"git clone failed: {msg}"}

        # Configure sparse checkout
        subprocess.run(
            ["git", "-C", tmpdir, "sparse-checkout", "init", "--cone"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", tmpdir, "sparse-checkout", "set"] + _HANDBOOK_SECTIONS,
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", tmpdir, "checkout"],
            capture_output=True, check=True, timeout=60,
        )

        # Find and ingest all .md / .html.md files
        md_files = list(Path(tmpdir).rglob("*.md"))
        if not md_files:
            return {"topic": collection, "status": "error", "reason": "no markdown files found after sparse checkout"}

        print(f"  Found {len(md_files)} markdown files", flush=True)
        results: list[dict] = []
        failed: list[str] = []

        for md_path in md_files:
            try:
                raw = md_path.read_text(encoding="utf-8", errors="replace")
                text = _strip_hugo_frontmatter(raw)
                if len(text.split()) < 30:
                    continue
                rel = str(md_path.relative_to(tmpdir))
                filename = rel.replace("/", "__") + ".md"
                # Save original (raw) markdown to source_docs so the viewer can serve it
                src_path = _save_source_text(raw, collection, filename)
                print(f"    {filename[:60]} …", end=" ", flush=True)
                r = _ingest_text(text, filename, collection, source_path=src_path)
                print(f"OK — {r['chunk_count']} chunks")
                if r["status"] == "ok":
                    results.append(r)
                else:
                    failed.append(filename)
            except Exception as exc:
                print(f"ERROR: {exc}")
                failed.append(str(md_path.name))

        total_chunks = sum(r["chunk_count"] for r in results)
        return {
            "topic": collection,
            "status": "ok" if results else "error",
            "files": len(results),
            "total_chunks": total_chunks,
            "failed": len(failed),
        }
    except subprocess.TimeoutExpired:
        return {"topic": collection, "status": "error", "reason": "git clone timed out"}
    except Exception as exc:
        return {"topic": collection, "status": "error", "reason": str(exc)}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Topic: franchise-ops ──────────────────────────────────────

_FRANCHISE_PDF = TEST_DOCS_DIR / "Chick-Fil-A-2022.pdf"
_FRANCHISE_COLLECTION = "franchise-ops"


def ingest_franchise_ops(force: bool = False) -> dict:
    collection = _FRANCHISE_COLLECTION
    if _already_has_data(collection) and not force:
        return {"topic": collection, "status": "skipped", "reason": "already has data"}

    if not _FRANCHISE_PDF.exists():
        return {
            "topic": collection,
            "status": "error",
            "reason": f"PDF not found: {_FRANCHISE_PDF}",
        }

    print(f"  Processing {_FRANCHISE_PDF.name} …", flush=True)
    try:
        r = _ingest_file(_FRANCHISE_PDF, collection)
        if r["status"] == "ok":
            return {
                "topic": collection,
                "status": "ok",
                "files": 1,
                "total_chunks": r["chunk_count"],
                "failed": 0,
            }
        else:
            return {"topic": collection, "status": "error", "reason": f"file produced no chunks: {_FRANCHISE_PDF.name}"}
    except Exception as exc:
        return {"topic": collection, "status": "error", "reason": str(exc)}


# ── Topic: real-estate ────────────────────────────────────────

_REAL_ESTATE_PDF = TEST_DOCS_DIR / "fairfull.pdf"
_REAL_ESTATE_COLLECTION = "real-estate"


def ingest_real_estate(force: bool = False) -> dict:
    collection = _REAL_ESTATE_COLLECTION
    if _already_has_data(collection) and not force:
        return {"topic": collection, "status": "skipped", "reason": "already has data"}

    if not _REAL_ESTATE_PDF.exists():
        return {
            "topic": collection,
            "status": "error",
            "reason": f"PDF not found: {_REAL_ESTATE_PDF}",
        }

    print(f"  Processing {_REAL_ESTATE_PDF.name} …", flush=True)
    try:
        r = _ingest_file(_REAL_ESTATE_PDF, collection)
        if r["status"] == "ok":
            return {
                "topic": collection,
                "status": "ok",
                "files": 1,
                "total_chunks": r["chunk_count"],
                "failed": 0,
            }
        else:
            return {"topic": collection, "status": "error", "reason": f"file produced no chunks: {_REAL_ESTATE_PDF.name}"}
    except Exception as exc:
        return {"topic": collection, "status": "error", "reason": str(exc)}


# ── Topic: sba-tax ────────────────────────────────────────────

_SBA_COLLECTION = "sba-tax"

_SBA_PAGES: list[dict] = [
    {
        "filename": "sba_business_guide.html",
        "url": "https://www.sba.gov/business-guide/launch-your-business/get-federal-state-tax-id-numbers",
        "section": "Tax ID Numbers",
    },
    {
        "filename": "sba_pay_taxes.html",
        "url": "https://www.sba.gov/business-guide/manage-your-business/pay-taxes",
        "section": "Pay Taxes",
    },
    {
        "filename": "sba_choose_structure.html",
        "url": "https://www.sba.gov/business-guide/launch-your-business/choose-business-structure",
        "section": "Business Structure",
    },
    {
        "filename": "sba_register_business.html",
        "url": "https://www.sba.gov/business-guide/launch-your-business/register-your-business",
        "section": "Register Your Business",
    },
    {
        "filename": "sba_fund_business.html",
        "url": "https://www.sba.gov/business-guide/plan-your-business/fund-your-business",
        "section": "Fund Your Business",
    },
]


def ingest_sba_tax(force: bool = False) -> dict:
    collection = _SBA_COLLECTION
    if _already_has_data(collection) and not force:
        return {"topic": collection, "status": "skipped", "reason": "already has data"}

    results: list[dict] = []
    failed: list[str] = []

    for page in _SBA_PAGES:
        print(f"  Fetching {page['filename']} …", end=" ", flush=True)
        try:
            raw_html = _fetch_url(page["url"])
            text = _strip_html(raw_html)
            if len(text.split()) < 30:
                print("SKIPPED (too little text after stripping)")
                failed.append(page["filename"])
                continue
            # Save stripped text as .md (clean, readable in viewer)
            md_filename = Path(page["filename"]).stem + ".md"
            src_path = _save_source_text(text, collection, md_filename)
            r = _ingest_text(text, page["filename"], collection,
                             file_type=".html", source_path=src_path)
            print(f"OK — {r['chunk_count']} chunks")
            if r["status"] == "ok":
                results.append(r)
            else:
                failed.append(page["filename"])
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code} — skipping")
            failed.append(page["filename"])
        except Exception as exc:
            print(f"ERROR: {exc} — skipping")
            failed.append(page["filename"])

    if not results:
        return {
            "topic": collection,
            "status": "error",
            "reason": f"all {len(_SBA_PAGES)} SBA pages failed to fetch",
        }

    total_chunks = sum(r["chunk_count"] for r in results)
    return {
        "topic": collection,
        "status": "ok",
        "files": len(results),
        "total_chunks": total_chunks,
        "failed": len(failed),
    }


# ── Topic: supabase-docs ──────────────────────────────────────

def ingest_supabase_docs(force: bool = False) -> dict:
    import scripts.ingest_supabase_docs as _supabase_mod
    return _supabase_mod.run(force=force)


# ── Dispatcher ────────────────────────────────────────────────

_TOPIC_HANDLERS: dict[str, callable] = {
    "employee-handbook": ingest_employee_handbook,
    "franchise-ops":     ingest_franchise_ops,
    "real-estate":       ingest_real_estate,
    "sba-tax":           ingest_sba_tax,
    "supabase-docs":     ingest_supabase_docs,
}


def _print_result(result: dict) -> None:
    topic = result.get("topic", "?")
    status = result.get("status", "?")
    if status == "skipped":
        print(f"  [{topic}] SKIPPED — {result.get('reason', '')}.  Use --force to re-ingest.")
    elif status == "ok":
        files = result.get("files", "?")
        chunks = result.get("total_chunks", "?")
        failed = result.get("failed", 0)
        print(f"  [{topic}] OK — {files} file(s), {chunks} total chunks", end="")
        if failed:
            print(f", {failed} skipped", end="")
        print()
    else:
        reason = result.get("reason", "unknown error")
        print(f"  [{topic}] ERROR — {reason}")


# ── CLI ───────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest demo topics into ChromaDB collections.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {k}" for k in _TOPIC_HANDLERS),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Ingest all topics")
    group.add_argument("--topic", choices=list(_TOPIC_HANDLERS), metavar="TOPIC",
                       help=f"Topic to ingest: {{{', '.join(_TOPIC_HANDLERS)}}}")
    parser.add_argument("--force", action="store_true",
                        help="Re-ingest even if collection already has data")
    args = parser.parse_args()

    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set. Add it to backend/.env.")
        sys.exit(1)

    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    topics_to_run = list(_TOPIC_HANDLERS) if args.all else [args.topic]

    all_results: list[dict] = []
    for topic_id in topics_to_run:
        handler = _TOPIC_HANDLERS[topic_id]
        print(f"\n── {topic_id} {'─' * max(0, 40 - len(topic_id))}")
        try:
            result = handler(force=args.force)
        except Exception as exc:
            result = {"topic": topic_id, "status": "error", "reason": str(exc)}
        _print_result(result)
        all_results.append(result)

    if len(all_results) > 1:
        print("\n── Summary ──────────────────────────────")
        ok      = [r for r in all_results if r["status"] == "ok"]
        skipped = [r for r in all_results if r["status"] == "skipped"]
        errors  = [r for r in all_results if r["status"] == "error"]
        total_chunks = sum(r.get("total_chunks", 0) for r in ok)
        print(f"  OK:      {len(ok)} topic(s), {total_chunks} total chunks")
        if skipped:
            print(f"  Skipped: {len(skipped)} topic(s)")
        if errors:
            print(f"  Errors:  {len(errors)} topic(s) — {[r['topic'] for r in errors]}")


if __name__ == "__main__":
    main()

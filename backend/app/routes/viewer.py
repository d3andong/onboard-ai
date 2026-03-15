"""
Document viewer endpoints.

GET /api/chunks/{chunk_id}/context  — chunk text + surrounding context chunks
GET /api/documents/{doc_id}/raw     — serve the original source file
"""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from app.config import TOPICS
from app.models import ChunkContextDocument, ChunkContextResponse
from app.services.vector_store import (
    get_chunk_by_id,
    get_chunks_by_doc_and_indices,
    get_doc_source_path,
)

router = APIRouter()

# How many adjacent chunks to gather for before/after context
_CONTEXT_NEIGHBORS = 3


def _validate_topic(topic: str) -> None:
    if topic not in TOPICS:
        valid = ", ".join(TOPICS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{topic}'. Valid topics: {valid}",
        )


# ── Overlap deduplication ─────────────────────────────────────

def _strip_tail_overlap(context: str, chunk_text: str,
                        max_n: int = 200, min_n: int = 10) -> str:
    """
    Remove any trailing portion of `context` that duplicates the beginning
    of `chunk_text` (caused by the chunker's overlap window).

    Tries lengths from max_n down to min_n; stops at the first exact match.
    """
    upper = min(max_n, len(context), len(chunk_text))
    for n in range(upper, min_n - 1, -1):
        if context[-n:] == chunk_text[:n]:
            return context[:-n].rstrip()
    return context


def _strip_head_overlap(context: str, chunk_text: str,
                        max_n: int = 200, min_n: int = 10) -> str:
    """
    Remove any leading portion of `context` that duplicates the end of
    `chunk_text` (caused by the chunker's overlap window).
    """
    upper = min(max_n, len(context), len(chunk_text))
    for n in range(upper, min_n - 1, -1):
        if context[:n] == chunk_text[-n:]:
            return context[n:].lstrip()
    return context


# ── Context trimming with sentence-boundary awareness ─────────

def _trim_context_before(text: str, max_chars: int) -> str:
    """
    Trim `text` to the last `max_chars` characters, then advance forward to
    the first sentence-start boundary so context_before never starts
    mid-sentence.

    A sentence boundary is recognised as:
      - ". " followed by an uppercase letter
      - A newline followed by a non-whitespace character
    """
    if not text or max_chars <= 0:
        return ""
    if len(text) > max_chars:
        text = text[-max_chars:]

    # Find first clean sentence start
    match = re.search(r'(?<=\. )[A-Z]|(?<=\n)\S', text)
    if match:
        return text[match.start():]
    return text


def _trim_context_after(text: str, max_chars: int) -> str:
    """
    Trim `text` to the first `max_chars` characters, then cut back to the
    last sentence-end boundary so context_after never ends mid-sentence.

    A sentence end is the last ". " or ".\n" in the truncated text.
    If neither is found, returns the truncated text as-is (avoids losing
    all context on chunks without periods).
    """
    if not text or max_chars <= 0:
        return ""
    if len(text) > max_chars:
        text = text[:max_chars]

    # Find last sentence end
    end_dot_space = text.rfind(". ")
    end_dot_nl    = text.rfind(".\n")
    idx = max(end_dot_space, end_dot_nl)
    if idx >= 0:
        return text[:idx + 1]
    return text


# ── Markdown rendering ────────────────────────────────────────

def _strip_md_frontmatter(text: str) -> str:
    """Strip YAML/TOML frontmatter delimited by --- or +++ at the top."""
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^\+\+\+\s*\n.*?\n\+\+\+\s*\n", "", text, flags=re.DOTALL)
    return text


def _markdown_to_html(title: str, md_text: str) -> str:
    """Convert markdown to a self-contained HTML page with clean styling."""
    md_text = _strip_md_frontmatter(md_text)

    try:
        import markdown as md_lib
        body = md_lib.markdown(md_text, extensions=["fenced_code", "tables"])
    except ImportError:
        import html
        body = f"<pre>{html.escape(md_text)}</pre>"

    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, system-ui, sans-serif;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px 40px;
      line-height: 1.7;
      color: #1a1a1a;
      overflow-x: hidden;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }}
    h1, h2, h3, h4, h5, h6 {{
      margin-top: 1.6em;
      margin-bottom: 0.4em;
      line-height: 1.3;
    }}
    p {{ margin: 0.75em 0; }}
    a {{ color: #0066cc; }}
    pre {{
      background: #f5f5f5;
      padding: 1rem;
      border-radius: 6px;
      overflow-x: auto;     /* only code blocks scroll horizontally */
      white-space: pre;
    }}
    code {{
      background: #f0f0f0;
      padding: .15em .4em;
      border-radius: 3px;
      font-size: .88em;
    }}
    pre code {{
      background: none;
      padding: 0;
      font-size: .88em;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1em 0;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: .5rem .75rem;
      text-align: left;
    }}
    th {{ background: #f5f5f5; font-weight: 600; }}
    blockquote {{
      margin: 1em 0;
      padding: .5em 1em;
      border-left: 4px solid #ddd;
      color: #555;
    }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


# ── GET /api/chunks/{chunk_id}/context ───────────────────────

@router.get("/chunks/{chunk_id}/context", response_model=ChunkContextResponse)
async def get_chunk_context(
    chunk_id: str,
    topic: str = Query(..., description="Topic ID (ChromaDB collection)"),
    context_chars: int = Query(default=2000, ge=0, le=10000,
                               description="Max characters of context before/after"),
):
    """
    Return a chunk with surrounding context assembled from adjacent chunks in
    the same document.

    Context is built by fetching up to 3 chunks before and after the target
    chunk (by chunk_index).  Overlap introduced by the chunker's sliding
    window is removed before the context is returned.  Both context strings
    are then trimmed to `context_chars` at sentence boundaries.
    """
    _validate_topic(topic)

    chunk = get_chunk_by_id(chunk_id, topic)
    if chunk is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chunk '{chunk_id}' not found in topic '{topic}'.",
        )

    meta        = chunk["metadata"]
    chunk_text  = chunk["text"]
    doc_id      = meta.get("doc_id", "")
    chunk_index = int(meta.get("chunk_index", 0))
    total_chunks = int(meta.get("total_chunks", 0))

    # Determine neighbor index ranges
    before_indices = list(range(max(0, chunk_index - _CONTEXT_NEIGHBORS), chunk_index))
    if total_chunks > 0:
        after_indices = list(range(
            chunk_index + 1,
            min(total_chunks, chunk_index + _CONTEXT_NEIGHBORS + 1),
        ))
    else:
        after_indices = list(range(chunk_index + 1, chunk_index + _CONTEXT_NEIGHBORS + 1))

    all_neighbor_indices = before_indices + after_indices
    neighbors = (
        get_chunks_by_doc_and_indices(doc_id, all_neighbor_indices, topic)
        if all_neighbor_indices else {}
    )

    # ── context_before ────────────────────────────────────────
    before_parts = [neighbors[i]["text"] for i in sorted(before_indices) if i in neighbors]
    raw_before = "\n\n".join(before_parts)

    # Remove overlap between the end of context_before and start of chunk_text
    raw_before = _strip_tail_overlap(raw_before, chunk_text)

    # Trim to requested length, starting at a clean sentence boundary
    context_before = _trim_context_before(raw_before, context_chars)

    # ── context_after ─────────────────────────────────────────
    after_parts = [neighbors[i]["text"] for i in sorted(after_indices) if i in neighbors]
    raw_after = "\n\n".join(after_parts)

    # Remove overlap between the end of chunk_text and start of context_after
    raw_after = _strip_head_overlap(raw_after, chunk_text)

    # Trim to requested length, ending at a clean sentence boundary
    context_after = _trim_context_after(raw_after, context_chars)

    return ChunkContextResponse(
        chunk_id=chunk_id,
        chunk_text=chunk_text,
        context_before=context_before,
        context_after=context_after,
        document=ChunkContextDocument(
            doc_id=doc_id,
            filename=meta.get("filename", ""),
            file_type=meta.get("file_type", ""),
            page_number=None,  # not tracked in current metadata
        ),
        section=meta.get("section") or None,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
    )


# ── GET /api/documents/{doc_id}/raw ──────────────────────────

@router.get("/documents/{doc_id}/raw")
async def get_document_raw(
    doc_id: str,
    topic: str = Query(..., description="Topic ID (ChromaDB collection)"),
):
    """
    Serve the original source file for a document.

    - PDF   → Content-Type: application/pdf, displayed inline
    - .md   → Frontmatter stripped, converted to styled HTML
    - .html → Served as text/html
    - .txt  → Served as text/plain
    """
    _validate_topic(topic)

    source_path = get_doc_source_path(doc_id, topic)
    if not source_path:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No source file recorded for document '{doc_id}' in topic '{topic}'. "
                "Re-ingest with the latest script to populate source_path metadata."
            ),
        )

    path = Path(source_path)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Source file '{path.name}' is recorded but no longer exists on disk.",
        )

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return FileResponse(
            path=str(path),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{path.name}"'},
        )

    content = path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".md":
        return HTMLResponse(content=_markdown_to_html(path.stem, content))

    if suffix == ".html":
        return HTMLResponse(content=content)

    return PlainTextResponse(content=content)

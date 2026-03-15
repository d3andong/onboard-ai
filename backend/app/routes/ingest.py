"""
POST /api/ingest — Upload and index one or more documents.

Flow per file:
  1. Validate file type and size.
  2. De-duplicate: if a document with the same filename already exists,
     remove its old chunks before re-indexing.
  3. Save the raw file to UPLOAD_DIR.
  4. Extract text via document_processor.
  5. Split into chunks via chunker.
  6. Embed chunks via embeddings.
  7. Store in ChromaDB via vector_store.
"""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models import IngestBatchResponse, IngestResponse
from app.services.chunker import chunk_document
from app.services.document_processor import process_file
from app.services.embeddings import embed_texts
from app.services.vector_store import add_chunks, delete_by_filename
from app.utils.file_helpers import (
    get_upload_path,
    validate_extension,
    validate_size,
)

router = APIRouter()


@router.post("/ingest", response_model=IngestBatchResponse)
async def ingest_files(files: list[UploadFile] = File(...)):
    """
    Accept one or more files (PDF, DOCX, MD, TXT), process them, and add
    them to the vector index.

    Returns a summary for each file: doc_id, chunk_count, word_count.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    results: list[IngestResponse] = []

    for upload in files:
        filename = upload.filename or "unknown"

        # ── 1. Validate extension ────────────────────────────
        try:
            validate_extension(filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        # ── 2. Read + validate size ──────────────────────────
        content = await upload.read()
        try:
            validate_size(content)
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc))

        # ── 3. De-duplicate (same filename → re-index) ───────
        delete_by_filename(filename)

        # ── 4. Persist to disk ───────────────────────────────
        doc_id = uuid.uuid4().hex[:8]
        save_path = get_upload_path(doc_id, filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(save_path, "wb") as fh:
            fh.write(content)

        # ── 5–7. Process → Chunk → Embed → Store ─────────────
        try:
            uploaded_at = datetime.now(timezone.utc).isoformat()

            processed = process_file(save_path)

            chunks = chunk_document(
                processed,
                doc_id=doc_id,
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
                uploaded_at=uploaded_at,
            )
            if not chunks:
                raise ValueError("Document produced no usable text chunks.")

            texts = [c.text for c in chunks]
            embeddings = embed_texts(texts)

            add_chunks(chunks, embeddings)

        except Exception as exc:
            # Clean up the saved file so we don't leave orphans.
            if os.path.exists(save_path):
                os.remove(save_path)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process '{filename}': {exc}",
            )

        results.append(
            IngestResponse(
                doc_id=doc_id,
                filename=filename,
                chunk_count=len(chunks),
                word_count=processed.metadata.get("word_count", 0),
                message="Successfully processed and indexed",
            )
        )

    return IngestBatchResponse(results=results)

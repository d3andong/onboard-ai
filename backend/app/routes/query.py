"""
POST /api/query — Answer a question against a specific topic collection.

Flow:
  1. Validate topic and question.
  2. Check the topic collection has indexed content.
  3. Embed the question.
  4. Retrieve top-K chunks from the topic collection.
  5. Generate a grounded answer with citations.
  6. Return answer + sources.
"""

from fastapi import APIRouter, HTTPException

from app.config import TOPICS
from app.models import QueryRequest, QueryResponse, SourceResponse
from app.services.embeddings import embed_query
from app.services.generator import generate_answer
from app.services.retriever import retrieve
from app.services.vector_store import get_collection

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Accept a natural-language question and optional conversation history.
    Returns a grounded answer with source citations from the specified topic.
    """
    # ── Validate topic ───────────────────────────────────────
    if request.topic not in TOPICS:
        valid = ", ".join(TOPICS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{request.topic}'. Valid topics: {valid}",
        )

    # ── Validate question ────────────────────────────────────
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # ── Ensure the topic has indexed content ─────────────────
    collection = get_collection(request.topic)
    if collection.count() == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No documents indexed for topic '{request.topic}'. Run the ingest script first.",
        )

    # ── Embed → Retrieve → Generate ──────────────────────────
    try:
        query_embedding = embed_query(question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    try:
        retrieved = retrieve(query_embedding, collection_name=request.topic)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}")

    try:
        result = generate_answer(
            query=question,
            retrieved_chunks=retrieved,
            conversation_history=request.conversation_history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {exc}")

    sources = [
        SourceResponse(
            doc_id=s.doc_id,
            chunk_id=s.chunk_id,
            filename=s.filename,
            chunk_text=s.chunk_text,
            score=s.score,
            section=s.section,
        )
        for s in result.sources
    ]

    return QueryResponse(answer=result.answer, sources=sources)

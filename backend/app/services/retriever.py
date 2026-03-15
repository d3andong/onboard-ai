"""
Retriever - Find the most relevant chunks for a query in a specific topic collection.

Converts ChromaDB cosine distances (0 = identical) into similarity scores
(1 - distance) and filters chunks below the relevance threshold.

Independently testable:
    python -m app.services.retriever supabase-docs "What is Supabase?"
"""

import logging
from dataclasses import dataclass

from app.config import settings
from app.services.chunker import Chunk
from app.services.vector_store import query_similar

log = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A Chunk paired with its cosine similarity score."""
    chunk: Chunk
    score: float   # 0.0 (irrelevant) → 1.0 (identical)


def retrieve(
    query_embedding: list[float],
    collection_name: str,
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[RetrievedChunk]:
    """
    Return the most relevant chunks from `collection_name` for an embedded query.

    Args:
        query_embedding:  Vector from embeddings.embed_query().
        collection_name:  Topic ID / ChromaDB collection to search.
        top_k:            Max results to consider (default: settings.TOP_K).
        threshold:        Min similarity score to keep (default: settings.RELEVANCE_THRESHOLD).

    Returns:
        List of RetrievedChunk sorted by descending similarity.
        Empty list → no content cleared the threshold.
    """
    top_k     = top_k     if top_k     is not None else settings.TOP_K
    threshold = threshold if threshold is not None else settings.RELEVANCE_THRESHOLD

    results = query_similar(query_embedding, collection_name=collection_name, top_k=top_k)

    ids       = results.get("ids",       [[]])[0]
    distances = results.get("distances", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    # Log raw scores once per query — helps diagnose threshold / metric issues.
    if distances:
        score_summary = ", ".join(f"{1.0 - d:.3f}" for d in distances)
        log.debug(
            "retriever [%s]: top-%d scores [%s] threshold=%.2f",
            collection_name, len(distances), score_summary, threshold,
        )

    retrieved: list[RetrievedChunk] = []

    for chunk_id, distance, text, meta in zip(ids, distances, documents, metadatas):
        # ChromaDB cosine distance ∈ [0, 2].  score = 1 - distance ∈ [-1, 1].
        # Clamp to [0, 1] to avoid negative scores from floating-point noise.
        score = max(0.0, 1.0 - float(distance))

        if score < threshold:
            log.debug(
                "retriever [%s]: dropped %s (score=%.3f < %.2f)",
                collection_name, chunk_id, score, threshold,
            )
            continue

        chunk = Chunk(
            id=chunk_id,
            text=text,
            doc_id=meta.get("doc_id", ""),
            chunk_index=int(meta.get("chunk_index", 0)),
            metadata=dict(meta),
        )
        retrieved.append(RetrievedChunk(chunk=chunk, score=round(score, 4)))

    log.info(
        "retriever [%s]: returning %d/%d chunks (threshold=%.2f)",
        collection_name, len(retrieved), len(ids), threshold,
    )
    return retrieved


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from app.services.embeddings import embed_query

    collection = sys.argv[1] if len(sys.argv) > 1 else "supabase-docs"
    question   = sys.argv[2] if len(sys.argv) > 2 else "What is Supabase?"
    print(f"Collection: {collection!r}")
    print(f"Query:      {question!r}\n")

    vec    = embed_query(question)
    chunks = retrieve(vec, collection_name=collection)

    if not chunks:
        print("No relevant chunks found (collection may be empty or threshold too high).")
    else:
        for rc in chunks:
            print(f"  score={rc.score:.3f}  [{rc.chunk.metadata.get('filename')}]  {rc.chunk.metadata.get('section')!r}")
            print(f"  {rc.chunk.text[:160]}\n")

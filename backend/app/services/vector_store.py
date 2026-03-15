"""
Vector Store - Persist and query chunks in ChromaDB.

Each knowledge-base topic is stored in its own ChromaDB collection whose
name matches the topic ID (e.g. "supabase-docs", "employee-handbook").
All public functions accept a `collection_name` parameter so callers are
always explicit about which topic they are reading from or writing to.

Independently testable:
    python -m app.services.vector_store
"""

import logging
import random

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.chunker import Chunk

log = logging.getLogger(__name__)

# ── Singletons ────────────────────────────────────────────────
# One shared PersistentClient; per-collection handles cached in a dict.

_client: chromadb.ClientAPI | None = None
_collections: dict[str, chromadb.Collection] = {}

_REQUIRED_SPACE = "cosine"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection(collection_name: str) -> chromadb.Collection:
    """
    Return (and lazily create) the ChromaDB collection for `collection_name`.

    Verifies the collection uses cosine distance.  If a pre-existing collection
    was created with L2 distance (the ChromaDB default), scores produced by
    `1 - distance` would be near zero and every query would return nothing.
    In that case the collection is deleted and recreated with cosine.
    """
    if collection_name in _collections:
        return _collections[collection_name]

    client = _get_client()
    col = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": _REQUIRED_SPACE},
    )

    actual_space = (col.metadata or {}).get("hnsw:space", "l2")
    if actual_space != _REQUIRED_SPACE:
        log.warning(
            "collection '%s' uses hnsw:space='%s' but '%s' is required. "
            "Deleting and recreating — all stored embeddings cleared. Re-ingest the documents.",
            collection_name, actual_space, _REQUIRED_SPACE,
        )
        client.delete_collection(collection_name)
        col = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": _REQUIRED_SPACE},
        )

    _collections[collection_name] = col
    return col


def reset_collection_cache(collection_name: str | None = None) -> None:
    """
    Drop the in-process collection handle(s) so the next call to
    get_collection() opens a fresh handle from disk.

    Pass a specific collection_name to reset just one topic, or None to
    reset everything (e.g. after an external ingest script runs).
    """
    global _client, _collections
    if collection_name:
        _collections.pop(collection_name, None)
    else:
        _client = None
        _collections.clear()


# ── Write operations ─────────────────────────────────────────

def add_chunks(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    collection_name: str,
) -> None:
    """Upsert chunks + embeddings into the named collection."""
    if not chunks:
        return
    col = get_collection(collection_name)
    col.upsert(
        ids=[c.id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[_build_chroma_meta(c) for c in chunks],
    )


def delete_document(doc_id: str, collection_name: str) -> int:
    """Delete all chunks for `doc_id`. Returns the number deleted."""
    col = get_collection(collection_name)
    results = col.get(where={"doc_id": doc_id}, include=["metadatas"])
    count = len(results["ids"])
    if count:
        col.delete(where={"doc_id": doc_id})
    return count


def delete_by_filename(filename: str, collection_name: str) -> int:
    """Delete all chunks whose metadata.filename matches. Returns chunk count."""
    col = get_collection(collection_name)
    results = col.get(where={"filename": filename}, include=["metadatas"])
    count = len(results["ids"])
    if count:
        col.delete(where={"filename": filename})
    return count


# ── Read operations ──────────────────────────────────────────

def query_similar(
    embedding: list[float],
    collection_name: str,
    top_k: int,
    where: dict | None = None,
) -> dict:
    """
    Nearest-neighbour search in the named collection.

    Returns the raw ChromaDB query result dict (ids, distances, documents,
    metadatas nested under index 0).
    """
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return {"ids": [[]], "distances": [[]], "documents": [[]], "metadatas": [[]]}

    kwargs: dict = dict(
        query_embeddings=[embedding],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    return col.query(**kwargs)


def get_all_documents(collection_name: str) -> list[dict]:
    """
    Return one metadata dict per unique doc_id in the collection, with
    an added `chunk_count` field.
    """
    col = get_collection(collection_name)
    if col.count() == 0:
        return []

    results = col.get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for meta in results["metadatas"]:
        doc_id = meta.get("doc_id", "")
        if not doc_id:
            continue
        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id":      doc_id,
                "filename":    meta.get("filename", ""),
                "file_type":   meta.get("file_type", ""),
                "word_count":  int(meta.get("word_count", 0)),
                "uploaded_at": meta.get("uploaded_at", ""),
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1

    return list(docs.values())


def get_collection_stats(collection_name: str) -> dict:
    """
    Return {"doc_count": int, "chunk_count": int} for a single collection.
    """
    col = get_collection(collection_name)
    chunk_count = col.count()
    if chunk_count == 0:
        return {"doc_count": 0, "chunk_count": 0}

    results = col.get(include=["metadatas"])
    doc_ids = {m.get("doc_id") for m in results["metadatas"] if m.get("doc_id")}
    return {"doc_count": len(doc_ids), "chunk_count": chunk_count}


def list_all_collection_stats() -> dict[str, dict]:
    """
    Return a stats dict for every topic defined in settings.TOPICS.

    Keys are topic IDs; values are {"doc_count": int, "chunk_count": int}.
    """
    return {
        topic_id: get_collection_stats(topic_id)
        for topic_id in settings.TOPICS
    }


def get_sample_chunks(collection_name: str, n: int = 10) -> list[str]:
    """
    Return up to `n` random chunk texts from the collection.

    Used by the suggested-questions endpoint to sample the actual content
    of a topic so the LLM can generate grounded questions.
    """
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []

    # Get all IDs (no embeddings or documents — cheap metadata-only fetch)
    all_ids_result = col.get(include=[])
    all_ids = all_ids_result["ids"]

    sample_ids = random.sample(all_ids, min(n, len(all_ids)))
    result = col.get(ids=sample_ids, include=["documents"])
    return result["documents"]


def get_section_headers(collection_name: str) -> list[str]:
    """Return distinct non-empty section headers stored in the collection."""
    col = get_collection(collection_name)
    if col.count() == 0:
        return []

    results = col.get(include=["metadatas"])
    seen: set[str] = set()
    headers: list[str] = []
    for meta in results["metadatas"]:
        h = meta.get("section", "")
        if h and h not in seen:
            seen.add(h)
            headers.append(h)
    return headers


# ── Viewer helpers ───────────────────────────────────────────

def get_chunk_by_id(chunk_id: str, collection_name: str) -> dict | None:
    """
    Return {id, text, metadata} for a single chunk, or None if not found.
    """
    col = get_collection(collection_name)
    result = col.get(ids=[chunk_id], include=["documents", "metadatas"])
    if not result["ids"]:
        return None
    return {
        "id":       result["ids"][0],
        "text":     result["documents"][0],
        "metadata": result["metadatas"][0],
    }


def get_chunks_by_doc_and_indices(
    doc_id: str,
    indices: list[int],
    collection_name: str,
) -> dict[int, dict]:
    """
    Fetch specific chunks from `doc_id` by their chunk_index positions.

    Chunk IDs follow the deterministic pattern "{doc_id}_chunk_{index}", so
    we request them directly rather than using a metadata filter.

    Returns a dict mapping chunk_index → {id, text, metadata}.
    Missing indices (chunk doesn't exist) are simply absent from the result.
    """
    col = get_collection(collection_name)
    if not indices:
        return {}
    ids = [f"{doc_id}_chunk_{i}" for i in indices]
    result = col.get(ids=ids, include=["documents", "metadatas"])
    out: dict[int, dict] = {}
    for cid, text, meta in zip(result["ids"], result["documents"], result["metadatas"]):
        idx = int(meta.get("chunk_index", -1))
        out[idx] = {"id": cid, "text": text, "metadata": meta}
    return out


def get_doc_source_path(doc_id: str, collection_name: str) -> str | None:
    """
    Return the source_path stored in any chunk belonging to doc_id, or None.
    Uses limit=1 to avoid fetching all chunks for large documents.
    """
    col = get_collection(collection_name)
    result = col.get(
        where={"doc_id": doc_id},
        include=["metadatas"],
        limit=1,
    )
    if not result["ids"]:
        return None
    return result["metadatas"][0].get("source_path") or None


# ── Internal helpers ─────────────────────────────────────────

def _build_chroma_meta(chunk: Chunk) -> dict:
    """
    Flatten a Chunk's metadata into ChromaDB-compatible types.
    ChromaDB metadata values must be str | int | float | bool (no None).
    """
    m = chunk.metadata
    return {
        "doc_id":       chunk.doc_id,
        "filename":     str(m.get("filename", "")),
        "file_type":    str(m.get("file_type", "")),
        "chunk_index":  int(chunk.chunk_index),
        "total_chunks": int(m.get("total_chunks", 0)),
        "section":      str(m.get("section", "")),
        "char_start":   int(m.get("char_start", 0)),
        "char_end":     int(m.get("char_end", 0)),
        "word_count":   int(m.get("word_count", 0)),
        "uploaded_at":  str(m.get("uploaded_at", "")),
        "source_path":  str(m.get("source_path", "")),
    }


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    from app.config import TOPICS

    print(f"CHROMA_PERSIST_DIR: {settings.CHROMA_PERSIST_DIR}\n")
    all_stats = list_all_collection_stats()
    for topic_id, stats in all_stats.items():
        name = TOPICS[topic_id]["name"]
        print(f"  {TOPICS[topic_id]['icon']} {name:<30} docs={stats['doc_count']:>3}  chunks={stats['chunk_count']:>4}")

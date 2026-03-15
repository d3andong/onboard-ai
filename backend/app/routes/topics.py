"""
GET /api/topics — List all knowledge-base topics that have indexed content.

Only topics with at least one document ingested are returned; empty topics
are silently omitted so the frontend never shows a broken topic picker.
"""

from fastapi import APIRouter

from app.config import TOPICS, settings
from app.models import TopicListResponse, TopicResponse
from app.services.vector_store import list_all_collection_stats

router = APIRouter()


@router.get("/topics", response_model=TopicListResponse)
async def list_topics():
    """
    Return every topic that has at least one document indexed, together with
    its doc_count and chunk_count.
    """
    all_stats = list_all_collection_stats()

    topics: list[TopicResponse] = []
    for topic_id, meta in TOPICS.items():
        stats = all_stats.get(topic_id, {"doc_count": 0, "chunk_count": 0})
        if stats["doc_count"] == 0:
            continue   # skip empty topics
        topics.append(
            TopicResponse(
                id=topic_id,
                name=meta["name"],
                icon=meta["icon"],
                description=meta["description"],
                doc_count=stats["doc_count"],
                chunk_count=stats["chunk_count"],
            )
        )

    return TopicListResponse(topics=topics)

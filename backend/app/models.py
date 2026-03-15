"""
Pydantic models for all API request / response bodies.
"""

from pydantic import BaseModel, Field


# ── Query ────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    topic: str = Field(
        default="employee-handbook",
        description="Topic ID to query (must be a key in settings.TOPICS).",
    )
    conversation_history: list[dict] = Field(
        default=[],
        description='[{"role": "user"|"assistant", "content": "…"}]',
    )


class SourceResponse(BaseModel):
    doc_id: str
    chunk_id: str = ""
    filename: str
    chunk_text: str
    score: float
    section: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]


# ── Topics ───────────────────────────────────────────────────

class TopicResponse(BaseModel):
    id: str
    name: str
    icon: str
    description: str
    doc_count: int
    chunk_count: int


class TopicListResponse(BaseModel):
    topics: list[TopicResponse]


# ── Documents ────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    word_count: int
    uploaded_at: str   # ISO 8601


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total_count: int


# ── Suggested questions ──────────────────────────────────────

class SuggestedQuestionsResponse(BaseModel):
    questions: list[str]


class FollowUpQuestionsRequest(BaseModel):
    topic: str
    last_question: str
    last_answer: str


# ── Ingest (kept for internal / script use) ──────────────────

class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    word_count: int
    message: str


class IngestBatchResponse(BaseModel):
    results: list[IngestResponse]


# ── Viewer ───────────────────────────────────────────────────

class ChunkContextDocument(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    page_number: int | None = None


class ChunkContextResponse(BaseModel):
    chunk_id: str
    chunk_text: str
    context_before: str
    context_after: str
    document: ChunkContextDocument
    section: str | None = None
    chunk_index: int
    total_chunks: int


# ── Misc ─────────────────────────────────────────────────────

class DeleteDocumentResponse(BaseModel):
    message: str
    doc_id: str
    chunks_removed: int

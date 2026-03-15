"""
Generator - Build prompts and call the OpenAI Chat API to produce answers.

The system prompt strictly instructs the model to:
  - Answer ONLY from provided context chunks.
  - Cite sources by label ([Source N]).
  - Say "I couldn't find relevant information" when context is empty or insufficient.

Independently testable:
    python -m app.services.generator
"""

from dataclasses import dataclass, field

from openai import OpenAI

from app.config import settings
from app.services.retriever import RetrievedChunk

_client: OpenAI | None = None

_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context documents.

Rules:
- ALWAYS attempt to answer using the provided context, even if the match is partial or indirect
- Cite your sources using [Source N] notation matching the chunk labels
- If the context contains partially relevant information, provide what you can and note what aspects aren't fully covered
- ONLY say you can't find information if ZERO context chunks are provided (empty context)
- Render your response in clean markdown: use headers, bullet points, bold text, and code blocks where appropriate
- Keep answers concise but thorough
"""

# Maximum conversation turns to include in the prompt (each turn = 2 messages)
_MAX_HISTORY_TURNS = 5


@dataclass
class Source:
    doc_id: str
    filename: str
    chunk_text: str
    score: float
    section: str | None = None
    chunk_id: str = ""


@dataclass
class QueryResult:
    answer: str
    sources: list[Source] = field(default_factory=list)
    query: str = ""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise EnvironmentError("OPENAI_API_KEY is not set.")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_answer(
    query: str,
    retrieved_chunks: list[RetrievedChunk],
    conversation_history: list[dict],
) -> QueryResult:
    """
    Generate a grounded answer using retrieved context and conversation history.

    Args:
        query:                The user's question.
        retrieved_chunks:     Output of retriever.retrieve() — may be empty.
        conversation_history: List of {"role": "user"|"assistant", "content": "…"}.
                              The last MAX_HISTORY_TURNS turns are included.

    Returns:
        QueryResult with .answer (str) and .sources (list[Source]).
    """
    if not retrieved_chunks:
        return QueryResult(
            answer=(
                "I couldn't find relevant information for your question. "
                "Try rephrasing your question or selecting a different topic."
            ),
            sources=[],
            query=query,
        )

    # Build the context block shown to the model
    context_parts: list[str] = []
    for i, rc in enumerate(retrieved_chunks, start=1):
        filename = rc.chunk.metadata.get("filename", "unknown")
        section  = rc.chunk.metadata.get("section", "")
        label    = f"[Source {i}: {filename}"
        if section:
            label += f" — {section}"
        label += "]"
        context_parts.append(f"{label}\n{rc.chunk.text}")

    context_block = "\n\n".join(context_parts)

    # Assemble the message list
    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    # Inject context as a synthetic assistant-preceded exchange so that
    # the model treats it as ground truth, not as a prior user message.
    messages.append({
        "role": "user",
        "content": (
            "Here are the relevant document excerpts for this conversation:\n\n"
            f"{context_block}\n\n"
            "Please use ONLY these excerpts to answer the upcoming question."
        ),
    })
    messages.append({
        "role": "assistant",
        "content": (
            "Understood. I will answer using only the provided document excerpts "
            "and cite sources by their labels."
        ),
    })

    # Conversation history (last N turns)
    history = conversation_history[- (_MAX_HISTORY_TURNS * 2):]
    messages.extend(history)

    # The current question
    messages.append({"role": "user", "content": query})

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content or ""

    sources = [
        Source(
            doc_id=rc.chunk.doc_id,
            chunk_id=rc.chunk.id,
            filename=rc.chunk.metadata.get("filename", ""),
            chunk_text=rc.chunk.text,
            score=rc.score,
            section=rc.chunk.metadata.get("section") or None,
        )
        for rc in retrieved_chunks
    ]

    return QueryResult(answer=answer, sources=sources, query=query)


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from app.services.embeddings import embed_query
    from app.services.retriever import retrieve

    question = sys.argv[1] if len(sys.argv) > 1 else "What is the PTO policy?"
    print(f"Query: {question!r}\n")

    vec = embed_query(question)
    chunks = retrieve(vec)
    result = generate_answer(question, chunks, [])

    print(f"Answer:\n{result.answer}\n")
    print(f"Sources ({len(result.sources)}):")
    for s in result.sources:
        print(f"  [{s.score:.3f}] {s.filename} — {s.section or 'no section'}")

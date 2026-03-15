"""
Embeddings - Generate vector embeddings via OpenAI API.

Uses text-embedding-3-small (1536 dimensions) by default.
Batches requests to stay within API limits.

Independently testable:
    python -m app.services.embeddings
"""

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None

# OpenAI allows up to 2048 inputs per request; we use a safe batch size.
_BATCH_SIZE = 100


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings using the configured embedding model.

    Automatically batches large lists to avoid API limits.

    Args:
        texts: Non-empty list of strings to embed.

    Returns:
        List of embedding vectors, one per input string, in order.

    Raises:
        ValueError:      texts is empty.
        openai.APIError: API call failed.
    """
    if not texts:
        raise ValueError("texts must be a non-empty list")

    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=batch,
        )
        # Response items are sorted by index — safe to extend in order.
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """
    Embed a single query string.

    Args:
        text: The query to embed.

    Returns:
        A single 1536-dimensional embedding vector.
    """
    return embed_texts([text])[0]


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    sample = ["What is the PTO policy?", "How do I set up the VPN?"]
    print(f"Embedding {len(sample)} texts with model={settings.EMBEDDING_MODEL}…")
    vecs = embed_texts(sample)
    print(f"OK — {len(vecs)} vectors, dimension={len(vecs[0])}")

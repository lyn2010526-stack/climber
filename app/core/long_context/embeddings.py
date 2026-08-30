"""Real embedding providers for the long-context RAG index.

The default provider reuses the project's primary embedding path — ChromaDB's
bundled ONNX all-MiniLM-L6-v2 — which runs fully locally with no API key and
is already battle-tested by ``vector_memory``. The RAG index falls back to a
hash-based embedding only when no provider is injected.
"""

from __future__ import annotations

from collections.abc import Callable

#: Embedding dimension of ChromaDB's default ONNX model (all-MiniLM-L6-v2).
DEFAULT_EMBEDDING_DIM = 384


def default_embed_fn() -> Callable[[str], list[float]]:
    """Return the ChromaDB default embedding as a ``text -> vector`` callable."""
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    ef = DefaultEmbeddingFunction()

    def embed(text: str) -> list[float]:
        return [float(v) for v in ef([text])[0]]

    return embed

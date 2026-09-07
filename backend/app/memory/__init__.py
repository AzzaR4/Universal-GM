"""Semantic memory package.

Provides an embedding-provider abstraction, a memory extractor, and cosine /
keyword retrieval. No external vector database is required — cosine similarity
is computed in pure Python (fine for well under ~10k memories per campaign).
"""
from app.memory.embedder import (
    EmbeddingProvider,
    NullEmbedder,
    OpenAIEmbedder,
    cosine_similarity,
    get_embedder,
)
from app.memory.extractor import MemoryExtractor
from app.memory.retrieval import retrieve_memories

__all__ = [
    "EmbeddingProvider",
    "NullEmbedder",
    "OpenAIEmbedder",
    "cosine_similarity",
    "get_embedder",
    "MemoryExtractor",
    "retrieve_memories",
]

"""Memory retrieval: semantic (cosine) with keyword fallback."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Memory
from app.game.memory.memory_manager import extract_keywords
from app.memory.embedder import EmbeddingProvider, NullEmbedder, cosine_similarity


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _keyword_score(query: str, mem: Memory) -> float:
    query_kw = set(extract_keywords(query))
    kw = set(mem.keywords or []) | {str(t).lower() for t in (mem.tags or [])}
    overlap = len(query_kw & kw)
    now = datetime.now(timezone.utc)
    age_days = max(0.0, (now - _aware(mem.created_at)).total_seconds() / 86400)
    recency = 1.0 / (1.0 + age_days)
    return overlap * 2.0 + (mem.importance or 0.0) + recency


async def retrieve_memories(
    session: AsyncSession,
    campaign_id: str,
    query: str,
    embedder: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> list[Memory]:
    """Return the top-k most relevant memories for a query.

    Uses cosine similarity over stored embeddings when an embedder is available
    and both the query and stored memories have embeddings; otherwise falls back
    to keyword + importance + recency scoring.
    """
    rows = (
        await session.execute(
            select(Memory).where(Memory.campaign_id == campaign_id)
        )
    ).scalars().all()
    if not rows:
        return []

    embedder = embedder or NullEmbedder()
    query_vec: list[float] = []
    try:
        query_vec = await embedder.embed(query)
    except Exception:  # noqa: BLE001
        query_vec = []

    embedded = [m for m in rows if m.embedding]
    if query_vec and embedded:
        scored = [
            (cosine_similarity(query_vec, m.embedding), m) for m in embedded
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        top = [m for score, m in scored if score > 0][:top_k]
        if top:
            return top

    # Keyword fallback (also used when no embeddings are present).
    scored_kw = [(_keyword_score(query, m), m) for m in rows]
    scored_kw = [
        (s, m) for s, m in scored_kw if s > 0 or (m.importance or 0) >= 0.8
    ]
    scored_kw.sort(key=lambda t: t[0], reverse=True)
    return [m for _, m in scored_kw[:top_k]]

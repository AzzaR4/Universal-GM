"""Layered memory: short-term (recent events) + campaign long-term (DB, keyword).

No vector DB dependency — retrieval is keyword + importance + recency based.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLog, Memory

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z']{2,}")
_STOP = {
    "the", "and", "you", "your", "with", "for", "that", "this", "are", "was",
    "his", "her", "their", "they", "from", "have", "has", "not", "but", "all",
}


def extract_keywords(text: str, limit: int = 10) -> list[str]:
    words = [w.lower() for w in _WORD_RE.findall(text or "")]
    seen: list[str] = []
    for w in words:
        if w in _STOP:
            continue
        if w not in seen:
            seen.append(w)
    return seen[:limit]


class MemoryManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        campaign_id: str,
        content: str,
        memory_type: str = "event",
        importance: float = 0.5,
        subject_id: str | None = None,
    ) -> Memory:
        mem = Memory(
            campaign_id=campaign_id,
            memory_type=memory_type,
            subject_id=subject_id,
            content=content,
            importance=importance,
            keywords=extract_keywords(content),
        )
        self.session.add(mem)
        await self.session.flush()
        return mem

    async def short_term(self, campaign_id: str, limit: int = 8) -> list[str]:
        """Return the most recent narration/event descriptions."""
        rows = (
            await self.session.execute(
                select(EventLog)
                .where(EventLog.campaign_id == campaign_id)
                .order_by(EventLog.timestamp.desc())
                .limit(limit)
            )
        ).scalars().all()
        out: list[str] = []
        for r in reversed(rows):
            data = r.data or {}
            text = data.get("summary") or data.get("narration") or data.get("description")
            if text:
                out.append(str(text))
        return out

    async def retrieve_relevant(
        self, campaign_id: str, query: str, limit: int = 5
    ) -> list[str]:
        """Keyword + importance retrieval of long-term memories."""
        query_kw = set(extract_keywords(query))
        rows = (
            await self.session.execute(
                select(Memory).where(Memory.campaign_id == campaign_id)
            )
        ).scalars().all()
        scored: list[tuple[float, str]] = []
        now = datetime.now(timezone.utc)
        for m in rows:
            kw = set(m.keywords or [])
            overlap = len(query_kw & kw)
            age_days = max(0.0, (now - _aware(m.created_at)).total_seconds() / 86400)
            recency = 1.0 / (1.0 + age_days)
            score = overlap * 2.0 + m.importance + recency
            if overlap > 0 or m.importance >= 0.8:
                scored.append((score, m.content))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for _, c in scored[:limit]]


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

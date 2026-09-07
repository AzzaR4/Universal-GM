"""Memory extraction: distill key facts from narrative and store them.

After each narrative response the extractor pulls 1-3 short factual statements,
embeds them (if an embedder is available), and stores them as Memory rows. When
no AI provider is configured it degrades to a sentence-splitting heuristic so
memories are still captured.
"""
from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Memory
from app.game.memory.memory_manager import extract_keywords
from app.memory.embedder import EmbeddingProvider, NullEmbedder

_SENT_RE = re.compile(r"(?<=[.!?])\s+")
# Words that hint a sentence is consequential (bumps importance).
_SIGNAL_WORDS = {
    "kill", "killed", "die", "died", "death", "betray", "betrayed", "discover",
    "discovered", "reveal", "revealed", "secret", "treasure", "quest", "defeat",
    "defeated", "ally", "enemy", "attack", "victory", "escape", "found", "learns",
}


def heuristic_facts(passage: str, limit: int = 3) -> list[str]:
    """Split a passage into up to `limit` short factual sentences."""
    text = (passage or "").strip()
    if not text:
        return []
    sentences = [s.strip() for s in _SENT_RE.split(text) if len(s.strip()) > 12]
    if not sentences:
        sentences = [text]
    # Rank by presence of signal words, then by moderate length.
    def score(s: str) -> float:
        words = set(w.lower() for w in re.findall(r"[a-zA-Z']+", s))
        signal = len(words & _SIGNAL_WORDS)
        length_pen = -abs(len(s) - 90) / 200.0
        return signal * 2.0 + length_pen

    ranked = sorted(sentences, key=score, reverse=True)
    return ranked[:limit]


def importance_for(fact: str) -> float:
    words = set(w.lower() for w in re.findall(r"[a-zA-Z']+", fact))
    signal = len(words & _SIGNAL_WORDS)
    return max(0.3, min(1.0, 0.4 + 0.2 * signal))


class MemoryExtractor:
    def __init__(
        self,
        session: AsyncSession,
        embedder: EmbeddingProvider | None = None,
        provider=None,
    ) -> None:
        self.session = session
        self.embedder = embedder or NullEmbedder()
        self.provider = provider

    async def _facts_via_ai(self, passage: str) -> list[str]:
        if self.provider is None:
            return []
        system = (
            "You extract durable facts from a tabletop RPG narrative. Return ONLY "
            "a JSON object of the form {\"facts\": [\"...\", ...]} containing 1-3 "
            "short, self-contained factual sentences worth remembering "
            "(named characters, decisions, outcomes, discoveries)."
        )
        try:
            data = await self.provider.complete_json(system, passage)
            facts = data.get("facts") if isinstance(data, dict) else None
            if isinstance(facts, list):
                return [str(f).strip() for f in facts if str(f).strip()][:3]
        except Exception:  # noqa: BLE001
            return []
        return []

    async def extract_and_store(
        self,
        campaign_id: str,
        passage: str,
        tags: list | None = None,
        source_action_id: str | None = None,
        memory_type: str = "fact",
    ) -> list[Memory]:
        facts = await self._facts_via_ai(passage)
        if not facts:
            facts = heuristic_facts(passage)
        created: list[Memory] = []
        for fact in facts:
            embedding = []
            try:
                embedding = await self.embedder.embed(fact)
            except Exception:  # noqa: BLE001
                embedding = []
            mem = Memory(
                campaign_id=campaign_id,
                memory_type=memory_type,
                content=fact,
                importance=importance_for(fact),
                keywords=extract_keywords(fact),
                tags=tags or [],
                embedding=embedding or None,
                source_action_id=source_action_id,
            )
            self.session.add(mem)
            created.append(mem)
        if created:
            await self.session.flush()
        return created

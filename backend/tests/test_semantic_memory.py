"""Tests for semantic memory: extraction, cosine retrieval, keyword fallback."""
from __future__ import annotations

import pytest

from app.api.campaigns import create_campaign
from app.api.memories import create_memory, delete_memory, list_memories
from app.api.schemas import CampaignCreate, MemoryCreate
from app.db.models import Memory
from app.memory.embedder import NullEmbedder, cosine_similarity
from app.memory.extractor import MemoryExtractor, heuristic_facts, importance_for
from app.memory.retrieval import retrieve_memories

pytestmark = pytest.mark.asyncio


class FakeEmbedder:
    """Deterministic 3-d embedder for tests (bag-of-signal-words)."""

    _VOCAB = ["dragon", "village", "treasure"]

    async def embed(self, text: str) -> list[float]:
        text = (text or "").lower()
        return [float(text.count(w)) for w in self._VOCAB]


async def _campaign(session):
    return await create_campaign(CampaignCreate(name="Mem"), session=session)


# --------------------------- cosine similarity --------------------------- #
def test_cosine_identical():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_orthogonal():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_degenerate():
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


# --------------------------- extraction --------------------------- #
def test_heuristic_facts_prioritises_signal():
    passage = (
        "The weather was mild today. The hero killed the dragon and discovered "
        "a hidden treasure beneath its lair."
    )
    facts = heuristic_facts(passage, limit=1)
    assert len(facts) == 1
    assert "dragon" in facts[0].lower() or "treasure" in facts[0].lower()


def test_heuristic_facts_empty():
    assert heuristic_facts("") == []


def test_importance_scales_with_signal():
    low = importance_for("They walked down the road.")
    high = importance_for("The king was betrayed and killed in the battle.")
    assert high > low


async def test_extractor_stores_memories(session):
    camp = await _campaign(session)
    extractor = MemoryExtractor(session, embedder=FakeEmbedder())
    passage = "The party defeated the goblin chief. They found a magic sword."
    mems = await extractor.extract_and_store(camp.id, passage, tags=["combat"])
    assert len(mems) >= 1
    assert all(m.campaign_id == camp.id for m in mems)
    assert mems[0].embedding is not None


async def test_extractor_null_embedder_no_embedding(session):
    camp = await _campaign(session)
    extractor = MemoryExtractor(session, embedder=NullEmbedder())
    mems = await extractor.extract_and_store(camp.id, "A dragon attacked the village.")
    assert len(mems) >= 1
    assert mems[0].embedding is None


# --------------------------- retrieval --------------------------- #
async def test_cosine_retrieval_ranks_by_similarity(session):
    camp = await _campaign(session)
    embedder = FakeEmbedder()
    extractor = MemoryExtractor(session, embedder=embedder)
    await extractor.extract_and_store(camp.id, "A fearsome dragon guards the cave.")
    await extractor.extract_and_store(camp.id, "The village holds a harvest festival.")
    await session.commit()
    results = await retrieve_memories(
        session, camp.id, "dragon attack", embedder=embedder, top_k=1
    )
    assert len(results) == 1
    assert "dragon" in results[0].content.lower()


async def test_keyword_fallback_without_embeddings(session):
    camp = await _campaign(session)
    # Stored via API create with NullEmbedder -> no embeddings.
    await create_memory(
        camp.id,
        MemoryCreate(content="The wizard Gandalf lives in Rivendell.", tags=["npc"]),
        session=session,
    )
    await create_memory(
        camp.id,
        MemoryCreate(content="A quiet farm sits by the river."),
        session=session,
    )
    results = await retrieve_memories(
        session, camp.id, "Where is Gandalf?", embedder=NullEmbedder(), top_k=2
    )
    assert results
    assert any("gandalf" in m.content.lower() for m in results)


async def test_retrieve_empty_campaign(session):
    camp = await _campaign(session)
    results = await retrieve_memories(session, camp.id, "anything")
    assert results == []


# --------------------------- API --------------------------- #
async def test_create_and_list_memory(session):
    camp = await _campaign(session)
    await create_memory(
        camp.id,
        MemoryCreate(content="The bridge is broken.", importance=0.7, tags=["location"]),
        session=session,
    )
    rows = await list_memories(camp.id, session=session)
    assert len(rows) == 1
    assert rows[0].content == "The bridge is broken."
    assert rows[0].keywords


async def test_list_memories_filter_by_tag(session):
    camp = await _campaign(session)
    await create_memory(camp.id, MemoryCreate(content="A", tags=["npc"]), session=session)
    await create_memory(camp.id, MemoryCreate(content="B", tags=["loot"]), session=session)
    npc = await list_memories(camp.id, tag="npc", session=session)
    assert len(npc) == 1 and npc[0].content == "A"


async def test_list_memories_filter_by_importance(session):
    camp = await _campaign(session)
    await create_memory(camp.id, MemoryCreate(content="low", importance=0.2), session=session)
    await create_memory(camp.id, MemoryCreate(content="high", importance=0.9), session=session)
    important = await list_memories(camp.id, min_importance=0.5, session=session)
    assert len(important) == 1 and important[0].content == "high"


async def test_list_memories_text_search(session):
    camp = await _campaign(session)
    await create_memory(camp.id, MemoryCreate(content="dragon lair"), session=session)
    await create_memory(camp.id, MemoryCreate(content="market square"), session=session)
    found = await list_memories(camp.id, q="dragon", session=session)
    assert len(found) == 1 and found[0].content == "dragon lair"


async def test_delete_memory(session):
    camp = await _campaign(session)
    m = await create_memory(camp.id, MemoryCreate(content="temp"), session=session)
    result = await delete_memory(camp.id, m.id, session=session)
    assert result["deleted"] == m.id
    assert await session.get(Memory, m.id) is None


async def test_create_memory_unknown_campaign(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await create_memory("nope", MemoryCreate(content="x"), session=session)

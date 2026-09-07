"""Tests for character creation & the party system."""
from __future__ import annotations

import pytest

from app.api.characters import (
    create_character,
    delete_character,
    list_characters,
)
from app.api.party import (
    add_to_party,
    get_character_schema,
    list_party,
    remove_from_party,
)
from app.api.campaigns import create_campaign
from app.api.schemas import CampaignCreate, CharacterCreate
from app.db.models import Character, PartyMember

pytestmark = pytest.mark.asyncio


async def _make_campaign(session, ruleset_id: str = "generic"):
    return await create_campaign(
        CampaignCreate(name="Test", ruleset_id=ruleset_id), session=session
    )


async def test_create_character_defaults_ruleset_data(session):
    camp = await _make_campaign(session)
    ch = await create_character(
        camp.id, CharacterCreate(name="Aria"), session=session
    )
    assert ch.name == "Aria"
    assert ch.is_player_character is True
    assert "attributes" in ch.ruleset_data
    assert "resources" in ch.ruleset_data


async def test_create_character_with_player_name(session):
    camp = await _make_campaign(session)
    ch = await create_character(
        camp.id,
        CharacterCreate(name="Borin", player_name="Alice"),
        session=session,
    )
    assert ch.player_name == "Alice"


async def test_create_character_add_to_party(session):
    camp = await _make_campaign(session)
    ch = await create_character(
        camp.id,
        CharacterCreate(name="Cael", add_to_party=True),
        session=session,
    )
    party = await list_party(camp.id, session=session)
    assert len(party) == 1
    assert party[0].id == ch.id


async def test_create_character_custom_ruleset_data(session):
    camp = await _make_campaign(session)
    data = {"attributes": {"STR": 3}, "skills": {}, "resources": {}}
    ch = await create_character(
        camp.id,
        CharacterCreate(name="Custom", ruleset_data=data),
        session=session,
    )
    assert ch.ruleset_data["attributes"]["STR"] == 3


async def test_create_character_unknown_campaign(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await create_character(
            "nope", CharacterCreate(name="Ghost"), session=session
        )


async def test_list_characters(session):
    camp = await _make_campaign(session)
    await create_character(camp.id, CharacterCreate(name="A"), session=session)
    await create_character(camp.id, CharacterCreate(name="B"), session=session)
    rows = await list_characters(camp.id, session=session)
    assert len(rows) == 2


async def test_add_to_party_idempotent(session):
    camp = await _make_campaign(session)
    ch = await create_character(camp.id, CharacterCreate(name="Dax"), session=session)
    await add_to_party(camp.id, ch.id, session=session)
    party = await add_to_party(camp.id, ch.id, session=session)
    # Adding twice should not duplicate the membership.
    assert len(party) == 1


async def test_add_to_party_unknown_character(session):
    from fastapi import HTTPException

    camp = await _make_campaign(session)
    with pytest.raises(HTTPException):
        await add_to_party(camp.id, "missing", session=session)


async def test_remove_from_party(session):
    camp = await _make_campaign(session)
    ch = await create_character(camp.id, CharacterCreate(name="Ella"), session=session)
    await add_to_party(camp.id, ch.id, session=session)
    result = await remove_from_party(camp.id, ch.id, session=session)
    assert result["removed"] == ch.id
    party = await list_party(camp.id, session=session)
    assert party == []


async def test_remove_from_party_not_member(session):
    from fastapi import HTTPException

    camp = await _make_campaign(session)
    ch = await create_character(camp.id, CharacterCreate(name="Finn"), session=session)
    with pytest.raises(HTTPException):
        await remove_from_party(camp.id, ch.id, session=session)


async def test_party_excludes_non_members(session):
    camp = await _make_campaign(session)
    await create_character(camp.id, CharacterCreate(name="G"), session=session)
    ch2 = await create_character(camp.id, CharacterCreate(name="H"), session=session)
    await add_to_party(camp.id, ch2.id, session=session)
    party = await list_party(camp.id, session=session)
    assert len(party) == 1
    assert party[0].id == ch2.id


async def test_character_schema_generic(session):
    result = await get_character_schema("generic", session=session)
    assert result["id"] == "generic"
    assert "attributes" in result
    assert "resources" in result
    assert isinstance(result["attributes"], list)


async def test_character_schema_dnd5e(session):
    result = await get_character_schema("dnd5e", session=session)
    assert result["id"] == "dnd5e"
    # Each ruleset defines its own schema shape (dnd5e uses "abilities").
    assert "schema" in result
    assert isinstance(result["schema"], dict) and result["schema"]


async def test_character_schema_unknown(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await get_character_schema("bogus", session=session)


async def test_delete_character(session):
    camp = await _make_campaign(session)
    ch = await create_character(
        camp.id, CharacterCreate(name="Iris", add_to_party=True), session=session
    )
    result = await delete_character(camp.id, ch.id, session=session)
    assert result["deleted"] == ch.id
    assert await session.get(Character, ch.id) is None


async def test_party_unknown_campaign(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await list_party("missing", session=session)

"""Pydantic request/response schemas for the REST API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --------------------------- Campaign --------------------------- #
class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    ruleset_id: str = "generic"
    campaign_style: str = ""
    narrative_style: str = ""
    gm_config: dict[str, Any] = Field(default_factory=dict)
    ruleset_config: dict[str, Any] = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    campaign_style: str | None = None
    narrative_style: str | None = None
    gm_config: dict[str, Any] | None = None
    ruleset_config: dict[str, Any] | None = None
    current_location_id: str | None = None
    is_active: bool | None = None


class CampaignOut(BaseModel):
    id: str
    name: str
    description: str
    ruleset_id: str
    campaign_style: str
    narrative_style: str
    gm_config: dict[str, Any]
    ruleset_config: dict[str, Any]
    world_state: dict[str, Any]
    current_location_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --------------------------- Character --------------------------- #
class CharacterCreate(BaseModel):
    name: str
    description: str = ""
    is_player_character: bool = True
    ruleset_data: dict[str, Any] | None = None
    conditions: list[Any] = Field(default_factory=list)
    inventory: list[Any] = Field(default_factory=list)
    location_id: str | None = None


class CharacterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    ruleset_data: dict[str, Any] | None = None
    conditions: list[Any] | None = None
    inventory: list[Any] | None = None
    location_id: str | None = None
    status: str | None = None


class CharacterOut(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str
    is_player_character: bool
    ruleset_data: dict[str, Any]
    conditions: list[Any]
    inventory: list[Any]
    location_id: str | None
    status: str

    class Config:
        from_attributes = True


# --------------------------- NPC --------------------------- #
class NPCCreate(BaseModel):
    name: str
    description: str = ""
    personality: dict[str, Any] = Field(default_factory=dict)
    goals: list[Any] = Field(default_factory=list)
    knowledge: list[Any] = Field(default_factory=list)
    secrets: list[Any] = Field(default_factory=list)
    relationships: dict[str, Any] = Field(default_factory=dict)
    location_id: str | None = None
    current_activity: str = ""


class NPCUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    personality: dict[str, Any] | None = None
    goals: list[Any] | None = None
    knowledge: list[Any] | None = None
    secrets: list[Any] | None = None
    relationships: dict[str, Any] | None = None
    location_id: str | None = None
    current_activity: str | None = None
    status: str | None = None


class NPCOut(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str
    personality: dict[str, Any]
    goals: list[Any]
    knowledge: list[Any]
    secrets: list[Any]
    relationships: dict[str, Any]
    location_id: str | None
    current_activity: str
    status: str

    class Config:
        from_attributes = True


# --------------------------- Location --------------------------- #
class LocationCreate(BaseModel):
    name: str
    description: str = ""
    atmosphere: str = ""
    connected_location_ids: list[Any] = Field(default_factory=list)
    is_discovered: bool = True
    lore: dict[str, Any] = Field(default_factory=dict)


class LocationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    atmosphere: str | None = None
    connected_location_ids: list[Any] | None = None
    is_discovered: bool | None = None
    lore: dict[str, Any] | None = None


class LocationOut(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str
    atmosphere: str
    connected_location_ids: list[Any]
    is_discovered: bool
    lore: dict[str, Any]

    class Config:
        from_attributes = True


# --------------------------- Quest --------------------------- #
class QuestCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "active"
    objectives: list[Any] = Field(default_factory=list)
    notes: str = ""


class QuestOut(BaseModel):
    id: str
    campaign_id: str
    title: str
    description: str
    status: str
    objectives: list[Any]
    notes: str

    class Config:
        from_attributes = True


# --------------------------- Action --------------------------- #
class ActionRequest(BaseModel):
    text: str


# --------------------------- AI Provider --------------------------- #
class ProviderCreate(BaseModel):
    name: str
    provider_type: str = "openai_compatible"
    endpoint_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    api_key: str | None = None
    temperature: float = 0.8
    max_tokens: int = 1024
    context_window: int = 8192
    extra_params: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    endpoint_url: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    context_window: int | None = None
    extra_params: dict[str, Any] | None = None
    is_active: bool | None = None


class ProviderOut(BaseModel):
    id: str
    name: str
    provider_type: str
    endpoint_url: str
    model_name: str
    has_api_key: bool
    temperature: float
    max_tokens: int
    context_window: int
    extra_params: dict[str, Any]
    is_active: bool

    class Config:
        from_attributes = True


class EventLogOut(BaseModel):
    id: str
    event_type: str
    data: dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True

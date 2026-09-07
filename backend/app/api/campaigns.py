"""Campaign CRUD and ruleset listing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import CampaignCreate, CampaignOut, CampaignUpdate, EventLogOut
from app.db.models import Campaign, EventLog
from app.rulesets.registry import get_ruleset, list_rulesets

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])
meta_router = APIRouter(prefix="/api", tags=["meta"])


@meta_router.get("/rulesets")
async def get_rulesets() -> list[dict]:
    return list_rulesets()


@meta_router.get("/rulesets/{ruleset_id}/schema")
async def get_ruleset_schema(ruleset_id: str) -> dict:
    try:
        rs = get_ruleset(ruleset_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "id": rs.id,
        "name": rs.name,
        "default_config": rs.default_config(),
        "character_schema": rs.character_schema(),
    }


@router.post("", response_model=CampaignOut)
async def create_campaign(
    payload: CampaignCreate, session: AsyncSession = Depends(db_session)
) -> Campaign:
    ruleset = get_ruleset(payload.ruleset_id)
    ruleset_config = payload.ruleset_config or ruleset.default_config()
    campaign = Campaign(
        name=payload.name,
        description=payload.description,
        ruleset_id=payload.ruleset_id,
        campaign_style=payload.campaign_style,
        narrative_style=payload.narrative_style,
        gm_config=payload.gm_config,
        ruleset_config=ruleset_config,
        world_state={},
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(session: AsyncSession = Depends(db_session)) -> list[Campaign]:
    rows = (
        await session.execute(select(Campaign).order_by(Campaign.updated_at.desc()))
    ).scalars().all()
    return list(rows)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    session: AsyncSession = Depends(db_session),
) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    await session.commit()
    await session.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await session.delete(campaign)
    await session.commit()
    return {"deleted": campaign_id}


@router.get("/{campaign_id}/events", response_model=list[EventLogOut])
async def get_events(
    campaign_id: str, limit: int = 50, session: AsyncSession = Depends(db_session)
) -> list[EventLog]:
    rows = (
        await session.execute(
            select(EventLog)
            .where(EventLog.campaign_id == campaign_id)
            .order_by(EventLog.timestamp.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)

"""Change-feed routes (clause-centric feed and single change)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from redline_agent.api.schemas.dto import ChangeOut
from redline_agent.deps import get_change_query_service, get_tenant_id
from redline_agent.services.change_query import ChangeFilters, ChangeQueryService

router = APIRouter(tags=["changes"])


class RoundChangesOut(BaseModel):
    round_id: int
    status: str
    changes: list[ChangeOut]


@router.get("/rounds/{round_id}/changes", response_model=RoundChangesOut)
async def round_changes(
    round_id: int,
    materiality: str | None = None,
    category: str | None = None,
    favored_party: str | None = None,
    risk: bool | None = None,
    feed: ChangeQueryService = Depends(get_change_query_service),
    tenant_id: str = Depends(get_tenant_id),
):
    round_ = await feed.get_round(round_id, tenant_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    filters = ChangeFilters(
        materiality=materiality,
        category=category,
        favored_party=favored_party,
        risk=risk,
    )
    changes = await feed.feed(round_id, tenant_id, filters)
    return RoundChangesOut(
        round_id=round_id,
        status=round_.status.value,
        changes=[ChangeOut.of(c) for c in changes],
    )


@router.get("/changes/{change_id}", response_model=ChangeOut)
async def get_change(
    change_id: int,
    feed: ChangeQueryService = Depends(get_change_query_service),
    tenant_id: str = Depends(get_tenant_id),
):
    change = await feed.get(change_id, tenant_id)
    if change is None:
        raise HTTPException(status_code=404, detail="Change not found")
    return ChangeOut.of(change)

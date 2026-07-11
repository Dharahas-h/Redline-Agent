"""Clause routes (cross-round clause lineage)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from redline_agent.api.schemas.dto import ClauseLineageOut
from redline_agent.deps import get_change_query_service, get_tenant_id
from redline_agent.services.change_query import ChangeQueryService

router = APIRouter(tags=["clauses"])


@router.get("/clauses/{clause_id}/lineage", response_model=ClauseLineageOut)
async def clause_lineage(
    clause_id: int,
    feed: ChangeQueryService = Depends(get_change_query_service),
    tenant_id: str = Depends(get_tenant_id),
):
    view = await feed.clause_lineage(clause_id, tenant_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Clause not found")
    return ClauseLineageOut.of(view)

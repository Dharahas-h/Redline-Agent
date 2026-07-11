"""Change-feed routes (clause-centric feed, single change, alignment override)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from redline_agent.api.schemas.dto import ChangeOut, StructuralAlertOut
from redline_agent.deps import (
    get_change_query_service,
    get_round_service,
    get_tenant_id,
)
from redline_agent.services.change_query import ChangeFilters, ChangeQueryService
from redline_agent.services.round_service import AlignmentLink, RoundService

router = APIRouter(tags=["changes"])


class RoundChangesOut(BaseModel):
    round_id: int
    status: str
    changes: list[ChangeOut]
    # Structural alerts (defined-term/table changes) surfaced prominently above
    # the change cards; not part of the deterministic change set (decision #6).
    alerts: list[StructuralAlertOut] = []


class AlignmentLinkIn(BaseModel):
    curr_clause_id: int
    prev_clause_id: int | None = None


class AlignmentOverrideIn(BaseModel):
    """A human alignment correction.

    Each link re-pairs a current clause to a prior clause (``prev_clause_id`` of
    ``null`` marks it as new). Re-pair is one link; a merge points several
    current clauses at one prior clause; a split leaves the extra current clauses
    as additions.
    """

    links: list[AlignmentLinkIn]


async def _feed_payload(
    round_id: int,
    tenant_id: str,
    feed: ChangeQueryService,
    filters: ChangeFilters,
) -> RoundChangesOut:
    round_ = await feed.get_round(round_id, tenant_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    changes = await feed.feed(round_id, tenant_id, filters)
    alignment = await feed.alignment_for_round(round_id, tenant_id)
    alerts = await feed.structural_alerts(round_id, tenant_id)
    return RoundChangesOut(
        round_id=round_id,
        status=round_.status.value,
        changes=[
            ChangeOut.of(c, alignment.get(c.curr_clause_id)) for c in changes
        ],
        alerts=[StructuralAlertOut.of(a) for a in alerts],
    )


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
    filters = ChangeFilters(
        materiality=materiality,
        category=category,
        favored_party=favored_party,
        risk=risk,
    )
    return await _feed_payload(round_id, tenant_id, feed, filters)


@router.patch("/rounds/{round_id}/alignment", response_model=RoundChangesOut)
async def override_alignment(
    round_id: int,
    body: AlignmentOverrideIn,
    rounds: RoundService = Depends(get_round_service),
    feed: ChangeQueryService = Depends(get_change_query_service),
    tenant_id: str = Depends(get_tenant_id),
):
    links = [
        AlignmentLink(
            curr_clause_id=link.curr_clause_id,
            prev_clause_id=link.prev_clause_id,
        )
        for link in body.links
    ]
    try:
        round_ = await rounds.override_alignment(round_id, tenant_id, links)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return await _feed_payload(round_id, tenant_id, feed, ChangeFilters())


@router.get("/changes/{change_id}", response_model=ChangeOut)
async def get_change(
    change_id: int,
    feed: ChangeQueryService = Depends(get_change_query_service),
    tenant_id: str = Depends(get_tenant_id),
):
    change = await feed.get(change_id, tenant_id)
    if change is None:
        raise HTTPException(status_code=404, detail="Change not found")
    lineage = (
        await feed.alignment_for_clause(change.curr_clause_id, tenant_id)
        if change.curr_clause_id is not None
        else None
    )
    return ChangeOut.of(change, lineage)

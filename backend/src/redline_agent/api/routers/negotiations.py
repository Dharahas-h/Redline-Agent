"""Negotiation and round-upload routes."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from redline_agent.api.schemas.dto import (
    NegotiationCreate,
    NegotiationDetailOut,
    NegotiationOut,
    RoundOut,
)
from redline_agent.deps import (
    get_negotiation_service,
    get_round_service,
    get_tenant_id,
)
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import RoundService

router = APIRouter(tags=["negotiations"])


@router.post("/negotiations", response_model=NegotiationOut, status_code=201)
async def create_negotiation(
    body: NegotiationCreate,
    service: NegotiationService = Depends(get_negotiation_service),
    tenant_id: str = Depends(get_tenant_id),
):
    negotiation = await service.create(
        body.title, body.represented_party, tenant_id
    )
    return NegotiationOut.of(negotiation)


@router.get("/negotiations", response_model=list[NegotiationOut])
async def list_negotiations(
    service: NegotiationService = Depends(get_negotiation_service),
    tenant_id: str = Depends(get_tenant_id),
):
    return [NegotiationOut.of(n) for n in await service.list(tenant_id)]


@router.get("/negotiations/{negotiation_id}", response_model=NegotiationDetailOut)
async def get_negotiation(
    negotiation_id: int,
    service: NegotiationService = Depends(get_negotiation_service),
    tenant_id: str = Depends(get_tenant_id),
):
    negotiation = await service.get(negotiation_id, tenant_id)
    if negotiation is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    rounds = await service.list_rounds(negotiation_id, tenant_id)
    detail = NegotiationDetailOut.of(negotiation)
    detail.rounds = [RoundOut.of(r) for r in rounds]
    return detail


@router.get(
    "/negotiations/{negotiation_id}/rounds", response_model=list[RoundOut]
)
async def list_rounds(
    negotiation_id: int,
    service: NegotiationService = Depends(get_negotiation_service),
    tenant_id: str = Depends(get_tenant_id),
):
    if await service.get(negotiation_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return [RoundOut.of(r) for r in await service.list_rounds(negotiation_id, tenant_id)]


@router.post(
    "/negotiations/{negotiation_id}/rounds",
    response_model=RoundOut,
    status_code=202,
)
async def upload_round(
    negotiation_id: int,
    background: BackgroundTasks,
    submitted_by_party: str = Form(...),
    file: UploadFile = File(...),
    negotiations: NegotiationService = Depends(get_negotiation_service),
    rounds: RoundService = Depends(get_round_service),
    tenant_id: str = Depends(get_tenant_id),
):
    if await negotiations.get(negotiation_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="A .docx file is required")

    data = await file.read()
    created = await rounds.create_round(
        negotiation_id, submitted_by_party, file.filename, data, tenant_id
    )
    background.add_task(rounds.process_round, created.id, tenant_id)
    return RoundOut.of(created)

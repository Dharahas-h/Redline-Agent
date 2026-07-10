"""Export routes: generate and download the latest-vs-prior redline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from redline_agent.api.schemas.dto import ExportOut
from redline_agent.deps import (
    get_export_service,
    get_negotiation_service,
    get_tenant_id,
)
from redline_agent.services.export import ExportService, NotEnoughRoundsError
from redline_agent.services.negotiation import NegotiationService

router = APIRouter(tags=["exports"])

_DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.post(
    "/negotiations/{negotiation_id}/export",
    response_model=ExportOut,
    status_code=201,
)
async def create_export(
    negotiation_id: int,
    negotiations: NegotiationService = Depends(get_negotiation_service),
    exports: ExportService = Depends(get_export_service),
    tenant_id: str = Depends(get_tenant_id),
):
    if await negotiations.get(negotiation_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    try:
        export = await exports.generate(negotiation_id, tenant_id)
    except NotEnoughRoundsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExportOut.of(export)


@router.get("/exports/{export_id}")
async def download_export(
    export_id: int,
    exports: ExportService = Depends(get_export_service),
    tenant_id: str = Depends(get_tenant_id),
):
    export = await exports.get(export_id, tenant_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    data = exports.read_bytes(export)
    return Response(
        content=data,
        media_type=_DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{export.filename}"'
        },
    )

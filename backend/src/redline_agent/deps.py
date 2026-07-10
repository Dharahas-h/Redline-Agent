"""FastAPI dependency providers.

Shared resources (settings, session factory, blob store) live on ``app.state``
and are wired up in the app factory. In v1 the tenant is fixed to the
configured default (decision #8: no auth yet).
"""

from __future__ import annotations

from fastapi import Request

from redline_agent.services.change_query import ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import RoundService


def get_tenant_id(request: Request) -> str:
    return request.app.state.settings.default_tenant_id


def get_negotiation_service(request: Request) -> NegotiationService:
    return NegotiationService(request.app.state.session_factory)


def get_round_service(request: Request) -> RoundService:
    return RoundService(
        request.app.state.session_factory, request.app.state.blob_store
    )


def get_change_query_service(request: Request) -> ChangeQueryService:
    return ChangeQueryService(request.app.state.session_factory)

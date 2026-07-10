"""Round application service: orchestrates the deterministic pipeline.

Upload flow: the original blob is stored and the round is flattened to
canonical text synchronously, then the round is created with ``pending`` status.
The pipeline (segment -> align -> diff -> persist) runs as a background task,
transitioning the round to ``processing`` then ``ready`` (or ``failed``).

This is the highest-value orchestration seam: with fakes injected and a real
DB, a fixture .docx drives the whole spine.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import (
    Change,
    Clause,
    ClauseLineage,
    Round,
    RoundStatus,
)
from redline_agent.infra.blob_store import BlobStore
from redline_agent.pipeline.aligner import align_positional
from redline_agent.pipeline.differ import diff_pairs
from redline_agent.pipeline.flatten import flatten_docx
from redline_agent.pipeline.segmenter import segment
from redline_agent.repositories.repos import (
    ChangeRepository,
    ClauseLineageRepository,
    ClauseRepository,
    RoundRepository,
)


class RoundService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        blob_store: BlobStore,
    ) -> None:
        self._session_factory = session_factory
        self._blob_store = blob_store

    async def create_round(
        self,
        negotiation_id: int,
        submitted_by_party: str,
        filename: str,
        data: bytes,
        tenant_id: str,
    ) -> Round:
        """Store the blob, flatten, and persist a pending round snapshot."""
        canonical_text = flatten_docx(data)
        async with self._session_factory() as session:
            rounds = RoundRepository(session)
            round_no = await rounds.next_round_no(negotiation_id, tenant_id)
            blob_uri = self._blob_store.put(
                f"{tenant_id}/{negotiation_id}/{round_no}/{filename}", data
            )
            created = await rounds.create(
                Round(
                    negotiation_id=negotiation_id,
                    round_no=round_no,
                    submitted_by_party=submitted_by_party,
                    tenant_id=tenant_id,
                    blob_uri=blob_uri,
                    canonical_text=canonical_text,
                    status=RoundStatus.PENDING,
                )
            )
            await session.commit()
            return created

    async def process_round(self, round_id: int, tenant_id: str) -> None:
        """Background task: segment this round and diff it against the prior."""
        try:
            async with self._session_factory() as session:
                await self._run_pipeline(session, round_id, tenant_id)
                await session.commit()
        except Exception:
            await self._mark_failed(round_id)
            raise

    async def _run_pipeline(
        self, session: AsyncSession, round_id: int, tenant_id: str
    ) -> None:
        rounds = RoundRepository(session)
        clauses_repo = ClauseRepository(session)
        lineage_repo = ClauseLineageRepository(session)
        changes_repo = ChangeRepository(session)

        round_ = await rounds.get(round_id, tenant_id)
        if round_ is None or round_.id is None:
            return
        await rounds.set_status(round_.id, RoundStatus.PROCESSING)

        segmented = segment(round_.canonical_text or "")
        curr_clauses = await clauses_repo.create_many(
            [
                Clause(
                    round_id=round_.id,
                    ordinal=s.ordinal,
                    text=s.text,
                    tenant_id=tenant_id,
                    number_label=s.number_label,
                    heading=s.heading,
                )
                for s in segmented
            ]
        )

        prior = await rounds.prior_round(
            round_.negotiation_id, round_.round_no, tenant_id
        )
        if prior is not None and prior.id is not None:
            prev_clauses = await clauses_repo.list_for_round(prior.id, tenant_id)
            pairs = align_positional(prev_clauses, curr_clauses)

            for pair in pairs:
                if pair.curr is None or pair.curr.id is None:
                    continue
                await lineage_repo.create(
                    ClauseLineage(
                        negotiation_id=round_.negotiation_id,
                        curr_clause_id=pair.curr.id,
                        prev_clause_id=pair.prev.id if pair.prev else None,
                        tenant_id=tenant_id,
                        similarity=pair.similarity,
                        confidence=pair.confidence,
                        align_method=pair.align_method,
                    )
                )

            diffs = diff_pairs(pairs)
            changes = [
                Change(
                    negotiation_id=round_.negotiation_id,
                    from_round_id=prior.id,
                    to_round_id=round_.id,
                    change_type=d.change_type,
                    tenant_id=tenant_id,
                    curr_clause_id=d.curr_clause.id if d.curr_clause else None,
                    prev_clause_id=d.prev_clause.id if d.prev_clause else None,
                    raw_before=d.raw_before,
                    raw_after=d.raw_after,
                )
                for d in diffs
            ]
            if changes:
                await changes_repo.create_many(changes)

        await rounds.set_status(round_.id, RoundStatus.READY)

    async def _mark_failed(self, round_id: int) -> None:
        async with self._session_factory() as session:
            await RoundRepository(session).set_status(
                round_id, RoundStatus.FAILED
            )
            await session.commit()

"""Round application service: orchestrates the deterministic pipeline.

Upload flow: the original blob is stored and the round is flattened to
canonical text synchronously, then the round is created with ``pending`` status.
The pipeline (segment -> align -> diff -> persist) runs as a background task,
transitioning the round to ``processing`` then ``ready`` (or ``failed``).

Alignment uses the embedding + structural aligner with LLM adjudication for
ambiguous cases (Slice 5); when no ``Embedder`` is injected it falls back to
Slice 1's positional alignment. A human can override the automatic pairing via
``override_alignment``, which regenerates the diff and interpretation for the
round (decision #5, the human-in-the-loop trust model).

This is the highest-value orchestration seam: with fakes injected and a real
DB, a fixture .docx drives the whole spine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import (
    AlertType,
    AlignMethod,
    Change,
    Clause,
    ClauseLineage,
    Round,
    RoundStatus,
    StructuralAlert,
)
from redline_agent.infra.blob_store import BlobStore
from redline_agent.infra.embedder import Embedder
from redline_agent.infra.llm.adjudicator import AlignmentAdjudicator
from redline_agent.infra.llm.interpreter import LLMInterpreter
from redline_agent.pipeline.aligner import AlignmentPair, align, align_positional
from redline_agent.pipeline.defined_terms import detect_definition_changes
from redline_agent.pipeline.differ import diff_pairs
from redline_agent.pipeline.flatten import flatten_docx
from redline_agent.pipeline.interpreter import interpret_changes
from redline_agent.pipeline.segmenter import segment
from redline_agent.pipeline.tables import detect_table_changes, extract_table_signatures
from redline_agent.repositories.repos import (
    ChangeRepository,
    ClauseLineageRepository,
    ClauseRepository,
    ExportRepository,
    NegotiationRepository,
    RoundRepository,
    StructuralAlertRepository,
)

logger = logging.getLogger(__name__)

# Statuses a round must be in to be deletable: the pipeline has settled, so a
# delete cannot race the background processing task.
_DELETABLE_STATUSES = (RoundStatus.READY, RoundStatus.FAILED)


class RoundNotDeletableError(Exception):
    """Raised when a round cannot be deleted (not latest, or still processing)."""


async def purge_round(
    session: AsyncSession, round_: Round, tenant_id: str
) -> list[str]:
    """Delete every DB row belonging to ``round_`` and return blob URIs to remove.

    Children are removed before parents (referencing rows first) so the cascade
    is safe under real FK enforcement. Blobs are *not* touched here — the caller
    deletes them best-effort after the DB transaction commits (the DB is the
    source of truth, so a stranded blob is preferable to a failed delete).
    Shared by round-delete and negotiation-delete so the cascade lives in one
    place.
    """
    blob_uris: list[str] = []
    if round_.blob_uri:
        blob_uris.append(round_.blob_uri)
    blob_uris.extend(
        await ExportRepository(session).delete_for_round(round_.id, tenant_id)
    )
    await StructuralAlertRepository(session).delete_for_round(round_.id, tenant_id)
    await ChangeRepository(session).delete_for_round(round_.id, tenant_id)
    await ClauseLineageRepository(session).delete_for_round(round_.id, tenant_id)
    await ClauseRepository(session).delete_for_round(round_.id, tenant_id)
    await RoundRepository(session).delete(round_.id, tenant_id)
    return blob_uris


def delete_blobs(blob_store: BlobStore, blob_uris: list[str]) -> None:
    """Best-effort blob removal: a failure is logged, never raised.

    The DB rows are already committed by the time this runs, so a blob-store
    failure must not surface as an error — the round is logically deleted.
    """
    for uri in blob_uris:
        try:
            blob_store.delete(uri)
        except Exception:  # noqa: BLE001 - the DB rows are already gone
            logger.warning("Failed to delete blob %s", uri, exc_info=True)


@dataclass
class AlignmentLink:
    """A single human-supplied clause pairing for an override.

    ``prev_clause_id`` of ``None`` marks the current clause as new (added).
    Re-pair is one link; a merge points several current clauses at the same
    prior clause; a split leaves the extra current clauses as additions.
    """

    curr_clause_id: int
    prev_clause_id: int | None = None


class RoundService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        blob_store: BlobStore,
        interpreter: LLMInterpreter,
        embedder: Embedder | None = None,
        adjudicator: AlignmentAdjudicator | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._blob_store = blob_store
        self._interpreter = interpreter
        self._embedder = embedder
        self._adjudicator = adjudicator

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
        table_signatures = extract_table_signatures(data)
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
                    table_signatures=table_signatures,
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

    async def _align(
        self, prev: list[Clause], curr: list[Clause]
    ) -> list[AlignmentPair]:
        if self._embedder is None:
            return align_positional(prev, curr)
        return await align(prev, curr, self._embedder, self._adjudicator)

    async def _run_pipeline(
        self, session: AsyncSession, round_id: int, tenant_id: str
    ) -> None:
        rounds = RoundRepository(session)
        clauses_repo = ClauseRepository(session)
        lineage_repo = ClauseLineageRepository(session)

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
            pairs = await self._align(prev_clauses, curr_clauses)

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

            await self._regenerate_changes(session, round_, prior, pairs, tenant_id)

        await rounds.set_status(round_.id, RoundStatus.READY)

    async def _regenerate_changes(
        self,
        session: AsyncSession,
        round_: Round,
        prior: Round,
        pairs: list[AlignmentPair],
        tenant_id: str,
    ) -> None:
        """Diff the pairs, interpret material changes, and persist them.

        The deterministic differ is the sole authority on which changes exist;
        interpretation only annotates them (decision #1). Existing changes for
        the round are cleared first so this is idempotent and safe to re-run on
        an override.
        """
        changes_repo = ChangeRepository(session)
        await changes_repo.delete_for_round(round_.id, tenant_id)

        negotiation = await NegotiationRepository(session).get(
            round_.negotiation_id, tenant_id
        )
        represented_party = negotiation.represented_party if negotiation else ""

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
            await interpret_changes(changes, self._interpreter, represented_party)
            await changes_repo.create_many(changes)

        await self._regenerate_alerts(session, round_, prior, pairs, tenant_id)

    async def _regenerate_alerts(
        self,
        session: AsyncSession,
        round_: Round,
        prior: Round,
        pairs: list[AlignmentPair],
        tenant_id: str,
    ) -> None:
        """Rebuild the round's structural alerts from the diffed pairs.

        Structural alerts (definition changes, table changes) are surfaced
        alongside the change feed but are *not* changes — the deterministic
        differ still owns the change set (decision #1). Existing alerts are
        cleared first so this is idempotent on an override re-run.
        """
        alerts_repo = StructuralAlertRepository(session)
        await alerts_repo.delete_for_round(round_.id, tenant_id)

        prev_texts = [p.prev.text for p in pairs if p.prev is not None]
        curr_texts = [p.curr.text for p in pairs if p.curr is not None]

        alerts: list[StructuralAlert] = []
        for dc in detect_definition_changes(prev_texts, curr_texts):
            noun = "clause" if dc.affected_clause_count == 1 else "clauses"
            alerts.append(
                StructuralAlert(
                    negotiation_id=round_.negotiation_id,
                    from_round_id=prior.id,
                    to_round_id=round_.id,
                    alert_type=AlertType.DEFINITION_CHANGED,
                    subject=dc.term,
                    detail=(
                        f'Definition of "{dc.term}" changed — affects '
                        f"{dc.affected_clause_count} {noun}."
                    ),
                    affected_clause_count=dc.affected_clause_count,
                    tenant_id=tenant_id,
                )
            )

        table_changes = detect_table_changes(
            prior.table_signatures or [], round_.table_signatures or []
        )
        for tc in table_changes:
            alerts.append(
                StructuralAlert(
                    negotiation_id=round_.negotiation_id,
                    from_round_id=prior.id,
                    to_round_id=round_.id,
                    alert_type=AlertType.TABLE_CHANGED,
                    subject=None,
                    detail=f"Table {tc.position} was {tc.kind} — review manually.",
                    affected_clause_count=None,
                    tenant_id=tenant_id,
                )
            )

        if alerts:
            await alerts_repo.create_many(alerts)

    async def override_alignment(
        self, round_id: int, tenant_id: str, links: list[AlignmentLink]
    ) -> Round | None:
        """Apply human alignment corrections and regenerate the round's diff.

        Each link re-pairs a current clause to a prior clause (or to nothing).
        Affected lineage links are marked ``overridden`` with method ``override``
        and full confidence; the diff and interpretation are then rebuilt from
        the corrected lineage. Returns ``None`` if the round is unknown, or
        raises ``ValueError`` if a link references clauses outside this round.
        """
        async with self._session_factory() as session:
            rounds = RoundRepository(session)
            clauses_repo = ClauseRepository(session)
            lineage_repo = ClauseLineageRepository(session)

            round_ = await rounds.get(round_id, tenant_id)
            if round_ is None or round_.id is None:
                return None
            prior = await rounds.prior_round(
                round_.negotiation_id, round_.round_no, tenant_id
            )
            if prior is None or prior.id is None:
                # No prior round -> nothing to align; the override is a no-op.
                return round_

            curr_clauses = await clauses_repo.list_for_round(round_.id, tenant_id)
            prev_clauses = await clauses_repo.list_for_round(prior.id, tenant_id)
            curr_ids = {c.id for c in curr_clauses}
            prev_ids = {c.id for c in prev_clauses}

            for link in links:
                if link.curr_clause_id not in curr_ids:
                    raise ValueError(
                        f"Clause {link.curr_clause_id} is not in this round"
                    )
                if (
                    link.prev_clause_id is not None
                    and link.prev_clause_id not in prev_ids
                ):
                    raise ValueError(
                        f"Clause {link.prev_clause_id} is not in the prior round"
                    )
                existing = await lineage_repo.get_by_curr_clause(
                    link.curr_clause_id, tenant_id
                )
                if existing is None:
                    await lineage_repo.create(
                        ClauseLineage(
                            negotiation_id=round_.negotiation_id,
                            curr_clause_id=link.curr_clause_id,
                            prev_clause_id=link.prev_clause_id,
                            tenant_id=tenant_id,
                            similarity=None,
                            confidence=1.0,
                            align_method=AlignMethod.OVERRIDE,
                            overridden=True,
                        )
                    )
                else:
                    existing.prev_clause_id = link.prev_clause_id
                    existing.similarity = None
                    existing.confidence = 1.0
                    existing.align_method = AlignMethod.OVERRIDE
                    existing.overridden = True
                    await lineage_repo.update(existing)

            pairs = await self._pairs_from_lineage(
                session, round_.id, tenant_id, prev_clauses, curr_clauses
            )
            await self._regenerate_changes(session, round_, prior, pairs, tenant_id)
            await session.commit()
            return round_

    async def _pairs_from_lineage(
        self,
        session: AsyncSession,
        round_id: int,
        tenant_id: str,
        prev_clauses: list[Clause],
        curr_clauses: list[Clause],
    ) -> list[AlignmentPair]:
        """Rebuild alignment pairs from the round's persisted lineage links."""
        lineage_repo = ClauseLineageRepository(session)
        lineage = await lineage_repo.list_for_round(round_id, tenant_id)
        by_curr = {link.curr_clause_id: link for link in lineage}
        prev_by_id = {c.id: c for c in prev_clauses}

        used_prev: set[int] = set()
        pairs: list[AlignmentPair] = []
        for c in curr_clauses:
            link = by_curr.get(c.id)
            prev = (
                prev_by_id.get(link.prev_clause_id)
                if link and link.prev_clause_id is not None
                else None
            )
            if prev is not None:
                used_prev.add(prev.id)
            pairs.append(
                AlignmentPair(
                    prev=prev,
                    curr=c,
                    align_method=link.align_method if link else AlignMethod.POSITIONAL,
                    similarity=link.similarity if link else None,
                    confidence=link.confidence if link else 1.0,
                )
            )
        for c in prev_clauses:
            if c.id not in used_prev:
                pairs.append(AlignmentPair(prev=c, curr=None))
        return pairs

    async def delete_round(
        self, negotiation_id: int, round_id: int, tenant_id: str
    ) -> bool:
        """Hard-delete the latest round of a negotiation and its blobs.

        Returns ``False`` if the round is unknown or not part of this
        negotiation/tenant (the router maps that to 404). Raises
        ``RoundNotDeletableError`` (mapped to 409) if the round is not the
        latest, or is still ``pending``/``processing``.
        """
        async with self._session_factory() as session:
            rounds = RoundRepository(session)
            round_ = await rounds.get(round_id, tenant_id)
            if round_ is None or round_.negotiation_id != negotiation_id:
                return False

            all_rounds = await rounds.list_for_negotiation(negotiation_id, tenant_id)
            latest = all_rounds[-1] if all_rounds else None
            if latest is None or latest.id != round_id:
                raise RoundNotDeletableError(
                    "Only the latest round of a negotiation can be deleted."
                )
            if round_.status not in _DELETABLE_STATUSES:
                raise RoundNotDeletableError(
                    "This round is still processing; try again once it is ready."
                )

            blob_uris = await purge_round(session, round_, tenant_id)
            await session.commit()

        delete_blobs(self._blob_store, blob_uris)
        return True

    async def _mark_failed(self, round_id: int) -> None:
        async with self._session_factory() as session:
            await RoundRepository(session).set_status(
                round_id, RoundStatus.FAILED
            )
            await session.commit()

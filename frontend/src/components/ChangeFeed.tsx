import { useEffect, useState } from "react";
import { getRoundChanges, updateAlignment } from "../api/client";
import type { RoundChanges } from "../types";
import { ChangeCard } from "./ChangeCard";
import type { AlignmentCandidate } from "./AlignmentOverride";

const CATEGORY_OPTIONS = [
  ["payment", "Payment"],
  ["liability", "Liability"],
  ["ip", "IP"],
  ["termination", "Termination"],
  ["confidentiality", "Confidentiality"],
  ["other", "Other"],
] as const;

const FAVORED_PARTY_OPTIONS = [
  ["represented", "Favors me"],
  ["counterparty", "Favors them"],
  ["neutral", "Neutral"],
] as const;

export function ChangeFeed({ roundId }: { roundId: number }) {
  const [data, setData] = useState<RoundChanges | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hideCosmetic, setHideCosmetic] = useState(false);
  const [category, setCategory] = useState("");
  const [favoredParty, setFavoredParty] = useState("");
  const [riskOnly, setRiskOnly] = useState(false);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    setData(null);
    setError(null);

    // Server-side filters: hide cosmetic == substantive-only.
    const filters = {
      materiality: hideCosmetic ? "substantive" : undefined,
      category: category || undefined,
      favoredParty: favoredParty || undefined,
      risk: riskOnly || undefined,
    };

    const poll = () => {
      getRoundChanges(roundId, filters)
        .then((d) => {
          if (!active) return;
          setData(d);
          // Keep polling while the pipeline is still running.
          if (d.status !== "ready" && d.status !== "failed") {
            timer = setTimeout(poll, 1000);
          }
        })
        .catch((e) => active && setError(String(e)));
    };
    poll();

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [roundId, hideCosmetic, category, favoredParty, riskOnly]);

  // Correcting an alignment regenerates the diff server-side; swap in the
  // refreshed feed it returns.
  const handleOverride = async (
    currClauseId: number,
    prevClauseId: number | null,
  ) => {
    const refreshed = await updateAlignment(roundId, [
      { curr_clause_id: currClauseId, prev_clause_id: prevClauseId },
    ]);
    setData(refreshed);
  };

  if (error) return <p role="alert">Failed to load changes: {error}</p>;
  if (!data) return <p>Loading changes…</p>;
  if (data.status !== "ready")
    return <p data-testid="round-status">Round is {data.status}…</p>;

  // Candidate prior clauses for re-pairing, derived from the feed itself.
  const candidateMap = new Map<number, AlignmentCandidate>();
  for (const c of data.changes) {
    if (c.prev_clause_id !== null && !candidateMap.has(c.prev_clause_id)) {
      const label = (c.raw_before ?? "").slice(0, 80) || `Clause ${c.prev_clause_id}`;
      candidateMap.set(c.prev_clause_id, {
        prev_clause_id: c.prev_clause_id,
        label,
      });
    }
  }
  const candidates = [...candidateMap.values()];

  return (
    <section className="change-feed" data-testid="change-feed">
      <div className="feed-controls">
        <label>
          <input
            type="checkbox"
            checked={hideCosmetic}
            onChange={(e) => setHideCosmetic(e.target.checked)}
          />
          Hide cosmetic changes
        </label>
        <label>
          Category
          <select
            aria-label="Filter by category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {CATEGORY_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Favored party
          <select
            aria-label="Filter by favored party"
            value={favoredParty}
            onChange={(e) => setFavoredParty(e.target.value)}
          >
            <option value="">Either side</option>
            {FAVORED_PARTY_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={riskOnly}
            onChange={(e) => setRiskOnly(e.target.checked)}
          />
          Flagged for review only
        </label>
      </div>
      {data.changes.length === 0 ? (
        <p data-testid="no-changes">No changes in this round.</p>
      ) : (
        <>
          <h3>{data.changes.length} changed clauses</h3>
          {data.changes.map((c) => (
            <ChangeCard
              key={c.id}
              change={c}
              candidates={candidates.filter(
                (cand) => cand.prev_clause_id !== c.prev_clause_id,
              )}
              onOverride={handleOverride}
            />
          ))}
        </>
      )}
    </section>
  );
}

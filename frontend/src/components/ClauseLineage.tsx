import { useEffect, useState } from "react";
import { getClauseLineage } from "../api/client";
import type { ClauseLineage as Lineage } from "../types";

const MATERIALITY_LABELS: Record<string, string> = {
  substantive: "Substantive",
  cosmetic: "Cosmetic",
};

// Drill-down: how a single clause evolved across every round of the
// negotiation. Fetches the clause's cross-round lineage and lays it out in
// round order, so the payoff of the stateful tracker — the whole life of one
// clause — is visible from any change in the feed.
export function ClauseLineage({ clauseId }: { clauseId: number }) {
  const [lineage, setLineage] = useState<Lineage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLineage(null);
    setError(null);
    getClauseLineage(clauseId)
      .then((l) => active && setLineage(l))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [clauseId]);

  if (error) return <p role="alert">Failed to load lineage: {error}</p>;
  if (!lineage) return <p>Loading lineage…</p>;

  return (
    <section className="clause-lineage" data-testid="clause-lineage">
      <h4>Clause history across rounds</h4>
      {lineage.entries.length === 1 && (
        <p data-testid="lineage-single">
          This clause first appears here — no earlier rounds to trace.
        </p>
      )}
      <ol className="lineage-timeline">
        {lineage.entries.map((entry) => (
          <li
            key={entry.clause_id}
            className="lineage-entry"
            data-testid="lineage-entry"
          >
            <div className="lineage-round" data-testid="lineage-round">
              Round {entry.round_no} — {entry.submitted_by_party}
            </div>
            {entry.change && (
              <div className="lineage-change" data-testid="lineage-change">
                <span className={`change-type ${entry.change.change_type}`}>
                  {entry.change.change_type}
                </span>
                {entry.change.materiality && (
                  <span
                    className={`materiality-badge ${entry.change.materiality}`}
                  >
                    {MATERIALITY_LABELS[entry.change.materiality] ??
                      entry.change.materiality}
                  </span>
                )}
                {entry.change.summary && (
                  <p className="summary" data-machine-generated="true">
                    {entry.change.summary}
                  </p>
                )}
              </div>
            )}
            <pre className="lineage-text" data-testid="lineage-text">
              {entry.text}
            </pre>
          </li>
        ))}
      </ol>
    </section>
  );
}

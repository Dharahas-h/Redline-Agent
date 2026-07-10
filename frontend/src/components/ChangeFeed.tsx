import { useEffect, useState } from "react";
import { getRoundChanges } from "../api/client";
import type { RoundChanges } from "../types";
import { ChangeCard } from "./ChangeCard";

export function ChangeFeed({ roundId }: { roundId: number }) {
  const [data, setData] = useState<RoundChanges | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hideCosmetic, setHideCosmetic] = useState(false);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    setData(null);
    setError(null);

    // Server-side materiality filter: hide cosmetic == substantive-only.
    const materiality = hideCosmetic ? "substantive" : undefined;

    const poll = () => {
      getRoundChanges(roundId, materiality)
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
  }, [roundId, hideCosmetic]);

  if (error) return <p role="alert">Failed to load changes: {error}</p>;
  if (!data) return <p>Loading changes…</p>;
  if (data.status !== "ready")
    return <p data-testid="round-status">Round is {data.status}…</p>;

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
      </div>
      {data.changes.length === 0 ? (
        <p data-testid="no-changes">No changes in this round.</p>
      ) : (
        <>
          <h3>{data.changes.length} changed clauses</h3>
          {data.changes.map((c) => (
            <ChangeCard key={c.id} change={c} />
          ))}
        </>
      )}
    </section>
  );
}

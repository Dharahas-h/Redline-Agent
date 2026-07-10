import type { Change } from "../types";

const LABELS: Record<string, string> = {
  added: "Added",
  removed: "Removed",
  modified: "Modified",
};

const MATERIALITY_LABELS: Record<string, string> = {
  substantive: "Substantive",
  cosmetic: "Cosmetic",
};

export function ChangeCard({ change }: { change: Change }) {
  return (
    <article className="change-card" data-testid="change-card">
      <header>
        <span className="change-type" data-testid="change-type">
          {LABELS[change.change_type] ?? change.change_type}
        </span>
        {change.materiality && (
          <span
            className={`materiality-badge ${change.materiality}`}
            data-testid="materiality-badge"
          >
            {MATERIALITY_LABELS[change.materiality] ?? change.materiality}
          </span>
        )}
      </header>
      {change.summary && (
        <div className="summary" data-testid="summary" data-machine-generated="true">
          <p>{change.summary}</p>
          <small className="disclaimer">
            Machine-generated — attorney work-product for review.
          </small>
        </div>
      )}
      {change.raw_before !== null && (
        <div className="raw before">
          <h4>Before</h4>
          <pre data-testid="raw-before">{change.raw_before}</pre>
        </div>
      )}
      {change.raw_after !== null && (
        <div className="raw after">
          <h4>After</h4>
          <pre data-testid="raw-after">{change.raw_after}</pre>
        </div>
      )}
    </article>
  );
}

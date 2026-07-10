import type { Change } from "../types";

const LABELS: Record<string, string> = {
  added: "Added",
  removed: "Removed",
  modified: "Modified",
};

export function ChangeCard({ change }: { change: Change }) {
  return (
    <article className="change-card" data-testid="change-card">
      <header>
        <span className="change-type" data-testid="change-type">
          {LABELS[change.change_type] ?? change.change_type}
        </span>
      </header>
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

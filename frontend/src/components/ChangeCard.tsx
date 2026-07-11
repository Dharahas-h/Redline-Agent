import type { Change } from "../types";
import { AlignmentOverride } from "./AlignmentOverride";
import type { AlignmentCandidate } from "./AlignmentOverride";

const LABELS: Record<string, string> = {
  added: "Added",
  removed: "Removed",
  modified: "Modified",
};

const MATERIALITY_LABELS: Record<string, string> = {
  substantive: "Substantive",
  cosmetic: "Cosmetic",
};

// Favored-party is stored relative to the represented party, so the badge maps
// straight to the user's point of view.
const FAVORED_PARTY_LABELS: Record<string, string> = {
  represented: "Favors me",
  counterparty: "Favors them",
  neutral: "Neutral",
};

const CATEGORY_LABELS: Record<string, string> = {
  payment: "Payment",
  liability: "Liability",
  ip: "IP",
  termination: "Termination",
  confidentiality: "Confidentiality",
  other: "Other",
};

export function ChangeCard({
  change,
  candidates,
  onOverride,
}: {
  change: Change;
  candidates?: AlignmentCandidate[];
  onOverride?: (currClauseId: number, prevClauseId: number | null) => void;
}) {
  return (
    <article className="change-card" data-testid="change-card">
      <header>
        <span className="change-type" data-testid="change-type">
          {LABELS[change.change_type] ?? change.change_type}
        </span>
        {change.low_confidence && (
          <span
            className="low-confidence-badge"
            data-testid="low-confidence-badge"
            role="note"
          >
            Uncertain match — please review
          </span>
        )}
        {change.overridden && (
          <span className="overridden-badge" data-testid="overridden-badge">
            Match corrected
          </span>
        )}
        {change.materiality && (
          <span
            className={`materiality-badge ${change.materiality}`}
            data-testid="materiality-badge"
          >
            {MATERIALITY_LABELS[change.materiality] ?? change.materiality}
          </span>
        )}
        {change.favored_party && (
          <span
            className={`favored-party-badge ${change.favored_party}`}
            data-testid="favored-party-badge"
          >
            {FAVORED_PARTY_LABELS[change.favored_party] ?? change.favored_party}
          </span>
        )}
        {change.category && (
          <span
            className={`category-tag ${change.category}`}
            data-testid="category-tag"
          >
            {CATEGORY_LABELS[change.category] ?? change.category}
          </span>
        )}
      </header>
      {change.risk_flag && (
        <p className="risk-flag" data-testid="risk-flag" role="note">
          ⚠ {change.risk_flag}
        </p>
      )}
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
      {onOverride && change.curr_clause_id !== null && (
        <AlignmentOverride
          change={change}
          candidates={candidates ?? []}
          onOverride={onOverride}
        />
      )}
    </article>
  );
}

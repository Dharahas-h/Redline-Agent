// Mirrors backend DTOs (redline_agent/api/schemas/dto.py).

export interface Negotiation {
  id: number;
  title: string;
  represented_party: string;
  created_at?: string | null;
}

export interface Round {
  id: number;
  negotiation_id: number;
  round_no: number;
  submitted_by_party: string;
  status: string;
  created_at?: string | null;
}

export interface NegotiationDetail extends Negotiation {
  rounds: Round[];
}

export type ChangeType = "added" | "removed" | "modified";

export interface Change {
  id: number;
  change_type: ChangeType;
  curr_clause_id: number | null;
  prev_clause_id: number | null;
  raw_before: string | null;
  raw_after: string | null;
  summary: string | null;
  materiality: string | null;
  category: string | null;
  favored_party: string | null;
  risk_flag: string | null;
  // Alignment provenance for this clause's match (clause lineage).
  alignment_confidence: number | null;
  alignment_method: string | null;
  alignment_similarity: number | null;
  low_confidence: boolean;
  overridden: boolean;
}

// A structural alert surfaced alongside the feed: a defined-term definition
// change (with its reference ripple count) or a table change flagged for manual
// review. Not a change — the deterministic differ owns the change set.
export type AlertType = "definition_changed" | "table_changed";

export interface StructuralAlert {
  id: number;
  alert_type: AlertType;
  subject: string | null;
  detail: string;
  affected_clause_count: number | null;
}

export interface RoundChanges {
  round_id: number;
  status: string;
  changes: Change[];
  alerts: StructuralAlert[];
}

// One round's view of a clause in its cross-round lineage.
export interface LineageEntry {
  round_id: number;
  round_no: number;
  submitted_by_party: string;
  clause_id: number;
  number_label: string | null;
  heading: string | null;
  text: string;
  // How the clause changed from the prior round; null in the round it first
  // appears with no prior.
  change: Change | null;
}

// A clause's evolution across every round of the negotiation, in order.
export interface ClauseLineage {
  clause_id: number;
  negotiation_id: number;
  entries: LineageEntry[];
}

export interface Export {
  id: number;
  negotiation_id: number;
  from_round_id: number;
  to_round_id: number;
  filename: string;
  created_at?: string | null;
}

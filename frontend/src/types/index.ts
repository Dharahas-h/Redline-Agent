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
}

export interface RoundChanges {
  round_id: number;
  status: string;
  changes: Change[];
}

export interface Export {
  id: number;
  negotiation_id: number;
  from_round_id: number;
  to_round_id: number;
  filename: string;
  created_at?: string | null;
}

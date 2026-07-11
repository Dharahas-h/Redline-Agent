// Typed API client: one function per backend route.

import type {
  Change,
  Export,
  Negotiation,
  NegotiationDetail,
  Round,
  RoundChanges,
} from "../types";

const BASE = "";

async function json<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText}`);
  }
  return (await resp.json()) as T;
}

export async function createNegotiation(
  title: string,
  representedParty: string,
): Promise<Negotiation> {
  return json(
    await fetch(`${BASE}/negotiations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, represented_party: representedParty }),
    }),
  );
}

export async function listNegotiations(): Promise<Negotiation[]> {
  return json(await fetch(`${BASE}/negotiations`));
}

export async function getNegotiation(id: number): Promise<NegotiationDetail> {
  return json(await fetch(`${BASE}/negotiations/${id}`));
}

export async function uploadRound(
  negotiationId: number,
  submittedByParty: string,
  file: File,
): Promise<Round> {
  const form = new FormData();
  form.append("submitted_by_party", submittedByParty);
  form.append("file", file);
  return json(
    await fetch(`${BASE}/negotiations/${negotiationId}/rounds`, {
      method: "POST",
      body: form,
    }),
  );
}

export async function listRounds(negotiationId: number): Promise<Round[]> {
  return json(await fetch(`${BASE}/negotiations/${negotiationId}/rounds`));
}

export interface ChangeFeedFilters {
  materiality?: string;
  category?: string;
  favoredParty?: string;
  risk?: boolean;
}

export async function getRoundChanges(
  roundId: number,
  filters: ChangeFeedFilters = {},
): Promise<RoundChanges> {
  const params = new URLSearchParams();
  if (filters.materiality) params.set("materiality", filters.materiality);
  if (filters.category) params.set("category", filters.category);
  if (filters.favoredParty) params.set("favored_party", filters.favoredParty);
  if (filters.risk) params.set("risk", "true");
  const query = params.toString();
  return json(
    await fetch(`${BASE}/rounds/${roundId}/changes${query ? `?${query}` : ""}`),
  );
}

export async function getChange(changeId: number): Promise<Change> {
  return json(await fetch(`${BASE}/changes/${changeId}`));
}

export async function createExport(negotiationId: number): Promise<Export> {
  return json(
    await fetch(`${BASE}/negotiations/${negotiationId}/export`, {
      method: "POST",
    }),
  );
}

// The download URL for a generated redline; used as an anchor href so the
// browser handles the .docx attachment download.
export function exportDownloadUrl(exportId: number): string {
  return `${BASE}/exports/${exportId}`;
}

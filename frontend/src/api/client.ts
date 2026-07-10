// Typed API client: one function per backend route.

import type {
  Change,
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

export async function getRoundChanges(
  roundId: number,
): Promise<RoundChanges> {
  return json(await fetch(`${BASE}/rounds/${roundId}/changes`));
}

export async function getChange(changeId: number): Promise<Change> {
  return json(await fetch(`${BASE}/changes/${changeId}`));
}

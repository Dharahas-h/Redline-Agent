import { useEffect, useRef, useState } from "react";
import { getNegotiation, listRounds, uploadRound } from "../api/client";
import type { NegotiationDetail as Detail, Round } from "../types";
import { ChangeFeed } from "../components/ChangeFeed";
import { ExportButton } from "../components/ExportButton";

export function NegotiationDetail({ negotiationId }: { negotiationId: number }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [party, setParty] = useState("");
  const [selectedRound, setSelectedRound] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    setDetail(await getNegotiation(negotiationId));
    setRounds(await listRounds(negotiationId));
  };
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [negotiationId]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file || !party) return;
    const round = await uploadRound(negotiationId, party, file);
    if (fileRef.current) fileRef.current.value = "";
    setParty("");
    await refresh();
    setSelectedRound(round.id);
  };

  if (!detail) return <p>Loading…</p>;

  return (
    <section>
      <h2>{detail.title}</h2>
      <p>Representing: {detail.represented_party}</p>

      <form onSubmit={submit} aria-label="upload-round">
        <input
          aria-label="submitted_by_party"
          placeholder="Submitted by party"
          value={party}
          onChange={(e) => setParty(e.target.value)}
        />
        <input aria-label="round-file" type="file" accept=".docx" ref={fileRef} />
        <button type="submit">Upload round</button>
      </form>

      <ExportButton negotiationId={negotiationId} />

      <h3>Rounds</h3>
      <ul>
        {rounds.map((r) => (
          <li key={r.id}>
            <button onClick={() => setSelectedRound(r.id)}>
              Round {r.round_no} — {r.submitted_by_party} ({r.status})
            </button>
          </li>
        ))}
      </ul>

      {selectedRound !== null && <ChangeFeed roundId={selectedRound} />}
    </section>
  );
}

import { useEffect, useState } from "react";
import { createNegotiation, listNegotiations } from "../api/client";
import type { Negotiation } from "../types";

export function NegotiationList({
  onSelect,
}: {
  onSelect: (id: number) => void;
}) {
  const [items, setItems] = useState<Negotiation[]>([]);
  const [title, setTitle] = useState("");
  const [party, setParty] = useState("");

  const refresh = () => listNegotiations().then(setItems);
  useEffect(() => {
    refresh();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !party) return;
    await createNegotiation(title, party);
    setTitle("");
    setParty("");
    await refresh();
  };

  return (
    <section>
      <h2>Negotiations</h2>
      <form onSubmit={submit} aria-label="create-negotiation">
        <input
          aria-label="title"
          placeholder="Contract title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          aria-label="represented_party"
          placeholder="Party you represent"
          value={party}
          onChange={(e) => setParty(e.target.value)}
        />
        <button type="submit">Create negotiation</button>
      </form>
      <ul>
        {items.map((n) => (
          <li key={n.id}>
            <button onClick={() => onSelect(n.id)}>
              {n.title} — representing {n.represented_party}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

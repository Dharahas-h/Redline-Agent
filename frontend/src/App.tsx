import { useState } from "react";
import { NegotiationList } from "./pages/NegotiationList";
import { NegotiationDetail } from "./pages/NegotiationDetail";

export default function App() {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "1.5rem" }}>
      <h1>Redline Agent</h1>
      <p>Machine-generated work-product for attorney review.</p>
      {selected === null ? (
        <NegotiationList onSelect={setSelected} />
      ) : (
        <>
          <button onClick={() => setSelected(null)}>← All negotiations</button>
          <NegotiationDetail negotiationId={selected} />
        </>
      )}
    </main>
  );
}

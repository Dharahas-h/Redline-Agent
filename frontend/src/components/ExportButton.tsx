import { useState } from "react";
import { createExport, exportDownloadUrl } from "../api/client";
import type { Export } from "../types";

// Generates a latest-vs-prior tracked-changes .docx for the negotiation, then
// surfaces a download link for the produced redline. Disabled while a redline
// is being generated; a negotiation needs two rounds before one can be made.
export function ExportButton({ negotiationId }: { negotiationId: number }) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState<Export | null>(null);

  const generate = async () => {
    setGenerating(true);
    setError(null);
    setReady(null);
    try {
      setReady(await createExport(negotiationId));
    } catch {
      setError("Could not generate a redline (two rounds are required).");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <section aria-label="export-redline">
      <button type="button" onClick={generate} disabled={generating}>
        {generating ? "Generating redline…" : "Export redline"}
      </button>
      {error && <p data-testid="export-error">{error}</p>}
      {ready && (
        <a
          data-testid="download-redline"
          href={exportDownloadUrl(ready.id)}
          download={ready.filename}
        >
          Download {ready.filename}
        </a>
      )}
    </section>
  );
}

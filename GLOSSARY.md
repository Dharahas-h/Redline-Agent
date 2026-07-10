# Glossary

Use these exact terms in code, database columns, API contracts, and UI copy.
Avoid synonyms (e.g. do not use "version" for round, or "diff" for change).

- **Negotiation** — the top-level container for one contract being negotiated
  over time. Owns rounds, the represented party, and all history.
- **Round** — one submitted `.docx` at a point in time, with a round number and
  the party who submitted it. Stored as its original blob plus a flattened
  canonical-text snapshot.
- **Represented party** — the side the user acts for, declared when the
  negotiation is created. Favored-party analysis is computed relative to it.
- **Canonical text** — the flattened, normalized plain-text form of a round's
  `.docx`, used as the basis for segmentation and diffing.
- **Clause** — a logical unit of a round (a numbered section, heading block,
  etc.) produced by segmentation. The unit of alignment, diffing, and display.
- **Segmentation** — splitting a round's canonical text into clauses using the
  document's heading/numbering structure.
- **Alignment** — matching a clause in one round to its counterpart in the
  prior round, despite renumbering, splits, merges, or moves.
- **Clause lineage** — the chain of aligned clauses across rounds; how a single
  clause evolved over the whole negotiation.
- **Change** — a detected delta between a pair of aligned clauses across two
  rounds. The deterministic differ is the sole authority on what changes exist.
- **Materiality** — whether a change is substantive or cosmetic.
- **Category** — the subject tag of a change (payment, liability, IP,
  termination, confidentiality, etc.).
- **Favored-party** — which side a change benefits, relative to the represented
  party.
- **Risk flag** — an attorney-review prompt on an unusual or aggressive change.
  Always framed as a prompt for review, never a legal conclusion.
- **Interpretation** — the LLM-generated annotation of a change (summary,
  materiality, category, favored-party, risk flag). Annotates existing changes;
  never creates them.
- **Redline** — the exported tracked-changes `.docx` (latest round vs prior),
  produced by the standalone export and opened in Word.
- **Confidence** — the certainty of an alignment, from embedding similarity and
  whether the LLM fallback was invoked. Low-confidence matches are flagged.
- **Override** — a human correction of an alignment (re-pair / split / merge)
  that regenerates the affected diff and interpretation.

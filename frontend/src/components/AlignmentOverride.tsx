import { useState } from "react";
import type { Change } from "../types";

// A prior clause the current clause could be re-paired to. Derived from the
// feed, so no extra endpoint is needed to populate the choices.
export interface AlignmentCandidate {
  prev_clause_id: number;
  label: string;
}

// Lets a user correct a clause match when the automatic alignment is wrong:
// re-pair to a different prior clause, or mark the clause as new (no prior).
// Submitting regenerates the diff and interpretation server-side.
export function AlignmentOverride({
  change,
  candidates,
  onOverride,
}: {
  change: Change;
  candidates: AlignmentCandidate[];
  onOverride: (currClauseId: number, prevClauseId: number | null) => void;
}) {
  const [open, setOpen] = useState(false);
  // "" is the "new clause / no prior match" choice.
  const [choice, setChoice] = useState<string>(
    change.prev_clause_id !== null ? String(change.prev_clause_id) : "",
  );

  if (change.curr_clause_id === null) return null;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onOverride(change.curr_clause_id!, choice === "" ? null : Number(choice));
    setOpen(false);
  };

  return (
    <div className="alignment-override" data-testid="alignment-override">
      {!open ? (
        <button type="button" onClick={() => setOpen(true)}>
          Fix match
        </button>
      ) : (
        <form onSubmit={submit} aria-label="fix-alignment">
          <label>
            Correct prior clause
            <select
              aria-label="prior clause"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
            >
              <option value="">New clause (no prior match)</option>
              {candidates.map((c) => (
                <option key={c.prev_clause_id} value={c.prev_clause_id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <button type="submit">Apply</button>
          <button type="button" onClick={() => setOpen(false)}>
            Cancel
          </button>
        </form>
      )}
    </div>
  );
}

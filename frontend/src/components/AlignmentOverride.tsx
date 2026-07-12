import { useState } from "react";
import { Box, Button, Stack, TextField } from "@mui/material";
import TuneIcon from "@mui/icons-material/TuneRounded";
import type { Change } from "../types";
import { C } from "./common/redline";

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
    <Box className="alignment-override" data-testid="alignment-override">
      {!open ? (
        <Button
          type="button"
          size="small"
          variant="outlined"
          startIcon={<TuneIcon />}
          onClick={() => setOpen(true)}
        >
          Fix match
        </Button>
      ) : (
        <Box
          component="form"
          onSubmit={submit}
          aria-label="fix-alignment"
          sx={{
            p: 2,
            bgcolor: C.snow,
            border: `1px solid ${C.cloud}`,
            borderRadius: 2,
          }}
        >
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.5}
            sx={{ alignItems: { sm: "flex-end" } }}
          >
            <TextField
              select
              label="Correct prior clause"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
              SelectProps={{ native: true }}
              inputProps={{ "aria-label": "prior clause" }}
              size="small"
              fullWidth
            >
              <option value="">New clause (no prior match)</option>
              {candidates.map((c) => (
                <option key={c.prev_clause_id} value={c.prev_clause_id}>
                  {c.label}
                </option>
              ))}
            </TextField>
            <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
              <Button type="submit" variant="contained" size="small">
                Apply
              </Button>
              <Button type="button" size="small" onClick={() => setOpen(false)}>
                Cancel
              </Button>
            </Stack>
          </Stack>
        </Box>
      )}
    </Box>
  );
}

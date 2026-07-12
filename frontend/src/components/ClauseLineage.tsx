import { useEffect, useState } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import { getClauseLineage } from "../api/client";
import type { ClauseLineage as Lineage } from "../types";
import { C } from "./common/redline";

const MATERIALITY_LABELS: Record<string, string> = {
  substantive: "Substantive",
  cosmetic: "Cosmetic",
};

const CHANGE_TYPE_LABELS: Record<string, string> = {
  added: "Added",
  removed: "Removed",
  modified: "Modified",
};

const MONO = '"JetBrains Mono", ui-monospace, monospace';

// Drill-down: how a single clause evolved across every round of the
// negotiation. Fetches the clause's cross-round lineage and lays it out in
// round order, so the payoff of the stateful tracker — the whole life of one
// clause — is visible from any change in the feed.
export function ClauseLineage({ clauseId }: { clauseId: number }) {
  const [lineage, setLineage] = useState<Lineage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLineage(null);
    setError(null);
    getClauseLineage(clauseId)
      .then((l) => active && setLineage(l))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [clauseId]);

  if (error)
    return (
      <Typography role="alert" color="error" variant="body2" sx={{ mt: 2 }}>
        Failed to load lineage: {error}
      </Typography>
    );
  if (!lineage)
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 2 }}>
        <CircularProgress size={16} />
        <Typography variant="body2" color="text.secondary">
          Loading lineage…
        </Typography>
      </Box>
    );

  return (
    <Box
      component="section"
      className="clause-lineage"
      data-testid="clause-lineage"
      sx={{
        mt: 2,
        p: 2,
        bgcolor: C.snow,
        border: `1px solid ${C.cloud}`,
        borderRadius: 3,
      }}
    >
      <Typography
        variant="overline"
        component="h4"
        sx={{ display: "block", color: C.slate, mb: 1.5 }}
      >
        Clause history across rounds
      </Typography>
      {lineage.entries.length === 1 && (
        <Typography
          variant="body2"
          color="text.secondary"
          data-testid="lineage-single"
          sx={{ mb: 1.5 }}
        >
          This clause first appears here — no earlier rounds to trace.
        </Typography>
      )}
      <Box
        component="ol"
        className="lineage-timeline"
        sx={{ listStyle: "none", m: 0, p: 0 }}
      >
        {lineage.entries.map((entry, i) => (
          <Box
            component="li"
            key={entry.clause_id}
            className="lineage-entry"
            data-testid="lineage-entry"
            sx={{
              position: "relative",
              pl: 3,
              pb: i === lineage.entries.length - 1 ? 0 : 2.5,
              // Timeline rail + node.
              "&::before": {
                content: '""',
                position: "absolute",
                left: 5,
                top: 6,
                bottom: 0,
                width: "2px",
                bgcolor: C.cloud,
              },
              "&:last-of-type::before": { display: "none" },
              "&::after": {
                content: '""',
                position: "absolute",
                left: 0,
                top: 4,
                width: 12,
                height: 12,
                borderRadius: "50%",
                bgcolor: C.cobalt,
                border: `2px solid ${C.snow}`,
              },
            }}
          >
            <Box
              className="lineage-round"
              data-testid="lineage-round"
              sx={{ fontWeight: 600, color: C.navy }}
            >
              Round {entry.round_no} — {entry.submitted_by_party}
            </Box>
            {entry.change && (
              <Box
                className="lineage-change"
                data-testid="lineage-change"
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 1,
                  mt: 0.75,
                }}
              >
                <Box
                  component="span"
                  className={`change-type ${entry.change.change_type}`}
                  sx={{
                    fontFamily: MONO,
                    fontSize: 11,
                    fontWeight: 500,
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                    color: C.slate,
                  }}
                >
                  {CHANGE_TYPE_LABELS[entry.change.change_type] ??
                    entry.change.change_type}
                </Box>
                {entry.change.materiality && (
                  <Box
                    component="span"
                    className={`materiality-badge ${entry.change.materiality}`}
                    sx={{
                      px: 1,
                      py: 0.25,
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 600,
                      ...(entry.change.materiality === "substantive"
                        ? { bgcolor: C.primaryWash, color: C.primaryInk }
                        : { border: `1px solid ${C.cloud}`, color: C.slate }),
                    }}
                  >
                    {MATERIALITY_LABELS[entry.change.materiality] ??
                      entry.change.materiality}
                  </Box>
                )}
                {entry.change.summary && (
                  <Typography
                    className="summary"
                    data-machine-generated="true"
                    variant="body2"
                    sx={{ width: "100%", color: C.navy }}
                  >
                    {entry.change.summary}
                  </Typography>
                )}
              </Box>
            )}
            <Box
              component="pre"
              className="lineage-text"
              data-testid="lineage-text"
              sx={{
                m: 0,
                mt: 1,
                p: 1.25,
                bgcolor: "#fff",
                border: `1px solid ${C.cloud}`,
                borderRadius: 2,
                fontFamily: MONO,
                fontSize: 12.5,
                lineHeight: 1.5,
                color: C.navy,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {entry.text}
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

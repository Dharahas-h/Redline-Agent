import { useEffect, useState } from "react";
import {
  Box,
  FormControlLabel,
  Paper,
  Skeleton,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { getRoundChanges, updateAlignment } from "../api/client";
import type { RoundChanges } from "../types";
import { ChangeCard } from "./ChangeCard";
import { StructuralAlerts } from "./StructuralAlerts";
import type { AlignmentCandidate } from "./AlignmentOverride";
import { C } from "./common/redline";

const CATEGORY_OPTIONS = [
  ["payment", "Payment"],
  ["liability", "Liability"],
  ["ip", "IP"],
  ["termination", "Termination"],
  ["confidentiality", "Confidentiality"],
  ["other", "Other"],
] as const;

const FAVORED_PARTY_OPTIONS = [
  ["represented", "Favors me"],
  ["counterparty", "Favors them"],
  ["neutral", "Neutral"],
] as const;

// Skeleton stand-ins keep the feed layout stable while the pipeline runs or a
// filter refetches, so nothing jumps when the real cards arrive.
function FeedSkeletons() {
  return (
    <Stack spacing={1.5}>
      {[0, 1, 2].map((i) => (
        <Paper key={i} variant="outlined" sx={{ p: 2.5, borderRadius: 5 }}>
          <Skeleton width={90} height={18} />
          <Skeleton width="70%" height={26} sx={{ mt: 1 }} />
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 2 }}>
            <Skeleton variant="rounded" height={72} sx={{ flex: 1 }} />
            <Skeleton variant="rounded" height={72} sx={{ flex: 1 }} />
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export function ChangeFeed({ roundId }: { roundId: number }) {
  const [data, setData] = useState<RoundChanges | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hideCosmetic, setHideCosmetic] = useState(false);
  const [category, setCategory] = useState("");
  const [favoredParty, setFavoredParty] = useState("");
  const [riskOnly, setRiskOnly] = useState(false);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    setData(null);
    setError(null);

    // Server-side filters: hide cosmetic == substantive-only.
    const filters = {
      materiality: hideCosmetic ? "substantive" : undefined,
      category: category || undefined,
      favoredParty: favoredParty || undefined,
      risk: riskOnly || undefined,
    };

    const poll = () => {
      getRoundChanges(roundId, filters)
        .then((d) => {
          if (!active) return;
          setData(d);
          // Keep polling while the pipeline is still running.
          if (d.status !== "ready" && d.status !== "failed") {
            timer = setTimeout(poll, 1000);
          }
        })
        .catch((e) => active && setError(String(e)));
    };
    poll();

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [roundId, hideCosmetic, category, favoredParty, riskOnly]);

  // Correcting an alignment regenerates the diff server-side; swap in the
  // refreshed feed it returns.
  const handleOverride = async (
    currClauseId: number,
    prevClauseId: number | null,
  ) => {
    const refreshed = await updateAlignment(roundId, [
      { curr_clause_id: currClauseId, prev_clause_id: prevClauseId },
    ]);
    setData(refreshed);
  };

  if (error)
    return (
      <Typography role="alert" color="error" sx={{ mt: 2 }}>
        Failed to load changes: {error}
      </Typography>
    );

  if (!data)
    return (
      <Box>
        <Box component="span" className="vt-eyebrow" sx={{ mb: 2, display: "inline-flex" }}>
          Loading changes…
        </Box>
        <FeedSkeletons />
      </Box>
    );

  if (data.status !== "ready")
    return (
      <Box>
        <Box
          component="span"
          className="vt-eyebrow"
          data-testid="round-status"
          sx={{ mb: 2, display: "inline-flex" }}
        >
          Analyzing round — {data.status}…
        </Box>
        <FeedSkeletons />
      </Box>
    );

  // Candidate prior clauses for re-pairing, derived from the feed itself.
  const candidateMap = new Map<number, AlignmentCandidate>();
  for (const c of data.changes) {
    if (c.prev_clause_id !== null && !candidateMap.has(c.prev_clause_id)) {
      const label =
        (c.raw_before ?? "").slice(0, 80) || `Clause ${c.prev_clause_id}`;
      candidateMap.set(c.prev_clause_id, {
        prev_clause_id: c.prev_clause_id,
        label,
      });
    }
  }
  const candidates = [...candidateMap.values()];

  return (
    <Box component="section" className="change-feed" data-testid="change-feed">
      <StructuralAlerts alerts={data.alerts ?? []} />

      <Paper
        variant="outlined"
        className="feed-controls"
        sx={{
          position: "sticky",
          top: 72,
          zIndex: 2,
          p: 1.5,
          my: 2,
          borderRadius: 4,
          backdropFilter: "blur(8px)",
          backgroundColor: "rgba(255,255,255,0.86)",
        }}
      >
        <Stack
          direction="row"
          spacing={2}
          useFlexGap
          flexWrap="wrap"
          sx={{ alignItems: "center" }}
        >
          <FormControlLabel
            control={
              <Switch
                checked={hideCosmetic}
                onChange={(e) => setHideCosmetic(e.target.checked)}
              />
            }
            label="Hide cosmetic changes"
          />
          <TextField
            select
            label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            SelectProps={{ native: true }}
            inputProps={{ "aria-label": "Filter by category" }}
            size="small"
            sx={{ minWidth: 170 }}
          >
            <option value="" />
            {CATEGORY_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </TextField>
          <TextField
            select
            label="Favored party"
            value={favoredParty}
            onChange={(e) => setFavoredParty(e.target.value)}
            SelectProps={{ native: true }}
            inputProps={{ "aria-label": "Filter by favored party" }}
            size="small"
            sx={{ minWidth: 170 }}
          >
            <option value=""></option>
            {FAVORED_PARTY_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </TextField>
          <FormControlLabel
            control={
              <Switch
                checked={riskOnly}
                onChange={(e) => setRiskOnly(e.target.checked)}
              />
            }
            label="Flagged for review only"
          />
        </Stack>
      </Paper>

      {data.changes.length === 0 ? (
        <Paper
          variant="outlined"
          sx={{
            p: 6,
            borderRadius: 5,
            textAlign: "center",
            borderStyle: "dashed",
          }}
        >
          <Typography
            data-testid="no-changes"
            variant="h6"
            sx={{ color: C.slate, fontWeight: 500 }}
          >
            No changes in this round.
          </Typography>
        </Paper>
      ) : (
        <Stack spacing={2}>
          <Typography variant="overline" sx={{ color: C.slate }}>
            {data.changes.length} changed clauses
          </Typography>
          {data.changes.map((c) => (
            <ChangeCard
              key={c.id}
              change={c}
              candidates={candidates.filter(
                (cand) => cand.prev_clause_id !== c.prev_clause_id,
              )}
              onOverride={handleOverride}
            />
          ))}
        </Stack>
      )}
    </Box>
  );
}

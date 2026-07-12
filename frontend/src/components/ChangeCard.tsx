import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Stack,
  Typography,
} from "@mui/material";
import HistoryIcon from "@mui/icons-material/HistoryRounded";
import type { Change } from "../types";
import { AlignmentOverride } from "./AlignmentOverride";
import type { AlignmentCandidate } from "./AlignmentOverride";
import { ClauseLineage } from "./ClauseLineage";
import {
  C,
  CategoryTag,
  ChangeTypeLabel,
  FavoredPartyBadge,
  MaterialityBadge,
} from "./common/redline";

const MONO = '"JetBrains Mono", ui-monospace, monospace';

// One neutral monospace panel of raw clause text. The diff stays colorless —
// the favored-party badge carries the only verdict color on the card.
function RawPanel({
  label,
  text,
  testId,
}: {
  label: string;
  text: string;
  testId: string;
}) {
  return (
    <Box sx={{ flex: 1, minWidth: 0 }}>
      <Box
        component="span"
        sx={{
          fontFamily: MONO,
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: C.slate,
        }}
      >
        {label}
      </Box>
      <Box
        component="pre"
        data-testid={testId}
        sx={{
          m: 0,
          mt: 0.75,
          p: 1.5,
          bgcolor: C.snow,
          border: `1px solid ${C.cloud}`,
          borderRadius: 2,
          fontFamily: MONO,
          fontSize: 13,
          lineHeight: 1.55,
          color: C.navy,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {text}
      </Box>
    </Box>
  );
}

export function ChangeCard({
  change,
  candidates,
  onOverride,
}: {
  change: Change;
  candidates?: AlignmentCandidate[];
  onOverride?: (currClauseId: number, prevClauseId: number | null) => void;
}) {
  const [showLineage, setShowLineage] = useState(false);
  return (
    <Card
      component="article"
      variant="outlined"
      className="change-card"
      data-testid="change-card"
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          flexWrap="wrap"
          sx={{ alignItems: "center", mb: 1.5 }}
          component="header"
        >
          <ChangeTypeLabel type={change.change_type} />
          <Box sx={{ flexGrow: 1 }} />
          {change.low_confidence && (
            <Chip
              size="small"
              label="Uncertain match — please review"
              className="low-confidence-badge"
              data-testid="low-confidence-badge"
              role="note"
              sx={{
                bgcolor: C.saffronWash,
                color: C.saffron,
                fontWeight: 600,
                fontSize: 12,
              }}
            />
          )}
          {change.overridden && (
            <Chip
              size="small"
              label="Match corrected"
              className="overridden-badge"
              data-testid="overridden-badge"
              sx={{
                bgcolor: C.primaryWash,
                color: C.primaryInk,
                fontWeight: 600,
                fontSize: 12,
              }}
            />
          )}
          {change.materiality && (
            <MaterialityBadge materiality={change.materiality} />
          )}
          {change.favored_party && (
            <FavoredPartyBadge favored={change.favored_party} />
          )}
          {change.category && <CategoryTag category={change.category} />}
        </Stack>

        {change.risk_flag && (
          <Alert
            severity="warning"
            variant="outlined"
            role="note"
            className="risk-flag"
            data-testid="risk-flag"
            sx={{ mb: 2, borderRadius: 2 }}
          >
            {change.risk_flag}
          </Alert>
        )}

        {change.summary && (
          <Box
            className="summary"
            data-testid="summary"
            data-machine-generated="true"
            sx={{ mb: 2 }}
          >
            <Typography variant="body1" sx={{ color: C.navy }}>
              {change.summary}
            </Typography>
            <Typography
              className="disclaimer"
              variant="caption"
              sx={{ color: C.slate, display: "block", mt: 0.5 }}
            >
              Machine-generated — attorney work-product for review.
            </Typography>
          </Box>
        )}

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          {change.raw_before !== null && (
            <RawPanel
              label="Before"
              text={change.raw_before}
              testId="raw-before"
            />
          )}
          {change.raw_after !== null && (
            <RawPanel label="After" text={change.raw_after} testId="raw-after" />
          )}
        </Stack>

        {onOverride && change.curr_clause_id !== null && (
          <Box sx={{ mt: 2 }}>
            <AlignmentOverride
              change={change}
              candidates={candidates ?? []}
              onOverride={onOverride}
            />
          </Box>
        )}

        {change.curr_clause_id !== null && (
          <Box className="clause-lineage-drilldown" sx={{ mt: 1 }}>
            <Button
              type="button"
              size="small"
              data-testid="show-lineage"
              aria-expanded={showLineage}
              onClick={() => setShowLineage((s) => !s)}
              startIcon={<HistoryIcon />}
              sx={{ color: "text.secondary", px: 1 }}
            >
              {showLineage ? "Hide clause history" : "Show clause history"}
            </Button>
            <Collapse in={showLineage} unmountOnExit>
              <ClauseLineage clauseId={change.curr_clause_id} />
            </Collapse>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

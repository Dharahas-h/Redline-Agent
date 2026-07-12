import { Alert, AlertTitle, Box, Stack } from "@mui/material";
import type { StructuralAlert } from "../types";

const ALERT_LABELS: Record<string, string> = {
  definition_changed: "Definition changed",
  table_changed: "Table changed",
};

// Structural alerts are surfaced prominently above the change cards: a
// defined-term redefinition (with its reference ripple count) or a table change
// flagged for manual review. They are not changes — the deterministic differ
// owns the change set — so they render as their own banner.
export function StructuralAlerts({ alerts }: { alerts: StructuralAlert[] }) {
  if (alerts.length === 0) return null;
  return (
    <Stack
      component="section"
      spacing={1.5}
      className="structural-alerts"
      data-testid="structural-alerts"
      aria-label="Structural alerts"
    >
      {alerts.map((alert) => (
        <Alert
          key={alert.id}
          severity="warning"
          variant="outlined"
          className={`structural-alert ${alert.alert_type}`}
          data-testid="structural-alert"
          sx={{ borderRadius: 3, alignItems: "flex-start" }}
        >
          <AlertTitle
            className="alert-type"
            data-testid="alert-type"
            sx={{ fontWeight: 600, mb: 0.25 }}
          >
            {ALERT_LABELS[alert.alert_type] ?? alert.alert_type}
          </AlertTitle>
          <Box className="alert-detail" data-testid="alert-detail">
            {alert.detail}
          </Box>
        </Alert>
      ))}
    </Stack>
  );
}

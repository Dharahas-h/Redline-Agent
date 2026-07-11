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
    <section
      className="structural-alerts"
      data-testid="structural-alerts"
      aria-label="Structural alerts"
    >
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`structural-alert ${alert.alert_type}`}
          data-testid="structural-alert"
          role="alert"
        >
          <span className="alert-type" data-testid="alert-type">
            {ALERT_LABELS[alert.alert_type] ?? alert.alert_type}
          </span>
          <p className="alert-detail" data-testid="alert-detail">
            ⚠ {alert.detail}
          </p>
        </div>
      ))}
    </section>
  );
}

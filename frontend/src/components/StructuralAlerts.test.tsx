import { expect, test } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StructuralAlerts } from "./StructuralAlerts";
import type { StructuralAlert } from "../types";

const DEFINITION_ALERT: StructuralAlert = {
  id: 1,
  alert_type: "definition_changed",
  subject: "Confidential Information",
  detail: 'Definition of "Confidential Information" changed — affects 2 clauses.',
  affected_clause_count: 2,
};

const TABLE_ALERT: StructuralAlert = {
  id: 2,
  alert_type: "table_changed",
  subject: null,
  detail: "Table 1 was modified — review manually.",
  affected_clause_count: null,
};

test("renders nothing when there are no alerts", () => {
  const { container } = render(<StructuralAlerts alerts={[]} />);
  expect(container).toBeEmptyDOMElement();
});

test("renders a definition alert with its reference ripple count", () => {
  render(<StructuralAlerts alerts={[DEFINITION_ALERT]} />);
  const alert = screen.getByTestId("structural-alert");
  expect(within(alert).getByTestId("alert-type")).toHaveTextContent(
    "Definition changed",
  );
  expect(within(alert).getByTestId("alert-detail")).toHaveTextContent(
    'Definition of "Confidential Information" changed — affects 2 clauses.',
  );
});

test("renders a table alert prompting manual review", () => {
  render(<StructuralAlerts alerts={[TABLE_ALERT]} />);
  const alert = screen.getByTestId("structural-alert");
  expect(within(alert).getByTestId("alert-type")).toHaveTextContent(
    "Table changed",
  );
  expect(within(alert).getByTestId("alert-detail")).toHaveTextContent(
    "review manually",
  );
});

test("renders each alert prominently as an alert role", () => {
  render(<StructuralAlerts alerts={[DEFINITION_ALERT, TABLE_ALERT]} />);
  expect(screen.getAllByRole("alert")).toHaveLength(2);
});

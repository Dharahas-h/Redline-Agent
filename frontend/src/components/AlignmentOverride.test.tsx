import { afterAll, afterEach, beforeAll, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AlignmentOverride } from "./AlignmentOverride";
import { ChangeFeed } from "./ChangeFeed";
import type { Change, RoundChanges } from "../types";

const LOW_CONF: Change = {
  id: 10,
  change_type: "modified",
  curr_clause_id: 5,
  prev_clause_id: 3,
  raw_before: "the party shall protect confidential information",
  raw_after: "the party shall protect confidential information and data",
  summary: "Scope of protection broadened.",
  materiality: "substantive",
  category: "confidentiality",
  favored_party: "neutral",
  risk_flag: null,
  alignment_confidence: 0.5,
  alignment_method: "embedding",
  alignment_similarity: 0.71,
  low_confidence: true,
  overridden: false,
};

const OTHER: Change = {
  ...LOW_CONF,
  id: 11,
  curr_clause_id: 8,
  prev_clause_id: 4,
  raw_before: "the party shall protect data and records",
  raw_after: "the party shall protect data and records",
  low_confidence: false,
};

test("submits a re-pair with the chosen prior clause", async () => {
  const user = userEvent.setup();
  const onOverride = vi.fn();
  render(
    <AlignmentOverride
      change={LOW_CONF}
      candidates={[{ prev_clause_id: 4, label: "the party shall protect data" }]}
      onOverride={onOverride}
    />,
  );

  await user.click(screen.getByRole("button", { name: /fix match/i }));
  await user.selectOptions(screen.getByLabelText(/prior clause/i), "4");
  await user.click(screen.getByRole("button", { name: /apply/i }));

  expect(onOverride).toHaveBeenCalledWith(5, 4);
});

test("submits a mark-as-new correction", async () => {
  const user = userEvent.setup();
  const onOverride = vi.fn();
  render(
    <AlignmentOverride
      change={LOW_CONF}
      candidates={[{ prev_clause_id: 4, label: "other clause" }]}
      onOverride={onOverride}
    />,
  );

  await user.click(screen.getByRole("button", { name: /fix match/i }));
  await user.selectOptions(screen.getByLabelText(/prior clause/i), "");
  await user.click(screen.getByRole("button", { name: /apply/i }));

  expect(onOverride).toHaveBeenCalledWith(5, null);
});

// End-to-end through ChangeFeed: the PATCH regenerates the feed server-side.
const READY: RoundChanges = {
  round_id: 2,
  status: "ready",
  changes: [LOW_CONF, OTHER],
};

const REGENERATED: RoundChanges = {
  round_id: 2,
  status: "ready",
  changes: [{ ...LOW_CONF, overridden: true, low_confidence: false }, OTHER],
};

const server = setupServer(
  http.get("/rounds/:id/changes", () => HttpResponse.json(READY)),
  http.patch("/rounds/:id/alignment", () => HttpResponse.json(REGENERATED)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test("flags low-confidence and applies a correction through the feed", async () => {
  const user = userEvent.setup();
  render(<ChangeFeed roundId={2} />);

  expect(await screen.findByTestId("change-feed")).toBeInTheDocument();
  // The uncertain match is flagged for review.
  expect(screen.getAllByTestId("low-confidence-badge").length).toBeGreaterThan(0);

  // Fix the first card's match.
  const fixButtons = screen.getAllByRole("button", { name: /fix match/i });
  await user.click(fixButtons[0]);
  await user.selectOptions(screen.getByLabelText(/prior clause/i), "");
  await user.click(screen.getByRole("button", { name: /apply/i }));

  // The regenerated feed marks the match as corrected.
  expect(await screen.findByTestId("overridden-badge")).toBeInTheDocument();
});

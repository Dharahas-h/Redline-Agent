import { afterAll, afterEach, beforeAll, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { ChangeFeed } from "./ChangeFeed";
import type { RoundChanges } from "../types";

const READY_FEED: RoundChanges = {
  round_id: 2,
  status: "ready",
  changes: [
    {
      id: 10,
      change_type: "modified",
      curr_clause_id: 5,
      prev_clause_id: 3,
      raw_before: "Buyer shall pay within 30 days.",
      raw_after: "Buyer shall pay within 45 days.",
      summary: null,
      materiality: null,
      category: null,
      favored_party: null,
      risk_flag: null,
    },
  ],
};

const server = setupServer(
  http.get("/rounds/:id/changes", () => HttpResponse.json(READY_FEED)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test("renders raw before/after for each change", async () => {
  render(<ChangeFeed roundId={2} />);

  expect(await screen.findByTestId("change-feed")).toBeInTheDocument();
  expect(screen.getByTestId("change-type")).toHaveTextContent("Modified");
  expect(screen.getByTestId("raw-before")).toHaveTextContent(
    "Buyer shall pay within 30 days.",
  );
  expect(screen.getByTestId("raw-after")).toHaveTextContent(
    "Buyer shall pay within 45 days.",
  );
});

test("shows an empty state when there are no changes", async () => {
  server.use(
    http.get("/rounds/:id/changes", () =>
      HttpResponse.json({ round_id: 1, status: "ready", changes: [] }),
    ),
  );
  render(<ChangeFeed roundId={1} />);
  expect(await screen.findByTestId("no-changes")).toBeInTheDocument();
});

test("shows processing status while the pipeline runs", async () => {
  server.use(
    http.get("/rounds/:id/changes", () =>
      HttpResponse.json({ round_id: 3, status: "processing", changes: [] }),
    ),
  );
  render(<ChangeFeed roundId={3} />);
  expect(await screen.findByTestId("round-status")).toHaveTextContent(
    "processing",
  );
});

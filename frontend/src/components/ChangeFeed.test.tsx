import { afterAll, afterEach, beforeAll, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { ChangeFeed } from "./ChangeFeed";
import type { Change, RoundChanges } from "../types";

const MATERIAL: Change = {
  id: 10,
  change_type: "modified",
  curr_clause_id: 5,
  prev_clause_id: 3,
  raw_before: "Buyer shall pay within 30 days.",
  raw_after: "Buyer shall pay within 45 days.",
  summary: "Payment window extended from 30 to 45 days.",
  materiality: "substantive",
  category: null,
  favored_party: null,
  risk_flag: null,
};

const COSMETIC: Change = {
  id: 11,
  change_type: "modified",
  curr_clause_id: 6,
  prev_clause_id: 4,
  raw_before: "This Agreement lasts one year.",
  raw_after: "this agreement lasts one year",
  summary: "Cosmetic change: only case/punctuation differs.",
  materiality: "cosmetic",
  category: null,
  favored_party: null,
  risk_flag: null,
};

const READY_FEED: RoundChanges = {
  round_id: 2,
  status: "ready",
  changes: [MATERIAL, COSMETIC],
};

// Honor the materiality filter server-side, as the real API does.
const server = setupServer(
  http.get("/rounds/:id/changes", ({ request }) => {
    const materiality = new URL(request.url).searchParams.get("materiality");
    const changes = materiality
      ? READY_FEED.changes.filter((c) => c.materiality === materiality)
      : READY_FEED.changes;
    return HttpResponse.json({ ...READY_FEED, changes });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test("renders a plain-English summary and materiality badge per change", async () => {
  render(<ChangeFeed roundId={2} />);

  expect(await screen.findByTestId("change-feed")).toBeInTheDocument();
  expect(screen.getByText("Payment window extended from 30 to 45 days.")).toBeInTheDocument();

  const badges = screen.getAllByTestId("materiality-badge");
  expect(badges.map((b) => b.textContent)).toEqual(["Substantive", "Cosmetic"]);

  // Interpretation is labeled as machine-generated attorney work-product.
  expect(screen.getAllByTestId("summary")[0]).toHaveAttribute(
    "data-machine-generated",
    "true",
  );
  // Raw before/after stays visible behind every summary.
  expect(screen.getAllByTestId("raw-before")[0]).toHaveTextContent(
    "Buyer shall pay within 30 days.",
  );
});

test("can hide cosmetic changes", async () => {
  const user = userEvent.setup();
  render(<ChangeFeed roundId={2} />);

  expect(await screen.findByTestId("change-feed")).toBeInTheDocument();
  expect(screen.getAllByTestId("change-card")).toHaveLength(2);

  await user.click(screen.getByLabelText(/hide cosmetic/i));

  expect(await screen.findByTestId("change-card")).toBeInTheDocument();
  const cards = screen.getAllByTestId("change-card");
  expect(cards).toHaveLength(1);
  expect(screen.getByTestId("materiality-badge")).toHaveTextContent("Substantive");
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

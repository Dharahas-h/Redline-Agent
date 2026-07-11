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
  category: "payment",
  favored_party: "counterparty",
  risk_flag: "For attorney review: payment terms shifted.",
  alignment_confidence: 0.9,
  alignment_method: "embedding",
  alignment_similarity: 0.9,
  low_confidence: false,
  overridden: false,
};

const NEUTRAL_IP: Change = {
  id: 12,
  change_type: "added",
  curr_clause_id: 7,
  prev_clause_id: null,
  raw_before: null,
  raw_after: "License is worldwide.",
  summary: "IP license scope clarified.",
  materiality: "substantive",
  category: "ip",
  favored_party: "represented",
  risk_flag: null,
  alignment_confidence: 0.9,
  alignment_method: "embedding",
  alignment_similarity: 0.9,
  low_confidence: false,
  overridden: false,
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
  alignment_confidence: 1.0,
  alignment_method: "heading",
  alignment_similarity: 1.0,
  low_confidence: false,
  overridden: false,
};

const READY_FEED: RoundChanges = {
  round_id: 2,
  status: "ready",
  changes: [MATERIAL, COSMETIC],
  alerts: [],
};

// Honor every filter server-side, as the real API does.
function feedHandler(changes: Change[]) {
  return http.get("/rounds/:id/changes", ({ request }) => {
    const params = new URL(request.url).searchParams;
    const materiality = params.get("materiality");
    const category = params.get("category");
    const favoredParty = params.get("favored_party");
    const risk = params.get("risk");
    const filtered = changes.filter(
      (c) =>
        (!materiality || c.materiality === materiality) &&
        (!category || c.category === category) &&
        (!favoredParty || c.favored_party === favoredParty) &&
        (risk !== "true" || Boolean(c.risk_flag)),
    );
    return HttpResponse.json({ round_id: 2, status: "ready", changes: filtered });
  });
}

const server = setupServer(feedHandler(READY_FEED.changes));

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

test("filters by favored-party, category, and risk", async () => {
  const user = userEvent.setup();
  server.use(feedHandler([MATERIAL, COSMETIC, NEUTRAL_IP]));
  render(<ChangeFeed roundId={2} />);

  expect(await screen.findByTestId("change-feed")).toBeInTheDocument();
  expect(screen.getAllByTestId("change-card")).toHaveLength(3);

  // Favored-party: only the change favoring the represented party.
  await user.selectOptions(
    screen.getByLabelText(/filter by favored party/i),
    "represented",
  );
  await screen.findByText("IP license scope clarified.");
  expect(screen.getAllByTestId("change-card")).toHaveLength(1);
  expect(screen.getByTestId("favored-party-badge")).toHaveTextContent("Favors me");

  // Back to all, then narrow by category.
  await user.selectOptions(
    screen.getByLabelText(/filter by favored party/i),
    "",
  );
  await user.selectOptions(screen.getByLabelText(/filter by category/i), "payment");
  await screen.findByText("Payment window extended from 30 to 45 days.");
  expect(screen.getAllByTestId("change-card")).toHaveLength(1);
  expect(screen.getByTestId("category-tag")).toHaveTextContent("Payment");

  // Reset category, then show only risk-flagged changes.
  await user.selectOptions(screen.getByLabelText(/filter by category/i), "");
  await user.click(screen.getByLabelText(/flagged for review only/i));
  await screen.findByTestId("risk-flag");
  const cards = screen.getAllByTestId("change-card");
  expect(cards).toHaveLength(1);
  expect(screen.getByTestId("risk-flag")).toHaveTextContent(
    "For attorney review: payment terms shifted.",
  );
});

test("surfaces structural alerts prominently above the change cards", async () => {
  server.use(
    http.get("/rounds/:id/changes", () =>
      HttpResponse.json({
        round_id: 2,
        status: "ready",
        changes: [MATERIAL],
        alerts: [
          {
            id: 1,
            alert_type: "definition_changed",
            subject: "Confidential Information",
            detail:
              'Definition of "Confidential Information" changed — affects 2 clauses.',
            affected_clause_count: 2,
          },
          {
            id: 2,
            alert_type: "table_changed",
            subject: null,
            detail: "Table 1 was modified — review manually.",
            affected_clause_count: null,
          },
        ],
      }),
    ),
  );
  render(<ChangeFeed roundId={2} />);

  const alerts = await screen.findAllByTestId("structural-alert");
  expect(alerts).toHaveLength(2);
  expect(screen.getByText(/affects 2 clauses/)).toBeInTheDocument();
  expect(screen.getByText(/review manually/)).toBeInTheDocument();

  // The banner precedes the change cards in the document.
  const banner = screen.getByTestId("structural-alerts");
  const card = screen.getByTestId("change-card");
  expect(banner.compareDocumentPosition(card)).toBe(
    Node.DOCUMENT_POSITION_FOLLOWING,
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

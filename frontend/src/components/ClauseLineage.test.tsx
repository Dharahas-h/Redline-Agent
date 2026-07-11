import { afterAll, afterEach, beforeAll, expect, test } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { ClauseLineage } from "./ClauseLineage";
import type { ClauseLineage as Lineage } from "../types";

const LINEAGE: Lineage = {
  clause_id: 30,
  negotiation_id: 1,
  entries: [
    {
      round_id: 1,
      round_no: 1,
      submitted_by_party: "Buyer",
      clause_id: 10,
      number_label: "1",
      heading: "Payment",
      text: "1. Payment\nBuyer pays in 30 days.",
      change: null,
    },
    {
      round_id: 2,
      round_no: 2,
      submitted_by_party: "Seller",
      clause_id: 20,
      number_label: "1",
      heading: "Payment",
      text: "1. Payment\nBuyer pays in 45 days.",
      change: {
        id: 100,
        change_type: "modified",
        curr_clause_id: 20,
        prev_clause_id: 10,
        raw_before: "1. Payment\nBuyer pays in 30 days.",
        raw_after: "1. Payment\nBuyer pays in 45 days.",
        summary: "Payment window extended from 30 to 45 days.",
        materiality: "substantive",
        category: "payment",
        favored_party: "counterparty",
        risk_flag: null,
        alignment_confidence: 1.0,
        alignment_method: "heading",
        alignment_similarity: 1.0,
        low_confidence: false,
        overridden: false,
      },
    },
    {
      round_id: 3,
      round_no: 3,
      submitted_by_party: "Buyer",
      clause_id: 30,
      number_label: "1",
      heading: "Payment",
      text: "1. Payment\nBuyer pays in 60 days.",
      change: {
        id: 101,
        change_type: "modified",
        curr_clause_id: 30,
        prev_clause_id: 20,
        raw_before: "1. Payment\nBuyer pays in 45 days.",
        raw_after: "1. Payment\nBuyer pays in 60 days.",
        summary: "Payment window extended from 45 to 60 days.",
        materiality: "substantive",
        category: "payment",
        favored_party: "counterparty",
        risk_flag: null,
        alignment_confidence: 1.0,
        alignment_method: "heading",
        alignment_similarity: 1.0,
        low_confidence: false,
        overridden: false,
      },
    },
  ],
};

const server = setupServer(
  http.get("/clauses/:id/lineage", () => HttpResponse.json(LINEAGE)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test("renders the clause's text for every round in order", async () => {
  render(<ClauseLineage clauseId={30} />);

  const entries = await screen.findAllByTestId("lineage-entry");
  expect(entries).toHaveLength(3);
  expect(entries.map((e) => within(e).getByTestId("lineage-round").textContent))
    .toEqual(["Round 1 — Buyer", "Round 2 — Seller", "Round 3 — Buyer"]);
  expect(within(entries[0]).getByTestId("lineage-text")).toHaveTextContent(
    "Buyer pays in 30 days.",
  );
  expect(within(entries[2]).getByTestId("lineage-text")).toHaveTextContent(
    "Buyer pays in 60 days.",
  );
});

test("shows the interpreted change into each round after the first", async () => {
  render(<ClauseLineage clauseId={30} />);

  const entries = await screen.findAllByTestId("lineage-entry");
  // The first round has no prior, so it carries no change summary.
  expect(within(entries[0]).queryByTestId("lineage-change")).not.toBeInTheDocument();
  expect(within(entries[1]).getByTestId("lineage-change")).toHaveTextContent(
    "Payment window extended from 30 to 45 days.",
  );
});

test("renders a single-round clause with no history", async () => {
  server.use(
    http.get("/clauses/:id/lineage", () =>
      HttpResponse.json({
        clause_id: 20,
        negotiation_id: 1,
        entries: [LINEAGE.entries[0]],
      }),
    ),
  );
  render(<ClauseLineage clauseId={20} />);
  expect(await screen.findByTestId("lineage-single")).toBeInTheDocument();
});

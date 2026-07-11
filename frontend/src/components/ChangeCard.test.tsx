import { afterAll, afterEach, beforeAll, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { ChangeCard } from "./ChangeCard";
import type { Change } from "../types";

const BASE: Change = {
  id: 1,
  change_type: "modified",
  curr_clause_id: 5,
  prev_clause_id: 3,
  raw_before: "cap is $1M",
  raw_after: "cap is $100k",
  summary: "Liability cap lowered.",
  materiality: "substantive",
  category: "liability",
  favored_party: "counterparty",
  risk_flag: "For attorney review: the liability cap was reduced tenfold.",
  alignment_confidence: 1.0,
  alignment_method: "heading",
  alignment_similarity: 1.0,
  low_confidence: false,
  overridden: false,
};

test("flags a low-confidence match for review", () => {
  render(<ChangeCard change={{ ...BASE, low_confidence: true }} />);
  expect(screen.getByTestId("low-confidence-badge")).toBeInTheDocument();
});

test("shows a corrected-match badge for an overridden alignment", () => {
  render(<ChangeCard change={{ ...BASE, overridden: true }} />);
  expect(screen.getByTestId("overridden-badge")).toBeInTheDocument();
});

test("shows favored-party badge, category tag, and risk-flag prompt", () => {
  render(<ChangeCard change={BASE} />);

  // Favored-party is rendered from the represented party's point of view.
  expect(screen.getByTestId("favored-party-badge")).toHaveTextContent("Favors them");
  expect(screen.getByTestId("category-tag")).toHaveTextContent("Liability");
  expect(screen.getByTestId("risk-flag")).toHaveTextContent(
    "For attorney review: the liability cap was reduced tenfold.",
  );
});

test("favors-me is shown when the change favors the represented party", () => {
  render(<ChangeCard change={{ ...BASE, favored_party: "represented" }} />);
  expect(screen.getByTestId("favored-party-badge")).toHaveTextContent("Favors me");
});

test("omits the risk flag, favored-party, and category when absent", () => {
  render(
    <ChangeCard
      change={{ ...BASE, favored_party: null, category: null, risk_flag: null }}
    />,
  );
  expect(screen.queryByTestId("favored-party-badge")).not.toBeInTheDocument();
  expect(screen.queryByTestId("category-tag")).not.toBeInTheDocument();
  expect(screen.queryByTestId("risk-flag")).not.toBeInTheDocument();
});

const lineageServer = setupServer(
  http.get("/clauses/:id/lineage", ({ params }) =>
    HttpResponse.json({
      clause_id: Number(params.id),
      negotiation_id: 1,
      entries: [
        {
          round_id: 1,
          round_no: 1,
          submitted_by_party: "Buyer",
          clause_id: 3,
          number_label: "1",
          heading: "Cap",
          text: "cap is $1M",
          change: null,
        },
        {
          round_id: 2,
          round_no: 2,
          submitted_by_party: "Seller",
          clause_id: 5,
          number_label: "1",
          heading: "Cap",
          text: "cap is $100k",
          change: BASE,
        },
      ],
    }),
  ),
);

beforeAll(() => lineageServer.listen({ onUnhandledRequest: "error" }));
afterEach(() => lineageServer.resetHandlers());
afterAll(() => lineageServer.close());

test("drills into the clause's cross-round lineage from a change", async () => {
  const user = userEvent.setup();
  render(<ChangeCard change={BASE} />);

  // Lineage is not fetched until the user opens the drill-down.
  expect(screen.queryByTestId("clause-lineage")).not.toBeInTheDocument();

  await user.click(screen.getByTestId("show-lineage"));

  expect(await screen.findByTestId("clause-lineage")).toBeInTheDocument();
  const entries = await screen.findAllByTestId("lineage-entry");
  expect(entries).toHaveLength(2);
});

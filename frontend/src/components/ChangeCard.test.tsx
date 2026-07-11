import { expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
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
};

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

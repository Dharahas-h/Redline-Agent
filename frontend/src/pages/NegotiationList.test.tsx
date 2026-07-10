import { afterAll, afterEach, beforeAll, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { NegotiationList } from "./NegotiationList";
import type { Negotiation } from "../types";

let store: Negotiation[] = [];

const server = setupServer(
  http.get("/negotiations", () => HttpResponse.json(store)),
  http.post("/negotiations", async ({ request }) => {
    const body = (await request.json()) as {
      title: string;
      represented_party: string;
    };
    const created: Negotiation = {
      id: store.length + 1,
      title: body.title,
      represented_party: body.represented_party,
    };
    store.push(created);
    return HttpResponse.json(created, { status: 201 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  store = [];
});
afterAll(() => server.close());

test("creates a negotiation and lists it", async () => {
  const user = userEvent.setup();
  render(<NegotiationList onSelect={vi.fn()} />);

  await user.type(screen.getByLabelText("title"), "Acme MSA");
  await user.type(screen.getByLabelText("represented_party"), "Buyer");
  await user.click(screen.getByRole("button", { name: /create negotiation/i }));

  expect(
    await screen.findByRole("button", { name: /Acme MSA — representing Buyer/i }),
  ).toBeInTheDocument();
});

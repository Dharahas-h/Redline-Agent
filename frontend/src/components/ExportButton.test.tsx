import { afterAll, afterEach, beforeAll, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { ExportButton } from "./ExportButton";
import type { Export } from "../types";

const EXPORT: Export = {
  id: 7,
  negotiation_id: 1,
  from_round_id: 1,
  to_round_id: 2,
  filename: "redline-negotiation-1-round-2-vs-1.docx",
};

const server = setupServer(
  http.post("/negotiations/:id/export", () =>
    HttpResponse.json(EXPORT, { status: 201 }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test("generates a redline and shows a download link", async () => {
  const user = userEvent.setup();
  render(<ExportButton negotiationId={1} />);

  await user.click(screen.getByRole("button", { name: /export redline/i }));

  const link = await screen.findByTestId("download-redline");
  expect(link).toHaveAttribute("href", "/exports/7");
  expect(link).toHaveAttribute("download", EXPORT.filename);
});

test("surfaces an error when export fails", async () => {
  server.use(
    http.post("/negotiations/:id/export", () =>
      HttpResponse.json({ detail: "need two rounds" }, { status: 400 }),
    ),
  );
  const user = userEvent.setup();
  render(<ExportButton negotiationId={1} />);

  await user.click(screen.getByRole("button", { name: /export redline/i }));

  expect(await screen.findByTestId("export-error")).toBeInTheDocument();
});

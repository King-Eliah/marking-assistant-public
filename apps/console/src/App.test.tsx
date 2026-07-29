import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";

test("console shell renders", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Marking Assistant" })).toBeDefined();
});

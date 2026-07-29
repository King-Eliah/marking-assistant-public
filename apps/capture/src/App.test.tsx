import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";

test("capture shell renders", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Marking Assistant" })).toBeDefined();
});

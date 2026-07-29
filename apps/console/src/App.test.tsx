import { Button, Mark } from "@marking/ui";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, test } from "vitest";

import { SignInPage } from "@/pages/sign-in";

function renderAt(path: string, element: React.ReactNode) {
  return render(
    <MemoryRouter
      initialEntries={[path]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path={path} element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

test("sign-in renders its fields and primary action", () => {
  renderAt("/sign-in", <SignInPage />);
  expect(screen.getByLabelText("Institution email")).toBeDefined();
  expect(screen.getByLabelText("Password")).toBeDefined();
  expect(screen.getByRole("button", { name: "Sign in" })).toBeDefined();
});

test("sign-in offers a password reset route", () => {
  renderAt("/sign-in", <SignInPage />);
  const link = screen.getByRole("link", { name: "Forgot your password?" });
  expect(link.getAttribute("href")).toBe("/forgot-password");
});

test("the mark carries no gradient", () => {
  // design.md §1, correction 2: the coral-orange gradient was removed because
  // it is a generative-design tell and carries no meaning here.
  const { container } = render(<Mark />);
  expect(container.querySelector("linearGradient")).toBeNull();
  expect(container.innerHTML).not.toContain("gradient");
});

test("the mark uses square line caps, not round", () => {
  // Round caps read as consumer software; square reads as a stamp. design.md §2.6.
  const { container } = render(<Mark />);
  expect(container.querySelector("path")?.getAttribute("stroke-linecap")).toBe("square");
});

test("buttons default to the machine hue, never destructive red", () => {
  // Nothing the system generates is ever red. design.md §2.1.
  render(<Button>Continue</Button>);
  const cls = screen.getByRole("button", { name: "Continue" }).className;
  expect(cls).toContain("bg-primary");
  expect(cls).not.toContain("destructive");
});

import { Button, Mark } from "@marking/ui";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

import { AuthProvider } from "@/lib/auth";
import { SignInPage } from "@/pages/sign-in";

beforeEach(() => {
  // AuthProvider tries to recover a session on mount. Refused here, so every
  // test starts signed out — which is the state the sign-in screen is for.
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ detail: "Not authenticated" }), { status: 401 })),
  );
});

function renderAt(path: string, element: ReactNode) {
  return render(
    <AuthProvider>
      <MemoryRouter
        initialEntries={[path]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path={path} element={element} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

test("sign-in renders its fields and primary action", async () => {
  renderAt("/sign-in", <SignInPage />);
  await waitFor(() => expect(screen.getByLabelText("Institution email")).toBeDefined());
  expect(screen.getByLabelText("Password")).toBeDefined();
  expect(screen.getByRole("button", { name: "Sign in" })).toBeDefined();
});

test("sign-in offers a password reset route", async () => {
  renderAt("/sign-in", <SignInPage />);
  const link = await screen.findByRole("link", { name: "Forgot your password?" });
  expect(link.getAttribute("href")).toBe("/forgot-password");
});

test("the remember-me choice is offered", async () => {
  renderAt("/sign-in", <SignInPage />);
  const checkbox = await screen.findByLabelText("Keep me signed in on this device");
  expect((checkbox as HTMLInputElement).checked).toBe(false);
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

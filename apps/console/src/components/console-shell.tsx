import { Mark, cn } from "@marking/ui";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

/**
 * Console shell — sidebar + top bar. design.md §0 and §6.2.
 *
 * Navigation items are links with `aria-current`, never Radix `Tabs`: this
 * strip switches *routes*, and Tabs would break the back button, deep links,
 * and screen-reader semantics (design.md §1, correction 4).
 */

const NAV = [
  { to: "/home", label: "Home" },
  { to: "/courses", label: "Courses" },
  { to: "/exams", label: "Exams" },
] as const;

export function ConsoleShell({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh grid-cols-[248px_1fr] bg-background">
      <nav aria-label="Main" className="flex flex-col border-r border-sidebar-border bg-sidebar">
        <div className="flex h-14 items-center gap-2.5 px-5">
          <Mark className="h-6 w-6" />
          <span className="text-sm font-medium text-sidebar-foreground">Marking Assistant</span>
        </div>

        <ul className="flex flex-col gap-0.5 px-3 py-2">
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "block rounded-md px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="mt-auto border-t border-sidebar-border p-4">
          <p className="text-caption uppercase tracking-[.06em] text-muted-foreground">
            Signed in as
          </p>
          <p className="mt-1 truncate text-sm text-sidebar-foreground">lecturer@knust.edu.gh</p>
        </div>
      </nav>

      <div className="flex flex-col">
        <header className="flex h-14 shrink-0 items-center border-b border-border px-6" />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}

/**
 * Console is desktop-only at 1280px and up.
 *
 * frontend.md §1: below that it says so rather than offering a cramped
 * fallback. Marking on a phone produces bad marking, and refusing is the
 * correct behaviour — the failure cost of a wrong mark is high and silent.
 */
export function RequiresWideDisplay({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="hidden min-[1280px]:contents">{children}</div>
      <div className="grid min-h-dvh place-items-center p-8 min-[1280px]:hidden">
        <div className="max-w-[46ch] text-center">
          <Mark className="mx-auto h-8 w-8" />
          <h1 className="mt-6 text-h2 text-foreground">This screen needs a wider display</h1>
          <p className="mt-3 text-lead text-muted-foreground">
            The console needs at least 1280px. Marking on a narrow screen produces bad marking,
            so it is not offered rather than cramped.
          </p>
          <p className="mt-3 text-base text-muted-foreground">
            To photograph scripts, open the capture app on your phone instead.
          </p>
        </div>
      </div>
    </>
  );
}

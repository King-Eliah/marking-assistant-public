import { Mark, cn } from "@marking/ui";
import {
  BookOpen,
  ChevronRight,
  FileText,
  Home,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
} from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/lib/auth";

/**
 * Console shell — design.md §10.1.
 *
 *   sidebar 260px (56px collapsed) │ top bar 52px
 *                                  │ page header 72px, scrolls away
 *                                  │ content, 24px gutter, max 1440px
 *
 * Navigation is links with `aria-current`, never Radix `Tabs`: this strip
 * switches *routes*, and Tabs breaks the back button, deep links and
 * screen-reader semantics (design.md §1, correction 4).
 *
 * Lucide icons only, and none of them a sparkle, wand, star, brain or robot
 * (design.md §15).
 */

const NAV = [
  { to: "/home", label: "Home", icon: Home },
  { to: "/courses", label: "Courses", icon: BookOpen },
  { to: "/exams", label: "Exams", icon: FileText },
] as const;

function initials(email: string): string {
  const name = email.split("@")[0] ?? "";
  const parts = name.split(/[._-]/).filter(Boolean);
  return (parts.length >= 2 ? `${parts[0]![0]}${parts[1]![0]}` : name.slice(0, 2)).toUpperCase();
}

function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { signOut, ...auth } = useAuth();
  const email = auth.status === "signed-in" ? auth.identity.email : "";

  return (
    <nav
      aria-label="Main"
      className={cn(
        "flex shrink-0 flex-col border-r border-sidebar-border bg-sidebar",
        // Only two widths, both from design.md §10.1. No transition on width:
        // §5 permits almost no motion, and a marker sees this 300 times.
        collapsed ? "w-14" : "w-[260px]",
      )}
    >
      <div className="flex h-13 items-center gap-2 px-4" style={{ height: 52 }}>
        <Mark className="size-6 shrink-0" />
        {!collapsed && (
          <span className="truncate text-sm font-medium text-sidebar-foreground">
            Marking Assistant
          </span>
        )}
      </div>

      <ul className="flex flex-col gap-1 px-2 py-2">
        {NAV.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded px-3 py-2 text-sm transition-colors",
                  collapsed && "justify-center px-0",
                  isActive
                    ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                )
              }
            >
              <Icon className="size-4 shrink-0" aria-hidden />
              {!collapsed && label}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="mt-auto border-t border-sidebar-border p-2">
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full items-center gap-3 rounded px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen className="size-4 shrink-0" aria-hidden />
          ) : (
            <PanelLeftClose className="size-4 shrink-0" aria-hidden />
          )}
          {!collapsed && "Collapse"}
        </button>

        {!collapsed && email && (
          <div className="mt-2 px-3 pb-1">
            <p className="text-caption uppercase tracking-[.06em] text-muted-foreground">
              Signed in as
            </p>
            <p className="mt-1 truncate text-sm text-sidebar-foreground">{email}</p>
          </div>
        )}

        <button
          type="button"
          onClick={() => void signOut()}
          className="mt-1 flex w-full items-center gap-3 rounded px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
          title={collapsed ? "Sign out" : undefined}
        >
          <LogOut className="size-4 shrink-0" aria-hidden />
          {!collapsed && "Sign out"}
        </button>
      </div>
    </nav>
  );
}

export type Crumb = { label: string; to?: string };

/** Top bar — 52px, `--card`, 1px bottom border. Does not scroll away. */
function TopBar({ breadcrumb }: { breadcrumb: Crumb[] }) {
  const { ...auth } = useAuth();
  const email = auth.status === "signed-in" ? auth.identity.email : "";

  return (
    <header
      className="flex shrink-0 items-center justify-between border-b border-border bg-card px-6"
      style={{ height: 52 }}
    >
      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1 text-sm">
        {breadcrumb.map((crumb, index) => (
          <span key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-1">
            {index > 0 && (
              <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
            )}
            {crumb.to && index < breadcrumb.length - 1 ? (
              <NavLink
                to={crumb.to}
                className="truncate text-muted-foreground hover:text-foreground"
              >
                {crumb.label}
              </NavLink>
            ) : (
              <span
                className="truncate text-foreground"
                aria-current={index === breadcrumb.length - 1 ? "page" : undefined}
              >
                {crumb.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      <div className="flex items-center gap-2">
        <button
          type="button"
          className="flex items-center gap-2 rounded border border-input px-2 py-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
          aria-label="Search"
        >
          <Search className="size-3.5" aria-hidden />
          {/* Keyboard hints are tucked, not shouted. design.md §3.2 caption. */}
          <kbd className="rounded-sm bg-muted px-1 text-caption text-muted-foreground">
            &#8984;K
          </kbd>
        </button>
        {email && (
          <span
            className="grid size-7 place-items-center rounded-full bg-muted text-caption font-medium text-muted-foreground"
            title={email}
          >
            {initials(email)}
          </span>
        )}
      </div>
    </header>
  );
}

/**
 * Page header — 72px. Scrolls away; the top bar does not.
 *
 * Title, optional subtitle, optional primary action.
 */
export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-6 border-b border-border px-6 py-4">
      <div className="min-w-0">
        <h1 className="truncate text-h2 text-foreground">{title}</h1>
        {subtitle && <p className="mt-1 truncate text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function ConsoleShell({
  breadcrumb,
  children,
}: {
  breadcrumb: Crumb[];
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-dvh bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar breadcrumb={breadcrumb} />
        <main className="flex-1 overflow-y-auto">
          {/* 24px gutter, max 1440px — design.md §4.1, §10.1 */}
          <div className="mx-auto max-w-[1440px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

/**
 * Console is desktop-only at 1280px and up.
 *
 * frontend.md §1: below that it says so rather than offering a cramped
 * fallback. Marking on a narrow screen produces bad marking, and the failure
 * cost of a wrong mark is high and silent.
 */
export function RequiresWideDisplay({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="hidden min-[1280px]:contents">{children}</div>
      <div className="grid min-h-dvh place-items-center p-8 min-[1280px]:hidden">
        <div className="max-w-[46ch] text-center">
          <Mark className="mx-auto size-8" />
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

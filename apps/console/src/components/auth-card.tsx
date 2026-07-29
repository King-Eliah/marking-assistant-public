import { Mark } from "@marking/ui";
import type { ReactNode } from "react";

/**
 * The auth surface. design.md §9: one layout, five states.
 *
 * Sign in, forgot, reset, MFA and invitation all share this card — same width,
 * same rhythm, same button, same footer. Anyone who signs in once already knows
 * how to reset.
 */
export function AuthCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="w-full max-w-[400px]">
      <div className="rounded-lg border border-border bg-card p-8 shadow-sm">
        <h1 className="text-h1 tracking-tight text-card-foreground">{title}</h1>
        {description && <p className="mt-2 text-lead text-muted-foreground">{description}</p>}
        <div className="mt-7 flex flex-col gap-4">{children}</div>
      </div>
      {footer && <p className="mt-5 text-center text-xs text-muted-foreground">{footer}</p>}
    </div>
  );
}

/**
 * Left brand panel, hidden below 900px.
 *
 * design.md §9.1: solid --muted, the mark, one true sentence, the institution.
 * No photograph, no illustration, no gradient, no abstract shapes. If it has
 * nothing true to say, it is empty.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh grid-cols-1 lg:grid-cols-[40%_60%]">
      <aside className="hidden flex-col justify-between bg-muted p-12 lg:flex">
        <Mark className="h-8 w-8" />
        <div className="max-w-[24ch]">
          <p className="text-h1 tracking-tight text-foreground">Marking that shows its work.</p>
          <p className="mt-4 text-lead text-muted-foreground">
            Every mark this system suggests comes with the sentence it came from.
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          KNUST · Department of Computer Science
        </p>
      </aside>
      <main className="flex items-center justify-center p-6">{children}</main>
    </div>
  );
}

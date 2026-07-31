import { Button } from "@marking/ui";
import { FileText } from "lucide-react";

import { ConsoleShell, PageHeader, RequiresWideDisplay } from "@/components/console-shell";
import { useAuth } from "@/lib/auth";

/** Greeting by clock, not by exclamation. design.md §15: no exclamation marks. */
function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/**
 * C1 · Home. frontend.md §C.
 *
 * Empty state uses a single line icon, not an illustration (design.md §15).
 * The card has a border and no shadow — shadowed cards in a grid are the most
 * reliable tell of a templated design (§4.3).
 */
export function HomePage() {
  const auth = useAuth();
  const name =
    auth.status === "signed-in" ? (auth.identity.email.split("@")[0] ?? "") : "";

  return (
    <RequiresWideDisplay>
      <ConsoleShell breadcrumb={[{ label: "Home" }]}>
        <PageHeader
          title={name ? `${greeting()}, ${name}` : greeting()}
          subtitle="Nothing needs your attention yet."
        />

        <div className="p-6">
          <div className="rounded-lg border border-dashed border-border p-10 text-center">
            <FileText className="mx-auto size-6 text-muted-foreground" aria-hidden />
            <h2 className="mt-4 text-h3 text-foreground">No exams yet</h2>
            <p className="mx-auto mt-2 max-w-[48ch] text-lead text-muted-foreground">
              Create an exam, write its rubric, then print answer booklets for your students.
            </p>
            <Button className="mt-6" disabled>
              Create an exam
            </Button>
            <p className="mt-3 text-xs text-muted-foreground">
              Available once authoring lands — see docs/TASKS.md.
            </p>
          </div>
        </div>
      </ConsoleShell>
    </RequiresWideDisplay>
  );
}

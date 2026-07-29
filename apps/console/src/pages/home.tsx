import { Button } from "@marking/ui";

import { ConsoleShell, RequiresWideDisplay } from "@/components/console-shell";

/**
 * C1 · Home. frontend.md §C.
 *
 * Empty state only — there is no data layer yet. The stage 1 gate is
 * "a user can sign in and see an empty home", and this is that.
 */
export function HomePage() {
  return (
    <RequiresWideDisplay>
      <ConsoleShell>
        <h1 className="text-h2 text-foreground">Good evening</h1>
        <p className="mt-1 text-base text-muted-foreground">
          Nothing needs your attention yet.
        </p>

        <div className="mt-8 rounded-lg border border-dashed border-border p-10 text-center">
          <h2 className="text-h3 text-foreground">No exams yet</h2>
          <p className="mx-auto mt-2 max-w-[48ch] text-lead text-muted-foreground">
            Create an exam, write its rubric, then print answer booklets for your students.
          </p>
          <Button className="mt-6" disabled>
            Create an exam
          </Button>
          <p className="mt-3 text-xs text-muted-foreground">
            Available once authoring lands — see docs/TASKS.md, week 3.
          </p>
        </div>
      </ConsoleShell>
    </RequiresWideDisplay>
  );
}

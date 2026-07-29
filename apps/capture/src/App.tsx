import { cn } from "@marking/ui";

/**
 * Scaffold shell. No screens yet — booklet registration and camera capture land
 * at stage 11, see docs/TASKS.md. Full-bleed, no chrome, thumb-first.
 */
export function App() {
  return (
    <main className={cn("grid min-h-dvh place-items-center bg-background p-6")}>
      <div className="space-y-2 text-center">
        <h1 className="text-xl font-semibold text-foreground">Marking Assistant</h1>
        <p className="text-sm text-muted-foreground">Capture scaffold. Mobile only.</p>
      </div>
    </main>
  );
}

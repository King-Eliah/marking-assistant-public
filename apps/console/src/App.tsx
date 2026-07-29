import { cn } from "@marking/ui";

/**
 * Scaffold shell. No screens yet — the console shell and auth land at stage 10,
 * see docs/TASKS.md.
 */
export function App() {
  return (
    <main className={cn("grid min-h-dvh place-items-center bg-background p-8")}>
      <div className="max-w-prose space-y-2 text-center">
        <h1 className="text-2xl font-semibold text-foreground">Marking Assistant</h1>
        <p className="text-sm text-muted-foreground">
          Console scaffold. Desktop 1280px and up.
        </p>
      </div>
    </main>
  );
}

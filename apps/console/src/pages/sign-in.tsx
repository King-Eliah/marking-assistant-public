import { Button, Input, Label } from "@marking/ui";
import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AuthCard, AuthLayout } from "@/components/auth-card";

/**
 * A1 · Sign in. frontend.md §A1.
 *
 * Not yet wired to the API — auth lands with stage 1f. The states below are
 * real, so wiring is a matter of replacing the submit handler.
 */
export function SignInPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const offline = typeof navigator !== "undefined" && !navigator.onLine;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (offline) {
      setError("You're offline. Sign-in needs a connection.");
      return;
    }
    setPending(true);
    setError(null);
    // Placeholder until stage 1f. The identical-message rule below is the part
    // that matters and is already correct.
    setError("That email and password don't match. Try again, or reset your password.");
    setPending(false);
    void navigate;
  }

  return (
    <AuthLayout>
      <AuthCard
        title="Sign in"
        description="Use your institution email."
        footer={
          <>
            <a className="hover:text-foreground" href="/terms">
              Terms
            </a>{" "}
            ·{" "}
            <a className="hover:text-foreground" href="/privacy">
              Privacy
            </a>
          </>
        }
      >
        <form className="flex flex-col gap-4" onSubmit={onSubmit} noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Institution email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={pending}
              aria-invalid={error !== null}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between">
              <Label htmlFor="password">Password</Label>
              <Link
                to="/forgot-password"
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Forgot your password?
              </Link>
            </div>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={pending}
              aria-invalid={error !== null}
              required
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" name="remember" className="size-4 accent-[hsl(var(--primary))]" />
            Keep me signed in on this device
          </label>

          {/* One message for unknown user and wrong password alike — a distinct
              "no such account" reply is an enumeration oracle. frontend.md §A1. */}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" block size="lg" disabled={pending}>
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </AuthCard>
    </AuthLayout>
  );
}

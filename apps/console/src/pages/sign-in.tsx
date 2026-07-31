import { Button, Input, Label } from "@marking/ui";
import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AuthCard, AuthLayout } from "@/components/auth-card";
import { ApiError, OfflineError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * A1 · Sign in. frontend.md §A1.
 *
 * Four states, all specified: loading, error, locked, offline. The error text
 * is identical for an unknown address and a wrong password, and matches what
 * the API returns — two different wordings would be a second, subtler way to
 * work out which accounts exist.
 */
export function SignInPage() {
  const navigate = useNavigate();
  const { status, signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "signed-in") navigate("/home", { replace: true });
  }, [status, navigate]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await signIn(email, password, rememberMe);
      navigate("/home", { replace: true });
    } catch (caught) {
      if (caught instanceof OfflineError) {
        setError(caught.message);
      } else if (caught instanceof ApiError) {
        setError(caught.message);
      } else {
        // Never the raw exception. A stack trace or a fetch message in the UI
        // tells the user nothing and can leak internals.
        setError("Something went wrong signing you in. Try again in a moment.");
      }
      setPending(false);
    }
  }

  const disabled = pending || status === "checking";

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
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Institution email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={disabled}
              aria-invalid={error !== null}
              aria-describedby={error ? "sign-in-error" : undefined}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
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
              disabled={disabled}
              aria-invalid={error !== null}
              aria-describedby={error ? "sign-in-error" : undefined}
              required
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={disabled}
              className="size-4 rounded-sm accent-[hsl(var(--primary))]"
            />
            Keep me signed in on this device
          </label>

          {/* role="alert" so a screen reader announces it without the user
              having to go looking. Text, not a coloured panel: design.md §2.4
              forbids a coloured background behind body text. */}
          {error && (
            <p id="sign-in-error" role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" block size="lg" disabled={disabled}>
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </AuthCard>
    </AuthLayout>
  );
}

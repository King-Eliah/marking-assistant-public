import { Mark } from "@marking/ui";
import type { ReactNode } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "@/lib/auth";
import { HomePage } from "@/pages/home";
import { SignInPage } from "@/pages/sign-in";

/**
 * Holds a route until the session has been worked out.
 *
 * Without this the app flashes the sign-in screen at someone who is already
 * signed in, while the refresh cookie is still being exchanged. A flash of the
 * wrong screen reads as a bug even when it resolves correctly a moment later.
 *
 * The waiting state is deliberately plain — design.md §5 forbids skeleton
 * shimmer, and a spinner for 200ms is worse than nothing.
 */
function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();

  if (status === "checking") {
    return (
      <div className="grid min-h-dvh place-items-center bg-background">
        <Mark className="size-8 opacity-40" />
      </div>
    );
  }
  if (status === "signed-out") {
    return <Navigate to="/sign-in" replace />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <AuthProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/sign-in" element={<SignInPage />} />
          <Route
            path="/home"
            element={
              <RequireAuth>
                <HomePage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

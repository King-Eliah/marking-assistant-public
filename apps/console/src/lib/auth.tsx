import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import type { Identity } from "./api";
import * as api from "./api";

type AuthState =
  /** Still working out whether a refresh cookie recovers a session. */
  | { status: "checking" }
  | { status: "signed-out" }
  | { status: "signed-in"; identity: Identity };

type AuthValue = AuthState & {
  signIn: (email: string, password: string, rememberMe: boolean) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "checking" });

  // On load, try to recover a session from the httpOnly refresh cookie. The
  // "checking" state exists so the app does not flash the sign-in screen at
  // someone who is already signed in — a flash of the wrong screen reads as a
  // bug even when it resolves correctly.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const recovered = await api.tryRefresh();
      if (cancelled) return;
      if (!recovered) {
        setState({ status: "signed-out" });
        return;
      }
      try {
        const identity = await api.me();
        if (!cancelled) setState({ status: "signed-in", identity });
      } catch {
        if (!cancelled) setState({ status: "signed-out" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(
    async (email: string, password: string, rememberMe: boolean) => {
      const identity = await api.login(email, password, rememberMe);
      setState({ status: "signed-in", identity });
    },
    [],
  );

  const signOut = useCallback(async () => {
    await api.logout();
    setState({ status: "signed-out" });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signOut }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return value;
}

import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { HomePage } from "@/pages/home";
import { SignInPage } from "@/pages/sign-in";

/**
 * Console routes. Only the MVP shell so far — the rest of the sitemap
 * (frontend.md §2) lands with its screens.
 */
export function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </Router>
  );
}

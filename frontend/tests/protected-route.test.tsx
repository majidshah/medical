import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { ProtectedRoute } from "@/lib/protected-route";
import "@/i18n";

function renderProtected(initialPath: string) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <ThemeProvider><AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/patients" element={<div>Patient List</div>} />
            </Route>
          </Routes>
        </AuthProvider></ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute", () => {
  it("redirects to login when not authenticated", () => {
    renderProtected("/patients");
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });
});

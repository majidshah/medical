import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { LoginPage } from "@/pages/login";
import "@/i18n";

vi.mock("@/api/auth", () => ({
  login: vi.fn(),
  register: vi.fn(),
  getMe: vi.fn(),
}));

function renderLogin() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ThemeProvider><AuthProvider>
          <LoginPage />
        </AuthProvider></ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  it("renders the login form", () => {
    renderLogin();
    expect(screen.getByText("Sign in to MedVault")).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows error on failed login", async () => {
    const { login } = await import("@/api/auth");
    const mockLogin = vi.mocked(login);
    const { ApiError } = await import("@/api/client");
    mockLogin.mockRejectedValueOnce(new ApiError(401, "Invalid credentials"));

    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email address"), "test@test.com");
    await user.type(screen.getByLabelText("Password"), "wrongpass");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect",
    );
  });
});

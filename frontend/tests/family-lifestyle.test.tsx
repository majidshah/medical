import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as fhApi from "@/api/family-history";
import * as obsApi from "@/api/observations";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { FamilyHistoryPage } from "@/pages/family-history";
import { LifestylePage } from "@/pages/lifestyle";
import "@/i18n";

vi.mock("@/api/family-history", () => ({
  listFamilyHistory: vi.fn(),
  createFamilyHistory: vi.fn(),
  updateFamilyHistory: vi.fn(),
  deleteFamilyHistory: vi.fn(),
}));

vi.mock("@/api/observations", () => ({
  fetchObservationTypes: vi.fn(),
  listObservations: vi.fn(),
  createObservation: vi.fn(),
  updateObservation: vi.fn(),
  deleteObservation: vi.fn(),
  fetchTrend: vi.fn(),
}));

function renderPage(path: string, element: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <ThemeProvider><AuthProvider>
          <Routes>
            <Route path={path.replace("p1", ":patientId")} element={element} />
          </Routes>
        </AuthProvider></ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FamilyHistoryPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows empty state with add button", async () => {
    vi.mocked(fhApi.listFamilyHistory).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/family-history", <FamilyHistoryPage />);
    expect(await screen.findByText("No family history recorded. Add one.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add family history" })).toBeInTheDocument();
  });

  it("renders list with relationship and condition", async () => {
    vi.mocked(fhApi.listFamilyHistory).mockResolvedValue({
      items: [{
        id: "fh1", patient_id: "p1", account_id: "a1",
        relationship: "father", condition_code_system: "", condition_code: null,
        condition_display_name: "Diabetes", onset_age: 55, deceased: true,
        notes: null, is_active: true,
      }],
      total: 1, limit: 20, offset: 0,
    });
    renderPage("/patients/p1/family-history", <FamilyHistoryPage />);
    expect(await screen.findByText("Diabetes")).toBeInTheDocument();
    expect(screen.getByText("Father")).toBeInTheDocument();
    expect(screen.getByText("Deceased")).toBeInTheDocument();
  });

  it("opens add form", async () => {
    vi.mocked(fhApi.listFamilyHistory).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/family-history", <FamilyHistoryPage />);
    const user = userEvent.setup();
    await screen.findByText("No family history recorded. Add one.");
    await user.click(screen.getByRole("button", { name: "Add family history" }));
    expect(screen.getByRole("heading", { name: "Add family history" })).toBeInTheDocument();
    expect(screen.getByLabelText("Condition")).toBeInTheDocument();
  });
});

describe("LifestylePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(obsApi.fetchObservationTypes).mockResolvedValue([
      { id: "t1", key: "sleep_duration", display_label: "Sleep Duration", loinc_code: "93832-4", value_type: "numeric", unit: "h" },
      { id: "t2", key: "smoking_status", display_label: "Smoking Status", loinc_code: "72166-2", value_type: "coded", unit: null },
    ]);
  });

  it("shows empty state", async () => {
    vi.mocked(obsApi.listObservations).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/lifestyle", <LifestylePage />);
    expect(await screen.findByText("No observations recorded.")).toBeInTheDocument();
  });

  it("renders observations list", async () => {
    vi.mocked(obsApi.listObservations).mockResolvedValue({
      items: [{
        id: "o1", patient_id: "p1", account_id: "a1", observation_type_id: "t1",
        effective_date: "2024-06-01", value_numeric: 7.5, value_code: null,
        value_text: null, unit: "h", notes: null, is_active: true,
      }],
      total: 1, limit: 20, offset: 0,
    });
    renderPage("/patients/p1/lifestyle", <LifestylePage />);
    expect(await screen.findByText("7.5 h")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sleep Duration" })).toBeInTheDocument();
  });

  it("opens type-adaptive form with numeric input for sleep", async () => {
    vi.mocked(obsApi.listObservations).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/lifestyle", <LifestylePage />);
    const user = userEvent.setup();
    await screen.findByText("No observations recorded.");
    await user.click(screen.getByRole("button", { name: "Record observation" }));
    expect(screen.getByText("Record an observation")).toBeInTheDocument();
    expect(screen.getByLabelText("Value")).toBeInTheDocument();
  });

  it("shows trend button when type is filtered", async () => {
    vi.mocked(obsApi.listObservations).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    vi.mocked(obsApi.fetchTrend).mockResolvedValue({
      observation_type_key: "sleep_duration", chartable: true, points: [],
    });
    renderPage("/patients/p1/lifestyle", <LifestylePage />);
    const user = userEvent.setup();
    await screen.findByText("No observations recorded.");
    const select = screen.getByDisplayValue("All types");
    await user.selectOptions(select, "sleep_duration");
    expect(screen.getByRole("button", { name: "Show trend" })).toBeInTheDocument();
  });

  it("shows non-chartable note for coded type", async () => {
    vi.mocked(obsApi.listObservations).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    vi.mocked(obsApi.fetchTrend).mockResolvedValue({
      observation_type_key: "smoking_status", chartable: false,
      points: [{ effective_date: "2024-01-01", value: "current", unit: null }],
    });
    renderPage("/patients/p1/lifestyle", <LifestylePage />);
    const user = userEvent.setup();
    await screen.findByText("No observations recorded.");
    await user.selectOptions(screen.getByDisplayValue("All types"), "smoking_status");
    await user.click(screen.getByRole("button", { name: "Show trend" }));
    expect(await screen.findByText(/not numeric and cannot be charted/)).toBeInTheDocument();
  });
});

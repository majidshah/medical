import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as allergiesApi from "@/api/allergies";
import * as medicationsApi from "@/api/medications";
import * as immunizationsApi from "@/api/immunizations";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { AllergiesPage } from "@/pages/allergies";
import { MedicationsPage } from "@/pages/medications";
import { ImmunizationsPage } from "@/pages/immunizations";
import "@/i18n";

vi.mock("@/api/allergies", () => ({
  listAllergies: vi.fn(),
  createAllergy: vi.fn(),
  updateAllergy: vi.fn(),
  deleteAllergy: vi.fn(),
}));
vi.mock("@/api/medications", () => ({
  listMedications: vi.fn(),
  createMedication: vi.fn(),
  updateMedication: vi.fn(),
  deleteMedication: vi.fn(),
}));
vi.mock("@/api/immunizations", () => ({
  listImmunizations: vi.fn(),
  createImmunization: vi.fn(),
  updateImmunization: vi.fn(),
  deleteImmunization: vi.fn(),
  fetchEPIVaccines: vi.fn(),
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

describe("AllergiesPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows empty state with add button", async () => {
    vi.mocked(allergiesApi.listAllergies).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/allergies", <AllergiesPage />);
    expect(await screen.findByText("No allergies recorded. Add one.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add allergy" })).toBeInTheDocument();
  });

  it("renders allergy list with category and criticality", async () => {
    vi.mocked(allergiesApi.listAllergies).mockResolvedValue({
      items: [{
        id: "a1", patient_id: "p1", account_id: "x", code_system: "", code: null,
        display_name: "Peanuts", category: "food", criticality: "high",
        clinical_status: "active", reaction: "Anaphylaxis", severity: "severe",
        onset_date: null, notes: null, is_active: true,
      }],
      total: 1, limit: 20, offset: 0,
    });
    renderPage("/patients/p1/allergies", <AllergiesPage />);
    expect(await screen.findByText("Peanuts")).toBeInTheDocument();
    expect(screen.getByText("Food")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("opens add form", async () => {
    vi.mocked(allergiesApi.listAllergies).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/allergies", <AllergiesPage />);
    const user = userEvent.setup();
    await screen.findByText("No allergies recorded. Add one.");
    await user.click(screen.getByRole("button", { name: "Add allergy" }));
    expect(screen.getByText("Add an allergy")).toBeInTheDocument();
    expect(screen.getByLabelText("Allergen / substance")).toBeInTheDocument();
  });
});

describe("MedicationsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows empty state with add button", async () => {
    vi.mocked(medicationsApi.listMedications).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/medications", <MedicationsPage />);
    expect(await screen.findByText("No medications recorded. Add one.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add medication" })).toBeInTheDocument();
  });

  it("renders medication list with status and dosage", async () => {
    vi.mocked(medicationsApi.listMedications).mockResolvedValue({
      items: [{
        id: "m1", patient_id: "p1", account_id: "x", code_system: null, code: null,
        display_name: "Metformin", dosage: "500mg", frequency: "twice daily",
        route: "oral", status: "active", start_date: null, end_date: null,
        prescribed_by: null, notes: null, is_active: true,
      }],
      total: 1, limit: 20, offset: 0,
    });
    renderPage("/patients/p1/medications", <MedicationsPage />);
    expect(await screen.findByText("Metformin")).toBeInTheDocument();
    expect(screen.getByText("500mg")).toBeInTheDocument();
    expect(screen.getByText("twice daily")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });
});

describe("ImmunizationsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows empty state with add button", async () => {
    vi.mocked(immunizationsApi.listImmunizations).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderPage("/patients/p1/immunizations", <ImmunizationsPage />);
    expect(await screen.findByText("No immunizations recorded. Add one.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add immunization" })).toBeInTheDocument();
  });

  it("renders immunization list with date and dose", async () => {
    vi.mocked(immunizationsApi.listImmunizations).mockResolvedValue({
      items: [{
        id: "i1", patient_id: "p1", account_id: "x", epi_vaccine_id: null,
        vaccine_display_name: "BCG", code_system: null, code: null,
        dose_number: 1, occurrence_date: "2024-01-15", lot_number: null,
        manufacturer: null, site: null, status: "completed", notes: null, is_active: true,
      }],
      total: 1, limit: 20, offset: 0,
    });
    renderPage("/patients/p1/immunizations", <ImmunizationsPage />);
    expect(await screen.findByText("BCG")).toBeInTheDocument();
    expect(screen.getByText("2024-01-15")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText(/Dose 1/)).toBeInTheDocument();
  });

  it("opens add form with EPI dropdown", async () => {
    vi.mocked(immunizationsApi.listImmunizations).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    vi.mocked(immunizationsApi.fetchEPIVaccines).mockResolvedValue([
      { id: "e1", name: "BCG", short_name: "BCG", total_doses: 1, description: null },
    ]);
    renderPage("/patients/p1/immunizations", <ImmunizationsPage />);
    const user = userEvent.setup();
    await screen.findByText("No immunizations recorded. Add one.");
    await user.click(screen.getByRole("button", { name: "Add immunization" }));
    expect(screen.getByText("Add an immunization")).toBeInTheDocument();
    await user.click(screen.getByLabelText("EPI vaccine (Pakistan schedule)"));
    expect(await screen.findByText("BCG (BCG)")).toBeInTheDocument();
  });
});

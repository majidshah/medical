import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as patientsApi from "@/api/patients";
import { AuthProvider } from "@/lib/auth-context";
import { PatientListPage } from "@/pages/patient-list";
import "@/i18n";

vi.mock("@/api/patients", () => ({
  fetchPatients: vi.fn(),
  fetchPatientSummary: vi.fn(),
  createPatient: vi.fn(),
}));

const mockFetchPatients = vi.mocked(patientsApi.fetchPatients);

function renderList() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <PatientListPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PatientListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockFetchPatients.mockReturnValue(new Promise(() => {}));
    renderList();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state", async () => {
    mockFetchPatients.mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    });
    renderList();
    expect(
      await screen.findByText("Add your first family member"),
    ).toBeInTheDocument();
  });

  it("renders patient list", async () => {
    mockFetchPatients.mockResolvedValue({
      items: [
        {
          id: "1",
          account_id: "a1",
          full_name: "Ali Khan",
          medical_id: "42201-1234567-8",
          relationship_to_account: "self",
          gender: "male",
          date_of_birth: null,
          has_cnic: true,
          guardian_patient_id: null,
          is_active: true,
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    });
    renderList();
    expect(await screen.findByText("Ali Khan")).toBeInTheDocument();
    expect(screen.getByText(/42201-1234567-8/)).toBeInTheDocument();
  });
});

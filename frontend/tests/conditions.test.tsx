import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as conditionsApi from "@/api/conditions";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { ConditionsPage } from "@/pages/conditions";
import "@/i18n";

vi.mock("@/api/conditions", () => ({
  listConditions: vi.fn(),
  createCondition: vi.fn(),
  updateCondition: vi.fn(),
  deleteCondition: vi.fn(),
}));

const mockList = vi.mocked(conditionsApi.listConditions);
const mockCreate = vi.mocked(conditionsApi.createCondition);
const mockDelete = vi.mocked(conditionsApi.deleteCondition);

function renderConditions() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/patients/p1/conditions"]}>
        <ThemeProvider><AuthProvider>
          <Routes>
            <Route
              path="/patients/:patientId/conditions"
              element={<ConditionsPage />}
            />
          </Routes>
        </AuthProvider></ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ConditionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state with add button", async () => {
    mockList.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    renderConditions();
    expect(
      await screen.findByText("No conditions recorded. Add one."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Add condition" }),
    ).toBeInTheDocument();
  });

  it("renders conditions list with status badges", async () => {
    mockList.mockResolvedValue({
      items: [
        {
          id: "c1",
          patient_id: "p1",
          account_id: "a1",
          code_system: "http://snomed.info/sct",
          code: null,
          display_name: "Hypertension",
          clinical_status: "active",
          onset_date: "2023-06-01",
          abatement_date: null,
          notes: null,
          is_active: true,
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    });
    renderConditions();
    expect(await screen.findByText("Hypertension")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText(/2023-06-01/)).toBeInTheDocument();
  });

  it("opens add form and submits", async () => {
    mockList.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    mockCreate.mockResolvedValue({
      id: "c2",
      patient_id: "p1",
      account_id: "a1",
      code_system: "http://snomed.info/sct",
      code: null,
      display_name: "Asthma",
      clinical_status: "active",
      onset_date: null,
      abatement_date: null,
      notes: null,
      is_active: true,
    });

    renderConditions();
    const user = userEvent.setup();
    await screen.findByText("No conditions recorded. Add one.");
    await user.click(screen.getByRole("button", { name: "Add condition" }));
    expect(screen.getByText("Add a condition")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Condition name"), "Asthma");
    await user.click(screen.getByRole("button", { name: "Add condition" }));

    expect(mockCreate).toHaveBeenCalledWith("p1", expect.objectContaining({
      display_name: "Asthma",
      clinical_status: "active",
    }));
  });

  it("shows confirm dialog before delete", async () => {
    mockList.mockResolvedValue({
      items: [
        {
          id: "c1",
          patient_id: "p1",
          account_id: "a1",
          code_system: "http://snomed.info/sct",
          code: null,
          display_name: "Old Condition",
          clinical_status: "resolved",
          onset_date: null,
          abatement_date: null,
          notes: null,
          is_active: true,
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    });
    mockDelete.mockResolvedValue(undefined);

    renderConditions();
    const user = userEvent.setup();
    await screen.findByText("Old Condition");
    await user.click(screen.getByText("Remove"));

    expect(
      screen.getByText(/Remove "Old Condition" from conditions/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
  });

  it("has edit and remove buttons on each condition", async () => {
    mockList.mockResolvedValue({
      items: [
        {
          id: "c1",
          patient_id: "p1",
          account_id: "a1",
          code_system: "http://snomed.info/sct",
          code: null,
          display_name: "Diabetes",
          clinical_status: "active",
          onset_date: null,
          abatement_date: null,
          notes: null,
          is_active: true,
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    });
    renderConditions();
    await screen.findByText("Diabetes");
    expect(screen.getByText("Edit")).toBeInTheDocument();
    expect(screen.getByText("Remove")).toBeInTheDocument();
  });
});

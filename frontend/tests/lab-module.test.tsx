import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as labApi from "@/api/lab";
import { AuthProvider } from "@/lib/auth-context";
import { LabReportsPage } from "@/pages/lab-reports";
import "@/i18n";

vi.mock("@/api/lab", () => ({
  searchCatalogue: vi.fn(),
  getCatalogueDetail: vi.fn(),
  uploadFile: vi.fn(),
  downloadFileUrl: vi.fn(),
  createReport: vi.fn(),
  listReports: vi.fn(),
  getReportDetail: vi.fn(),
  createResult: vi.fn(),
  deleteReport: vi.fn(),
  getTimeline: vi.fn(),
  getLabTrend: vi.fn(),
  exportPdf: vi.fn(),
  exportFhir: vi.fn(),
}));

function renderLab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/patients/p1/reports"]}>
        <AuthProvider>
          <Routes>
            <Route path="/patients/:patientId/reports" element={<LabReportsPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LabReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(labApi.getTimeline).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    vi.mocked(labApi.searchCatalogue).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
  });

  it("shows timeline empty state", async () => {
    renderLab();
    expect(await screen.findByText("No reports yet.")).toBeInTheDocument();
  });

  it("shows export buttons", async () => {
    renderLab();
    await screen.findByText("No reports yet.");
    expect(screen.getByRole("button", { name: "Export PDF" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export FHIR" })).toBeInTheDocument();
  });

  it("shows new report button", async () => {
    renderLab();
    await screen.findByText("No reports yet.");
    expect(screen.getByRole("button", { name: "New report" })).toBeInTheDocument();
  });

  it("opens create report form", async () => {
    renderLab();
    const user = userEvent.setup();
    await screen.findByText("No reports yet.");
    await user.click(screen.getByRole("button", { name: "New report" }));
    expect(screen.getByText("Create a report")).toBeInTheDocument();
    expect(screen.getByLabelText("Report date")).toBeInTheDocument();
  });

  it("renders timeline with entries", async () => {
    vi.mocked(labApi.getTimeline).mockResolvedValue({
      items: [
        { id: "r1", report_date: "2024-06-01", category: "lab", lab_name: "City Lab", result_count: 3, has_out_of_range: true },
      ],
      total: 1, limit: 20, offset: 0,
    });
    renderLab();
    expect(await screen.findByText("2024-06-01")).toBeInTheDocument();
    expect(screen.getByText("City Lab")).toBeInTheDocument();
    expect(screen.getByText("3 results")).toBeInTheDocument();
  });

  it("switches to trends tab", async () => {
    renderLab();
    const user = userEvent.setup();
    await screen.findByText("No reports yet.");
    await user.click(screen.getByRole("button", { name: "Trends" }));
    expect(screen.getByText("Choose a test...")).toBeInTheDocument();
  });

  it("has timeline and trends tabs", async () => {
    renderLab();
    await screen.findByText("No reports yet.");
    expect(screen.getByRole("button", { name: "Timeline" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trends" })).toBeInTheDocument();
  });

  it("shows error when export fails", async () => {
    vi.mocked(labApi.exportPdf).mockRejectedValue(new Error("fail"));
    renderLab();
    const user = userEvent.setup();
    await screen.findByText("No reports yet.");
    await user.click(screen.getByRole("button", { name: "Export PDF" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Export failed. Please try again.");
  });
});

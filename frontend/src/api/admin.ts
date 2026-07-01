import { api } from "./client";

export interface Department {
  id: string;
  key: string;
  name: string;
  display_order: number;
  is_active: boolean;
}

export interface DepartmentFormData {
  key: string;
  name: string;
  display_order: number;
}

export interface Panel {
  id: string;
  department_id: string;
  key: string;
  name: string;
  display_order: number;
  is_active: boolean;
}

export interface PanelFormData {
  department_id: string;
  key: string;
  name: string;
  display_order: number;
}

export interface CatalogueTest {
  id: string;
  key: string;
  display_name: string;
  department_id: string;
  panel_id: string | null;
  loinc_code: string | null;
  category: string;
  specimen: string | null;
  default_unit: string | null;
  is_active: boolean;
}

export interface TestFormData {
  key: string;
  display_name: string;
  department_id: string;
  panel_id?: string;
  loinc_code?: string;
  category: string;
  specimen?: string;
  default_unit?: string;
}

export interface AdminRange {
  id: string;
  test_id: string;
  applies_to: string;
  low: number | null;
  high: number | null;
  unit: string;
  notes: string | null;
  lab_id: string | null;
  needs_clinical_review: boolean;
}

export interface RangeFormData {
  test_id: string;
  applies_to: string;
  low?: number;
  high?: number;
  unit: string;
  notes?: string;
  lab_id?: string;
  needs_clinical_review?: boolean;
}

export interface Lab {
  id: string;
  key: string;
  name: string;
  is_active: boolean;
}

export interface LabFormData {
  key: string;
  name: string;
}

// --- Departments ---

export async function listDepartments(): Promise<Department[]> {
  return api<Department[]>("/api/v1/admin/departments");
}

export async function createDepartment(data: DepartmentFormData): Promise<Department> {
  return api<Department>("/api/v1/admin/departments", {
    method: "POST", body: JSON.stringify(data),
  });
}

export async function updateDepartment(
  id: string, data: Partial<DepartmentFormData & { is_active: boolean }>,
): Promise<Department> {
  return api<Department>(`/api/v1/admin/departments/${id}`, {
    method: "PATCH", body: JSON.stringify(data),
  });
}

export async function deactivateDepartment(id: string): Promise<void> {
  await api<Department>(`/api/v1/admin/departments/${id}`, { method: "DELETE" });
}

// --- Panels ---

export async function listPanels(departmentId?: string): Promise<Panel[]> {
  const qs = departmentId ? `?department_id=${departmentId}` : "";
  return api<Panel[]>(`/api/v1/admin/panels${qs}`);
}

export async function createPanel(data: PanelFormData): Promise<Panel> {
  return api<Panel>("/api/v1/admin/panels", { method: "POST", body: JSON.stringify(data) });
}

export async function updatePanel(
  id: string, data: Partial<Omit<PanelFormData, "department_id"> & { is_active: boolean }>,
): Promise<Panel> {
  return api<Panel>(`/api/v1/admin/panels/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deactivatePanel(id: string): Promise<void> {
  await api<Panel>(`/api/v1/admin/panels/${id}`, { method: "DELETE" });
}

// --- Tests ---

export async function listTests(params?: { departmentId?: string; panelId?: string }): Promise<CatalogueTest[]> {
  const query = new URLSearchParams();
  if (params?.departmentId) query.set("department_id", params.departmentId);
  if (params?.panelId) query.set("panel_id", params.panelId);
  const qs = query.toString();
  return api<CatalogueTest[]>(`/api/v1/admin/tests${qs ? `?${qs}` : ""}`);
}

export async function createTest(data: TestFormData): Promise<CatalogueTest> {
  return api<CatalogueTest>("/api/v1/admin/tests", { method: "POST", body: JSON.stringify(data) });
}

export async function updateTest(
  id: string, data: Partial<TestFormData & { is_active: boolean }>,
): Promise<CatalogueTest> {
  return api<CatalogueTest>(`/api/v1/admin/tests/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deactivateTest(id: string): Promise<void> {
  await api<CatalogueTest>(`/api/v1/admin/tests/${id}`, { method: "DELETE" });
}

// --- Reference ranges ---

export async function listRanges(testId: string): Promise<AdminRange[]> {
  return api<AdminRange[]>(`/api/v1/admin/tests/${testId}/ranges`);
}

export async function createRange(data: RangeFormData): Promise<AdminRange> {
  return api<AdminRange>("/api/v1/admin/ranges", { method: "POST", body: JSON.stringify(data) });
}

export async function updateRange(id: string, data: Partial<RangeFormData>): Promise<AdminRange> {
  return api<AdminRange>(`/api/v1/admin/ranges/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteRange(id: string): Promise<void> {
  await api<void>(`/api/v1/admin/ranges/${id}`, { method: "DELETE" });
}

// --- Labs ---

export async function listLabs(): Promise<Lab[]> {
  return api<Lab[]>("/api/v1/admin/labs");
}

export async function createLab(data: LabFormData): Promise<Lab> {
  return api<Lab>("/api/v1/admin/labs", { method: "POST", body: JSON.stringify(data) });
}

export async function updateLab(
  id: string, data: Partial<LabFormData & { is_active: boolean }>,
): Promise<Lab> {
  return api<Lab>(`/api/v1/admin/labs/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deactivateLab(id: string): Promise<void> {
  await api<Lab>(`/api/v1/admin/labs/${id}`, { method: "DELETE" });
}

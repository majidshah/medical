import { api, apiBlob, apiUpload } from "./client";

export interface LabTest {
  id: string;
  key: string;
  display_name: string;
  loinc_code: string | null;
  category: string;
  specimen: string | null;
  default_unit: string | null;
}

export interface ReferenceRange {
  id: string;
  test_id: string;
  applies_to: string;
  low: number | null;
  high: number | null;
  unit: string;
  notes: string | null;
}

export interface LabTestDetail extends LabTest {
  reference_ranges: ReferenceRange[];
}

export interface LabTestList {
  items: LabTest[];
  total: number;
  limit: number;
  offset: number;
}

export interface StoredFileRef {
  id: string;
  patient_id: string;
  account_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  is_active: boolean;
}

export interface NormalityInfo {
  status: string;
  range_low: number | null;
  range_high: number | null;
  range_unit: string | null;
  range_applies_to: string | null;
  reason: string | null;
}

export interface LabResult {
  id: string;
  report_id: string;
  patient_id: string;
  account_id: string;
  test_id: string | null;
  display_name: string;
  loinc_code: string | null;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  effective_date: string;
  notes: string | null;
  is_active: boolean;
  normality?: NormalityInfo;
}

export interface Report {
  id: string;
  patient_id: string;
  account_id: string;
  category: string;
  report_date: string;
  lab_name: string | null;
  file_id: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface ReportDetail extends Report {
  results: LabResult[];
  file_ref: StoredFileRef | null;
}

export interface ReportList {
  items: Report[];
  total: number;
  limit: number;
  offset: number;
}

export interface TimelineEntry {
  id: string;
  report_date: string;
  category: string;
  lab_name: string | null;
  result_count: number;
  has_out_of_range: boolean;
}

export interface TimelineResponse {
  items: TimelineEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface LabTrendPoint {
  effective_date: string;
  value: number | null;
  unit: string | null;
  normality_status: string;
}

export interface LabTrendResponse {
  test_key: string;
  test_display_name: string;
  chartable: boolean;
  range_low: number | null;
  range_high: number | null;
  range_unit: string | null;
  points: LabTrendPoint[];
}

export async function searchCatalogue(params?: {
  q?: string;
  category?: string;
}): Promise<LabTestList> {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.category) query.set("category", params.category);
  const qs = query.toString();
  return api<LabTestList>(`/api/v1/lab-catalogue${qs ? `?${qs}` : ""}`);
}

export async function getCatalogueDetail(testId: string): Promise<LabTestDetail> {
  return api<LabTestDetail>(`/api/v1/lab-catalogue/${testId}`);
}

export async function uploadFile(patientId: string, file: File): Promise<StoredFileRef> {
  const fd = new FormData();
  fd.append("file", file);
  return apiUpload<StoredFileRef>(`/api/v1/patients/${patientId}/files`, fd);
}

export async function downloadFileUrl(patientId: string, fileId: string): Promise<Blob> {
  return apiBlob(`/api/v1/patients/${patientId}/files/${fileId}`);
}

export async function createReport(
  patientId: string,
  data: { category: string; report_date: string; lab_name?: string; file_id?: string; notes?: string },
): Promise<Report> {
  return api<Report>(`/api/v1/patients/${patientId}/reports`, {
    method: "POST", body: JSON.stringify(data),
  });
}

export async function listReports(
  patientId: string,
  params?: { category?: string; from?: string; to?: string },
): Promise<ReportList> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const qs = query.toString();
  return api<ReportList>(`/api/v1/patients/${patientId}/reports${qs ? `?${qs}` : ""}`);
}

export async function getReportDetail(patientId: string, reportId: string): Promise<ReportDetail> {
  return api<ReportDetail>(`/api/v1/patients/${patientId}/reports/${reportId}`);
}

export async function createResult(
  patientId: string,
  reportId: string,
  data: {
    display_name: string;
    test_id?: string;
    value_numeric?: number;
    value_text?: string;
    unit?: string;
    effective_date: string;
    notes?: string;
  },
): Promise<LabResult> {
  return api<LabResult>(`/api/v1/patients/${patientId}/reports/${reportId}/results`, {
    method: "POST", body: JSON.stringify(data),
  });
}

export async function deleteReport(patientId: string, reportId: string): Promise<void> {
  return api<void>(`/api/v1/patients/${patientId}/reports/${reportId}`, { method: "DELETE" });
}

export async function getTimeline(
  patientId: string,
  params?: { category?: string; from?: string; to?: string },
): Promise<TimelineResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const qs = query.toString();
  return api<TimelineResponse>(`/api/v1/patients/${patientId}/timeline${qs ? `?${qs}` : ""}`);
}

export async function getLabTrend(
  patientId: string,
  testKey: string,
  from?: string,
  to?: string,
): Promise<LabTrendResponse> {
  const query = new URLSearchParams({ test: testKey });
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  return api<LabTrendResponse>(`/api/v1/patients/${patientId}/lab-trend?${query}`);
}

export async function exportPdf(patientId: string): Promise<Blob> {
  return apiBlob(`/api/v1/patients/${patientId}/export/pdf`);
}

export async function exportFhir(patientId: string): Promise<Blob> {
  return apiBlob(`/api/v1/patients/${patientId}/export/fhir`);
}

import { api } from "./client";

export interface ObservationType {
  id: string;
  key: string;
  display_label: string;
  loinc_code: string | null;
  value_type: string;
  unit: string | null;
}

export interface Observation {
  id: string;
  patient_id: string;
  account_id: string;
  observation_type_id: string;
  effective_date: string;
  value_numeric: number | null;
  value_code: string | null;
  value_text: string | null;
  unit: string | null;
  notes: string | null;
  is_active: boolean;
}

interface ObservationList {
  items: Observation[];
  total: number;
  limit: number;
  offset: number;
}

export interface ObservationFormData {
  observation_type_id: string;
  effective_date: string;
  value_numeric?: number;
  value_code?: string;
  value_text?: string;
  unit?: string;
  notes?: string;
}

export interface TrendPoint {
  effective_date: string;
  value: number | string | null;
  unit: string | null;
}

export interface TrendResponse {
  observation_type_key: string;
  chartable: boolean;
  points: TrendPoint[];
}

export async function fetchObservationTypes(): Promise<ObservationType[]> {
  return api<ObservationType[]>("/api/v1/observation-types");
}

export async function listObservations(
  patientId: string,
  params?: { type?: string; from?: string; to?: string },
): Promise<ObservationList> {
  const query = new URLSearchParams();
  if (params?.type) query.set("type", params.type);
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const qs = query.toString();
  return api<ObservationList>(`/api/v1/patients/${patientId}/observations${qs ? `?${qs}` : ""}`);
}

export async function createObservation(patientId: string, data: ObservationFormData): Promise<Observation> {
  return api<Observation>(`/api/v1/patients/${patientId}/observations`, {
    method: "POST", body: JSON.stringify(data),
  });
}

export async function updateObservation(patientId: string, id: string, data: Partial<ObservationFormData>): Promise<Observation> {
  return api<Observation>(`/api/v1/patients/${patientId}/observations/${id}`, {
    method: "PATCH", body: JSON.stringify(data),
  });
}

export async function deleteObservation(patientId: string, id: string): Promise<void> {
  return api<void>(`/api/v1/patients/${patientId}/observations/${id}`, { method: "DELETE" });
}

export async function fetchTrend(
  patientId: string,
  typeKey: string,
  from?: string,
  to?: string,
): Promise<TrendResponse> {
  const query = new URLSearchParams({ type: typeKey });
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  return api<TrendResponse>(`/api/v1/patients/${patientId}/observations/trend?${query}`);
}

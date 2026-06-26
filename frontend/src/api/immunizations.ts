import { api } from "./client";

export interface EPIVaccine {
  id: string;
  name: string;
  short_name: string;
  total_doses: number | null;
  description: string | null;
}

export interface Immunization {
  id: string;
  patient_id: string;
  account_id: string;
  epi_vaccine_id: string | null;
  vaccine_display_name: string;
  code_system: string | null;
  code: string | null;
  dose_number: number | null;
  occurrence_date: string;
  lot_number: string | null;
  manufacturer: string | null;
  site: string | null;
  status: string;
  notes: string | null;
  is_active: boolean;
}

interface ImmunizationList {
  items: Immunization[];
  total: number;
  limit: number;
  offset: number;
}

export interface ImmunizationFormData {
  vaccine_display_name: string;
  epi_vaccine_id?: string;
  dose_number?: number;
  occurrence_date: string;
  lot_number?: string;
  manufacturer?: string;
  site?: string;
  status?: string;
  notes?: string;
}

export async function listImmunizations(
  patientId: string,
): Promise<ImmunizationList> {
  return api<ImmunizationList>(`/api/v1/patients/${patientId}/immunizations`);
}

export async function createImmunization(
  patientId: string,
  data: ImmunizationFormData,
): Promise<Immunization> {
  return api<Immunization>(`/api/v1/patients/${patientId}/immunizations`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateImmunization(
  patientId: string,
  id: string,
  data: Partial<ImmunizationFormData>,
): Promise<Immunization> {
  return api<Immunization>(
    `/api/v1/patients/${patientId}/immunizations/${id}`,
    { method: "PATCH", body: JSON.stringify(data) },
  );
}

export async function deleteImmunization(
  patientId: string,
  id: string,
): Promise<void> {
  return api<void>(`/api/v1/patients/${patientId}/immunizations/${id}`, {
    method: "DELETE",
  });
}

export async function fetchEPIVaccines(): Promise<EPIVaccine[]> {
  return api<EPIVaccine[]>("/api/v1/epi-vaccines");
}

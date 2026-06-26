import { api } from "./client";

export interface Allergy {
  id: string;
  patient_id: string;
  account_id: string;
  code_system: string;
  code: string | null;
  display_name: string;
  category: string;
  criticality: string | null;
  clinical_status: string;
  reaction: string | null;
  severity: string | null;
  onset_date: string | null;
  notes: string | null;
  is_active: boolean;
}

interface AllergyList {
  items: Allergy[];
  total: number;
  limit: number;
  offset: number;
}

export interface AllergyFormData {
  display_name: string;
  category: string;
  criticality?: string;
  clinical_status?: string;
  reaction?: string;
  severity?: string;
  onset_date?: string;
  notes?: string;
  code?: string;
}

export async function listAllergies(patientId: string): Promise<AllergyList> {
  return api<AllergyList>(`/api/v1/patients/${patientId}/allergies`);
}

export async function createAllergy(
  patientId: string,
  data: AllergyFormData,
): Promise<Allergy> {
  return api<Allergy>(`/api/v1/patients/${patientId}/allergies`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAllergy(
  patientId: string,
  id: string,
  data: Partial<AllergyFormData>,
): Promise<Allergy> {
  return api<Allergy>(`/api/v1/patients/${patientId}/allergies/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAllergy(
  patientId: string,
  id: string,
): Promise<void> {
  return api<void>(`/api/v1/patients/${patientId}/allergies/${id}`, {
    method: "DELETE",
  });
}

import { api } from "./client";

export interface Medication {
  id: string;
  patient_id: string;
  account_id: string;
  code_system: string | null;
  code: string | null;
  display_name: string;
  dosage: string | null;
  frequency: string | null;
  route: string | null;
  status: string;
  start_date: string | null;
  end_date: string | null;
  prescribed_by: string | null;
  notes: string | null;
  is_active: boolean;
}

interface MedicationList {
  items: Medication[];
  total: number;
  limit: number;
  offset: number;
}

export interface MedicationFormData {
  display_name: string;
  dosage?: string;
  frequency?: string;
  route?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  prescribed_by?: string;
  notes?: string;
  code?: string;
}

export async function listMedications(
  patientId: string,
): Promise<MedicationList> {
  return api<MedicationList>(`/api/v1/patients/${patientId}/medications`);
}

export async function createMedication(
  patientId: string,
  data: MedicationFormData,
): Promise<Medication> {
  return api<Medication>(`/api/v1/patients/${patientId}/medications`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateMedication(
  patientId: string,
  id: string,
  data: Partial<MedicationFormData>,
): Promise<Medication> {
  return api<Medication>(`/api/v1/patients/${patientId}/medications/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteMedication(
  patientId: string,
  id: string,
): Promise<void> {
  return api<void>(`/api/v1/patients/${patientId}/medications/${id}`, {
    method: "DELETE",
  });
}

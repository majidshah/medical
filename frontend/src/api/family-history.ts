import { api } from "./client";

export interface FamilyHistory {
  id: string;
  patient_id: string;
  account_id: string;
  relationship: string;
  condition_code_system: string;
  condition_code: string | null;
  condition_display_name: string;
  onset_age: number | null;
  deceased: boolean | null;
  notes: string | null;
  is_active: boolean;
}

interface FamilyHistoryList {
  items: FamilyHistory[];
  total: number;
  limit: number;
  offset: number;
}

export interface FamilyHistoryFormData {
  relationship: string;
  condition_display_name: string;
  condition_code?: string;
  condition_code_system?: string;
  onset_age?: number;
  deceased?: boolean;
  notes?: string;
}

export async function listFamilyHistory(patientId: string): Promise<FamilyHistoryList> {
  return api<FamilyHistoryList>(`/api/v1/patients/${patientId}/family-history`);
}

export async function createFamilyHistory(patientId: string, data: FamilyHistoryFormData): Promise<FamilyHistory> {
  return api<FamilyHistory>(`/api/v1/patients/${patientId}/family-history`, {
    method: "POST", body: JSON.stringify(data),
  });
}

export async function updateFamilyHistory(patientId: string, id: string, data: Partial<FamilyHistoryFormData>): Promise<FamilyHistory> {
  return api<FamilyHistory>(`/api/v1/patients/${patientId}/family-history/${id}`, {
    method: "PATCH", body: JSON.stringify(data),
  });
}

export async function deleteFamilyHistory(patientId: string, id: string): Promise<void> {
  return api<void>(`/api/v1/patients/${patientId}/family-history/${id}`, { method: "DELETE" });
}

import { api } from "./client";

export interface Condition {
  id: string;
  patient_id: string;
  account_id: string;
  code_system: string;
  code: string | null;
  display_name: string;
  clinical_status: string;
  onset_date: string | null;
  abatement_date: string | null;
  notes: string | null;
  is_active: boolean;
}

interface ConditionList {
  items: Condition[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConditionFormData {
  display_name: string;
  clinical_status?: string;
  onset_date?: string;
  abatement_date?: string;
  notes?: string;
  code?: string;
  code_system?: string;
}

export async function listConditions(
  patientId: string,
): Promise<ConditionList> {
  return api<ConditionList>(
    `/api/v1/patients/${patientId}/conditions`,
  );
}

export async function createCondition(
  patientId: string,
  data: ConditionFormData,
): Promise<Condition> {
  return api<Condition>(
    `/api/v1/patients/${patientId}/conditions`,
    { method: "POST", body: JSON.stringify(data) },
  );
}

export async function updateCondition(
  patientId: string,
  conditionId: string,
  data: Partial<ConditionFormData>,
): Promise<Condition> {
  return api<Condition>(
    `/api/v1/patients/${patientId}/conditions/${conditionId}`,
    { method: "PATCH", body: JSON.stringify(data) },
  );
}

export async function deleteCondition(
  patientId: string,
  conditionId: string,
): Promise<void> {
  return api<void>(
    `/api/v1/patients/${patientId}/conditions/${conditionId}`,
    { method: "DELETE" },
  );
}

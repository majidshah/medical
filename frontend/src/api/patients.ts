import { api } from "./client";

export interface Patient {
  id: string;
  account_id: string;
  medical_id: string;
  full_name: string;
  date_of_birth: string | null;
  gender: string;
  relationship_to_account: string;
  has_cnic: boolean;
  guardian_patient_id: string | null;
  is_active: boolean;
}

interface PatientList {
  items: Patient[];
  total: number;
  limit: number;
  offset: number;
}

export interface PatientSummary {
  patient: {
    id: string;
    medical_id: string;
    full_name: string;
    date_of_birth: string | null;
    gender: string;
    relationship_to_account: string;
  };
  active_conditions: Array<{
    id: string;
    display_name: string;
    code: string | null;
    clinical_status: string;
    onset_date: string | null;
  }>;
  current_medications: Array<{
    id: string;
    display_name: string;
    dosage: string | null;
    frequency: string | null;
    status: string;
    start_date: string | null;
  }>;
  allergies: Array<{
    id: string;
    display_name: string;
    category: string;
    criticality: string | null;
    severity: string | null;
    reaction: string | null;
  }>;
  recent_results: Array<{
    id: string;
    report_id: string;
    display_name: string;
    value_numeric: number | null;
    value_text: string | null;
    unit: string | null;
    effective_date: string;
    normality_status: string;
  }>;
  counts: {
    conditions: number;
    medications: number;
    allergies: number;
    immunizations: number;
    family_history: number;
    reports: number;
  };
}

export async function fetchPatients(): Promise<PatientList> {
  return api<PatientList>("/api/v1/patients");
}

export async function fetchPatientSummary(
  patientId: string,
): Promise<PatientSummary> {
  return api<PatientSummary>(`/api/v1/patients/${patientId}/summary`);
}

export async function createPatient(data: {
  full_name: string;
  date_of_birth?: string;
  gender: string;
  relationship_to_account: string;
  cnic?: string;
  guardian_patient_id?: string;
}): Promise<Patient> {
  return api<Patient>("/api/v1/patients", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

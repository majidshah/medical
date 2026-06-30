import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import { createPatient, fetchPatients, type Patient } from "@/api/patients";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { PageHeader } from "@/components/ui/page-header";
import { FormRow } from "@/components/ui/form-row";

function AddPatientModal({
  patients,
  open,
  onClose,
}: {
  patients: Patient[];
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const submitRef = useRef<HTMLButtonElement>(null);

  const [fullName, setFullName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [gender, setGender] = useState("male");
  const [relationship, setRelationship] = useState("self");
  const [idType, setIdType] = useState<"cnic" | "dependent">("cnic");
  const [cnic, setCnic] = useState("");
  const [guardianId, setGuardianId] = useState("");
  const [error, setError] = useState("");

  const guardians = patients.filter((p) => p.has_cnic);

  const mutation = useMutation({
    mutationFn: createPatient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      onClose();
    },
    onError: (err: Error) => {
      if (err instanceof ApiError && err.status === 409) {
        setError(t("patients.form.error_duplicate_cnic"));
      } else if (err instanceof ApiError && err.status === 422) {
        setError(err.detail);
      } else {
        setError(t("patients.form.error_generic"));
      }
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");

    const data: Parameters<typeof createPatient>[0] = {
      full_name: fullName,
      gender,
      relationship_to_account: relationship,
      date_of_birth: dateOfBirth || undefined,
    };

    if (idType === "cnic") {
      const digits = cnic.replace(/-/g, "");
      if (!/^\d{13}$/.test(digits)) {
        setError(t("patients.form.error_cnic_format"));
        return;
      }
      data.cnic = cnic;
    } else {
      data.guardian_patient_id = guardianId;
    }

    mutation.mutate(data);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("patients.form.title")}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("patients.form.cancel")}
          </Button>
          <Button onClick={() => submitRef.current?.click()} disabled={mutation.isPending}>
            {mutation.isPending ? t("common.loading") : t("patients.form.submit")}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          label={t("patients.form.full_name")}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />
        <FormRow>
          <Input
            label={t("patients.form.date_of_birth")}
            type="date"
            value={dateOfBirth}
            onChange={(e) => setDateOfBirth(e.target.value)}
          />
          <div>
            <label className="block text-base font-medium text-ink mb-1">
              {t("patients.form.gender")}
            </label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-theme bg-surface text-ink text-base"
            >
              <option value="male">{t("patients.form.gender_male")}</option>
              <option value="female">{t("patients.form.gender_female")}</option>
              <option value="other">{t("patients.form.gender_other")}</option>
            </select>
          </div>
        </FormRow>

        <div>
          <label className="block text-base font-medium text-ink mb-1">
            {t("patients.form.relationship_to_account")}
          </label>
          <select
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
            className="w-full px-3 py-2 border border-border rounded-theme bg-surface text-ink text-base"
          >
            <option value="self">{t("patients.form.rel_self")}</option>
            <option value="child">{t("patients.form.rel_child")}</option>
            <option value="spouse">{t("patients.form.rel_spouse")}</option>
            <option value="parent">{t("patients.form.rel_parent")}</option>
            <option value="other">{t("patients.form.rel_other")}</option>
          </select>
        </div>

        <div>
          <label className="block text-base font-medium text-ink mb-1">
            {t("patients.form.id_type")}
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-base cursor-pointer">
              <input
                type="radio"
                name="idType"
                checked={idType === "cnic"}
                onChange={() => setIdType("cnic")}
                style={{ accentColor: "var(--accent)" }}
              />
              {t("patients.form.id_cnic")}
            </label>
            <label className="flex items-center gap-2 text-base cursor-pointer">
              <input
                type="radio"
                name="idType"
                checked={idType === "dependent"}
                onChange={() => setIdType("dependent")}
                style={{ accentColor: "var(--accent)" }}
              />
              {t("patients.form.id_dependent")}
            </label>
          </div>
        </div>

        {idType === "cnic" ? (
          <Input
            label={t("patients.form.cnic")}
            value={cnic}
            onChange={(e) => setCnic(e.target.value)}
            required
            placeholder="42201-1234567-8"
          />
        ) : (
          <div>
            <label className="block text-base font-medium text-ink mb-1">
              {t("patients.form.guardian")}
            </label>
            {guardians.length === 0 ? (
              <p className="text-base text-muted">
                {t("patients.form.no_guardians")}
              </p>
            ) : (
              <select
                value={guardianId}
                onChange={(e) => setGuardianId(e.target.value)}
                required
                className="w-full px-3 py-2 border border-border rounded-theme bg-surface text-ink text-base"
              >
                <option value="">—</option>
                {guardians.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.full_name} ({g.medical_id})
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {error && (
          <p className="text-base text-status-warning" role="alert">
            {error}
          </p>
        )}

        <button ref={submitRef} type="submit" className="hidden" aria-hidden="true" tabIndex={-1} />
      </form>
    </Modal>
  );
}

export function PatientListPage() {
  const { t } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading, error } = useQuery({
    queryKey: ["patients"],
    queryFn: fetchPatients,
  });

  if (isLoading) {
    return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  }
  if (error) {
    return <p className="text-status-warning text-center py-12">{t("common.error")}</p>;
  }

  const patients = data?.items || [];

  return (
    <div>
      <PageHeader
        title={t("patients.title")}
        actions={
          patients.length > 0 ? (
            <Button onClick={() => setShowForm(true)}>
              {t("patients.add")}
            </Button>
          ) : undefined
        }
      />

      <AddPatientModal
        patients={patients}
        open={showForm}
        onClose={() => setShowForm(false)}
      />

      {patients.length === 0 && !showForm ? (
        <EmptyState
          title={t("patients.empty")}
          action={
            <Button onClick={() => setShowForm(true)}>
              {t("patients.add")}
            </Button>
          }
        />
      ) : (
        <div className="space-y-2">
          {patients.map((p) => (
            <Link key={p.id} to={`/patients/${p.id}`}>
              <Card className="hover:border-accent/40 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-medium text-ink">{p.full_name}</h2>
                    <p className="text-sm text-muted">
                      {t("patients.medical_id")}: {p.medical_id}
                    </p>
                  </div>
                  <span className="text-sm text-muted capitalize">
                    {p.relationship_to_account}
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

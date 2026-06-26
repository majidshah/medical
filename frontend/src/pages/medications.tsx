import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import {
  createMedication,
  deleteMedication,
  listMedications,
  updateMedication,
  type Medication,
  type MedicationFormData,
} from "@/api/medications";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { PatientNav } from "@/components/layout/patient-nav";

const STATUSES = ["active", "completed", "stopped", "on-hold", "unknown"] as const;

function MedicationForm({
  patientId,
  existing,
  onClose,
}: {
  patientId: string;
  existing?: Medication;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(existing?.display_name || "");
  const [dosage, setDosage] = useState(existing?.dosage || "");
  const [frequency, setFrequency] = useState(existing?.frequency || "");
  const [route, setRoute] = useState(existing?.route || "");
  const [status, setStatus] = useState(existing?.status || "active");
  const [startDate, setStartDate] = useState(existing?.start_date || "");
  const [endDate, setEndDate] = useState(existing?.end_date || "");
  const [prescribedBy, setPrescribedBy] = useState(existing?.prescribed_by || "");
  const [notes, setNotes] = useState(existing?.notes || "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: MedicationFormData) =>
      existing ? updateMedication(patientId, existing.id, data) : createMedication(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medications", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patient-summary", patientId] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err instanceof ApiError && err.status === 422 ? err.detail : t("medications.form.error"));
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    mutation.mutate({
      display_name: displayName,
      dosage: dosage || undefined,
      frequency: frequency || undefined,
      route: route || undefined,
      status,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      prescribed_by: prescribedBy || undefined,
      notes: notes || undefined,
    });
  };

  return (
    <Card className="mb-6">
      <h2 className="font-serif text-xl text-ink mb-4">
        {existing ? t("medications.form.edit_title") : t("medications.form.add_title")}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label={t("medications.form.display_name")} value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
        <Input label={t("medications.form.dosage")} value={dosage} onChange={(e) => setDosage(e.target.value)} placeholder="500 mg" />
        <Input label={t("medications.form.frequency")} value={frequency} onChange={(e) => setFrequency(e.target.value)} placeholder={t("medications.form.frequency_placeholder")} />
        <Input label={t("medications.form.route")} value={route} onChange={(e) => setRoute(e.target.value)} placeholder={t("medications.form.route_placeholder")} />
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("medications.form.status")}</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
            {STATUSES.map((s) => <option key={s} value={s}>{t(`medications.status.${s}`)}</option>)}
          </select>
        </div>
        <Input label={t("medications.form.start_date")} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <Input label={t("medications.form.end_date")} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        <Input label={t("medications.form.prescribed_by")} value={prescribedBy} onChange={(e) => setPrescribedBy(e.target.value)} />
        <Input label={t("medications.form.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {error && <p className="text-base text-amber" role="alert">{error}</p>}
        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? t("common.loading") : existing ? t("medications.form.save") : t("medications.form.add")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

export function MedicationsPage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Medication | undefined>();
  const [deleting, setDeleting] = useState<Medication | undefined>();

  const { data, isLoading, error } = useQuery({ queryKey: ["medications", patientId], queryFn: () => listMedications(patientId!), enabled: !!patientId });
  const deleteMutation = useMutation({
    mutationFn: () => deleteMedication(patientId!, deleting!.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["medications", patientId] }); queryClient.invalidateQueries({ queryKey: ["patient-summary", patientId] }); setDeleting(undefined); },
  });

  const handleEdit = (m: Medication) => { setEditing(m); setShowForm(true); };
  const handleCloseForm = () => { setShowForm(false); setEditing(undefined); };

  if (isLoading) return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  if (error) return <p className="text-amber text-center py-12">{t("common.error")}</p>;

  const items = data?.items || [];

  return (
    <div>
      <PatientNav patientId={patientId!} />
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-2xl text-ink">{t("medications.title")}</h1>
        {!showForm && items.length > 0 && <Button onClick={() => setShowForm(true)}>{t("medications.add")}</Button>}
      </div>
      {showForm && <MedicationForm patientId={patientId!} existing={editing} onClose={handleCloseForm} />}
      {items.length === 0 && !showForm ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-4">{t("medications.empty")}</p>
          <Button onClick={() => setShowForm(true)}>{t("medications.add")}</Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((m) => (
            <Card key={m.id}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-medium text-ink">{m.display_name}</h2>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <StatusBadge status={m.status} translationPrefix="medications.status" />
                    {m.dosage && <span className="text-base text-muted">{m.dosage}</span>}
                    {m.frequency && <span className="text-base text-muted">{m.frequency}</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleEdit(m)} className="text-base text-teal hover:underline">{t("common.edit")}</button>
                  <button onClick={() => setDeleting(m)} className="text-base text-amber hover:underline">{t("common.delete")}</button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      {deleting && <ConfirmDialog message={t("medications.confirm_delete", { name: deleting.display_name })} onConfirm={() => deleteMutation.mutate()} onCancel={() => setDeleting(undefined)} loading={deleteMutation.isPending} />}
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import {
  createImmunization,
  deleteImmunization,
  fetchEPIVaccines,
  listImmunizations,
  updateImmunization,
  type Immunization,
  type ImmunizationFormData,
} from "@/api/immunizations";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { PatientNav } from "@/components/layout/patient-nav";

const STATUSES = ["completed", "entered-in-error", "not-done"] as const;

function ImmunizationForm({
  patientId,
  existing,
  onClose,
}: {
  patientId: string;
  existing?: Immunization;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: epiVaccines } = useQuery({ queryKey: ["epi-vaccines"], queryFn: fetchEPIVaccines });

  const [vaccineSource, setVaccineSource] = useState<"epi" | "free">(existing?.epi_vaccine_id ? "epi" : "free");
  const [epiVaccineId, setEpiVaccineId] = useState(existing?.epi_vaccine_id || "");
  const [vaccineName, setVaccineName] = useState(existing?.vaccine_display_name || "");
  const [doseNumber, setDoseNumber] = useState(existing?.dose_number?.toString() || "");
  const [occurrenceDate, setOccurrenceDate] = useState(existing?.occurrence_date || "");
  const [lotNumber, setLotNumber] = useState(existing?.lot_number || "");
  const [manufacturer, setManufacturer] = useState(existing?.manufacturer || "");
  const [site, setSite] = useState(existing?.site || "");
  const [status, setStatus] = useState(existing?.status || "completed");
  const [notes, setNotes] = useState(existing?.notes || "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: ImmunizationFormData) =>
      existing ? updateImmunization(patientId, existing.id, data) : createImmunization(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["immunizations", patientId] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err instanceof ApiError && err.status === 422 ? err.detail : t("immunizations.form.error"));
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    let displayName = vaccineName;
    let epiId: string | undefined;
    if (vaccineSource === "epi" && epiVaccineId) {
      epiId = epiVaccineId;
      const epi = epiVaccines?.find((v) => v.id === epiVaccineId);
      if (epi) displayName = epi.name;
    }
    mutation.mutate({
      vaccine_display_name: displayName,
      epi_vaccine_id: epiId,
      dose_number: doseNumber ? parseInt(doseNumber, 10) : undefined,
      occurrence_date: occurrenceDate,
      lot_number: lotNumber || undefined,
      manufacturer: manufacturer || undefined,
      site: site || undefined,
      status,
      notes: notes || undefined,
    });
  };

  return (
    <Card className="mb-6">
      <h2 className="font-serif text-xl text-ink mb-4">
        {existing ? t("immunizations.form.edit_title") : t("immunizations.form.add_title")}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("immunizations.form.vaccine_source")}</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-base cursor-pointer">
              <input type="radio" name="vaccineSource" checked={vaccineSource === "epi"} onChange={() => setVaccineSource("epi")} className="accent-teal" />
              {t("immunizations.form.epi_vaccine")}
            </label>
            <label className="flex items-center gap-2 text-base cursor-pointer">
              <input type="radio" name="vaccineSource" checked={vaccineSource === "free"} onChange={() => setVaccineSource("free")} className="accent-teal" />
              {t("immunizations.form.free_text")}
            </label>
          </div>
        </div>
        {vaccineSource === "epi" ? (
          <div>
            <label className="block text-base font-medium text-ink mb-1">{t("immunizations.form.epi_select")}</label>
            <select value={epiVaccineId} onChange={(e) => setEpiVaccineId(e.target.value)} required className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
              <option value="">—</option>
              {(epiVaccines || []).map((v) => <option key={v.id} value={v.id}>{v.name} ({v.short_name})</option>)}
            </select>
          </div>
        ) : (
          <Input label={t("immunizations.form.vaccine_name")} value={vaccineName} onChange={(e) => setVaccineName(e.target.value)} required />
        )}
        <Input label={t("immunizations.form.dose_number")} type="number" value={doseNumber} onChange={(e) => setDoseNumber(e.target.value)} />
        <Input label={t("immunizations.form.occurrence_date")} type="date" value={occurrenceDate} onChange={(e) => setOccurrenceDate(e.target.value)} required />
        <Input label={t("immunizations.form.lot_number")} value={lotNumber} onChange={(e) => setLotNumber(e.target.value)} />
        <Input label={t("immunizations.form.manufacturer")} value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} />
        <Input label={t("immunizations.form.site")} value={site} onChange={(e) => setSite(e.target.value)} />
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("immunizations.form.status")}</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
            {STATUSES.map((s) => <option key={s} value={s}>{t(`immunizations.status.${s}`)}</option>)}
          </select>
        </div>
        <Input label={t("immunizations.form.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {error && <p className="text-base text-amber" role="alert">{error}</p>}
        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? t("common.loading") : existing ? t("immunizations.form.save") : t("immunizations.form.add")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

export function ImmunizationsPage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Immunization | undefined>();
  const [deleting, setDeleting] = useState<Immunization | undefined>();

  const { data, isLoading, error } = useQuery({ queryKey: ["immunizations", patientId], queryFn: () => listImmunizations(patientId!), enabled: !!patientId });
  const deleteMutation = useMutation({
    mutationFn: () => deleteImmunization(patientId!, deleting!.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["immunizations", patientId] }); setDeleting(undefined); },
  });

  const handleEdit = (i: Immunization) => { setEditing(i); setShowForm(true); };
  const handleCloseForm = () => { setShowForm(false); setEditing(undefined); };

  if (isLoading) return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  if (error) return <p className="text-amber text-center py-12">{t("common.error")}</p>;

  const items = data?.items || [];

  return (
    <div>
      <PatientNav patientId={patientId!} />
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-2xl text-ink">{t("immunizations.title")}</h1>
        {!showForm && items.length > 0 && <Button onClick={() => setShowForm(true)}>{t("immunizations.add")}</Button>}
      </div>
      {showForm && <ImmunizationForm patientId={patientId!} existing={editing} onClose={handleCloseForm} />}
      {items.length === 0 && !showForm ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-4">{t("immunizations.empty")}</p>
          <Button onClick={() => setShowForm(true)}>{t("immunizations.add")}</Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((i) => (
            <Card key={i.id}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-medium text-ink">{i.vaccine_display_name}</h2>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <StatusBadge status={i.status} translationPrefix="immunizations.status" />
                    <span className="text-base text-muted">{i.occurrence_date}</span>
                    {i.dose_number && <span className="text-base text-muted">{t("immunizations.dose")} {i.dose_number}</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleEdit(i)} className="text-base text-teal hover:underline">{t("common.edit")}</button>
                  <button onClick={() => setDeleting(i)} className="text-base text-amber hover:underline">{t("common.delete")}</button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      {deleting && <ConfirmDialog message={t("immunizations.confirm_delete", { name: deleting.vaccine_display_name })} onConfirm={() => deleteMutation.mutate()} onCancel={() => setDeleting(undefined)} loading={deleteMutation.isPending} />}
    </div>
  );
}

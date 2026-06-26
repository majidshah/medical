import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import {
  createAllergy,
  deleteAllergy,
  listAllergies,
  updateAllergy,
  type Allergy,
  type AllergyFormData,
} from "@/api/allergies";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { PatientNav } from "@/components/layout/patient-nav";

const CATEGORIES = ["food", "medication", "environment", "biologic"] as const;
const CRITICALITIES = ["low", "high", "unable-to-assess"] as const;
const SEVERITIES = ["mild", "moderate", "severe"] as const;
const STATUSES = ["active", "inactive", "resolved"] as const;

function AllergyForm({
  patientId,
  existing,
  onClose,
}: {
  patientId: string;
  existing?: Allergy;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(existing?.display_name || "");
  const [category, setCategory] = useState(existing?.category || "food");
  const [criticality, setCriticality] = useState(existing?.criticality || "");
  const [clinicalStatus, setClinicalStatus] = useState(existing?.clinical_status || "active");
  const [reaction, setReaction] = useState(existing?.reaction || "");
  const [severity, setSeverity] = useState(existing?.severity || "");
  const [onsetDate, setOnsetDate] = useState(existing?.onset_date || "");
  const [notes, setNotes] = useState(existing?.notes || "");
  const [code, setCode] = useState(existing?.code || "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: AllergyFormData) =>
      existing ? updateAllergy(patientId, existing.id, data) : createAllergy(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["allergies", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patient-summary", patientId] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err instanceof ApiError && err.status === 422 ? err.detail : t("allergies.form.error"));
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    mutation.mutate({
      display_name: displayName,
      category,
      criticality: criticality || undefined,
      clinical_status: clinicalStatus,
      reaction: reaction || undefined,
      severity: severity || undefined,
      onset_date: onsetDate || undefined,
      notes: notes || undefined,
      code: code || undefined,
    });
  };

  return (
    <Card className="mb-6">
      <h2 className="font-serif text-xl text-ink mb-4">
        {existing ? t("allergies.form.edit_title") : t("allergies.form.add_title")}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label={t("allergies.form.display_name")} value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("allergies.form.category")}</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
            {CATEGORIES.map((c) => <option key={c} value={c}>{t(`allergies.category.${c}`)}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("allergies.form.criticality")}</label>
          <select value={criticality} onChange={(e) => setCriticality(e.target.value)} className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
            <option value="">{t("allergies.form.none")}</option>
            {CRITICALITIES.map((c) => <option key={c} value={c}>{t(`allergies.criticality.${c}`)}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("allergies.form.clinical_status")}</label>
          <select value={clinicalStatus} onChange={(e) => setClinicalStatus(e.target.value)} className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
            {STATUSES.map((s) => <option key={s} value={s}>{t(`allergies.status.${s}`)}</option>)}
          </select>
        </div>
        <Input label={t("allergies.form.reaction")} value={reaction} onChange={(e) => setReaction(e.target.value)} />
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("allergies.form.severity")}</label>
          <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base">
            <option value="">{t("allergies.form.none")}</option>
            {SEVERITIES.map((s) => <option key={s} value={s}>{t(`allergies.severity.${s}`)}</option>)}
          </select>
        </div>
        <Input label={t("allergies.form.onset_date")} type="date" value={onsetDate} onChange={(e) => setOnsetDate(e.target.value)} />
        <Input label={t("allergies.form.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        <Input label={t("allergies.form.code")} value={code} onChange={(e) => setCode(e.target.value)} placeholder={t("conditions.form.code_placeholder")} />
        {error && <p className="text-base text-amber" role="alert">{error}</p>}
        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? t("common.loading") : existing ? t("allergies.form.save") : t("allergies.form.add")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

export function AllergiesPage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Allergy | undefined>();
  const [deleting, setDeleting] = useState<Allergy | undefined>();

  const { data, isLoading, error } = useQuery({ queryKey: ["allergies", patientId], queryFn: () => listAllergies(patientId!), enabled: !!patientId });
  const deleteMutation = useMutation({
    mutationFn: () => deleteAllergy(patientId!, deleting!.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["allergies", patientId] }); queryClient.invalidateQueries({ queryKey: ["patient-summary", patientId] }); setDeleting(undefined); },
  });

  const handleEdit = (a: Allergy) => { setEditing(a); setShowForm(true); };
  const handleCloseForm = () => { setShowForm(false); setEditing(undefined); };

  if (isLoading) return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  if (error) return <p className="text-amber text-center py-12">{t("common.error")}</p>;

  const items = data?.items || [];

  return (
    <div>
      <PatientNav patientId={patientId!} />
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-2xl text-ink">{t("allergies.title")}</h1>
        {!showForm && items.length > 0 && <Button onClick={() => setShowForm(true)}>{t("allergies.add")}</Button>}
      </div>
      {showForm && <AllergyForm patientId={patientId!} existing={editing} onClose={handleCloseForm} />}
      {items.length === 0 && !showForm ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-4">{t("allergies.empty")}</p>
          <Button onClick={() => setShowForm(true)}>{t("allergies.add")}</Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((a) => (
            <Card key={a.id} className="border-amber/30">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-medium text-ink">{a.display_name}</h2>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <StatusBadge status={a.clinical_status} translationPrefix="allergies.status" />
                    <span className="text-base text-muted capitalize">{t(`allergies.category.${a.category}`)}</span>
                    {a.criticality && <span className="text-base text-amber font-medium">{t(`allergies.criticality.${a.criticality}`)}</span>}
                    {a.severity && <span className="text-base text-muted">{t(`allergies.severity.${a.severity}`)}</span>}
                  </div>
                  {a.reaction && <p className="text-base text-muted mt-1">{a.reaction}</p>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleEdit(a)} className="text-base text-teal hover:underline">{t("common.edit")}</button>
                  <button onClick={() => setDeleting(a)} className="text-base text-amber hover:underline">{t("common.delete")}</button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      {deleting && <ConfirmDialog message={t("allergies.confirm_delete", { name: deleting.display_name })} onConfirm={() => deleteMutation.mutate()} onCancel={() => setDeleting(undefined)} loading={deleteMutation.isPending} />}
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import {
  createCondition,
  deleteCondition,
  listConditions,
  updateCondition,
  type Condition,
  type ConditionFormData,
} from "@/api/conditions";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const CLINICAL_STATUSES = [
  "active",
  "recurrence",
  "relapse",
  "inactive",
  "remission",
  "resolved",
] as const;

function ConditionForm({
  patientId,
  existing,
  onClose,
}: {
  patientId: string;
  existing?: Condition;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState(existing?.display_name || "");
  const [clinicalStatus, setClinicalStatus] = useState(
    existing?.clinical_status || "active",
  );
  const [onsetDate, setOnsetDate] = useState(existing?.onset_date || "");
  const [abatementDate, setAbatementDate] = useState(
    existing?.abatement_date || "",
  );
  const [notes, setNotes] = useState(existing?.notes || "");
  const [code, setCode] = useState(existing?.code || "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: ConditionFormData) =>
      existing
        ? updateCondition(patientId, existing.id, data)
        : createCondition(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["conditions", patientId],
      });
      queryClient.invalidateQueries({
        queryKey: ["patient-summary", patientId],
      });
      onClose();
    },
    onError: (err: Error) => {
      if (err instanceof ApiError && err.status === 422) {
        setError(err.detail);
      } else {
        setError(t("conditions.form.error"));
      }
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const data: ConditionFormData = {
      display_name: displayName,
      clinical_status: clinicalStatus,
      onset_date: onsetDate || undefined,
      abatement_date: abatementDate || undefined,
      notes: notes || undefined,
      code: code || undefined,
    };
    mutation.mutate(data);
  };

  return (
    <Card className="mb-6">
      <h2 className="font-serif text-xl text-ink mb-4">
        {existing
          ? t("conditions.form.edit_title")
          : t("conditions.form.add_title")}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label={t("conditions.form.display_name")}
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
        />

        <div>
          <label className="block text-base font-medium text-ink mb-1">
            {t("conditions.form.clinical_status")}
          </label>
          <select
            value={clinicalStatus}
            onChange={(e) => setClinicalStatus(e.target.value)}
            className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base"
          >
            {CLINICAL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`conditions.status.${s}`)}
              </option>
            ))}
          </select>
        </div>

        <Input
          label={t("conditions.form.onset_date")}
          type="date"
          value={onsetDate}
          onChange={(e) => setOnsetDate(e.target.value)}
        />

        <Input
          label={t("conditions.form.abatement_date")}
          type="date"
          value={abatementDate}
          onChange={(e) => setAbatementDate(e.target.value)}
        />

        <Input
          label={t("conditions.form.notes")}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />

        <Input
          label={t("conditions.form.code")}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder={t("conditions.form.code_placeholder")}
        />

        {error && (
          <p className="text-base text-amber" role="alert">
            {error}
          </p>
        )}

        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? t("common.loading")
              : existing
                ? t("conditions.form.save")
                : t("conditions.form.add")}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function ConditionsPage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Condition | undefined>();
  const [deleting, setDeleting] = useState<Condition | undefined>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["conditions", patientId],
    queryFn: () => listConditions(patientId!),
    enabled: !!patientId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCondition(patientId!, deleting!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["conditions", patientId],
      });
      queryClient.invalidateQueries({
        queryKey: ["patient-summary", patientId],
      });
      setDeleting(undefined);
    },
  });

  const handleEdit = (c: Condition) => {
    setEditing(c);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditing(undefined);
  };

  if (isLoading) {
    return (
      <p className="text-muted text-center py-12">{t("common.loading")}</p>
    );
  }
  if (error) {
    return (
      <p className="text-amber text-center py-12">{t("common.error")}</p>
    );
  }

  const conditions = data?.items || [];

  return (
    <div>
      <div className="mb-2">
        <Link
          to={`/patients/${patientId}`}
          className="text-base text-teal hover:underline"
        >
          &larr; {t("conditions.back_to_summary")}
        </Link>
      </div>

      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-2xl text-ink">
          {t("conditions.title")}
        </h1>
        {!showForm && conditions.length > 0 && (
          <Button onClick={() => setShowForm(true)}>
            {t("conditions.add")}
          </Button>
        )}
      </div>

      {showForm && (
        <ConditionForm
          patientId={patientId!}
          existing={editing}
          onClose={handleCloseForm}
        />
      )}

      {conditions.length === 0 && !showForm ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-4">{t("conditions.empty")}</p>
          <Button onClick={() => setShowForm(true)}>
            {t("conditions.add")}
          </Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {conditions.map((c) => (
            <Card key={c.id}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-medium text-ink">
                    {c.display_name}
                  </h2>
                  <div className="flex items-center gap-3 mt-1">
                    <StatusBadge
                      status={c.clinical_status}
                      translationPrefix="conditions.status"
                    />
                    {c.onset_date && (
                      <span className="text-base text-muted">
                        {t("conditions.onset")}: {c.onset_date}
                      </span>
                    )}
                  </div>
                  {c.notes && (
                    <p className="text-base text-muted mt-1">{c.notes}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleEdit(c)}
                    className="text-base text-teal hover:underline"
                  >
                    {t("common.edit")}
                  </button>
                  <button
                    onClick={() => setDeleting(c)}
                    className="text-base text-amber hover:underline"
                  >
                    {t("common.delete")}
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {deleting && (
        <ConfirmDialog
          message={t("conditions.confirm_delete", {
            name: deleting.display_name,
          })}
          onConfirm={() => deleteMutation.mutate()}
          onCancel={() => setDeleting(undefined)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import {
  createObservation,
  deleteObservation,
  fetchObservationTypes,
  fetchTrend,
  listObservations,
  updateObservation,
  type Observation,
  type ObservationFormData,
  type ObservationType,
} from "@/api/observations";
import { TrendChart } from "@/components/clinical/trend-chart";
import { PatientNav } from "@/components/layout/patient-nav";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";

const CODED_OPTIONS: Record<string, string[]> = {
  smoking_status: ["current", "former", "never"],
  alcohol_use: ["current", "former", "never", "occasional"],
};

function ObservationForm({
  patientId,
  types,
  existing,
  onClose,
}: {
  patientId: string;
  types: ObservationType[];
  existing?: Observation;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [typeId, setTypeId] = useState(existing?.observation_type_id || (types[0]?.id ?? ""));
  const [effectiveDate, setEffectiveDate] = useState(existing?.effective_date || "");
  const [valueNumeric, setValueNumeric] = useState(existing?.value_numeric?.toString() || "");
  const [valueCode, setValueCode] = useState(existing?.value_code || "");
  const [valueText, setValueText] = useState(existing?.value_text || "");
  const [unit, setUnit] = useState(existing?.unit || "");
  const [notes, setNotes] = useState(existing?.notes || "");
  const [error, setError] = useState("");

  const selectedType = types.find((t) => t.id === typeId);
  const vt = selectedType?.value_type || "text";

  const mutation = useMutation({
    mutationFn: (data: ObservationFormData) =>
      existing
        ? updateObservation(patientId, existing.id, data)
        : createObservation(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["observations", patientId] });
      queryClient.invalidateQueries({ queryKey: ["trend", patientId] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err instanceof ApiError && err.status === 422 ? err.detail : t("lifestyle.form.error"));
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const data: ObservationFormData = {
      observation_type_id: typeId,
      effective_date: effectiveDate,
      unit: unit || selectedType?.unit || undefined,
      notes: notes || undefined,
    };
    if (vt === "numeric") {
      data.value_numeric = parseFloat(valueNumeric);
    } else if (vt === "coded") {
      data.value_code = valueCode;
    } else {
      data.value_text = valueText;
    }
    mutation.mutate(data);
  };

  return (
    <Card className="mb-6">
      <h2 className="text-lg text-ink font-medium mb-4">
        {existing ? t("lifestyle.form.edit_title") : t("lifestyle.form.add_title")}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {!existing && (
          <div>
            <label className="block text-base text-secondary mb-1">
              {t("lifestyle.form.type")}
            </label>
            <select
              value={typeId}
              onChange={(e) => setTypeId(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
            >
              {types.map((tp) => (
                <option key={tp.id} value={tp.id}>
                  {tp.display_label}
                </option>
              ))}
            </select>
          </div>
        )}
        <Input
          label={t("lifestyle.form.date")}
          type="date"
          value={effectiveDate}
          onChange={(e) => setEffectiveDate(e.target.value)}
          required
        />
        {vt === "numeric" && (
          <Input
            label={t("lifestyle.form.value_numeric")}
            type="number"
            step="any"
            value={valueNumeric}
            onChange={(e) => setValueNumeric(e.target.value)}
            required
          />
        )}
        {vt === "coded" && (
          <div>
            <label className="block text-base text-secondary mb-1">
              {t("lifestyle.form.value_coded")}
            </label>
            <select
              value={valueCode}
              onChange={(e) => setValueCode(e.target.value)}
              required
              className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
            >
              <option value="">—</option>
              {(CODED_OPTIONS[selectedType?.key || ""] || ["current", "former", "never"]).map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>
        )}
        {vt === "text" && (
          <Input
            label={t("lifestyle.form.value_text")}
            value={valueText}
            onChange={(e) => setValueText(e.target.value)}
            required
          />
        )}
        {vt === "numeric" && (
          <Input
            label={t("lifestyle.form.unit")}
            value={unit || selectedType?.unit || ""}
            onChange={(e) => setUnit(e.target.value)}
          />
        )}
        <Input
          label={t("lifestyle.form.notes")}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        {error && <p className="text-base text-status-warning" role="alert">{error}</p>}
        <div className="flex gap-3 justify-end pt-3">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("common.loading") : existing ? t("lifestyle.form.save") : t("lifestyle.form.add")}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function LifestylePage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Observation | undefined>();
  const [deleting, setDeleting] = useState<Observation | undefined>();
  const [filterType, setFilterType] = useState("");
  const [showTrend, setShowTrend] = useState(false);

  const { data: types } = useQuery({
    queryKey: ["observation-types"],
    queryFn: fetchObservationTypes,
  });

  const { data: obsData, isLoading } = useQuery({
    queryKey: ["observations", patientId, filterType],
    queryFn: () => listObservations(patientId!, { type: filterType || undefined }),
    enabled: !!patientId,
  });

  const selectedType = types?.find((tp) => tp.key === filterType);

  const { data: trendData } = useQuery({
    queryKey: ["trend", patientId, filterType],
    queryFn: () => fetchTrend(patientId!, filterType),
    enabled: !!patientId && !!filterType && showTrend,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteObservation(patientId!, deleting!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["observations", patientId] });
      queryClient.invalidateQueries({ queryKey: ["trend", patientId] });
      setDeleting(undefined);
    },
  });

  const handleCloseForm = () => { setShowForm(false); setEditing(undefined); };

  const items = obsData?.items || [];
  const typesList = types || [];

  const getTypeName = (typeId: string) => {
    const tp = typesList.find((t) => t.id === typeId);
    return tp?.display_label || "";
  };

  const getValue = (o: Observation) => {
    if (o.value_numeric != null) return `${o.value_numeric}${o.unit ? ` ${o.unit}` : ""}`;
    if (o.value_code) return o.value_code;
    return o.value_text || "—";
  };

  if (isLoading) return <p className="text-muted text-center py-12">{t("common.loading")}</p>;

  return (
    <div>
      <PatientNav patientId={patientId!} />
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg text-ink font-medium font-medium">{t("lifestyle.title")}</h1>
        <Button onClick={() => { setEditing(undefined); setShowForm(true); }}>
          {t("lifestyle.add")}
        </Button>
      </div>

      {showForm && (
        <ObservationForm
          patientId={patientId!}
          types={typesList}
          existing={editing}
          onClose={handleCloseForm}
        />
      )}

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setShowTrend(false); }}
          className="px-3 py-2 border border-border rounded bg-surface text-ink text-base"
        >
          <option value="">{t("lifestyle.all_types")}</option>
          {typesList.map((tp) => (
            <option key={tp.key} value={tp.key}>{tp.display_label}</option>
          ))}
        </select>
        {filterType && (
          <Button
            variant="secondary"
            onClick={() => setShowTrend(!showTrend)}
          >
            {showTrend ? t("lifestyle.hide_trend") : t("lifestyle.show_trend")}
          </Button>
        )}
      </div>

      {showTrend && filterType && trendData && (
        <div className="mb-6">
          <TrendChart
            title={selectedType?.display_label || filterType}
            points={trendData.points}
            chartable={trendData.chartable}
            unit={selectedType?.unit}
          />
        </div>
      )}

      {items.length === 0 && !showForm ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-4">{t("lifestyle.empty")}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((o) => (
            <Card key={o.id}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-medium text-ink">{getTypeName(o.observation_type_id)}</h2>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-base font-sans tabular-nums">{getValue(o)}</span>
                    <span className="text-base text-muted">{o.effective_date}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setEditing(o); setShowForm(true); }} className="text-base text-accent hover:underline">{t("common.edit")}</button>
                  <button onClick={() => setDeleting(o)} className="text-base text-status-warning hover:underline">{t("common.delete")}</button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {deleting && (
        <ConfirmDialog
          message={t("lifestyle.confirm_delete")}
          onConfirm={() => deleteMutation.mutate()}
          onCancel={() => setDeleting(undefined)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}

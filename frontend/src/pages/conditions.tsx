import { useTranslation } from "react-i18next";

import {
  createCondition,
  deleteCondition,
  listConditions,
  updateCondition,
  type Condition,
  type ConditionFormData,
} from "@/api/conditions";
import { ResourcePage } from "@/components/clinical/resource-page";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const CLINICAL_STATUSES = [
  "active", "recurrence", "relapse", "inactive", "remission", "resolved",
] as const;

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="block text-base text-secondary mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export function ConditionsPage() {
  const { t } = useTranslation();

  return (
    <ResourcePage<Condition, ConditionFormData>
      config={{
        resourceKey: "conditions",
        i18nPrefix: "conditions",
        api: {
          list: listConditions,
          create: (pid, data) => createCondition(pid, data),
          update: (pid, id, data) => updateCondition(pid, id, data),
          delete: deleteCondition,
        },
        getId: (c) => c.id,
        getName: (c) => c.display_name,
        getInitialValues: (existing) => ({
          display_name: existing?.display_name || "",
          clinical_status: existing?.clinical_status || "active",
          onset_date: existing?.onset_date || "",
          abatement_date: existing?.abatement_date || "",
          notes: existing?.notes || "",
          code: existing?.code || "",
        }),
        buildFormData: (v) => ({
          display_name: v.display_name as string,
          clinical_status: v.clinical_status as string,
          onset_date: (v.onset_date as string) || undefined,
          abatement_date: (v.abatement_date as string) || undefined,
          notes: (v.notes as string) || undefined,
          code: (v.code as string) || undefined,
        }),
        renderItem: (c) => (
          <div>
            <h2 className="text-base font-medium text-ink">{c.display_name}</h2>
            <div className="flex items-center gap-3 mt-1">
              <StatusBadge status={c.clinical_status} translationPrefix="conditions.status" />
              {c.onset_date && (
                <span className="text-base text-muted">
                  {t("conditions.onset")}: {c.onset_date}
                </span>
              )}
            </div>
            {c.notes && <p className="text-base text-muted mt-1">{c.notes}</p>}
          </div>
        ),
        renderFormFields: (values, onChange, t) => (
          <>
            <Input
              label={t("conditions.form.display_name")}
              value={(values.display_name as string) || ""}
              onChange={(e) => onChange("display_name", e.target.value)}
              required
            />
            <SelectField
              label={t("conditions.form.clinical_status")}
              value={(values.clinical_status as string) || "active"}
              onChange={(v) => onChange("clinical_status", v)}
              options={CLINICAL_STATUSES.map((s) => ({ value: s, label: t(`conditions.status.${s}`) }))}
            />
            <Input
              label={t("conditions.form.onset_date")}
              type="date"
              value={(values.onset_date as string) || ""}
              onChange={(e) => onChange("onset_date", e.target.value)}
            />
            <Input
              label={t("conditions.form.abatement_date")}
              type="date"
              value={(values.abatement_date as string) || ""}
              onChange={(e) => onChange("abatement_date", e.target.value)}
            />
            <Input
              label={t("conditions.form.notes")}
              value={(values.notes as string) || ""}
              onChange={(e) => onChange("notes", e.target.value)}
            />
            <Input
              label={t("conditions.form.code")}
              value={(values.code as string) || ""}
              onChange={(e) => onChange("code", e.target.value)}
              placeholder={t("conditions.form.code_placeholder")}
            />
          </>
        ),
      }}
    />
  );
}

import { useTranslation } from "react-i18next";

import {
  createAllergy,
  deleteAllergy,
  listAllergies,
  updateAllergy,
  type Allergy,
  type AllergyFormData,
} from "@/api/allergies";
import { ResourcePage } from "@/components/clinical/resource-page";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const CATEGORIES = ["food", "medication", "environment", "biologic"] as const;
const CRITICALITIES = ["low", "high", "unable-to-assess"] as const;
const SEVERITIES = ["mild", "moderate", "severe"] as const;
const STATUSES = ["active", "inactive", "resolved"] as const;

function Select({
  label,
  value,
  onChange,
  options,
  allowEmpty,
  emptyLabel,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  allowEmpty?: boolean;
  emptyLabel?: string;
}) {
  return (
    <div>
      <label className="block text-base font-medium text-ink mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
      >
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export function AllergiesPage() {
  const { t } = useTranslation();

  return (
    <ResourcePage<Allergy, AllergyFormData>
      config={{
        resourceKey: "allergies",
        i18nPrefix: "allergies",
        cardClassName: "border-status-warning/30",
        api: {
          list: listAllergies,
          create: (pid, data) => createAllergy(pid, data),
          update: (pid, id, data) => updateAllergy(pid, id, data),
          delete: deleteAllergy,
        },
        getId: (a) => a.id,
        getName: (a) => a.display_name,
        getInitialValues: (existing) => ({
          display_name: existing?.display_name || "",
          category: existing?.category || "food",
          criticality: existing?.criticality || "",
          clinical_status: existing?.clinical_status || "active",
          reaction: existing?.reaction || "",
          severity: existing?.severity || "",
          onset_date: existing?.onset_date || "",
          notes: existing?.notes || "",
          code: existing?.code || "",
        }),
        buildFormData: (v) => ({
          display_name: v.display_name as string,
          category: v.category as string,
          criticality: (v.criticality as string) || undefined,
          clinical_status: v.clinical_status as string,
          reaction: (v.reaction as string) || undefined,
          severity: (v.severity as string) || undefined,
          onset_date: (v.onset_date as string) || undefined,
          notes: (v.notes as string) || undefined,
          code: (v.code as string) || undefined,
        }),
        renderItem: (a) => (
          <div>
            <h2 className="text-base font-medium text-ink">{a.display_name}</h2>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <StatusBadge status={a.clinical_status} translationPrefix="allergies.status" />
              <span className="text-base text-muted capitalize">{t(`allergies.category.${a.category}`)}</span>
              {a.criticality && <span className="text-base text-status-warning font-medium">{t(`allergies.criticality.${a.criticality}`)}</span>}
              {a.severity && <span className="text-base text-muted">{t(`allergies.severity.${a.severity}`)}</span>}
            </div>
            {a.reaction && <p className="text-base text-muted mt-1">{a.reaction}</p>}
          </div>
        ),
        renderFormFields: (values, onChange, t) => (
          <>
            <Input label={t("allergies.form.display_name")} value={(values.display_name as string) || ""} onChange={(e) => onChange("display_name", e.target.value)} required />
            <Select label={t("allergies.form.category")} value={(values.category as string) || "food"} onChange={(v) => onChange("category", v)} options={CATEGORIES.map((c) => ({ value: c, label: t(`allergies.category.${c}`) }))} />
            <Select label={t("allergies.form.criticality")} value={(values.criticality as string) || ""} onChange={(v) => onChange("criticality", v)} options={CRITICALITIES.map((c) => ({ value: c, label: t(`allergies.criticality.${c}`) }))} allowEmpty emptyLabel={t("allergies.form.none")} />
            <Select label={t("allergies.form.clinical_status")} value={(values.clinical_status as string) || "active"} onChange={(v) => onChange("clinical_status", v)} options={STATUSES.map((s) => ({ value: s, label: t(`allergies.status.${s}`) }))} />
            <Input label={t("allergies.form.reaction")} value={(values.reaction as string) || ""} onChange={(e) => onChange("reaction", e.target.value)} />
            <Select label={t("allergies.form.severity")} value={(values.severity as string) || ""} onChange={(v) => onChange("severity", v)} options={SEVERITIES.map((s) => ({ value: s, label: t(`allergies.severity.${s}`) }))} allowEmpty emptyLabel={t("allergies.form.none")} />
            <Input label={t("allergies.form.onset_date")} type="date" value={(values.onset_date as string) || ""} onChange={(e) => onChange("onset_date", e.target.value)} />
            <Input label={t("allergies.form.notes")} value={(values.notes as string) || ""} onChange={(e) => onChange("notes", e.target.value)} />
            <Input label={t("allergies.form.code")} value={(values.code as string) || ""} onChange={(e) => onChange("code", e.target.value)} placeholder={t("conditions.form.code_placeholder")} />
          </>
        ),
      }}
    />
  );
}

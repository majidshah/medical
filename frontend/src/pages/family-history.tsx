import { useTranslation } from "react-i18next";

import {
  createFamilyHistory,
  deleteFamilyHistory,
  listFamilyHistory,
  updateFamilyHistory,
  type FamilyHistory,
  type FamilyHistoryFormData,
} from "@/api/family-history";
import { ResourcePage } from "@/components/clinical/resource-page";
import { Input } from "@/components/ui/input";

const RELATIONSHIPS = [
  "mother", "father", "brother", "sister",
  "grandfather-paternal", "grandmother-paternal",
  "grandfather-maternal", "grandmother-maternal",
  "son", "daughter", "other",
] as const;

export function FamilyHistoryPage() {
  const { t } = useTranslation();

  return (
    <ResourcePage<FamilyHistory, FamilyHistoryFormData>
      config={{
        resourceKey: "family-history",
        i18nPrefix: "family_history",
        api: {
          list: listFamilyHistory,
          create: (pid, data) => createFamilyHistory(pid, data),
          update: (pid, id, data) => updateFamilyHistory(pid, id, data),
          delete: deleteFamilyHistory,
        },
        getId: (fh) => fh.id,
        getName: (fh) => fh.condition_display_name,
        getInitialValues: (existing) => ({
          relationship: existing?.relationship || "mother",
          condition_display_name: existing?.condition_display_name || "",
          condition_code: existing?.condition_code || "",
          onset_age: existing?.onset_age != null ? String(existing.onset_age) : "",
          deceased: existing?.deceased ?? false,
          notes: existing?.notes || "",
        }),
        buildFormData: (v) => ({
          relationship: v.relationship as string,
          condition_display_name: v.condition_display_name as string,
          condition_code: (v.condition_code as string) || undefined,
          onset_age: v.onset_age ? parseInt(v.onset_age as string, 10) : undefined,
          deceased: v.deceased as boolean || undefined,
          notes: (v.notes as string) || undefined,
        }),
        renderItem: (fh) => (
          <div>
            <h2 className="text-base font-medium text-ink">{fh.condition_display_name}</h2>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <span className="text-base text-muted capitalize">
                {t(`family_history.relationship.${fh.relationship}`)}
              </span>
              {fh.onset_age != null && (
                <span className="text-base text-muted">
                  {t("family_history.onset_age")}: {fh.onset_age}
                </span>
              )}
              {fh.deceased && (
                <span className="text-base text-status-warning font-medium">
                  {t("family_history.deceased_label")}
                </span>
              )}
            </div>
          </div>
        ),
        renderFormFields: (values, onChange, t) => (
          <>
            <div>
              <label className="block text-base text-secondary mb-1">
                {t("family_history.form.relationship")}
              </label>
              <select
                value={(values.relationship as string) || "mother"}
                onChange={(e) => onChange("relationship", e.target.value)}
                className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
              >
                {RELATIONSHIPS.map((r) => (
                  <option key={r} value={r}>{t(`family_history.relationship.${r}`)}</option>
                ))}
              </select>
            </div>
            <Input
              label={t("family_history.form.condition")}
              value={(values.condition_display_name as string) || ""}
              onChange={(e) => onChange("condition_display_name", e.target.value)}
              required
            />
            <Input
              label={t("family_history.form.code")}
              value={(values.condition_code as string) || ""}
              onChange={(e) => onChange("condition_code", e.target.value)}
              placeholder={t("conditions.form.code_placeholder")}
            />
            <Input
              label={t("family_history.form.onset_age")}
              type="number"
              value={String(values.onset_age ?? "")}
              onChange={(e) => onChange("onset_age", e.target.value)}
            />
            <div>
              <label className="flex items-center gap-2 text-base cursor-pointer">
                <input
                  type="checkbox"
                  checked={(values.deceased as boolean) || false}
                  onChange={(e) => onChange("deceased", e.target.checked)}
                  style={{ accentColor: "var(--accent)" }}
                />
                {t("family_history.form.deceased")}
              </label>
            </div>
            <Input
              label={t("family_history.form.notes")}
              value={(values.notes as string) || ""}
              onChange={(e) => onChange("notes", e.target.value)}
            />
          </>
        ),
      }}
    />
  );
}

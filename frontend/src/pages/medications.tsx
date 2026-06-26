import {
  createMedication,
  deleteMedication,
  listMedications,
  updateMedication,
  type Medication,
  type MedicationFormData,
} from "@/api/medications";
import { ResourcePage } from "@/components/clinical/resource-page";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const STATUSES = ["active", "completed", "stopped", "on-hold", "unknown"] as const;

export function MedicationsPage() {
  return (
    <ResourcePage<Medication, MedicationFormData>
      config={{
        resourceKey: "medications",
        i18nPrefix: "medications",
        api: {
          list: listMedications,
          create: (pid, data) => createMedication(pid, data),
          update: (pid, id, data) => updateMedication(pid, id, data),
          delete: deleteMedication,
        },
        getId: (m) => m.id,
        getName: (m) => m.display_name,
        getInitialValues: (existing) => ({
          display_name: existing?.display_name || "",
          dosage: existing?.dosage || "",
          frequency: existing?.frequency || "",
          route: existing?.route || "",
          status: existing?.status || "active",
          start_date: existing?.start_date || "",
          end_date: existing?.end_date || "",
          prescribed_by: existing?.prescribed_by || "",
          notes: existing?.notes || "",
        }),
        buildFormData: (v) => ({
          display_name: v.display_name as string,
          dosage: (v.dosage as string) || undefined,
          frequency: (v.frequency as string) || undefined,
          route: (v.route as string) || undefined,
          status: v.status as string,
          start_date: (v.start_date as string) || undefined,
          end_date: (v.end_date as string) || undefined,
          prescribed_by: (v.prescribed_by as string) || undefined,
          notes: (v.notes as string) || undefined,
        }),
        renderItem: (m) => (
          <div>
            <h2 className="text-base font-medium text-ink">{m.display_name}</h2>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <StatusBadge status={m.status} translationPrefix="medications.status" />
              {m.dosage && <span className="text-base text-muted">{m.dosage}</span>}
              {m.frequency && <span className="text-base text-muted">{m.frequency}</span>}
            </div>
          </div>
        ),
        renderFormFields: (values, onChange, t) => (
          <>
            <Input label={t("medications.form.display_name")} value={(values.display_name as string) || ""} onChange={(e) => onChange("display_name", e.target.value)} required />
            <Input label={t("medications.form.dosage")} value={(values.dosage as string) || ""} onChange={(e) => onChange("dosage", e.target.value)} placeholder="500 mg" />
            <Input label={t("medications.form.frequency")} value={(values.frequency as string) || ""} onChange={(e) => onChange("frequency", e.target.value)} placeholder={t("medications.form.frequency_placeholder")} />
            <Input label={t("medications.form.route")} value={(values.route as string) || ""} onChange={(e) => onChange("route", e.target.value)} placeholder={t("medications.form.route_placeholder")} />
            <div>
              <label className="block text-base font-medium text-ink mb-1">{t("medications.form.status")}</label>
              <select
                value={(values.status as string) || "active"}
                onChange={(e) => onChange("status", e.target.value)}
                className="w-full px-3 py-2 border border-muted/40 rounded bg-surface text-ink text-base"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{t(`medications.status.${s}`)}</option>)}
              </select>
            </div>
            <Input label={t("medications.form.start_date")} type="date" value={(values.start_date as string) || ""} onChange={(e) => onChange("start_date", e.target.value)} />
            <Input label={t("medications.form.end_date")} type="date" value={(values.end_date as string) || ""} onChange={(e) => onChange("end_date", e.target.value)} />
            <Input label={t("medications.form.prescribed_by")} value={(values.prescribed_by as string) || ""} onChange={(e) => onChange("prescribed_by", e.target.value)} />
            <Input label={t("medications.form.notes")} value={(values.notes as string) || ""} onChange={(e) => onChange("notes", e.target.value)} />
          </>
        ),
      }}
    />
  );
}

import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";

import {
  createImmunization,
  deleteImmunization,
  fetchEPIVaccines,
  listImmunizations,
  updateImmunization,
  type Immunization,
  type ImmunizationFormData,
} from "@/api/immunizations";
import { ResourcePage } from "@/components/clinical/resource-page";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const STATUSES = ["completed", "entered-in-error", "not-done"] as const;

function ImmunizationFormFields({
  values,
  onChange,
}: {
  values: Partial<ImmunizationFormData> & { vaccine_source?: string };
  onChange: (field: string, value: unknown) => void;
}) {
  const { t } = useTranslation();
  const { data: epiVaccines } = useQuery({
    queryKey: ["epi-vaccines"],
    queryFn: fetchEPIVaccines,
  });

  const vaccineSource = (values.vaccine_source as string) || "free";

  return (
    <>
      <div>
        <label className="block text-base font-medium text-ink mb-1">
          {t("immunizations.form.vaccine_source")}
        </label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-base cursor-pointer">
            <input
              type="radio"
              name="vaccineSource"
              checked={vaccineSource === "epi"}
              onChange={() => onChange("vaccine_source", "epi")}
              style={{ accentColor: "var(--accent)" }}
            />
            {t("immunizations.form.epi_vaccine")}
          </label>
          <label className="flex items-center gap-2 text-base cursor-pointer">
            <input
              type="radio"
              name="vaccineSource"
              checked={vaccineSource === "free"}
              onChange={() => onChange("vaccine_source", "free")}
              style={{ accentColor: "var(--accent)" }}
            />
            {t("immunizations.form.free_text")}
          </label>
        </div>
      </div>
      {vaccineSource === "epi" ? (
        <div>
          <label className="block text-base font-medium text-ink mb-1">
            {t("immunizations.form.epi_select")}
          </label>
          <select
            value={(values.epi_vaccine_id as string) || ""}
            onChange={(e) => onChange("epi_vaccine_id", e.target.value)}
            required
            className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
          >
            <option value="">—</option>
            {(epiVaccines || []).map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.short_name})
              </option>
            ))}
          </select>
        </div>
      ) : (
        <Input
          label={t("immunizations.form.vaccine_name")}
          value={(values.vaccine_display_name as string) || ""}
          onChange={(e) => onChange("vaccine_display_name", e.target.value)}
          required
        />
      )}
      <Input
        label={t("immunizations.form.dose_number")}
        type="number"
        value={values.dose_number?.toString() || ""}
        onChange={(e) => onChange("dose_number", e.target.value)}
      />
      <Input
        label={t("immunizations.form.occurrence_date")}
        type="date"
        value={(values.occurrence_date as string) || ""}
        onChange={(e) => onChange("occurrence_date", e.target.value)}
        required
      />
      <Input
        label={t("immunizations.form.lot_number")}
        value={(values.lot_number as string) || ""}
        onChange={(e) => onChange("lot_number", e.target.value)}
      />
      <Input
        label={t("immunizations.form.manufacturer")}
        value={(values.manufacturer as string) || ""}
        onChange={(e) => onChange("manufacturer", e.target.value)}
      />
      <Input
        label={t("immunizations.form.site")}
        value={(values.site as string) || ""}
        onChange={(e) => onChange("site", e.target.value)}
      />
      <div>
        <label className="block text-base font-medium text-ink mb-1">
          {t("immunizations.form.status")}
        </label>
        <select
          value={(values.status as string) || "completed"}
          onChange={(e) => onChange("status", e.target.value)}
          className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`immunizations.status.${s}`)}
            </option>
          ))}
        </select>
      </div>
      <Input
        label={t("immunizations.form.notes")}
        value={(values.notes as string) || ""}
        onChange={(e) => onChange("notes", e.target.value)}
      />
    </>
  );
}

export function ImmunizationsPage() {
  const { t } = useTranslation();
  const { data: epiVaccines } = useQuery({
    queryKey: ["epi-vaccines"],
    queryFn: fetchEPIVaccines,
  });

  return (
    <ResourcePage<Immunization, ImmunizationFormData>
      config={{
        resourceKey: "immunizations",
        i18nPrefix: "immunizations",
        invalidateSummary: false,
        api: {
          list: listImmunizations,
          create: (pid, data) => createImmunization(pid, data),
          update: (pid, id, data) => updateImmunization(pid, id, data),
          delete: deleteImmunization,
        },
        getId: (i) => i.id,
        getName: (i) => i.vaccine_display_name,
        getInitialValues: (existing) => ({
          vaccine_source: existing?.epi_vaccine_id ? "epi" : "free",
          vaccine_display_name: existing?.vaccine_display_name || "",
          epi_vaccine_id: existing?.epi_vaccine_id || "",
          dose_number: existing?.dose_number?.toString() || "",
          occurrence_date: existing?.occurrence_date || "",
          lot_number: existing?.lot_number || "",
          manufacturer: existing?.manufacturer || "",
          site: existing?.site || "",
          status: existing?.status || "completed",
          notes: existing?.notes || "",
        }),
        buildFormData: (v) => {
          let displayName = v.vaccine_display_name as string;
          let epiId: string | undefined;
          if (v.vaccine_source === "epi" && v.epi_vaccine_id) {
            epiId = v.epi_vaccine_id as string;
            const epi = epiVaccines?.find((vac) => vac.id === epiId);
            if (epi) displayName = epi.name;
          }
          return {
            vaccine_display_name: displayName,
            epi_vaccine_id: epiId,
            dose_number: v.dose_number ? parseInt(v.dose_number as string, 10) : undefined,
            occurrence_date: v.occurrence_date as string,
            lot_number: (v.lot_number as string) || undefined,
            manufacturer: (v.manufacturer as string) || undefined,
            site: (v.site as string) || undefined,
            status: v.status as string,
            notes: (v.notes as string) || undefined,
          };
        },
        renderItem: (i) => (
          <div>
            <h2 className="text-base font-medium text-ink">{i.vaccine_display_name}</h2>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <StatusBadge status={i.status} translationPrefix="immunizations.status" />
              <span className="text-base text-muted">{i.occurrence_date}</span>
              {i.dose_number && (
                <span className="text-base text-muted">
                  {t("immunizations.dose")} {i.dose_number}
                </span>
              )}
            </div>
          </div>
        ),
        renderFormFields: (values, onChange) => (
          <ImmunizationFormFields values={values} onChange={onChange} />
        ),
      }}
    />
  );
}

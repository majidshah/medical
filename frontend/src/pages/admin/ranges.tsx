import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import {
  createRange,
  deleteRange,
  listLabs,
  listRanges,
  listTests,
  updateRange,
  type AdminRange,
  type RangeFormData,
} from "@/api/admin";
import { AdminResourcePage } from "@/components/admin/admin-resource-page";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

export function AdminRangesPage() {
  const { t } = useTranslation();
  const { testId } = useParams<{ testId: string }>();

  const { data: tests } = useQuery({
    queryKey: ["admin-tests:all"],
    queryFn: () => listTests(),
  });
  const { data: labs } = useQuery({
    queryKey: ["admin-labs"],
    queryFn: listLabs,
  });

  const test = tests?.find((t_) => t_.id === testId);
  const labOptions = (labs || []).map((l) => ({ value: l.id, label: l.name }));
  const labName = (id: string | null) => (id ? labs?.find((l) => l.id === id)?.name || id : t("admin.ranges.form.no_lab"));

  if (!testId) return null;

  return (
    <div>
      <Link to="/admin/tests" className="text-base text-secondary hover:text-accent mb-4 inline-block">
        ← {t("admin.ranges.back")}
      </Link>
      <AdminResourcePage<AdminRange, RangeFormData>
        config={{
          resourceKey: `admin-ranges:${testId}`,
          title: t("admin.ranges.title"),
          subtitle: t("admin.ranges.subtitle", { test: test?.display_name || "…" }),
          addLabel: t("admin.ranges.add"),
          addTitle: t("admin.ranges.add_title"),
          editTitle: t("admin.ranges.edit_title"),
          emptyTitle: t("admin.ranges.empty"),
          deleteActionLabel: t("admin.ranges.delete"),
          confirmDeleteMessage: (name) => t("admin.ranges.confirm_delete", { name }),
          api: {
            list: () => listRanges(testId),
            create: createRange,
            update: (id, data) => updateRange(id, data),
            delete: deleteRange,
          },
          getId: (r) => r.id,
          getName: (r) => r.applies_to,
          columns: [
            { key: "applies_to", header: t("admin.ranges.table.applies_to"), render: (r) => <span className="font-medium">{r.applies_to}</span> },
            { key: "low", header: t("admin.ranges.table.low"), render: (r) => r.low ?? "—" },
            { key: "high", header: t("admin.ranges.table.high"), render: (r) => r.high ?? "—" },
            { key: "unit", header: t("admin.ranges.table.unit"), render: (r) => r.unit },
            { key: "lab", header: t("admin.ranges.table.lab"), render: (r) => labName(r.lab_id) },
            { key: "review", header: t("admin.ranges.table.review"), render: (r) => (r.needs_clinical_review ? "⚠" : "") },
          ],
          getInitialValues: (existing) => ({
            applies_to: existing?.applies_to || "",
            low: existing?.low ?? "",
            high: existing?.high ?? "",
            unit: existing?.unit || "",
            notes: existing?.notes || "",
            lab_id: existing?.lab_id || "",
            needs_clinical_review: existing?.needs_clinical_review || false,
          }),
          buildFormData: (v) => ({
            test_id: testId,
            applies_to: v.applies_to as string,
            low: v.low === "" ? undefined : Number(v.low),
            high: v.high === "" ? undefined : Number(v.high),
            unit: v.unit as string,
            notes: (v.notes as string) || undefined,
            lab_id: (v.lab_id as string) || undefined,
            needs_clinical_review: !!v.needs_clinical_review,
          }),
          renderFormFields: (values, onChange) => (
            <>
              <Input
                label={t("admin.ranges.form.applies_to")}
                placeholder={t("admin.ranges.form.applies_to_placeholder")}
                value={(values.applies_to as string) || ""}
                onChange={(e) => onChange("applies_to", e.target.value)}
                required
              />
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label={t("admin.ranges.form.low")}
                  type="number"
                  step="any"
                  value={(values.low as string) ?? ""}
                  onChange={(e) => onChange("low", e.target.value)}
                />
                <Input
                  label={t("admin.ranges.form.high")}
                  type="number"
                  step="any"
                  value={(values.high as string) ?? ""}
                  onChange={(e) => onChange("high", e.target.value)}
                />
              </div>
              <Input
                label={t("admin.ranges.form.unit")}
                value={(values.unit as string) || ""}
                onChange={(e) => onChange("unit", e.target.value)}
                required
              />
              <Select
                label={t("admin.ranges.form.lab")}
                value={(values.lab_id as string) || ""}
                onChange={(v) => onChange("lab_id", v)}
                options={labOptions}
                placeholder={t("admin.ranges.form.no_lab")}
              />
              <Input
                label={t("admin.ranges.form.notes")}
                value={(values.notes as string) || ""}
                onChange={(e) => onChange("notes", e.target.value)}
              />
              <label className="flex items-center gap-2 text-base text-secondary">
                <input
                  type="checkbox"
                  checked={!!values.needs_clinical_review}
                  onChange={(e) => onChange("needs_clinical_review", e.target.checked)}
                />
                {t("admin.ranges.form.needs_clinical_review")}
              </label>
            </>
          ),
        }}
      />
    </div>
  );
}

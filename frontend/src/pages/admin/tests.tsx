import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import {
  createTest,
  deactivateTest,
  listDepartments,
  listPanels,
  listTests,
  updateTest,
  type CatalogueTest,
  type TestFormData,
} from "@/api/admin";
import { AdminNav } from "@/components/admin/admin-nav";
import { AdminResourcePage } from "@/components/admin/admin-resource-page";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/status-badge";

export function AdminTestsPage() {
  const { t } = useTranslation();
  const [filterDept, setFilterDept] = useState("");

  const { data: departments } = useQuery({
    queryKey: ["admin-departments"],
    queryFn: listDepartments,
  });
  const { data: allPanels } = useQuery({
    queryKey: ["admin-panels:all"],
    queryFn: () => listPanels(),
  });

  const deptOptions = (departments || []).map((d) => ({ value: d.id, label: d.name }));
  const deptName = (id: string) => departments?.find((d) => d.id === id)?.name || id;
  const panelName = (id: string | null) =>
    id ? allPanels?.find((p) => p.id === id)?.name || id : t("admin.tests.no_panel");

  return (
    <div>
      <AdminNav />
      <AdminResourcePage<CatalogueTest, TestFormData>
        config={{
          resourceKey: `admin-tests:${filterDept || "all"}`,
          title: t("admin.tests.title"),
          subtitle: t("admin.tests.subtitle"),
          addLabel: t("admin.tests.add"),
          addTitle: t("admin.tests.add_title"),
          editTitle: t("admin.tests.edit_title"),
          emptyTitle: t("admin.tests.empty"),
          deleteActionLabel: t("admin.tests.deactivate"),
          confirmDeleteMessage: (name) => t("admin.tests.confirm_deactivate", { name }),
          headerActions: (
            <div className="w-56">
              <Select
                label=""
                value={filterDept}
                onChange={setFilterDept}
                options={deptOptions}
                placeholder={t("admin.tests.table.department")}
              />
            </div>
          ),
          rowActions: (item) => (
            <Link
              to={`/admin/tests/${item.id}/ranges`}
              className="text-xs text-secondary hover:text-accent"
            >
              {t("admin.tests.ranges")}
            </Link>
          ),
          api: {
            list: () => listTests({ departmentId: filterDept || undefined }),
            create: createTest,
            update: (id, data) => updateTest(id, data),
            delete: deactivateTest,
          },
          getId: (t_) => t_.id,
          getName: (t_) => t_.display_name,
          columns: [
            { key: "key", header: t("admin.tests.table.key"), render: (t_) => <span className="font-mono text-sm">{t_.key}</span> },
            { key: "name", header: t("admin.tests.table.name"), render: (t_) => t_.display_name },
            { key: "department", header: t("admin.tests.table.department"), render: (t_) => deptName(t_.department_id) },
            { key: "panel", header: t("admin.tests.table.panel"), render: (t_) => panelName(t_.panel_id) },
            {
              key: "status",
              header: t("admin.tests.table.status"),
              render: (t_) => <StatusBadge status={t_.is_active ? "active" : "inactive"} translationPrefix="common" />,
            },
          ],
          getInitialValues: (existing) => ({
            department_id: existing?.department_id || filterDept || "",
            panel_id: existing?.panel_id || "",
            key: existing?.key || "",
            display_name: existing?.display_name || "",
            loinc_code: existing?.loinc_code || "",
            category: existing?.category || "lab",
            specimen: existing?.specimen || "",
            default_unit: existing?.default_unit || "",
          }),
          buildFormData: (v) => ({
            department_id: v.department_id as string,
            panel_id: (v.panel_id as string) || undefined,
            key: v.key as string,
            display_name: v.display_name as string,
            loinc_code: (v.loinc_code as string) || undefined,
            category: v.category as string,
            specimen: (v.specimen as string) || undefined,
            default_unit: (v.default_unit as string) || undefined,
          }),
          renderFormFields: (values, onChange, isEditing) => {
            const dept = values.department_id as string;
            const panelOptions = (allPanels || [])
              .filter((p) => p.department_id === dept)
              .map((p) => ({ value: p.id, label: p.name }));
            return (
              <>
                <Select
                  label={t("admin.tests.form.department")}
                  value={dept || ""}
                  onChange={(v) => { onChange("department_id", v); onChange("panel_id", ""); }}
                  options={deptOptions}
                  required
                />
                <Select
                  label={t("admin.tests.form.panel")}
                  value={(values.panel_id as string) || ""}
                  onChange={(v) => onChange("panel_id", v)}
                  options={panelOptions}
                  placeholder={t("admin.tests.no_panel")}
                />
                <Input
                  label={t("admin.tests.form.key")}
                  value={(values.key as string) || ""}
                  onChange={(e) => onChange("key", e.target.value)}
                  disabled={isEditing}
                  required
                />
                <Input
                  label={t("admin.tests.form.display_name")}
                  value={(values.display_name as string) || ""}
                  onChange={(e) => onChange("display_name", e.target.value)}
                  required
                />
                <Input
                  label={t("admin.tests.form.category")}
                  value={(values.category as string) || ""}
                  onChange={(e) => onChange("category", e.target.value)}
                  required
                />
                <Input
                  label={t("admin.tests.form.loinc_code")}
                  value={(values.loinc_code as string) || ""}
                  onChange={(e) => onChange("loinc_code", e.target.value)}
                />
                <Input
                  label={t("admin.tests.form.specimen")}
                  value={(values.specimen as string) || ""}
                  onChange={(e) => onChange("specimen", e.target.value)}
                />
                <Input
                  label={t("admin.tests.form.default_unit")}
                  value={(values.default_unit as string) || ""}
                  onChange={(e) => onChange("default_unit", e.target.value)}
                />
              </>
            );
          },
        }}
      />
    </div>
  );
}

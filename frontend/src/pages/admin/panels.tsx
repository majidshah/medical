import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";

import {
  createPanel,
  deactivatePanel,
  listDepartments,
  listPanels,
  updatePanel,
  type Panel,
  type PanelFormData,
} from "@/api/admin";
import { AdminNav } from "@/components/admin/admin-nav";
import { AdminResourcePage } from "@/components/admin/admin-resource-page";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/status-badge";

export function AdminPanelsPage() {
  const { t } = useTranslation();
  const [filterDept, setFilterDept] = useState("");

  const { data: departments } = useQuery({
    queryKey: ["admin-departments"],
    queryFn: listDepartments,
  });
  const deptOptions = (departments || []).map((d) => ({ value: d.id, label: d.name }));
  const deptName = (id: string) => departments?.find((d) => d.id === id)?.name || id;

  return (
    <div>
      <AdminNav />
      <AdminResourcePage<Panel, PanelFormData>
        config={{
          resourceKey: `admin-panels:${filterDept || "all"}`,
          title: t("admin.panels.title"),
          subtitle: t("admin.panels.subtitle"),
          addLabel: t("admin.panels.add"),
          addTitle: t("admin.panels.add_title"),
          editTitle: t("admin.panels.edit_title"),
          emptyTitle: t("admin.panels.empty"),
          deleteActionLabel: t("admin.panels.deactivate"),
          confirmDeleteMessage: (name) => t("admin.panels.confirm_deactivate", { name }),
          headerActions: (
            <div className="w-56">
              <Select
                label=""
                value={filterDept}
                onChange={setFilterDept}
                options={deptOptions}
                placeholder={t("admin.panels.table.department")}
              />
            </div>
          ),
          api: {
            list: () => listPanels(filterDept || undefined),
            create: createPanel,
            update: (id, data) => updatePanel(id, data),
            delete: deactivatePanel,
          },
          getId: (p) => p.id,
          getName: (p) => p.name,
          columns: [
            { key: "key", header: t("admin.panels.table.key"), render: (p) => <span className="font-mono text-sm">{p.key}</span> },
            { key: "name", header: t("admin.panels.table.name"), render: (p) => p.name },
            { key: "department", header: t("admin.panels.table.department"), render: (p) => deptName(p.department_id) },
            { key: "order", header: t("admin.panels.table.order"), render: (p) => p.display_order },
            {
              key: "status",
              header: t("admin.panels.table.status"),
              render: (p) => <StatusBadge status={p.is_active ? "active" : "inactive"} translationPrefix="common" />,
            },
          ],
          getInitialValues: (existing) => ({
            department_id: existing?.department_id || filterDept || "",
            key: existing?.key || "",
            name: existing?.name || "",
            display_order: existing?.display_order ?? 0,
          }),
          buildFormData: (v) => ({
            department_id: v.department_id as string,
            key: v.key as string,
            name: v.name as string,
            display_order: Number(v.display_order) || 0,
          }),
          renderFormFields: (values, onChange, isEditing) => (
            <>
              <Select
                label={t("admin.panels.form.department")}
                value={(values.department_id as string) || ""}
                onChange={(v) => onChange("department_id", v)}
                options={deptOptions}
                disabled={isEditing}
                required
              />
              <Input
                label={t("admin.panels.form.key")}
                value={(values.key as string) || ""}
                onChange={(e) => onChange("key", e.target.value)}
                disabled={isEditing}
                required
              />
              <Input
                label={t("admin.panels.form.name")}
                value={(values.name as string) || ""}
                onChange={(e) => onChange("name", e.target.value)}
                required
              />
              <Input
                label={t("admin.panels.form.display_order")}
                type="number"
                value={(values.display_order as number) ?? 0}
                onChange={(e) => onChange("display_order", e.target.value)}
              />
            </>
          ),
        }}
      />
    </div>
  );
}

import { useTranslation } from "react-i18next";

import {
  createDepartment,
  deactivateDepartment,
  listDepartments,
  updateDepartment,
  type Department,
  type DepartmentFormData,
} from "@/api/admin";
import { AdminNav } from "@/components/admin/admin-nav";
import { AdminResourcePage } from "@/components/admin/admin-resource-page";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export function AdminDepartmentsPage() {
  const { t } = useTranslation();

  return (
    <div>
      <AdminNav />
      <AdminResourcePage<Department, DepartmentFormData>
        config={{
          resourceKey: "admin-departments",
          title: t("admin.departments.title"),
          subtitle: t("admin.departments.subtitle"),
          addLabel: t("admin.departments.add"),
          addTitle: t("admin.departments.add_title"),
          editTitle: t("admin.departments.edit_title"),
          emptyTitle: t("admin.departments.empty"),
          deleteActionLabel: t("admin.departments.deactivate"),
          confirmDeleteMessage: (name) => t("admin.departments.confirm_deactivate", { name }),
          api: {
            list: listDepartments,
            create: createDepartment,
            update: (id, data) => updateDepartment(id, data),
            delete: deactivateDepartment,
          },
          getId: (d) => d.id,
          getName: (d) => d.name,
          columns: [
            { key: "key", header: t("admin.departments.table.key"), render: (d) => <span className="font-mono text-sm">{d.key}</span> },
            { key: "name", header: t("admin.departments.table.name"), render: (d) => d.name },
            { key: "order", header: t("admin.departments.table.order"), render: (d) => d.display_order },
            {
              key: "status",
              header: t("admin.departments.table.status"),
              render: (d) => <StatusBadge status={d.is_active ? "active" : "inactive"} translationPrefix="common" />,
            },
          ],
          getInitialValues: (existing) => ({
            key: existing?.key || "",
            name: existing?.name || "",
            display_order: existing?.display_order ?? 0,
          }),
          buildFormData: (v) => ({
            key: v.key as string,
            name: v.name as string,
            display_order: Number(v.display_order) || 0,
          }),
          renderFormFields: (values, onChange, isEditing) => (
            <>
              <Input
                label={t("admin.departments.form.key")}
                value={(values.key as string) || ""}
                onChange={(e) => onChange("key", e.target.value)}
                disabled={isEditing}
                required
              />
              <Input
                label={t("admin.departments.form.name")}
                value={(values.name as string) || ""}
                onChange={(e) => onChange("name", e.target.value)}
                required
              />
              <Input
                label={t("admin.departments.form.display_order")}
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

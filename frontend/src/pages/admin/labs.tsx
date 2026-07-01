import { useTranslation } from "react-i18next";

import {
  createLab,
  deactivateLab,
  listLabs,
  updateLab,
  type Lab,
  type LabFormData,
} from "@/api/admin";
import { AdminNav } from "@/components/admin/admin-nav";
import { AdminResourcePage } from "@/components/admin/admin-resource-page";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export function AdminLabsPage() {
  const { t } = useTranslation();

  return (
    <div>
      <AdminNav />
      <AdminResourcePage<Lab, LabFormData>
        config={{
          resourceKey: "admin-labs",
          title: t("admin.labs.title"),
          subtitle: t("admin.labs.subtitle"),
          addLabel: t("admin.labs.add"),
          addTitle: t("admin.labs.add_title"),
          editTitle: t("admin.labs.edit_title"),
          emptyTitle: t("admin.labs.empty"),
          deleteActionLabel: t("admin.labs.deactivate"),
          confirmDeleteMessage: (name) => t("admin.labs.confirm_deactivate", { name }),
          api: {
            list: listLabs,
            create: createLab,
            update: (id, data) => updateLab(id, data),
            delete: deactivateLab,
          },
          getId: (l) => l.id,
          getName: (l) => l.name,
          columns: [
            { key: "key", header: t("admin.labs.table.key"), render: (l) => <span className="font-mono text-sm">{l.key}</span> },
            { key: "name", header: t("admin.labs.table.name"), render: (l) => l.name },
            {
              key: "status",
              header: t("admin.labs.table.status"),
              render: (l) => <StatusBadge status={l.is_active ? "active" : "inactive"} translationPrefix="common" />,
            },
          ],
          getInitialValues: (existing) => ({
            key: existing?.key || "",
            name: existing?.name || "",
          }),
          buildFormData: (v) => ({
            key: v.key as string,
            name: v.name as string,
          }),
          renderFormFields: (values, onChange, isEditing) => (
            <>
              <Input
                label={t("admin.labs.form.key")}
                value={(values.key as string) || ""}
                onChange={(e) => onChange("key", e.target.value)}
                disabled={isEditing}
                required
              />
              <Input
                label={t("admin.labs.form.name")}
                value={(values.name as string) || ""}
                onChange={(e) => onChange("name", e.target.value)}
                required
              />
            </>
          ),
        }}
      />
    </div>
  );
}

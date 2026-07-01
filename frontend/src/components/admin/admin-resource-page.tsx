import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { Modal } from "@/components/ui/modal";
import { PageHeader } from "@/components/ui/page-header";

interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => ReactNode;
  className?: string;
}

interface AdminResourcePageConfig<TItem, TFormData> {
  resourceKey: string;
  title: string;
  subtitle?: string;
  addLabel: string;
  addTitle: string;
  editTitle: string;
  emptyTitle: string;
  deleteActionLabel: string;
  confirmDeleteMessage: (name: string) => string;
  api: {
    list: () => Promise<TItem[]>;
    create: (data: TFormData) => Promise<TItem>;
    update: (id: string, data: Partial<TFormData>) => Promise<TItem>;
    delete: (id: string) => Promise<void>;
  };
  columns: Column<TItem>[];
  getId: (item: TItem) => string;
  getName: (item: TItem) => string;
  renderFormFields: (
    values: Record<string, unknown>,
    onChange: (field: string, value: unknown) => void,
    isEditing: boolean,
  ) => ReactNode;
  buildFormData: (values: Record<string, unknown>) => TFormData;
  getInitialValues: (existing?: TItem) => Record<string, unknown>;
  headerActions?: ReactNode;
  rowActions?: (item: TItem) => ReactNode;
}

export function AdminResourcePage<TItem, TFormData>({
  config,
}: {
  config: AdminResourcePageConfig<TItem, TFormData>;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const submitRef = useRef<HTMLButtonElement>(null);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<TItem | undefined>();
  const [deleting, setDeleting] = useState<TItem | undefined>();
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [formError, setFormError] = useState("");

  const queryKey = [config.resourceKey];

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: config.api.list,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const formData = config.buildFormData(formValues);
      return editing
        ? config.api.update(config.getId(editing), formData as Partial<TFormData>)
        : config.api.create(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      handleCloseForm();
    },
    onError: (err: Error) => {
      if (err instanceof ApiError) {
        setFormError(err.detail);
      } else {
        setFormError(t("common.error"));
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => config.api.delete(config.getId(deleting!)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setDeleting(undefined);
    },
  });

  const handleOpenAdd = () => {
    setEditing(undefined);
    setFormValues(config.getInitialValues());
    setFormError("");
    setShowForm(true);
  };

  const handleEdit = (item: TItem) => {
    setEditing(item);
    setFormValues(config.getInitialValues(item));
    setFormError("");
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditing(undefined);
    setFormValues({});
    setFormError("");
  };

  const handleFieldChange = (field: string, value: unknown) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFormError("");
    saveMutation.mutate();
  };

  if (isLoading) {
    return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  }
  if (error) {
    return <p className="text-status-warning text-center py-12">{t("common.error")}</p>;
  }

  const items = data || [];

  const columns: Column<TItem>[] = [
    ...config.columns,
    {
      key: "__actions",
      header: "",
      className: "text-right",
      render: (item) => (
        <div className="flex gap-3 justify-end items-center">
          {config.rowActions?.(item)}
          <button
            onClick={() => handleEdit(item)}
            className="text-xs text-secondary hover:text-accent"
          >
            {t("common.edit")}
          </button>
          <button
            onClick={() => setDeleting(item)}
            className="text-xs text-secondary hover:text-status-warning"
          >
            {config.deleteActionLabel}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={config.title}
        subtitle={config.subtitle}
        actions={
          <>
            {config.headerActions}
            <Button onClick={handleOpenAdd}>{config.addLabel}</Button>
          </>
        }
      />

      <Modal
        open={showForm}
        onClose={handleCloseForm}
        title={editing ? config.editTitle : config.addTitle}
        footer={
          <>
            <Button variant="secondary" onClick={handleCloseForm}>
              {t("common.cancel")}
            </Button>
            <Button onClick={() => submitRef.current?.click()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? t("common.loading") : t("common.save")}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-5">
          {config.renderFormFields(formValues, handleFieldChange, !!editing)}
          {formError && (
            <p className="text-sm text-status-warning" role="alert">
              {formError}
            </p>
          )}
          <button ref={submitRef} type="submit" className="hidden" aria-hidden="true" tabIndex={-1} />
        </form>
      </Modal>

      {items.length === 0 ? (
        <EmptyState
          title={config.emptyTitle}
          action={<Button onClick={handleOpenAdd}>{config.addLabel}</Button>}
        />
      ) : (
        <Card>
          <DataTable columns={columns} data={items} getKey={config.getId} />
        </Card>
      )}

      {deleting && (
        <ConfirmDialog
          message={config.confirmDeleteMessage(config.getName(deleting))}
          onConfirm={() => deleteMutation.mutate()}
          onCancel={() => setDeleting(undefined)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}

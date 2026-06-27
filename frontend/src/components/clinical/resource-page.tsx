import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PatientNav } from "@/components/layout/patient-nav";

interface ResourcePageConfig<TItem, TFormData> {
  resourceKey: string;
  i18nPrefix: string;
  api: {
    list: (patientId: string) => Promise<{ items: TItem[]; total: number }>;
    create: (patientId: string, data: TFormData) => Promise<TItem>;
    update: (patientId: string, id: string, data: Partial<TFormData>) => Promise<TItem>;
    delete: (patientId: string, id: string) => Promise<void>;
  };
  getId: (item: TItem) => string;
  getName: (item: TItem) => string;
  renderItem: (item: TItem, t: (key: string, opts?: Record<string, string>) => string) => ReactNode;
  renderFormFields: (
    values: Partial<TFormData>,
    onChange: (field: string, value: unknown) => void,
    t: (key: string, opts?: Record<string, string>) => string,
  ) => ReactNode;
  buildFormData: (values: Record<string, unknown>) => TFormData;
  getInitialValues: (existing?: TItem) => Record<string, unknown>;
  cardClassName?: string;
  invalidateSummary?: boolean;
}

export function ResourcePage<TItem, TFormData>({
  config,
}: {
  config: ResourcePageConfig<TItem, TFormData>;
}) {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<TItem | undefined>();
  const [deleting, setDeleting] = useState<TItem | undefined>();
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [formError, setFormError] = useState("");

  const queryKey = [config.resourceKey, patientId];

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => config.api.list(patientId!),
    enabled: !!patientId,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const formData = config.buildFormData(formValues);
      return editing
        ? config.api.update(patientId!, config.getId(editing), formData as Partial<TFormData>)
        : config.api.create(patientId!, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      if (config.invalidateSummary !== false) {
        queryClient.invalidateQueries({ queryKey: ["patient-summary", patientId] });
      }
      handleCloseForm();
    },
    onError: (err: Error) => {
      if (err instanceof ApiError && err.status === 422) {
        setFormError(err.detail);
      } else {
        setFormError(t(`${config.i18nPrefix}.form.error`));
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => config.api.delete(patientId!, config.getId(deleting!)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      if (config.invalidateSummary !== false) {
        queryClient.invalidateQueries({ queryKey: ["patient-summary", patientId] });
      }
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

  const items = data?.items || [];

  return (
    <div>
      <PatientNav patientId={patientId!} />

      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-2xl text-ink">
          {t(`${config.i18nPrefix}.title`)}
        </h1>
        {!showForm && items.length > 0 && (
          <Button onClick={handleOpenAdd}>
            {t(`${config.i18nPrefix}.add`)}
          </Button>
        )}
      </div>

      {showForm && (
        <Card className="mb-6">
          <h2 className="font-serif text-xl text-ink mb-4">
            {editing
              ? t(`${config.i18nPrefix}.form.edit_title`)
              : t(`${config.i18nPrefix}.form.add_title`)}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {config.renderFormFields(formValues as Partial<TFormData>, handleFieldChange, t)}
            {formError && (
              <p className="text-base text-status-warning" role="alert">
                {formError}
              </p>
            )}
            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending
                  ? t("common.loading")
                  : editing
                    ? t(`${config.i18nPrefix}.form.save`)
                    : t(`${config.i18nPrefix}.form.add`)}
              </Button>
              <Button type="button" variant="secondary" onClick={handleCloseForm}>
                {t("common.cancel")}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {items.length === 0 && !showForm ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-4">
            {t(`${config.i18nPrefix}.empty`)}
          </p>
          <Button onClick={handleOpenAdd}>
            {t(`${config.i18nPrefix}.add`)}
          </Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={config.getId(item)} className={config.cardClassName}>
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  {config.renderItem(item, t)}
                </div>
                <div className="flex gap-2 ml-4 shrink-0">
                  <button
                    onClick={() => handleEdit(item)}
                    className="text-base text-accent hover:underline"
                  >
                    {t("common.edit")}
                  </button>
                  <button
                    onClick={() => setDeleting(item)}
                    className="text-base text-status-warning hover:underline"
                  >
                    {t("common.delete")}
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {deleting && (
        <ConfirmDialog
          message={t(`${config.i18nPrefix}.confirm_delete`, {
            name: config.getName(deleting),
          })}
          onConfirm={() => deleteMutation.mutate()}
          onCancel={() => setDeleting(undefined)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}

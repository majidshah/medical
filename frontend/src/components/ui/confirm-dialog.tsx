import { useTranslation } from "react-i18next";

import { Button } from "./button";

interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function ConfirmDialog({
  message,
  onConfirm,
  onCancel,
  loading,
}: ConfirmDialogProps) {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30">
      <div className="bg-surface rounded-lg border border-muted/20 p-6 shadow-lg max-w-sm w-full mx-4">
        <p className="text-base text-ink mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {t("common.cancel")}
          </Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading ? t("common.loading") : t("common.confirm")}
          </Button>
        </div>
      </div>
    </div>
  );
}

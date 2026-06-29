import { useTranslation } from "react-i18next";

interface StatusBadgeProps {
  status: string;
  translationPrefix: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-accent-50 text-accent",
  recurrence: "bg-status-warning-bg text-status-warning",
  relapse: "bg-status-warning-bg text-status-warning",
  inactive: "bg-status-unknown-bg text-secondary",
  remission: "bg-accent-50 text-accent",
  resolved: "bg-status-unknown-bg text-secondary",
  completed: "bg-accent-50 text-accent",
  stopped: "bg-status-unknown-bg text-secondary",
  "on-hold": "bg-status-warning-bg text-status-warning",
  unknown: "bg-status-unknown-bg text-secondary",
  "entered-in-error": "bg-status-warning-bg text-status-warning",
  "not-done": "bg-status-unknown-bg text-secondary",
};

export function StatusBadge({ status, translationPrefix }: StatusBadgeProps) {
  const { t } = useTranslation();
  const style = STATUS_STYLES[status] || "bg-status-unknown-bg text-secondary";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-theme text-xs font-medium ${style}`}>
      {t(`${translationPrefix}.${status}`, status)}
    </span>
  );
}

import { useTranslation } from "react-i18next";

interface StatusBadgeProps {
  status: string;
  translationPrefix: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-accent-50 text-accent",
  recurrence: "bg-status-warning-bg text-status-warning",
  relapse: "bg-status-warning-bg text-status-warning",
  inactive: "bg-status-unknown-bg text-muted",
  remission: "bg-accent-50 text-accent",
  resolved: "bg-status-unknown-bg text-muted",
  completed: "bg-accent-50 text-accent",
  stopped: "bg-status-unknown-bg text-muted",
  "on-hold": "bg-status-warning-bg text-status-warning",
  unknown: "bg-status-unknown-bg text-muted",
  "entered-in-error": "bg-status-warning-bg text-status-warning",
  "not-done": "bg-status-unknown-bg text-muted",
};

export function StatusBadge({ status, translationPrefix }: StatusBadgeProps) {
  const { t } = useTranslation();
  const style = STATUS_STYLES[status] || "bg-status-unknown-bg text-muted";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-theme text-base font-medium ${style}`}
    >
      {t(`${translationPrefix}.${status}`, status)}
    </span>
  );
}

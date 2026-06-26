import { useTranslation } from "react-i18next";

interface StatusBadgeProps {
  status: string;
  translationPrefix: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-teal-50 text-teal-600",
  recurrence: "bg-amber-50 text-amber-600",
  relapse: "bg-amber-50 text-amber-600",
  inactive: "bg-gray-100 text-muted",
  remission: "bg-teal-50 text-teal-600",
  resolved: "bg-gray-100 text-muted",
};

export function StatusBadge({ status, translationPrefix }: StatusBadgeProps) {
  const { t } = useTranslation();
  const style = STATUS_STYLES[status] || "bg-gray-100 text-muted";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-base font-medium ${style}`}
    >
      {t(`${translationPrefix}.${status}`, status)}
    </span>
  );
}

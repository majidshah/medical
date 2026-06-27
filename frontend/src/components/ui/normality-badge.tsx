import { useTranslation } from "react-i18next";

interface NormalityBadgeProps {
  status: string;
}

const CONFIG: Record<string, { bg: string; text: string; icon: string }> = {
  in_range: { bg: "bg-status-normal-bg", text: "text-status-normal", icon: "✓" },
  below_low: { bg: "bg-status-warning-bg", text: "text-status-warning", icon: "▼" },
  above_high: { bg: "bg-status-warning-bg", text: "text-status-warning", icon: "▲" },
  unknown: { bg: "bg-status-unknown-bg", text: "text-status-unknown", icon: "?" },
};

export function NormalityBadge({ status }: NormalityBadgeProps) {
  const { t } = useTranslation();
  const c = CONFIG[status] || CONFIG.unknown;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-theme text-base font-medium ${c.bg} ${c.text}`}
    >
      <span aria-hidden="true">{c.icon}</span>
      {t(`normality.${status}`, status)}
    </span>
  );
}

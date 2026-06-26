import { useTranslation } from "react-i18next";

interface NormalityBadgeProps {
  status: string;
}

export function NormalityBadge({ status }: NormalityBadgeProps) {
  const { t } = useTranslation();

  const config: Record<string, { bg: string; text: string; icon: string }> = {
    in_range: { bg: "bg-normal-green/10", text: "text-normal-green", icon: "✓" },
    below_low: { bg: "bg-amber-50", text: "text-amber-600", icon: "▼" },
    above_high: { bg: "bg-amber-50", text: "text-amber-600", icon: "▲" },
    unknown: { bg: "bg-gray-100", text: "text-muted", icon: "?" },
  };

  const c = config[status] || config.unknown;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-base font-medium ${c.bg} ${c.text}`}
    >
      <span aria-hidden="true">{c.icon}</span>
      {t(`normality.${status}`, status)}
    </span>
  );
}

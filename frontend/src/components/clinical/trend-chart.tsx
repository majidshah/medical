import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";

interface TrendPoint {
  effective_date: string;
  value: number | string | null;
  unit: string | null;
}

interface TrendChartProps {
  title: string;
  points: TrendPoint[];
  chartable: boolean;
  unit?: string | null;
  rangeLow?: number | null;
  rangeHigh?: number | null;
}

function getTokenValue(varName: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

export function TrendChart({
  title,
  points,
  chartable,
  unit,
  rangeLow,
  rangeHigh,
}: TrendChartProps) {
  const { t } = useTranslation();
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const accentColor = getTokenValue("--accent") || "#1A6B5A";
  const mutedColor = getTokenValue("--text-muted") || "#8C8C8C";
  const borderColor = getTokenValue("--border") || "#e0e0e0";
  const rangeColor = getTokenValue("--status-normal") || "#2D7A4F";

  if (points.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="text-muted text-base">{t("trend.empty")}</p>
      </Card>
    );
  }

  if (!chartable) {
    return (
      <Card>
        <h3 className="font-serif text-lg text-ink mb-3">{title}</h3>
        <p className="text-base text-muted mb-3">{t("trend.not_chartable")}</p>
        <TrendTable points={points} unit={unit} />
      </Card>
    );
  }

  const data = points.map((p) => ({
    date: p.effective_date,
    value: typeof p.value === "number" ? p.value : null,
  }));

  return (
    <Card>
      <h3 className="font-serif text-lg text-ink mb-3">{title}</h3>
      <div className="h-64" role="img" aria-label={t("trend.chart_label", { title })}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke={mutedColor} />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke={mutedColor}
              label={unit ? { value: unit, angle: -90, position: "insideLeft", style: { fontSize: 12 } } : undefined}
            />
            <Tooltip
              contentStyle={{ fontSize: 12, border: `1px solid ${borderColor}` }}
              formatter={(v) => [unit ? `${v} ${unit}` : String(v ?? ""), title]}
            />
            {rangeLow != null && (
              <Line
                type="monotone"
                dataKey={() => rangeLow}
                stroke={rangeColor}
                strokeDasharray="5 5"
                dot={false}
                isAnimationActive={!prefersReducedMotion}
                name={t("trend.range_low")}
              />
            )}
            {rangeHigh != null && (
              <Line
                type="monotone"
                dataKey={() => rangeHigh}
                stroke={rangeColor}
                strokeDasharray="5 5"
                dot={false}
                isAnimationActive={!prefersReducedMotion}
                name={t("trend.range_high")}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={accentColor}
              strokeWidth={2}
              dot={{ r: 4, fill: accentColor }}
              isAnimationActive={!prefersReducedMotion}
              name={title}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-4">
        <summary className="text-base text-accent cursor-pointer hover:underline">
          {t("trend.show_table")}
        </summary>
        <div className="mt-2">
          <TrendTable points={points} unit={unit} />
        </div>
      </details>
    </Card>
  );
}

function TrendTable({
  points,
  unit,
}: {
  points: TrendPoint[];
  unit?: string | null;
}) {
  const { t } = useTranslation();
  return (
    <table className="w-full text-base">
      <thead>
        <tr className="border-b border-border-light text-left">
          <th className="pb-2 font-medium">{t("trend.table_date")}</th>
          <th className="pb-2 font-medium">{t("trend.table_value")}</th>
        </tr>
      </thead>
      <tbody>
        {points.map((p, i) => (
          <tr key={i} className="border-b border-border-light">
            <td className="py-1.5 text-muted">{p.effective_date}</td>
            <td className="py-1.5 font-sans tabular-nums">
              {p.value ?? "—"} {unit && <span className="text-muted">{unit}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

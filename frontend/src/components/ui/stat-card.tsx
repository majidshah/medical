import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  tint?: "accent" | "warning" | "normal" | "neutral";
}

const TINT_STYLES = {
  accent: "bg-accent-50 text-accent",
  warning: "bg-status-warning-bg text-status-warning",
  normal: "bg-status-normal-bg text-status-normal",
  neutral: "bg-status-unknown-bg text-secondary",
};

export function StatCard({ label, value, icon, tint = "neutral" }: StatCardProps) {
  return (
    <div className="bg-surface rounded-theme border border-border-light p-4 flex items-center gap-3">
      {icon && (
        <div className={`w-9 h-9 rounded-theme flex items-center justify-center text-sm shrink-0 ${TINT_STYLES[tint]}`}>
          {icon}
        </div>
      )}
      <div>
        <p className="text-2xl font-sans tabular-nums font-medium text-ink">{value}</p>
        <p className="text-xs text-secondary">{label}</p>
      </div>
    </div>
  );
}

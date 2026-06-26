import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`bg-surface rounded-lg border border-muted/20 p-6 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

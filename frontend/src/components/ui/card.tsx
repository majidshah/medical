import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`bg-surface rounded-theme border border-border-light p-6 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

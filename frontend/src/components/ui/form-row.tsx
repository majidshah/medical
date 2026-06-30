import type { ReactNode } from "react";

interface FormRowProps {
  cols?: 1 | 2 | 3;
  children: ReactNode;
}

const GRID = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-3",
};

export function FormRow({ cols = 2, children }: FormRowProps) {
  return <div className={`grid ${GRID[cols]} gap-4`}>{children}</div>;
}

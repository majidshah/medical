import type { ReactNode } from "react";

import { Card } from "./card";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Card className="text-center py-16">
      <p className="text-secondary text-base mb-1">{title}</p>
      {description && <p className="text-muted text-sm mb-4">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </Card>
  );
}

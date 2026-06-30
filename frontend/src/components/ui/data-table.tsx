import type { ReactNode } from "react";

interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  getKey: (item: T) => string;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
}

export function DataTable<T>({ columns, data, getKey, emptyMessage, onRowClick }: DataTableProps<T>) {
  if (data.length === 0 && emptyMessage) {
    return <p className="text-muted text-base py-6 text-center">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-base">
        <thead>
          <tr className="border-b border-border-light">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`pb-2 text-left text-xs font-medium text-secondary uppercase tracking-wide ${col.className || ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={getKey(item)}
              className={`border-b border-border-light last:border-b-0 ${onRowClick ? "cursor-pointer hover:bg-accent-50/50 transition-colors" : ""}`}
              onClick={onRowClick ? () => onRowClick(item) : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className={`py-2.5 ${col.className || ""}`}>
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, id, ...props }: InputProps) {
  const inputId = id || label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="mb-4">
      <label
        htmlFor={inputId}
        className="block text-base font-medium text-ink mb-1"
      >
        {label}
      </label>
      <input
        id={inputId}
        className={`w-full px-3 py-2 border rounded-theme bg-surface text-ink font-sans text-base ${
          error ? "border-status-warning" : "border-border"
        }`}
        {...props}
      />
      {error && <p className="mt-1 text-base text-status-warning">{error}</p>}
    </div>
  );
}

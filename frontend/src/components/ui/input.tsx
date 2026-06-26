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
        className={`w-full px-3 py-2 border rounded bg-surface text-ink font-sans text-base focus-visible:outline-2 focus-visible:outline-teal ${
          error ? "border-amber" : "border-muted/40"
        }`}
        {...props}
      />
      {error && <p className="mt-1 text-base text-amber">{error}</p>}
    </div>
  );
}

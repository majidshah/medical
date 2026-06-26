import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  const base =
    "px-4 py-2 rounded font-sans font-medium text-base transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-teal text-white hover:bg-teal-700",
    secondary:
      "bg-transparent text-teal border border-teal hover:bg-teal-50",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props} />
  );
}

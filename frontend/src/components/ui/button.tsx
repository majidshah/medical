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
    "px-4 py-2 rounded-theme font-sans font-medium text-base transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-accent text-on-accent hover:bg-accent-hover",
    secondary: "bg-transparent text-accent border border-accent hover:bg-accent-light",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props} />
  );
}

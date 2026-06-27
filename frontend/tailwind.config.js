/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "var(--bg-page)",
        surface: "var(--bg-surface)",
        sidebar: "var(--bg-sidebar)",
        ink: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        "on-sidebar": "var(--text-on-sidebar)",
        "on-accent": "var(--text-on-accent)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          light: "var(--accent-light)",
          50: "var(--accent-50)",
        },
        border: "var(--border)",
        "border-light": "var(--border-light)",
        "status-normal": "var(--status-normal)",
        "status-normal-bg": "var(--status-normal-bg)",
        "status-warning": "var(--status-warning)",
        "status-warning-bg": "var(--status-warning-bg)",
        "status-unknown": "var(--status-unknown)",
        "status-unknown-bg": "var(--status-unknown-bg)",
      },
      fontFamily: {
        serif: ['"Libre Baskerville"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        base: ["0.875rem", { lineHeight: "1.5" }],
        lg: ["1.094rem", { lineHeight: "1.5" }],
        xl: ["1.369rem", { lineHeight: "1.3" }],
        "2xl": ["1.709rem", { lineHeight: "1.2" }],
      },
      spacing: {
        "theme-xs": "var(--space-xs)",
        "theme-sm": "var(--space-sm)",
        "theme-md": "var(--space-md)",
        "theme-lg": "var(--space-lg)",
        "theme-xl": "var(--space-xl)",
      },
      borderRadius: {
        theme: "var(--radius)",
      },
    },
  },
  plugins: [],
};

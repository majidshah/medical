/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F7F4EF",
        surface: "#FFFFFF",
        ink: "#2C2C2C",
        teal: {
          DEFAULT: "#1A6B5A",
          50: "#E8F5F1",
          100: "#C5E8DE",
          600: "#1A6B5A",
          700: "#145A4B",
        },
        amber: {
          DEFAULT: "#C47F17",
          50: "#FEF5E7",
          600: "#C47F17",
        },
        muted: "#8C8C8C",
        "normal-green": "#2D7A4F",
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
    },
  },
  plugins: [],
};

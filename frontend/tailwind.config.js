/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0F4C81",
          light: "#1a6db5"
        },
        accent: {
          DEFAULT: "#1D9E75"
        },
        warning: {
          DEFAULT: "#D97706"
        },
        danger: {
          DEFAULT: "#DC2626"
        },
        medical: {
          bg: "#F8FAFC",
          surface: "#FFFFFF",
          muted: "#64748B",
          text: "#1E293B",
          border: "#E2E8F0"
        }
      }
    }
  },
  plugins: []
};

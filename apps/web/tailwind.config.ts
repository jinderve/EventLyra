import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#090C12",
        ink: "#F7F9FC",
        muted: "#98A4B7",
        line: "#20283A",
        panel: "#0E131B",
        primary: "#8B5CF6",
        signal: "#22D3EE",
        live: "#F43F5E",
        online: "#34D399",
      },
      borderRadius: {
        box: "15px",
        control: "9px",
        visual: "18px",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        focus: "0 0 0 2px #090C12, 0 0 0 4px #8B5CF6",
      },
    },
  },
  plugins: [],
} satisfies Config;

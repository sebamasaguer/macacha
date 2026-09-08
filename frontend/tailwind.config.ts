import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        macacha: {
          pink: "#f1446f",
          blue: "#0078c9",
          blueDark: "#005aba",
          navy: "#1a2732",
        },
      },
      fontFamily: {
        sans: ["var(--font-montserrat)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;

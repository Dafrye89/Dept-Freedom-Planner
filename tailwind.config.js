/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./**/*.py",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0a192f",
          blue: "#172a45",
          red: "#b91c1c",
          crimson: "#991b1b",
          gold: "#d4af37",
          light: "#f8fafc",
          muted: "#64748b"
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        heading: ["Montserrat", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        'solid': '4px 4px 0 0 rgba(10, 25, 47, 1)',
        'solid-red': '4px 4px 0 0 rgba(185, 28, 28, 1)',
      }
    },
  },
  plugins: [],
};

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
        patriotic: {
          navy: "#0f204b",
          blue: "#1a3673",
          red: "#cc0000",
          white: "#ffffff",
          silver: "#dbe5f1",
          gray: "#eef4fa",
          ink: "#172033",
          mute: "#5b677d",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        heading: ["Montserrat", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 18px 54px rgba(15, 32, 75, 0.12)",
        glow: "0 24px 70px rgba(15, 32, 75, 0.18)",
      },
      backgroundImage: {
        "patriot-gradient":
          "linear-gradient(135deg, #0f204b 0%, #1a3673 56%, #cc0000 100%)",
        "patriot-soft":
          "linear-gradient(135deg, rgba(15, 32, 75, 0.96) 0%, rgba(26, 54, 115, 0.92) 56%, rgba(204, 0, 0, 0.82) 100%)",
        "surface-glow":
          "radial-gradient(circle at top left, rgba(26, 54, 115, 0.18), transparent 34%), radial-gradient(circle at right center, rgba(204, 0, 0, 0.12), transparent 28%), linear-gradient(180deg, #f8fbff 0%, #edf3f8 100%)",
      },
    },
  },
  plugins: [],
};

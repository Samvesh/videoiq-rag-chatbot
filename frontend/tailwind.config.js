// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2ECC71",
        background: "#0A0A0A",
        foreground: "#FFFFFF"
      },
      boxShadow: {
        glow: "0 0 8px #2ECC71"
      }
    }
  },
  plugins: []
};

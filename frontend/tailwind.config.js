/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#102033",
        "muted-text": "#667085",
        surface: "#FFFFFF",
        background: "#F5F7FA",
        border: "#E4E7EC",
        primary: "#1D4ED8",
        positive: "#16803C",
        warning: "#B54708",
        error: "#C43232",
      }
    },
  },
  plugins: [],
}

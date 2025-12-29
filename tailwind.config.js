/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      screens: {
        xs: "375px", // Breakpoint personnalisé pour très petits mobiles
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        defitech: {
          blue: "#0047AB", // Bleu "Roi" professionnel (proche du #0000FF demandé mais lisible)
          red: "#D60000", // Rouge vif (proche du #FF0000 mais moins agressif)
          dark: "#0f172a",
          light: "#f8fafc",
        },
      },
      primary: {
        50: '#f0f9ff',
        100: '#e0f2fe',
        200: '#bae6fd',
        300: '#7dd3fc',
        400: '#38bdf8',
        500: '#0ea5e9',
        600: '#0284c7',
        700: '#0369a1',
        800: '#075985',
        900: '#0c4a6e',
      },
      slate: {
        850: '#151e2e',
        900: '#0f172a'
      },
      dark: {
        bg: '#0f172a',
        surface: '#1e293b',
        border: '#334155',
      },
    },
    animation: {
      'fade-in': 'fadeIn 0.3s ease-out',
      'slide-up': 'slideUp 0.4s ease-out',
      'pulse-slow': 'pulse 3s infinite',
    },
    keyframes: {
      fadeIn: {
        '0%': { opacity: '0' },
        '100%': { opacity: '1' },
      },
      slideUp: {
        '0%': { transform: 'translateY(20px)', opacity: '0' },
        '100%': { transform: 'translateY(0)', opacity: '1' },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

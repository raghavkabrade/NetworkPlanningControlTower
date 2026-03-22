/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#1A6B3C', light: '#2DC653', dark: '#0F4024' },
      },
    },
  },
  plugins: [],
}

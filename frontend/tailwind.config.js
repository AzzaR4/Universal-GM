/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0a0a0f',
          900: '#12121a',
          800: '#1a1a26',
          700: '#242433',
          600: '#33334a',
        },
        ember: {
          400: '#f0a868',
          500: '#e8893c',
          600: '#c96a1f',
        },
        arcane: {
          400: '#9d7cf0',
          500: '#7c5ce8',
          600: '#5f3fc9',
        },
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', 'serif'],
      },
    },
  },
  plugins: [],
}

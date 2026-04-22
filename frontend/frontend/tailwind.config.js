/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#effef8',
          100: '#d9fff0',
          200: '#b6ffe2',
          300: '#7dffd0',
          400: '#3feab7',
          500: '#16c995',
          600: '#0ea77c',
          700: '#0e8665',
          800: '#116a52',
          900: '#125645',
        },
      },
      boxShadow: {
        soft: '0 10px 30px rgba(0,0,0,0.18)',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Kanit', 'sans-serif'],
        display: ['Kanit', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#f1faec',
          100: '#dff3d2',
          200: '#bfe6a5',
          300: '#94d168',
          400: '#5c8d2f',
          500: '#3f7a1c',
          600: '#2f6b14',
          700: '#256111',
          800: '#1c5210',
          900: '#13420c',
        },
      },
      boxShadow: {
        soft: '0 10px 30px rgba(0,0,0,0.08)',
        card: '0 4px 14px rgba(33, 81, 83, 0.08)',
        elevated: '0 12px 28px rgba(33, 81, 83, 0.12)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(to bottom right, #16a34a, #14532d)',
      },
    },
  },
  plugins: [],
}

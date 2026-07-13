/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#14213d',
        canvas: '#f7f8fc',
        accent: '#5b5ce2',
      },
      boxShadow: {
        panel: '0 16px 50px -28px rgba(20, 33, 61, 0.35)',
      },
    },
  },
  plugins: [],
}


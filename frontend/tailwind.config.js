/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        linkedin: {
          blue: '#0A66C2',
          darkblue: '#004182',
        },
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        imeet: {
          black: '#000000',
          panel: '#1A1B1E',
          card: '#2C2E33',
          gold: '#FFD700',
          'gold-hover': '#FFE44D',
          'gold-dim': '#B8960F',
          border: '#3A3B3F',
          'border-light': '#56595F',
          'text-primary': '#FFFFFF',
          'text-secondary': '#A0A0A0',
          'text-muted': '#6B6B6B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'imeet': '8px',
        'imeet-lg': '12px',
      },
    },
  },
  plugins: [],
}

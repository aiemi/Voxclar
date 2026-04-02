/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        imeet: {
          black: '#000000',
          panel: '#1A1A1A',
          card: '#232323',
          gold: '#FFDD02',
          'gold-hover': '#FFE84D',
          'gold-dim': '#B8960F',
          border: 'rgba(255, 255, 255, 0.12)',
          'border-light': 'rgba(255, 255, 255, 0.2)',
          'text-primary': '#FFFFFF',
          'text-secondary': 'rgba(255, 255, 255, 0.6)',
          'text-muted': 'rgba(255, 255, 255, 0.35)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'imeet': '8px',
        'imeet-lg': '12px',
        'imeet-xl': '20px',
      },
      backdropBlur: {
        'glass': '10px',
      },
    },
  },
  plugins: [],
}

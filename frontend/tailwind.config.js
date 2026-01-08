/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Neumorphic color palette
        'neu-base': '#e8ecf1',
        'neu-dark': '#d1d9e6',
        'neu-light': '#ffffff',
        'neu-shadow-dark': '#b8c5d6',
        'neu-shadow-light': '#ffffff',
        'primary': {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
      },
      boxShadow: {
        'neu-flat': '6px 6px 12px #b8c5d6, -6px -6px 12px #ffffff',
        'neu-flat-sm': '3px 3px 6px #b8c5d6, -3px -3px 6px #ffffff',
        'neu-raised': '8px 8px 16px #b8c5d6, -8px -8px 16px #ffffff',
        'neu-pressed': 'inset 4px 4px 8px #b8c5d6, inset -4px -4px 8px #ffffff',
        'neu-hover': '10px 10px 20px #b8c5d6, -10px -10px 20px #ffffff',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a0f',
        surface: '#12121a',
        'surface-2': '#1a1a26',
        border: '#2a2a3a',
        green: '#00e5a0',
        amber: '#f5a623',
        red: '#ff4757',
        blue: '#4a9eff',
        purple: '#b44aff',
        muted: '#6b6b8a',
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
import { colors } from './src/colors.js';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: colors.bg,
        surface: colors.surface,
        'surface-2': colors.surface2,
        border: colors.border,
        green: colors.green,
        amber: colors.amber,
        red: colors.red,
        blue: colors.blue,
        purple: colors.purple,
        muted: colors.muted,
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

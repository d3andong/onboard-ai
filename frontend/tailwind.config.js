/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1a2332',
          light: '#243044',
          dark: '#111826',
        },
        amber: {
          brand: '#f0a030',
          light: '#f8b84e',
          dark: '#d48a20',
        },
        bg: '#f8f7f4',
        surface: '#ffffff',
        charcoal: '#2d2d2d',
        muted: '#8c8c8c',
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        body: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

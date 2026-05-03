import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: 'var(--bg)',
          2: 'var(--bg-2)',
          3: 'var(--bg-3)',
        },
        line: 'var(--border)',
        ink: {
          DEFAULT: 'var(--text)',
          2: 'var(--text-2)',
          3: 'var(--text-3)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          bg: 'var(--accent-bg)',
        },
        danger: 'var(--danger)',
      },
      fontFamily: {
        serif: ['DM Serif Display', 'Georgia', 'serif'],
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 4px 24px oklch(16% 0.01 60 / 0.08)',
        menu: '0 8px 32px oklch(16% 0.01 60 / 0.12)',
        modal: '0 20px 60px oklch(16% 0.01 60 / 0.15)',
      },
      transitionDuration: {
        DEFAULT: '150ms',
      },
      maxWidth: {
        article: '720px',
      },
    },
  },
  plugins: [],
} satisfies Config

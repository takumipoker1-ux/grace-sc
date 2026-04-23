/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './*.html',
    './articles/*.html',
    './stores/*.html',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          gold:      '#c9a96e',
          goldLight: '#e8d5a3',
          rose:      '#c4838a',
          roseLight: '#e8b4b8',
          dark:      '#0d0d0d',
          charcoal:  '#1a1a1a',
          muted:     '#2a2520',
          line:      '#C13584',
          lineDark:  '#833AB4',
          mint:      '#a7f3d0',
          mintDark:  '#34d399',
        },
      },
      fontFamily: {
        sans:  ['"Noto Sans JP"', 'sans-serif'],
        serif: ['"Noto Serif JP"', 'serif'],
      },
    },
  },
  plugins: [],
  safelist: [
    // Classes that might be dynamically added
    'hidden',
    'block',
    'flex',
    'inline',
  ],
}

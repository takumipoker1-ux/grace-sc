/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './*.html',
    './articles/*.html',
    './stores/*.html',
    './ranking/*.html',
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
          line:      '#06C755',
          lineDark:  '#05a847',
          mint:      '#a7f3d0',
          mintDark:  '#34d399',
        },
      },
      fontFamily: {
        // 本文はOS標準の書体（Webフォントを読まない＝表示が速い）。明朝は Shippori Mincho の1書体だけ読む
        sans:  ['-apple-system', 'BlinkMacSystemFont', '"Hiragino Sans"', '"Hiragino Kaku Gothic ProN"', '"Noto Sans JP"', '"Yu Gothic UI"', 'Meiryo', 'sans-serif'],
        serif: ['"Shippori Mincho"', '"Hiragino Mincho ProN"', '"Yu Mincho"', 'serif'],
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

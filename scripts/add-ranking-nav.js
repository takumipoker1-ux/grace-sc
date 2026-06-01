#!/usr/bin/env node
/**
 * 全ページの共通ナビに「ランキング(/ranking/)」リンクを冪等に挿入する。
 * 「店舗・求人」リンクの直後に、デスクトップ/モバイルそれぞれの様式で追加する。
 *   node scripts/add-ranking-nav.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const dirs = ['.', 'stores', 'articles'];

const DESKTOP = '<a href="/ranking/" class="hover:text-white transition-colors">ランキング</a>';
const MOBILE =
  '<a href="/ranking/" class="py-4 border-b border-white/10 hover:text-[#c9a96e] transition-colors">ランキング</a>';

// 「店舗・求人」リンクのアンカー全体を捕まえる（class は active/inactive で変動するため属性は緩く拾う）
const STORE_ANCHOR = /<a href="\/stores\/index\.html"[^>]*>店舗・求人<\/a>/g;

let changed = 0;
let skipped = 0;

for (const d of dirs) {
  const abs = path.join(ROOT, d);
  if (!fs.existsSync(abs)) continue;
  for (const f of fs.readdirSync(abs)) {
    if (!f.endsWith('.html')) continue;
    const fp = path.join(abs, f);
    let html = fs.readFileSync(fp, 'utf8');
    if (html.includes('href="/ranking/"')) {
      skipped++;
      continue;
    }
    if (!STORE_ANCHOR.test(html)) {
      skipped++;
      continue;
    }
    STORE_ANCHOR.lastIndex = 0;
    html = html.replace(STORE_ANCHOR, (m) => {
      const link = m.includes('py-4') ? MOBILE : DESKTOP;
      return m + '\n        ' + link;
    });
    fs.writeFileSync(fp, html, 'utf8');
    changed++;
  }
}
console.log(`✓ ranking nav inserted: ${changed} files changed, ${skipped} skipped`);

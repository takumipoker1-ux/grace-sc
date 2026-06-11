#!/usr/bin/env node
/**
 * 全ページの共通ナビ／フッターから「ランキング(/ranking/)」リンクを除去する。
 * add-ranking-nav.js の対（リンクを一旦非表示にするときに使う）。
 *   node scripts/remove-ranking-nav.js
 *
 * 復活させたいときは add-ranking-nav.js を再実行する。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const dirs = ['.', 'stores', 'articles'];

// class は active/inactive・PC/モバイル/フッターで変動するため属性は緩く拾い、
// 行頭インデント＋アンカー＋末尾改行ごと除去する。
const RANKING_LINK = /[ \t]*<a href="\/ranking\/"[^>]*>[^<]*<\/a>\r?\n/g;

let changed = 0;
let skipped = 0;
let removed = 0;

for (const d of dirs) {
  const abs = path.join(ROOT, d);
  if (!fs.existsSync(abs)) continue;
  for (const f of fs.readdirSync(abs)) {
    if (!f.endsWith('.html')) continue;
    const fp = path.join(abs, f);
    const html = fs.readFileSync(fp, 'utf8');
    if (!html.includes('href="/ranking/"')) {
      skipped++;
      continue;
    }
    const matches = html.match(RANKING_LINK);
    const next = html.replace(RANKING_LINK, '');
    if (next !== html) {
      fs.writeFileSync(fp, next, 'utf8');
      changed++;
      removed += matches ? matches.length : 0;
    } else {
      skipped++;
    }
  }
}
console.log(`✓ ranking nav removed: ${changed} files changed (${removed} links), ${skipped} skipped`);

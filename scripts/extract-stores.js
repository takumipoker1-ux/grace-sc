#!/usr/bin/env node
/**
 * stores/*.html から storeId / 店名(h1) / エリア(og:title) を抽出し、
 * 東京/東京外に分類して一覧表示する。データ投入前の棚卸し用。
 *   node scripts/extract-stores.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const STORES = path.join(ROOT, 'stores');

// 東京23区+市部の主要エリア（夜職集積地）
const TOKYO_AREAS = [
  '新宿', '歌舞伎町', '池袋', '上野', '六本木', '銀座', '錦糸町', '神楽坂',
  '渋谷', '赤坂', '恵比寿', '中野', '北千住', '町田', '吉祥寺', '五反田', '新橋', '東京',
];

const rows = [];
for (const f of fs.readdirSync(STORES)) {
  if (!f.endsWith('.html')) continue;
  if (f.startsWith('index')) continue;
  const html = fs.readFileSync(path.join(STORES, f), 'utf8');
  const id = f.replace(/\.html$/, '');
  const h1raw = (html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || [])[1] || '';
  const h1 = h1raw.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  const ogt = (html.match(/og:title" content="([^"]+)"/) || [])[1] || '';
  // 「｜○○キャバクラ」「｜○○ラウンジ」からエリア語を拾う
  const areaM = ogt.match(/｜([^｜【]*?)(キャバクラ|ラウンジ|キャバ|クラブ)/);
  let area = areaM ? areaM[1].trim() : '';
  // 拾えなければ本文のエリアバッジから
  if (!area) {
    const badge = html.match(/rounded-full border border-\[#c9a96e\]\/20">([^<]+)<\/span>/);
    if (badge) area = badge[1].trim();
  }
  const isTokyo = TOKYO_AREAS.some((a) => area.includes(a) || ogt.includes(a + 'キャバ') || ogt.includes(a + 'ラウンジ'));
  rows.push({ id, name: h1.trim(), area, isTokyo, og: ogt });
}

const tokyo = rows.filter((r) => r.isTokyo);
const other = rows.filter((r) => !r.isTokyo);

// エリア別集計
const byArea = {};
for (const r of tokyo) byArea[r.area] = (byArea[r.area] || 0) + 1;

console.log(`総ページ: ${rows.length}`);
console.log(`東京判定: ${tokyo.length}  /  東京外・不明: ${other.length}\n`);
console.log('=== 東京エリア別 ===');
for (const [a, c] of Object.entries(byArea).sort((x, y) => y[1] - x[1])) {
  console.log(`  ${a}: ${c}`);
}
console.log('\n=== 東京外・エリア不明（要確認） ===');
const otherAreas = {};
for (const r of other) otherAreas[r.area || '(不明)'] = (otherAreas[r.area || '(不明)'] || 0) + 1;
for (const [a, c] of Object.entries(otherAreas).sort((x, y) => y[1] - x[1])) {
  console.log(`  ${a}: ${c}`);
}

// JSON も書き出して後工程で使えるように
fs.writeFileSync(
  path.join(ROOT, 'ranking', 'data', '_stores_index.json'),
  JSON.stringify({ tokyo, other }, null, 2),
  'utf8'
);
console.log('\n→ ranking/data/_stores_index.json に書き出し');

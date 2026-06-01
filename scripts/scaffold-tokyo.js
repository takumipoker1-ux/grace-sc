#!/usr/bin/env node
/**
 * _stores_index.json の東京店舗を rankings.json に流し込む（スキャフォールド）。
 * - エリア表記を正規化
 * - 既存の rankers（サンプル/実データ）は storeId で引き継ぐ
 * - データ未投入の店は rankers: [] のまま（生成側で「掲載準備中」に回る）
 *   node scripts/scaffold-tokyo.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const IDX = path.join(ROOT, 'ranking', 'data', '_stores_index.json');
const OUT = path.join(ROOT, 'ranking', 'data', 'rankings.json');

const idx = JSON.parse(fs.readFileSync(IDX, 'utf8'));
const prev = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { stores: [] };
const prevById = Object.fromEntries((prev.stores || []).map((s) => [s.storeId, s]));

// エリア正規化（部分一致を上から評価）
const AREA_RULES = [
  ['歌舞伎町', '歌舞伎町'],
  ['新宿', '新宿'],
  ['六本木', '六本木'],
  ['銀座', '銀座'],
  ['池袋', '池袋'],
  ['上野', '上野'],
  ['錦糸町', '錦糸町'],
  ['神楽坂', '神楽坂'],
];
function normArea(raw) {
  for (const [needle, label] of AREA_RULES) if (raw.includes(needle)) return label;
  return raw;
}

// タブ表示順
const AREA_ORDER = ['歌舞伎町', '新宿', '六本木', '銀座', '池袋', '上野', '錦糸町', '神楽坂'];

const stores = idx.tokyo
  .map((r) => {
    const area = normArea(r.area);
    const old = prevById[r.id];
    return {
      storeId: r.id,
      storeName: r.name,
      area,
      storePage: `/stores/${r.id}.html`,
      officialUrl: old?.officialUrl || '',
      rankers: old?.rankers || [],
    };
  })
  .sort((a, b) => {
    const ai = AREA_ORDER.indexOf(a.area);
    const bi = AREA_ORDER.indexOf(b.area);
    if (ai !== bi) return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    return a.storeName.localeCompare(b.storeName, 'ja');
  });

const out = {
  period: prev.period || '2026-06',
  prevPeriod: prev.prevPeriod || '2026-05',
  updatedAt: prev.updatedAt || '2026-06-01',
  sample: prev.sample !== undefined ? prev.sample : true,
  region: '東京',
  _note: prev._note || '各店公式サイトの月間ランキングを rankers に転記。name=源氏名 / rank=今月順位 / prevRank=先月順位(圏外/新人はnull)。',
  stores,
};

fs.writeFileSync(OUT, JSON.stringify(out, null, 2), 'utf8');

const withData = stores.filter((s) => s.rankers.length).length;
const byArea = {};
for (const s of stores) byArea[s.area] = (byArea[s.area] || 0) + 1;
console.log(`✓ rankings.json scaffolded: 東京 ${stores.length}店舗 (データ投入済 ${withData} / 準備中 ${stores.length - withData})`);
console.log('  エリア別:', Object.entries(byArea).map(([a, c]) => `${a}${c}`).join(' / '));

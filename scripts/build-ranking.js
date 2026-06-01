#!/usr/bin/env node
/**
 * GRACE RANKING ジェネレーター
 * ranking/data/rankings.json を読み込み、ranking/index.html を生成する。
 *
 * 使い方:  node scripts/build-ranking.js
 *
 * データ更新フロー:
 *   1. 各店公式サイトの月間ランキングを rankings.json に転記
 *      （name=源氏名 / rank=今月順位 / prevRank=先月順位、圏外や新人は null）
 *   2. このスクリプトを実行 → ranking/index.html が再生成される
 *   3. period を翌月に進めるときは、今月の rank を prevRank にスライドして使い回す
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DATA = path.join(ROOT, 'ranking', 'data', 'rankings.json');
const OUT = path.join(ROOT, 'ranking', 'index.html');

const SITE = 'https://grace-sc.com';
const GA_ID = 'G-E0HBTZW846';

const data = JSON.parse(fs.readFileSync(DATA, 'utf8'));

// ---- ユーティリティ ---------------------------------------------------------
const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function fmtPeriod(p) {
  const [y, m] = p.split('-');
  return `${y}年${parseInt(m, 10)}月`;
}

// 順位変動を表すバッジ情報を返す
function movement(r) {
  if (r.prevRank == null) return { type: 'new', delta: 999, label: 'NEW', cls: 'mv-new' };
  const delta = r.prevRank - r.rank; // プラス = 上昇
  if (delta > 0) return { type: 'up', delta, label: `▲${delta}`, cls: 'mv-up' };
  if (delta < 0) return { type: 'down', delta, label: `▼${-delta}`, cls: 'mv-down' };
  return { type: 'same', delta: 0, label: '—', cls: 'mv-same' };
}

// 全店舗のランカーをフラット化（店舗情報を付与）
const allRankers = [];
for (const s of data.stores) {
  for (const r of s.rankers) {
    allRankers.push({ ...r, mv: movement(r), store: s });
  }
}

// 急上昇 = 上昇幅が大きい順（NEW は別枠なので除外）
const risers = allRankers
  .filter((r) => r.mv.type === 'up')
  .sort((a, b) => b.mv.delta - a.mv.delta || a.rank - b.rank)
  .slice(0, 6);

// NEW IN = 今月新規ランクイン
const newcomers = allRankers
  .filter((r) => r.mv.type === 'new')
  .sort((a, b) => a.rank - b.rank)
  .slice(0, 6);

const periodLabel = fmtPeriod(data.period);
const prevLabel = data.prevPeriod ? fmtPeriod(data.prevPeriod) : '';
const storeCount = data.stores.length;

// データ投入済 / 準備中 で分割
const liveStores = data.stores.filter((s) => s.rankers.length);
const pendingStores = data.stores.filter((s) => !s.rankers.length);
const region = data.region || '';

// ---- 部品テンプレート -------------------------------------------------------
function shareBtn(text) {
  const url = `${SITE}/ranking/`;
  const intent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  return `<a href="${intent}" target="_blank" rel="noopener" class="share-x inline-flex items-center gap-1.5 text-xs font-bold text-white bg-black hover:bg-gray-800 border border-white/20 px-3 py-1.5 rounded-full transition-colors">
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        ポスト
      </a>`;
}

// 急上昇/NEW のハイライトカード
function highlightCard(r, accent) {
  const badge =
    r.mv.type === 'new'
      ? `<span class="text-[11px] font-extrabold tracking-wider text-emerald-300 bg-emerald-400/10 border border-emerald-400/30 px-2.5 py-1 rounded-full">NEW IN</span>`
      : `<span class="text-[11px] font-extrabold tracking-wider text-rose-200 bg-rose-500/15 border border-rose-400/30 px-2.5 py-1 rounded-full">先月${r.prevRank}位 → ${r.rank}位</span>`;
  const movePost =
    r.mv.type === 'new'
      ? `${esc(r.store.storeName)}の${periodLabel}ランキングに「${esc(r.name)}」がNEWランクイン✨ #キャバ嬢ランキング #${esc(r.store.area)}`
      : `${esc(r.store.storeName)}の${esc(r.name)}が先月${r.prevRank}位→今月${r.rank}位に急上昇📈 #キャバ嬢ランキング #${esc(r.store.area)}`;
  return `
        <div class="relative bg-gradient-to-br from-[#1a1614] to-[#14110f] border border-${accent}/30 rounded-2xl p-5 flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <span class="text-[10px] text-gray-400 font-bold tracking-widest">${esc(r.store.area)}・${esc(r.store.storeName)}</span>
            ${badge}
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-extrabold text-white leading-none">${r.rank}<span class="text-base font-bold text-gray-400">位</span></span>
            <span class="text-lg font-bold text-[#e8d5a3] truncate">${esc(r.name)}</span>
          </div>
          <div class="flex items-center justify-between mt-auto pt-1">
            <a href="${esc(r.store.storePage)}" class="text-[11px] text-[#c9a96e] hover:text-[#e8d5a3] transition-colors">店舗を見る →</a>
            ${shareBtn(movePost)}
          </div>
        </div>`;
}

// 店舗別ランキングブロック
function storeBlock(s) {
  const rows = s.rankers
    .slice()
    .sort((a, b) => a.rank - b.rank)
    .map((r) => {
      const mv = movement(r);
      const medal = r.rank === 1 ? '👑' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : '';
      const mvHtml =
        mv.type === 'new'
          ? `<span class="mv-new text-[11px] font-extrabold text-emerald-300 bg-emerald-400/10 px-2 py-0.5 rounded">NEW</span>`
          : mv.type === 'up'
          ? `<span class="mv-up text-[11px] font-extrabold text-rose-300">${mv.label}</span>`
          : mv.type === 'down'
          ? `<span class="mv-down text-[11px] font-bold text-sky-400/80">${mv.label}</span>`
          : `<span class="mv-same text-[11px] text-gray-600">—</span>`;
      return `
            <div class="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
              <span class="w-8 text-center text-base font-extrabold ${r.rank <= 3 ? 'text-[#e8d5a3]' : 'text-gray-500'}">${r.rank}</span>
              <span class="text-base">${medal}</span>
              <span class="flex-1 text-sm font-bold text-gray-100 truncate">${esc(r.name)}</span>
              <span class="w-14 text-right">${mvHtml}</span>
            </div>`;
    })
    .join('');
  const topPost = `${periodLabel}の${esc(s.storeName)}(${esc(s.area)})ランキングTOP3🏆 1位${esc(
    s.rankers.find((x) => x.rank === 1)?.name || ''
  )} #キャバ嬢ランキング #${esc(s.area)}`;
  return `
        <div class="store-rank bg-[#1a1a1a] rounded-2xl border border-white/10 overflow-hidden" data-area="${esc(s.area)}">
          <div class="flex items-center justify-between gap-2 px-5 py-3.5 bg-white/[0.03] border-b border-white/10">
            <div class="min-w-0">
              <span class="text-[10px] text-[#c9a96e] font-bold tracking-widest">${esc(s.area)}</span>
              <h3 class="text-base font-bold text-white truncate">${esc(s.storeName)}</h3>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              ${shareBtn(topPost)}
              <a href="${esc(s.storePage)}" class="text-[11px] text-gray-400 hover:text-[#c9a96e] whitespace-nowrap transition-colors">求人 →</a>
            </div>
          </div>
          <div class="px-5 py-2">
            ${rows}
          </div>
        </div>`;
}

// 掲載準備中の店舗（コンパクトなグリッド・エリア別）
function pendingSection() {
  if (!pendingStores.length) return '';
  const areasP = [...new Set(pendingStores.map((s) => s.area))];
  const groups = areasP
    .map((a) => {
      const items = pendingStores
        .filter((s) => s.area === a)
        .map(
          (s) =>
            `<a href="${esc(s.storePage)}" class="block text-xs text-gray-400 hover:text-[#c9a96e] py-1.5 px-3 bg-white/[0.02] rounded-lg border border-white/5 truncate transition-colors">${esc(
              s.storeName
            )}</a>`
        )
        .join('\n            ');
      return `
        <div>
          <h3 class="text-xs font-bold text-[#c9a96e] mb-2 tracking-wider">${esc(a)} <span class="text-gray-600 font-normal">${
        pendingStores.filter((s) => s.area === a).length
      }</span></h3>
          <div class="grid grid-cols-1 gap-1.5">
            ${items}
          </div>
        </div>`;
    })
    .join('\n');
  return `
  <section class="py-10 px-6 border-t border-white/10 bg-[#0f0f0f]">
    <div class="max-w-4xl mx-auto">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-2xl">🗓️</span>
        <div>
          <span class="text-gray-400 text-[10px] md:text-xs font-extrabold tracking-widest">COMING SOON</span>
          <h2 class="text-lg md:text-xl font-bold text-white">掲載準備中の店舗</h2>
        </div>
      </div>
      <p class="text-xs text-gray-500 mb-5">${region}主要エリアの掲載予定店舗。順次ランキングを反映していきます（全${storeCount}店舗対応）。</p>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-5">
        ${groups}
      </div>
    </div>
  </section>`;
}

// エリアタブ（データ投入済の店があるエリアのみ）
const areas = [...new Set(liveStores.map((s) => s.area))];
const areaTabs = ['すべて', ...areas]
  .map(
    (a, i) =>
      `<button class="area-tab ${i === 0 ? 'tab-active' : 'tab-inactive'} text-xs font-bold px-4 py-1.5 rounded-full border transition-colors" data-area="${esc(
        a
      )}" onclick="filterArea(this,'${esc(a)}')">${esc(a)}</button>`
  )
  .join('\n        ');

const sampleBanner = data.sample
  ? `
  <div class="bg-amber-500/10 border-b border-amber-500/30">
    <div class="max-w-4xl mx-auto px-6 py-2.5 text-center text-[11px] text-amber-300/90">
      ⚠ これはサンプルデータです。各店公式サイトの実データを <code>ranking/data/rankings.json</code> に転記し、<code>"sample": false</code> にすると本番表示になります。
    </div>
  </div>`
  : '';

const metaTitle = `${periodLabel} キャバ嬢ランキング｜店舗別・順位変動まとめ【GRACE RANKING】`;
const metaDesc = `${periodLabel}の主要キャバクラ店舗別ランキングを${storeCount}店舗分まとめて掲載。先月からの順位変動（急上昇・NEWランクイン）が一目でわかる、GRACE SELECTION独自集計のキャバ嬢ランキング。`;

const heroPost = `${periodLabel}のキャバ嬢ランキングを更新しました🏆 急上昇・NEWランクインをチェック！ #キャバ嬢ランキング #キャバクラ`;

// ---- HTML 全体 --------------------------------------------------------------
const html = `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="${esc(metaTitle)}" />
  <meta property="og:description" content="${esc(metaDesc)}" />
  <meta property="og:url" content="${SITE}/ranking/" />
  <meta property="og:site_name" content="GRACE SELECTION" />
  <meta property="og:locale" content="ja_JP" />
  <meta property="og:image" content="${SITE}/assets/ogp.jpg" />
  <meta name="twitter:image" content="${SITE}/assets/ogp.jpg" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="${esc(metaTitle)}" />
  <meta name="twitter:description" content="${esc(metaDesc)}" />
  <link rel="canonical" href="${SITE}/ranking/" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${esc(metaTitle)}</title>
  <meta name="description" content="${esc(metaDesc)}" />
  <link rel="stylesheet" href="/assets/tailwind.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&family=Noto+Serif+JP:wght@400;600&display=swap" rel="stylesheet" />
  <style>
    h1,h2,h3,h4,h5,h6 { word-break: keep-all; overflow-wrap: break-word; line-break: strict; }
    .jp-keep { word-break: keep-all; overflow-wrap: break-word; line-break: strict; }
    .jp-nobreak { display: inline-block; }
    html { scroll-behavior: smooth; }
    .card-shadow { box-shadow: 0 2px 20px rgba(0,0,0,0.5); }
    .tab-active { background: #c9a96e !important; color: #0d0d0d !important; border-color: #c9a96e !important; }
    .tab-inactive { background: #1a1a1a; color: #9ca3af; border-color: rgba(255,255,255,0.1); }
  </style>
  <link rel="icon" type="image/x-icon" href="/assets/favicon.ico" />
  <link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=${GA_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '${GA_ID}');
  </script>
  <script src="/assets/js/cta-tracker.js" defer></script>
</head>
<body class="font-sans text-gray-200 bg-[#0d0d0d]">

  <header class="fixed top-0 left-0 right-0 z-50 bg-[#0d0d0d]/95 backdrop-blur border-b border-white/10">
    <div class="max-w-5xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between gap-2">
      <a href="/index.html" class="text-[#c9a96e] font-bold text-sm md:text-base tracking-widest whitespace-nowrap shrink-0">GRACE SELECTION</a>
      <nav class="hidden sm:flex items-center gap-2.5 md:gap-6 text-xs md:text-sm font-medium text-gray-300">
        <a href="/index.html" class="hover:text-white transition-colors hidden sm:inline">トップ</a>
        <a href="/stores/index.html" class="hover:text-white transition-colors">店舗・求人</a>
        <a href="/ranking/" class="text-white font-bold transition-colors">ランキング</a>
        <a href="/articles/index.html" class="hover:text-white transition-colors">記事</a>
        <a href="/about.html" class="hover:text-white transition-colors">ぞのとは</a>
        <a href="/index.html#cta" class="bg-brand-line hover:bg-brand-lineDark text-white text-xs font-bold px-3 py-1.5 md:px-4 md:py-2 rounded transition-colors whitespace-nowrap">LINE相談</a>
      </nav>
      <button id="mobile-menu-btn" onclick="toggleMobileMenu()" class="sm:hidden text-gray-300 p-2 -mr-2" aria-label="メニューを開く">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
      </button>
    </div>
  </header>

  <div id="mobile-menu" class="hidden sm:hidden fixed inset-0 z-[60] bg-[#0d0d0d]" onclick="if(event.target.id==='mobile-menu')toggleMobileMenu()">
    <div class="flex justify-end p-3">
      <button onclick="toggleMobileMenu()" class="text-gray-300 p-2" aria-label="閉じる">
        <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>
    <nav class="px-8 pt-4 flex flex-col gap-1 text-white text-base font-medium">
      <a href="/index.html" class="py-4 border-b border-white/10 hover:text-[#c9a96e] transition-colors">トップ</a>
      <a href="/stores/index.html" class="py-4 border-b border-white/10 hover:text-[#c9a96e] transition-colors">店舗・求人</a>
      <a href="/ranking/" class="py-4 border-b border-white/10 hover:text-[#c9a96e] transition-colors">ランキング</a>
      <a href="/articles/index.html" class="py-4 border-b border-white/10 hover:text-[#c9a96e] transition-colors">記事</a>
      <a href="/about.html" class="py-4 border-b border-white/10 hover:text-[#c9a96e] transition-colors">ぞのとは</a>
      <a href="/index.html#cta" class="mt-6 bg-brand-line hover:bg-brand-lineDark text-white text-center font-bold py-4 rounded transition-colors">LINEで相談する</a>
    </nav>
  </div>
${sampleBanner}
  <!-- HERO -->
  <section class="pt-24 sm:pt-28 pb-10 px-6 bg-gradient-to-b from-[#15110a] to-[#0d0d0d] border-b border-white/10">
    <div class="max-w-4xl mx-auto text-center">
      <span class="text-[#c9a96e] text-xs font-bold tracking-[0.3em]">GRACE RANKING</span>
      <h1 class="text-2xl md:text-4xl font-bold text-white mt-3 mb-3">${periodLabel} ${region}キャバ嬢ランキング</h1>
      <p class="text-sm text-gray-400 leading-relaxed max-w-2xl mx-auto">
        ${region}主要エリアの${storeCount}店舗を網羅。${prevLabel ? `${prevLabel}からの` : ''}順位変動・急上昇・NEWランクインを独自集計でチェックできます。
      </p>
      <div class="flex items-center justify-center gap-2 mt-5 text-[11px] text-gray-500">
        <span>更新日 ${esc(data.updatedAt || data.period)}</span><span>·</span><span>${storeCount}店舗対応</span>${
  liveStores.length ? `<span>·</span><span>今月${liveStores.length}店掲載</span>` : ''
}
      </div>
      <div class="mt-5 flex justify-center">
        ${shareBtn(heroPost)}
      </div>
    </div>
  </section>

  <!-- 急上昇 -->
  ${
    risers.length
      ? `<section class="py-10 px-6 border-b border-white/10">
    <div class="max-w-4xl mx-auto">
      <div class="flex items-center gap-2 mb-5">
        <span class="text-2xl">📈</span>
        <div>
          <span class="text-rose-300 text-[10px] md:text-xs font-extrabold tracking-widest">RISING</span>
          <h2 class="text-lg md:text-xl font-bold text-white">今月の急上昇</h2>
        </div>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        ${risers.map((r) => highlightCard(r, 'rose-400')).join('\n')}
      </div>
    </div>
  </section>`
      : ''
  }

  <!-- NEW IN -->
  ${
    newcomers.length
      ? `<section class="py-10 px-6 border-b border-white/10 bg-[#0f0f0f]">
    <div class="max-w-4xl mx-auto">
      <div class="flex items-center gap-2 mb-5">
        <span class="text-2xl">✨</span>
        <div>
          <span class="text-emerald-300 text-[10px] md:text-xs font-extrabold tracking-widest">NEW IN</span>
          <h2 class="text-lg md:text-xl font-bold text-white">今月の新規ランクイン</h2>
        </div>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        ${newcomers.map((r) => highlightCard(r, 'emerald-400')).join('\n')}
      </div>
    </div>
  </section>`
      : ''
  }

  <!-- 店舗別ランキング -->
  <section class="py-10 px-6">
    <div class="max-w-4xl mx-auto">
      <div class="flex items-center gap-2 mb-5">
        <span class="text-2xl">🏆</span>
        <div>
          <span class="text-[#c9a96e] text-[10px] md:text-xs font-extrabold tracking-widest">BY STORE</span>
          <h2 class="text-lg md:text-xl font-bold text-white">店舗別ランキング</h2>
        </div>
      </div>
      <div class="flex flex-wrap gap-2 mb-6">
        ${areaTabs}
      </div>
      <div class="grid md:grid-cols-2 gap-5" id="store-grid">
        ${liveStores.length ? liveStores.map(storeBlock).join('\n') : '<p class="text-sm text-gray-500 col-span-2 py-8 text-center">ランキングデータを準備中です。</p>'}
      </div>
    </div>
  </section>

  ${pendingSection()}

  <!-- CTA -->
  <section class="py-14 px-6 bg-[#111111] border-t border-white/10">
    <div class="max-w-xl mx-auto text-center">
      <h2 class="text-xl font-bold text-white mb-2">ランキング上位を狙える店を紹介します</h2>
      <p class="text-sm text-gray-400 mb-7">「稼げる箱で上を目指したい」——あなたに合う店舗の条件交渉・体入同行まで一貫対応。まずはLINEで相談を。</p>
      <a href="/index.html#cta" class="inline-flex items-center gap-3 bg-brand-line hover:bg-brand-lineDark text-white text-sm font-bold px-8 py-4 rounded-full shadow-lg transition-all">
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
        LINEで相談する
      </a>
    </div>
  </section>

  <footer class="py-8 px-6 bg-[#0a0a0a] text-center">
    <p class="text-gray-500 text-[11px] mb-1">ランキングは各店公式サイトの公開情報をもとにGRACE SELECTIONが独自集計したものです。</p>
    <p class="text-gray-400 text-xs">© 2026 GRACE SELECTION. All rights reserved.</p>
  </footer>

  <script>
    function toggleMobileMenu(){var m=document.getElementById("mobile-menu");m.classList.toggle("hidden");document.body.style.overflow=m.classList.contains("hidden")?"":"hidden";}
    function filterArea(btn, area){
      document.querySelectorAll('.area-tab').forEach(function(b){b.classList.remove('tab-active');b.classList.add('tab-inactive');});
      btn.classList.add('tab-active');btn.classList.remove('tab-inactive');
      document.querySelectorAll('.store-rank').forEach(function(el){
        el.style.display = (area==='すべて' || el.dataset.area===area) ? '' : 'none';
      });
    }
  </script>
</body>
</html>
`;

fs.writeFileSync(OUT, html, 'utf8');
console.log(`✓ generated ${path.relative(ROOT, OUT)}`);
console.log(`  period: ${data.period}  stores: ${storeCount}  rankers: ${allRankers.length}`);
console.log(`  risers: ${risers.length}  newcomers: ${newcomers.length}`);
if (data.sample) console.log('  ⚠ sample mode ON (rankings.json: "sample": true)');

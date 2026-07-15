const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const UPDATE_DATE = '2026-07-15';
const UPDATE_DATE_JA = '2026年7月15日';

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function writeIfChanged(file, next) {
  const current = read(file);
  if (current === next) return false;
  fs.writeFileSync(file, next, 'utf8');
  return true;
}

function htmlFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.html'))
    .map((entry) => path.join(dir, entry.name));
}

function normalizeHomeLinks(html) {
  return html
    .replaceAll('href="/index.html#', 'href="/#')
    .replaceAll('href="/index.html"', 'href="/"')
    .replaceAll('href="/stores/index.html"', 'href="/stores/"')
    .replaceAll('href="/articles/index.html"', 'href="/articles/"')
    .replaceAll('https://grace-sc.com/stores/index.html', 'https://grace-sc.com/stores/')
    .replaceAll('https://grace-sc.com/articles/index.html', 'https://grace-sc.com/articles/');
}

function insertBeforeFooter(html, block) {
  const footerIndex = html.indexOf('<footer');
  if (footerIndex < 0) throw new Error('footer not found');
  return html.slice(0, footerIndex) + block + html.slice(footerIndex);
}

function articleEditorialNote(modified) {
  const date = modified
    ? modified.replace(/^(\d{4})-(\d{2})-(\d{2})$/, (_, y, m, d) => `${y}年${Number(m)}月${Number(d)}日`)
    : '更新時に記載';

  return `  <!-- EDITORIAL_NOTE_v1 -->
  <section class="py-8 px-6 bg-[#111] border-t border-white/10">
    <div class="max-w-2xl mx-auto text-xs md:text-sm text-gray-400 leading-relaxed">
      <p class="text-white font-bold mb-2">執筆・編集：ぞの</p>
      <p>この記事は、店舗訪問・面接同行・現場での聞き取りを通じて得た一次情報と、継続的な実務経験・知識をもとに、ぞの本人が執筆・編集しています。店舗条件や相場は変わるため、個別の最新情報は相談時に確認しています。</p>
      <p class="mt-3 text-gray-500">ページ更新日：${date}</p>
    </div>
  </section>
`;
}

function storeInformationNote() {
  return `  <!-- STORE_INFO_NOTE_v1 -->
  <section class="py-8 px-6 bg-[#111] border-t border-white/10">
    <div class="max-w-4xl mx-auto text-xs md:text-sm text-gray-400 leading-relaxed">
      <p class="text-white font-bold mb-2">掲載情報について</p>
      <p>掲載内容は、ぞのが店舗訪問・面接同行・現場での聞き取りを通じて蓄積した情報をもとに、本人が編集しています。時給・採用条件・営業時間などは変更される場合があるため、最新条件は相談時に確認しています。</p>
      <p class="mt-3 text-gray-500">ページ更新日：${UPDATE_DATE_JA}　※店舗への最終確認日を示すものではありません。</p>
    </div>
  </section>
`;
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

const addedRoppongiPages = [
  'ariel-roppongi.html',
  'bene-roppongi.html',
  'chic-roppongi.html',
  'daytona-morning.html',
  'daytona-roppongi.html',
  'fabric-roppongi.html',
  'jungle-second.html',
  'jungle-tokyo.html',
  'lalah-roppongi.html',
  'lucra-roppongi.html',
  'muselerva.html',
  'nova-roppongi.html',
  'nrg-morning.html',
  'nrg-roppongi.html',
  'poseidon-roppongi.html',
  'prima-tokyo.html',
  'red-dragon.html',
  'smile-roppongi.html',
  'sweet-roppongi.html',
  'unjour-tokyo.html',
  'xee-roppongi.html',
  'zoo-roppongi.html',
];

const duplicatePages = new Map([
  ['burj-roppongi.html', '/stores/bourj.html'],
  ['fabric7-roppongi.html', '/stores/fabric7.html'],
  ['kisui-roppongi.html', '/stores/hisui.html'],
]);

function storeCard(fileName) {
  const file = path.join(ROOT, 'stores', fileName);
  const html = read(file);
  const match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  if (!match) throw new Error(`h1 not found: ${fileName}`);
  const name = match[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

  return `          <!-- ${escapeHtml(name)} -->
          <div class="store-card min-w-0 bg-[#1a1a1a] rounded-xl p-4 border border-white/10 flex flex-col gap-2" data-rate="unknown">
            <div class="flex items-start justify-between gap-1 mb-0.5">
              <h3 class="min-w-0 text-sm font-bold text-white leading-snug break-all">${escapeHtml(name)}</h3>
            </div>
            <div class="flex flex-wrap gap-1">
              <span class="text-[11px] bg-white/5 text-gray-400 px-2 py-0.5 rounded-full whitespace-nowrap">条件は要問い合わせ</span>
            </div>
            <div class="flex gap-1.5 mt-auto pt-1">
              <a href="/stores/${fileName}" class="flex-1 text-center text-xs text-[#c9a96e] border border-[#c9a96e]/30 py-2.5 rounded-lg hover:bg-[#c9a96e]/10 transition-colors">詳細</a>
              <a href="/#cta" class="flex-1 text-center text-xs text-white bg-brand-line hover:bg-brand-lineDark py-2.5 rounded-lg font-bold transition-colors">相談</a>
            </div>
          </div>`;
}

function addRoppongiDirectory(html) {
  if (html.includes('ROPPONGI_STORE_DIRECTORY_v1')) {
    const markerIndex = html.indexOf('ROPPONGI_STORE_DIRECTORY_v1');
    const nextSection = html.indexOf('<!-- ========== 23', markerIndex);
    const directory = html.slice(markerIndex, nextSection);
    const missingPages = addedRoppongiPages.filter(
      (fileName) => !directory.includes(`href="/stores/${fileName}"`),
    );
    if (missingPages.length === 0) return html;

    const gridClose = html.lastIndexOf('          </div>', nextSection);
    if (gridClose < markerIndex) throw new Error('Roppongi directory grid not found');
    const cards = missingPages.map(storeCard).join('\n');
    return html.slice(0, gridClose) + cards + '\n' + html.slice(gridClose);
  }

  const sectionStart = html.indexOf('<div id="area-roppongi"');
  const nextSection = html.indexOf('<!-- ========== 23区内 ========== -->');
  if (sectionStart < 0 || nextSection < 0 || sectionStart >= nextSection) {
    throw new Error('Roppongi section boundary not found');
  }

  const closeIndex = html.lastIndexOf('</div>', nextSection);
  if (closeIndex < sectionStart) throw new Error('Roppongi closing tag not found');

  const cards = addedRoppongiPages.map(storeCard).join('\n');
  const block = `
        <!-- ROPPONGI_STORE_DIRECTORY_v1 -->
        <div class="mt-6 bg-[#111] rounded-2xl p-5 border border-white/10">
          <h3 class="text-sm font-bold text-gray-300 mb-2">六本木エリア 詳細ページ</h3>
          <p class="text-xs text-gray-500 mb-4">時給などの最新条件は相談時に確認します。</p>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
${cards}
          </div>
        </div>
      `;

  return html.slice(0, closeIndex) + block + html.slice(closeIndex);
}

function updateStoreIndex() {
  const file = path.join(ROOT, 'stores', 'index.html');
  let html = read(file);

  html = html.replace(
    /(<!--\s*セレネ（新宿）\s*-->[\s\S]{0,1200}?href=")\/stores\/serene-minamikoshigaya\.html"/,
    '$1/stores/selene-shinjuku.html"',
  );
  html = html.replace(
    /(<!--\s*ララァ（大宮）\s*-->[\s\S]{0,1200}?href=")\/stores\/lalah-roppongi\.html"/,
    '$1/stores/lalah-omiya.html"',
  );
  html = html
    .replaceAll(
      'class="store-card bg-[#1a1a1a]',
      'class="store-card min-w-0 bg-[#1a1a1a]',
    )
    .replaceAll(
      'class="text-sm font-bold text-white leading-snug"',
      'class="min-w-0 text-sm font-bold text-white leading-snug break-all"',
    )
    .replaceAll(
      'class="text-sm font-bold text-white leading-snug break-words"',
      'class="min-w-0 text-sm font-bold text-white leading-snug break-all"',
  );
  html = addRoppongiDirectory(html);
  html = normalizeHomeLinks(html);
  html = html.replace(/^[ \t]+$/gm, '');

  return writeIfChanged(file, html);
}

function updateDuplicatePage(html, canonicalPath) {
  html = html.replace(
    /<link rel="canonical" href="[^"]+"\s*\/>/,
    `<link rel="canonical" href="https://grace-sc.com${canonicalPath}" />`,
  );
  if (!html.includes('name="robots"')) {
    html = html.replace(
      /<meta charset="UTF-8"\s*\/>/,
      '<meta charset="UTF-8" />\n  <meta name="robots" content="noindex, follow" />',
    );
  }
  return html;
}

function updateStorePages() {
  let changed = 0;
  const files = htmlFiles(path.join(ROOT, 'stores')).filter((file) => path.basename(file) !== 'index.html');

  for (const file of files) {
    const fileName = path.basename(file);
    let html = read(file);

    html = html
      .replaceAll('体入時給―〜。', '体入時給は要問い合わせ。')
      .replaceAll('記載なし系の店舗。', '詳細条件は要問い合わせ。')
      .replaceAll('記載なし系。', '詳細条件は要問い合わせ。')
      .replace(/>\s*―〜\s*</g, '>要問い合わせ<')
      .replace(/>\s*―\s*</g, '>要問い合わせ<')
      .replace(/>\s*記載なし\s*</g, '>要問い合わせ<');

    if (!html.includes('STORE_INFO_NOTE_v1')) {
      html = insertBeforeFooter(html, storeInformationNote());
    }

    if (duplicatePages.has(fileName)) {
      html = updateDuplicatePage(html, duplicatePages.get(fileName));
    }

    html = normalizeHomeLinks(html);
    if (writeIfChanged(file, html)) changed += 1;
  }

  return changed;
}

function updateArticlePages() {
  let changed = 0;
  const files = htmlFiles(path.join(ROOT, 'articles')).filter((file) => path.basename(file) !== 'index.html');

  for (const file of files) {
    let html = read(file);
    const modified = html.match(/"dateModified"\s*:\s*"([^"]+)"/)?.[1] || '';

    html = html
      .replaceAll('GRACE SELECTION編集部', '執筆・編集：ぞの')
      .replaceAll('情報・マーケティングを小手先しながら', '情報・マーケティングを専攻しながら');

    if (!html.includes('EDITORIAL_NOTE_v1')) {
      html = insertBeforeFooter(html, articleEditorialNote(modified));
    }

    html = normalizeHomeLinks(html);
    if (writeIfChanged(file, html)) changed += 1;
  }

  return changed;
}

function updateOtherPages() {
  let changed = 0;
  const rootFiles = htmlFiles(ROOT).filter((file) => !path.basename(file).startsWith('google'));
  const indexFiles = [path.join(ROOT, 'articles', 'index.html')];

  for (const file of [...rootFiles, ...indexFiles]) {
    const html = normalizeHomeLinks(read(file));
    if (writeIfChanged(file, html)) changed += 1;
  }
  return changed;
}

function updateSitemap() {
  const file = path.join(ROOT, 'sitemap.xml');
  let xml = read(file);
  const excluded = [
    'googleb7555c33fff78856.html',
    'stores/burj-roppongi.html',
    'stores/fabric7-roppongi.html',
    'stores/kisui-roppongi.html',
  ];

  for (const suffix of excluded) {
    const escaped = suffix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    xml = xml.replace(new RegExp(`^\\s*<url><loc>https://grace-sc\\.com/${escaped}</loc>.*?</url>\\r?\\n`, 'm'), '');
  }

  xml = xml.replace('https://grace-sc.com/index.html', 'https://grace-sc.com/');
  xml = xml.replace('https://grace-sc.com/stores/index.html', 'https://grace-sc.com/stores/');
  xml = xml.replace('https://grace-sc.com/articles/index.html', 'https://grace-sc.com/articles/');
  xml = xml.replace(/<lastmod>[^<]+<\/lastmod>/g, '');
  xml = xml.replace(/(<loc>[^<]+<\/loc>)/g, `$1<lastmod>${UPDATE_DATE}</lastmod>`);
  xml = xml
    .replace(/<\/url>\s*<url>/g, '</url>\n  <url>')
    .replace(/\r\n/g, '\n');

  return writeIfChanged(file, xml);
}

const result = {
  storePages: updateStorePages(),
  articlePages: updateArticlePages(),
  otherPages: updateOtherPages(),
  storeIndex: updateStoreIndex(),
  sitemap: updateSitemap(),
};

console.log(JSON.stringify(result, null, 2));

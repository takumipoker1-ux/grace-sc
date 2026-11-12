// 各ページを手元のサーバーで開き、Shippori Mincho が指定されている文字を太さ別に集める。読むだけ。
// 使い方: node collect_chars.mjs <サイトのフォルダ> <出力.json> [ポート]
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';

const root = process.argv[2];
const out = process.argv[3];
const base = 'http://127.0.0.1:' + (process.argv[4] || '8765') + '/';
const SKIP_DIR = new Set(['node_modules', '.git', 'okujo', 'scripts', 'src']);
const pages = [];
(function walk(d) {
  for (const f of readdirSync(d)) {
    const p = join(d, f);
    if (statSync(p).isDirectory()) { if (!SKIP_DIR.has(f)) walk(p); }
    else if (f.endsWith('.html')) pages.push(relative(root, p).split('\\').join('/'));
  }
})(root);

const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const port = 9336;
const profile = mkdtempSync(join(tmpdir(), 'fontchars-'));
const proc = spawn(chrome, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--window-size=412,823', '--no-first-run', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function target() {
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/json`); const j = await r.json(); const p = j.find(x => x.type === 'page'); if (p) return p.webSocketDebuggerUrl; } catch {}
    await sleep(250);
  }
  throw new Error('chrome not reachable');
}
const ws = new WebSocket(await target());
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map(); let loaded = null;
ws.addEventListener('message', m => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result || { error: d.error }); pending.delete(d.id); }
  if (d.method === 'Page.loadEventFired' && loaded) { loaded(); loaded = null; }
});
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 412, height: 823, deviceScaleFactor: 1, mobile: true });
// 外部（Google Fonts・GA など）は読まない
await send('Network.enable');
await send('Network.setBlockedURLs', { urls: ['*googleapis.com*', '*gstatic.com*', '*googletagmanager.com*', '*google-analytics.com*'] });

const JS = `(() => {
  const res = {};
  const add = (w, s) => { if (!s) return; (res[w] = res[w] || new Set()); for (const ch of s) res[w].add(ch); };
  const isMin = cs => /^\\s*["']?Shippori Mincho/.test(cs.fontFamily);
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = tw.nextNode())) {
    const p = n.parentElement; if (!p) continue;
    const tag = p.tagName; if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') continue;
    const cs = getComputedStyle(p);
    if (isMin(cs)) add(cs.fontWeight, n.nodeValue);
  }
  for (const el of document.body.querySelectorAll('*')) {
    for (const ps of ['::before', '::after']) {
      const cs = getComputedStyle(el, ps);
      if (cs.content && cs.content !== 'none' && cs.content !== 'normal' && isMin(cs)) add(cs.fontWeight, cs.content.replace(/^"|"$/g, ''));
    }
    if ((el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && isMin(getComputedStyle(el))) add(getComputedStyle(el).fontWeight, (el.placeholder || '') + (el.value || ''));
  }
  const o = {}; for (const k in res) o[k] = [...res[k]].join('');
  return JSON.stringify(o);
})()`;

const total = {}; const perPage = {};
for (const pg of pages) {
  const done = new Promise(r => { loaded = r; });
  await send('Page.navigate', { url: base + pg });
  await Promise.race([done, sleep(8000)]);
  await sleep(250);
  const r = await send('Runtime.evaluate', { returnByValue: true, expression: JS });
  let o = {};
  try { o = JSON.parse(r.result.value); } catch { console.log('読めない:', pg, JSON.stringify(r).slice(0, 200)); }
  let cnt = 0;
  for (const w in o) { total[w] = total[w] || new Set(); for (const ch of o[w]) { total[w].add(ch); cnt++; } }
  perPage[pg] = cnt;
}
const res = {}; for (const w in total) res[w] = [...total[w]].sort().join('');
writeFileSync(out, JSON.stringify({ pages: pages.length, weights: res, perPage }, null, 1), 'utf8');
const all = new Set(); for (const w in res) for (const ch of res[w]) all.add(ch);
console.log('ページ数', pages.length, '/ 太さ別の文字数', Object.fromEntries(Object.entries(res).map(([w, s]) => [w, [...s].length])), '/ 全体', all.size);
console.log('文字が0のページ', Object.entries(perPage).filter(([, c]) => c === 0).map(([p]) => p).join(', ') || 'なし');
ws.close(); proc.kill();
process.exit(0);

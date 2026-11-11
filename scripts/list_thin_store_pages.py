# -*- coding: utf-8 -*-
"""店舗ページのうち、中身が薄いもの（noindex の候補）を一覧にする（2026-11-11）

読むだけで、ページは書き換えない。
見るのは2つ:
  - 条件表で「要問い合わせ」等ではない、実際の値が入っている項目の数
  - 店の説明の文章の長さ（「店舗の特徴」などの段落。条件表・Q&A・共通の案内文は数えない）
判定（このスクリプトで決めた目安。Google の基準ではない）:
  候補A: 体入時給も本入時給も値が無く、実際の値が入っている項目が 8 個以下で、説明の文章が 300 字未満
  候補B: 候補A ではないが、説明の文章が 80 字未満で、実際の値が入っている項目が 10 個以下

使い方:
  PYTHONIOENCODING=utf-8 python scripts/list_thin_store_pages.py            # 画面に出す
  PYTHONIOENCODING=utf-8 python scripts/list_thin_store_pages.py --md 出力先.md
"""
import glob, io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = re.compile(r'<span class="text-gray-500 shrink-0 pr-3">(.*?)</span>\s*<span[^>]*>(.*?)</span>', re.S)
TILE = re.compile(r'<div class="text-xs text-gray-500 mb-1">(.*?)</div>\s*<div[^>]*>(.*?)</div>', re.S)
SKIP = {'', '-', '―', 'ー', '要問い合わせ', '要相談', '応相談', '要確認', '不明', '店舗による'}


def text(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def analyze(page):
    name = text(re.sub(r'<span[^>]*>.*?</span>', '', (re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S) or [None, ''])[1], flags=re.S))
    d = {}
    for k, v in TILE.findall(page) + ROW.findall(page):
        k, v = text(k), text(v)
        if k and k not in d:
            d[k] = v
    real = [k for k, v in d.items() if v not in SKIP and not v.startswith('要問い合わせ')]
    wage = any(k in real for k in ('体入時給', '本入時給', '体入・本入時給', '時給'))
    # 説明の文章：main の <p> のうち、共通の案内文・Q&A・掲載情報を除いたもの
    body = re.sub(r'<!-- STORE_FAQ_v1 -->.*?<!-- /STORE_FAQ_v1 -->', '', page, flags=re.S)
    body = re.sub(r'<!-- STORE_INFO_NOTE_v1 -->.*', '', body, flags=re.S)
    body = body[body.find('</h1>'):] if '</h1>' in body else body
    paras = [text(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', body, re.S)]
    paras = [p for p in paras if p and 'GRACE SELECTIONでは' not in p and '条件交渉・同行対応' not in p and '詳細な条件はLINE' not in p]
    # 条件表の値をそのまま段落にしたもの（ノルマ・ペナルティ）は説明に数えない
    norma = re.search(r'<h[23][^>]*>\s*ノルマ・ペナルティ\s*</h[23]>\s*<p[^>]*>(.*?)</p>', body, re.S)
    if norma and text(norma.group(1)) in paras:
        paras.remove(text(norma.group(1)))
        if text(norma.group(1)) not in SKIP:
            real.append('ノルマ・ペナルティ')
    desc_len = sum(len(p) for p in paras)
    if not wage and len(real) <= 8 and desc_len < 300:
        grade = 'A'
    elif desc_len < 80 and len(real) <= 10:
        grade = 'B'
    else:
        grade = ''
    return dict(name=name, real=len(real), total=len(d), wage=wage, desc=desc_len, grade=grade)


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'stores', '*.html'))):
        f = os.path.basename(p)
        if f == 'index.html':
            continue
        page = io.open(p, encoding='utf-8').read()
        r = analyze(page)
        r['file'] = f
        r['noindex'] = bool(re.search(r'<meta name="robots" content="[^"]*noindex', page))
        rows.append(r)
    a = [r for r in rows if r['grade'] == 'A']
    b = [r for r in rows if r['grade'] == 'B']
    out = []
    out.append('# 店舗ページ：noindex の候補（%d ページ中）' % len(rows))
    out.append('')
    out.append('- 候補A（時給の値が無く、値のある項目が8個以下で、説明が300字未満）: %d ページ' % len(a))
    out.append('- 候補B（説明の文章が80字未満で、値のある項目が10個以下）: %d ページ' % len(b))
    out.append('- どちらでもない: %d ページ' % (len(rows) - len(a) - len(b)))
    out.append('- すでに noindex のページ: %d' % sum(r['noindex'] for r in rows))
    for title, lst in (('候補A', a), ('候補B', b)):
        out.append('')
        out.append('## ' + title)
        out.append('')
        out.append('| ページ | 店名 | 値のある項目 | 時給の値 | 説明の字数 |')
        out.append('|---|---|---|---|---|')
        for r in sorted(lst, key=lambda r: (r['real'], r['desc'])):
            out.append('| %s | %s | %d / %d | %s | %d |' % (r['file'], r['name'], r['real'], r['total'], 'あり' if r['wage'] else 'なし', r['desc']))
    res = '\n'.join(out) + '\n'
    if '--md' in sys.argv:
        dst = sys.argv[sys.argv.index('--md') + 1]
        io.open(dst, 'w', encoding='utf-8', newline='\n').write(res)
        print('書き出し:', dst, '/ 候補A', len(a), '候補B', len(b), '対象外', len(rows) - len(a) - len(b))
    else:
        print(res)
    # 分布（しきい値を見直すとき用）
    import collections
    c = collections.Counter(min(r['real'], 20) for r in rows)
    print('値のある項目の数の分布:', sorted(c.items()))
    print('時給の値あり:', sum(r['wage'] for r in rows), '/ 説明80字未満:', sum(r['desc'] < 80 for r in rows))


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""店舗ページに「よくある質問」を入れる（2026-11-11）

- stores/*.html の条件表（ページに既に載っている値）だけを使って、検索される疑問文の形の Q&A を作る。
- 値が「要問い合わせ」などの項目は質問ごと出さない。ページに無い内容は書かない。
- 何度実行しても同じ結果になる（既にある Q&A は作り直す）。
- 3問に満たないページには入れない。

使い方:
  PYTHONIOENCODING=utf-8 python scripts/add_store_faq.py          # 全店舗ページ
  PYTHONIOENCODING=utf-8 python scripts/add_store_faq.py --dry    # 書き込まずに件数だけ
"""
import glob, html, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry' in sys.argv
TODAY_JP = '2026年11月11日'

ROW = re.compile(r'<span class="text-gray-500 shrink-0 pr-3">(.*?)</span>\s*<span[^>]*>(.*?)</span>', re.S)
TILE = re.compile(r'<div class="text-xs text-gray-500 mb-1">(.*?)</div>\s*<div[^>]*>(.*?)</div>', re.S)
NORMA = re.compile(r'<h[23][^>]*>\s*ノルマ・ペナルティ\s*</h[23]>\s*<p[^>]*>(.*?)</p>', re.S)
H1 = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
FAQ_BLOCK = re.compile(r'[ \t]*<!-- STORE_FAQ_v1 -->.*?<!-- /STORE_FAQ_v1 -->\n?', re.S)
FAQ_LD = re.compile(r'[ \t]*<script type="application/ld\+json" data-faq="1">.*?</script>\n?', re.S)

SKIP = {'', '-', '―', 'ー', '要問い合わせ', '要相談', '応相談', '要確認', '不明', '店舗による'}
NONE = {'なし', '無し', '無', 'ナシ', '特になし'}


def text(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'^[◯○◎]\s*', '', s)
    return s.rstrip('。')


def real(v):
    return v is not None and v not in SKIP and not v.startswith('要問い合わせ')


def pick(d, *labels):
    for k in labels:
        if real(d.get(k)):
            return d[k]
    return None


def build(page):
    m = H1.search(page)
    if not m:
        return None, []
    name = text(re.sub(r'<span[^>]*>.*?</span>', '', m.group(1), flags=re.S))  # 見出し内のバッジ（「ぞの激推し」等）は店名に含めない
    d = {}
    for k, v in TILE.findall(page) + ROW.findall(page):
        k, v = text(k), text(v)
        if k and k not in d:
            d[k] = v
    qa = []

    # 時給
    both = pick(d, '体入・本入時給', '時給')
    tai, hon = pick(d, '体入時給'), pick(d, '本入時給')
    if tai or hon:
        parts = []
        if tai: parts.append('体入時給は%s' % tai)
        if hon: parts.append('本入時給は%s' % hon)
        qa.append(('%sの時給はいくらですか？' % name, '、'.join(parts) + 'です。'))
    elif both:
        qa.append(('%sの時給はいくらですか？' % name, '時給は%sです。' % both))

    # 年齢
    v = pick(d, '採用年齢', '年齢')
    if v:
        qa.append(('%sは何歳まで働けますか？' % name, '採用年齢は%sです。' % v))
    v = pick(d, '未成年')
    if v:
        if v.startswith('不可'):
            a = '働けません。未成年は%sです。' % v
        elif v.startswith('可'):
            a = '働けます。未成年は%sです。' % v
        else:
            a = '未成年は%sです。' % v
        qa.append(('%sは18歳・19歳でも働けますか？' % name, a))

    # 日払い
    v = pick(d, '日払い上限', '日払い')
    if v:
        v = re.sub(r'^上限\s*', '', v)
        qa.append(('%sは日払いできますか？' % name, '日払いの上限は%sです。' % v if not v.startswith('あり') else '日払いは%sです。' % v))

    # ノルマ・罰金
    m = NORMA.search(page)
    norma = text(m.group(1)) if m else None
    if not real(norma):
        parts = []
        for k in ('ノルマ', '全ノルマ', '指名・出勤ノルマ', '指名・出勤・イベントノルマ', '出勤ノルマ', '指名ノルマ', '同伴ノルマ', '遅刻', '当日欠勤', '無断欠勤', '当欠・無欠'):
            if real(d.get(k)):
                parts.append('%s:%s' % (k, d[k]))
        norma = ' / '.join(parts) if parts else None
    if real(norma):
        qa.append(('%sにノルマや罰金はありますか？' % name, norma + '。'))

    # 送り
    v = pick(d, '送り')
    if v:
        a = '送りはありません。' if v in NONE else '送りは次のとおりです。%s。' % v
        qa.append(('%sに送り（送迎）はありますか？' % name, a))

    # 寮
    v = pick(d, '寮')
    if v:
        if v in NONE:
            a = '寮はありません。'
        elif v in ('あり', '有り', '有'):
            a = '寮があります。'
        else:
            a = '寮は「%s」です。' % v
        qa.append(('%sに寮はありますか？' % name, a))

    # タトゥー・傷
    parts = []
    both = pick(d, 'タトゥー・リスカ', 'タトゥー・傷', '傷・タトゥー')
    if both:
        parts.append('タトゥー・傷跡は%s' % both)
    else:
        t, r = pick(d, 'タトゥー'), pick(d, 'リスカ・傷', 'リスカ')
        if t: parts.append('タトゥーは%s' % t)
        if r: parts.append('リスカ・傷跡は%s' % r)
    if parts:
        qa.append(('%sはタトゥーや傷跡があっても働けますか？' % name, '、'.join(parts) + 'です。'))

    # 保証期間
    v = pick(d, '保証期間')
    if v:
        qa.append(('%sの時給保証はいつまでですか？' % name, '保証期間は%sです。' % v))

    # 給料日
    v = pick(d, '給与日', '給料日', '給与')
    if v:
        qa.append(('%sの給料日はいつですか？' % name, '給料日は%sです。' % v))

    # 引かれもの
    tax, hik = pick(d, '税金・控除', '税金'), pick(d, '主な引かれもの', '引かれもの')
    if tax or hik:
        parts = []
        if tax: parts.append('税金・控除は%s' % tax)
        if hik: parts.append('引かれものは%s' % re.sub(r'^引かれもの[:：]\s*', '', hik))
        qa.append(('%sで給料から引かれるものは何ですか？' % name, '。'.join(parts) + '。'))

    # バック
    v = pick(d, '主なバック')
    if v:
        qa.append(('%sのバックはいくらですか？' % name, '主なバックは次のとおりです。%s。' % v))

    # 営業時間
    t, c = pick(d, '営業時間'), pick(d, '定休日')
    if t:
        a = '営業時間は%sです。' % t + ('定休日は%sです。' % c if c and c not in NONE else '')
        qa.append(('%sの営業時間は何時から何時までですか？' % name, a))

    return name, qa


def render(name, qa):
    rows = '\n'.join('        <dt>%s</dt>\n        <dd>%s</dd>' % (q, a) for q, a in qa)
    return ('  <!-- STORE_FAQ_v1 -->\n'
            '  <section class="py-10 px-6 border-t border-white/10">\n'
            '    <div class="max-w-4xl mx-auto">\n'
            '      <h2 class="text-base font-bold text-white mb-4">%sのよくある質問</h2>\n'
            '      <dl class="store-faq">\n%s\n      </dl>\n'
            '      <p class="store-faq-note">条件は変わることがあります。最新の内容は相談のときに確認しています。</p>\n'
            '    </div>\n'
            '  </section>\n'
            '  <!-- /STORE_FAQ_v1 -->\n') % (name, rows)


def render_ld(qa):
    data = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': html.unescape(q), 'acceptedAnswer': {'@type': 'Answer', 'text': html.unescape(a)}} for q, a in qa]}
    return '  <script type="application/ld+json" data-faq="1">%s</script>\n' % json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def main():
    done, skipped, counts = 0, [], []
    for p in sorted(glob.glob(os.path.join(ROOT, 'stores', '*.html'))):
        if os.path.basename(p) == 'index.html':
            continue
        raw = io.open(p, encoding='utf-8', newline='').read()
        nl = '\r\n' if '\r\n' in raw else '\n'
        s = raw.replace('\r\n', '\n')
        s = FAQ_BLOCK.sub('', s)
        s = FAQ_LD.sub('', s)
        name, qa = build(s)
        if len(qa) < 3:
            skipped.append((os.path.basename(p), len(qa)))
        else:
            i = s.find('<!-- AREA_LINKS_v1 -->')
            if i < 0:
                i = s.find('<!-- STORE_INFO_NOTE_v1 -->')
            if i < 0:
                skipped.append((os.path.basename(p), 'no anchor'))
                continue
            i = s.rfind('\n', 0, i) + 1
            s = s[:i] + render(name, qa) + '\n' + s[i:]
            s = s.replace('</head>', render_ld(qa) + '</head>', 1)
            s = re.sub(r'ページ更新日：\d+年\d+月\d+日', 'ページ更新日：' + TODAY_JP, s)
            done += 1
            counts.append(len(qa))
        out = s.replace('\n', nl)
        if out != raw and not DRY:
            io.open(p, 'w', encoding='utf-8', newline='').write(out)
    print('入れたページ', done, '/ 平均の問数', round(sum(counts) / max(1, len(counts)), 1), '/ 最少', min(counts or [0]), '最多', max(counts or [0]))
    print('入れなかったページ', skipped)


if __name__ == '__main__':
    main()

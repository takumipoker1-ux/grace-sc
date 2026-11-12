# -*- coding: utf-8 -*-
"""各ページの Google Fonts（Shippori Mincho）の読み込みを、assets/fonts/ の自前のファイルに置き換える（2026-11-13）

置き換えるのは head の4行（preconnect 2行・css2 の link・noscript の link）。
書体・太さ・display=optional（表示のあとで書体が切り替わらない）は変えない。
何度回しても同じ結果になる。okujo/ は別の書体を読んでいるので触らない。

使い方:
  python scripts/apply_selfhost_font.py            # サイト全体を書き換える
  python scripts/apply_selfhost_font.py --root <別のフォルダ>   # 試し用の写しを書き換える
  python scripts/apply_selfhost_font.py --dry      # 件数だけ出す
"""
import io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIR = {'node_modules', '.git', 'okujo'}
# 太さごとに2つ。先に書いた「予備」（集めた文字に無い漢字）は、その字がページに出たときだけ読まれる。
FACE = ''.join(
    "@font-face{font-family:'Shippori Mincho';font-style:normal;font-weight:%s;font-display:optional;"
    "src:url(/assets/fonts/ShipporiMincho-%s-ext.woff2) format('woff2');unicode-range:U+4E00-9FFF}"
    "@font-face{font-family:'Shippori Mincho';font-style:normal;font-weight:%s;font-display:optional;"
    "src:url(/assets/fonts/ShipporiMincho-%s.woff2) format('woff2')}" % (w, w, w, w) for w in ('500', '600', '700'))
BLOCK = '<style>/* SELF_FONT_v1 */' + FACE + '</style>'
PRE = re.compile(r'[ \t]*<link rel="preconnect" href="https://fonts\.(?:googleapis|gstatic)\.com"[^>]*>\r?\n')
LINK = re.compile(r'<link href="https://fonts\.googleapis\.com/css2\?family=Shippori\+Mincho[^"]*" rel="stylesheet" media="print" onload="this\.media=\'all\'" ?/?>')
NOS = re.compile(r'[ \t]*<noscript><link href="https://fonts\.googleapis\.com/css2\?family=Shippori\+Mincho[^"]*" rel="stylesheet" ?/?></noscript>\r?\n')
OLD = re.compile(r'<style>/\* SELF_FONT_v1 \*/.*?</style>', re.S)


def main():
    root = sys.argv[sys.argv.index('--root') + 1] if '--root' in sys.argv else ROOT
    dry = '--dry' in sys.argv
    changed = same = rest = 0
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIR]
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(d, f)
            s = io.open(p, encoding='utf-8', newline='').read()
            t = s
            if LINK.search(t):
                t = LINK.sub(lambda m: BLOCK, t, count=1)
                t = NOS.sub('', t)
                t = PRE.sub('', t)
            elif OLD.search(t):
                t = OLD.sub(lambda m: BLOCK, t, count=1)
            if 'fonts.googleapis.com' in t or 'fonts.gstatic.com' in t:
                rest += 1
                print('Google Fonts の記述が残る:', os.path.relpath(p, root))
            if t != s:
                changed += 1
                if not dry:
                    io.open(p, 'w', encoding='utf-8', newline='').write(t)
            elif 'SELF_FONT_v1' in t:
                same += 1
    print('書き換え %d / 置き換え済みで変更なし %d / Google Fonts の記述が残る %d%s' % (changed, same, rest, '（--dry：書き込んでいない）' if dry else ''))


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""Shippori Mincho を、サイトで使っている文字だけに削って assets/fonts/ に書き出す（2026-11-13）

なぜ: Google Fonts の定義ファイル（css2）は約347KBあり、ほぼ全部が使わない文字の定義。
      自分のサーバーに、使う文字だけのファイルを置けば、その読み込みが無くなる。

手順（見出しに新しい漢字が増えたら、この2つを回し直す。回さないと、その字だけ端末の明朝になる）:
  1) サイトのフォルダで手元のサーバーを立てる:  python -m http.server 8765 --bind 127.0.0.1
  2) 文字を集める:  node scripts/collect_font_chars.mjs . <chars.json の置き場> 8765
  3) 削る:          python scripts/build_font_subset.py --src <元のttfがあるフォルダ> --chars <chars.json>

元の ttf（1つ約8.6MB。サイトのフォルダには置かない）:
  https://github.com/google/fonts/tree/main/ofl/shipporimincho
  ShipporiMincho-Medium.ttf / -SemiBold.ttf / -Bold.ttf（ライセンスは SIL Open Font License 1.1）
必要な道具:  pip install fonttools brotli
"""
import argparse, io, json, os, sys
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = (('500', 'ShipporiMincho-Medium.ttf'), ('600', 'ShipporiMincho-SemiBold.ttf'), ('700', 'ShipporiMincho-Bold.ttf'))


def always():
    """集めた文字に無くても入れる文字：英数字・記号、ひらがな、カタカナ、よく使う約物"""
    s = set(chr(c) for c in range(0x20, 0x7F))
    s |= set(chr(c) for c in range(0x3041, 0x3097))   # ひらがな
    s |= set(chr(c) for c in range(0x30A1, 0x30FD))   # カタカナ（・ー を含む）
    s |= set('　、。，．・：；？！゛゜´｀¨＾￣＿ヽヾゝゞ〃仝々〆〇ー―‐／＼～∥｜…‥‘’“”（）〔〕［］｛｝〈〉《》「」『』【】＋－±×÷＝≠＜＞≦≧∞∴♂♀°′″℃￥＄％＃＆＊＠§☆★○●◎◇◆□■△▲▽▼※〒→←↑↓〜｜')
    s |= set('０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ')
    return s


def jis1_kanji():
    # JIS 第1水準の漢字（2965字）。よく使う漢字はほぼここに入る
    out = set()
    for ku in range(16, 48):
        for ten in range(1, 95):
            try:
                out.add(bytes([0xA0 + ku, 0xA0 + ten]).decode('euc_jp'))
            except UnicodeDecodeError:
                pass
    return out


def write_subset(src, dst, chars):
    opt = subset.Options()
    opt.flavor = 'woff2'
    opt.layout_features = ['*']
    opt.name_IDs = [1, 2, 3, 4, 6, 13, 14]   # 名前とライセンスの記載は残す
    opt.notdef_outline = True
    font = subset.load_font(src, opt)
    cmap = font.getBestCmap()
    missing = [c for c in chars if ord(c) not in cmap]
    sub = subset.Subsetter(opt)
    sub.populate(unicodes=[ord(c) for c in chars])
    sub.subset(font)
    subset.save_font(font, dst, opt)
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='元の ttf があるフォルダ')
    ap.add_argument('--chars', required=True, help='collect_font_chars.mjs が書き出した json')
    ap.add_argument('--out', default=os.path.join(ROOT, 'assets', 'fonts'), help='書き出し先（既定は assets/fonts）')
    a = ap.parse_args()

    data = json.load(io.open(a.chars, encoding='utf-8'))
    # 太さごとに、その太さで実際に出ている文字だけを入れる（ファイルを小さくするため）。
    # 指定が 400 の文字は 500 のファイル、800・900 の文字は 700 のファイルで表示される。
    per = {'500': always(), '600': always(), '700': always()}
    for w, s in data['weights'].items():
        n = int(w)
        key = '500' if n <= 550 else ('600' if n < 650 else '700')
        per[key] |= set(s)
    os.makedirs(a.out, exist_ok=True)
    listing = []
    for w, fname in WEIGHTS:
        chars = sorted(c for c in per[w] if ord(c) >= 0x20)
        listing.append('[%s] %s' % (w, ''.join(chars)))
        src = os.path.join(a.src, fname)
        if not os.path.exists(src):
            sys.exit('元のファイルが無い: ' + src)
        dst = os.path.join(a.out, 'ShipporiMincho-%s.woff2' % w)
        missing = write_subset(src, dst, chars)
        # 予備：集めた文字に無い第1水準の漢字。ページにその字が出たときだけ読まれる（unicode-range で指定）
        ext = sorted(jis1_kanji() - set(chars))
        ext_dst = os.path.join(a.out, 'ShipporiMincho-%s-ext.woff2' % w)
        write_subset(src, ext_dst, ext)
        print('  予備 %s: %d 字（%.1f KB）' % (os.path.basename(ext_dst), len(ext), os.path.getsize(ext_dst) / 1024.0))
        print('%s: %d 字 → %s（%.1f KB）/ 元の書体に無い字 %d: %s' % (
            w, len(chars) - len(missing), os.path.basename(dst), os.path.getsize(dst) / 1024.0, len(missing), ''.join(missing)[:60]))
    io.open(os.path.join(a.out, 'chars.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(listing) + '\n')


if __name__ == '__main__':
    main()

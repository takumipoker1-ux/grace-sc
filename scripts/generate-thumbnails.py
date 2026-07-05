# -*- coding: utf-8 -*-
"""grace-sc.com 記事サムネイル生成 v2 — 墨×金箔×一字"""
import os, re, html, sys

ROOT = r"C:/仕事/CTO/GitHub/grace-sc"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "thumbnails")

# slug: (一字, カテゴリ)
META = {
    "advice-shusha-sentaku":  ("択", "考え方"),
    "roppongi-guide":         ("六", "エリアガイド"),
    "daigakusei-scout-kachi": ("選", "スカウトの見極め"),
    "joukyou-junbi":          ("都", "はじめての夜職"),
    "iseki-timing":           ("移", "移籍・キャリア"),
    "hyakuman-kabe":          ("壁", "売上と指名"),
    "hosho-ake-kyuritsu":     ("率", "お金と制度"),
    "fuuzoku-cabaret-tenkou": ("転", "移籍・キャリア"),
    "chokin-shukan":          ("貯", "お金と制度"),
    "miken-yarubekikoto":     ("備", "はじめての夜職"),
    "kyujin-site-jouken":     ("求", "求人の読み方"),
    "area-tokuchou":          ("街", "エリアガイド"),
    "tsuki-hyakuman":         ("百", "売上と指名"),
    "toraburu-taisei":        ("守", "自衛と対処"),
    "wwork":                  ("兼", "働き方"),
    "taiken-nagare":          ("体", "はじめての夜職"),
    "mensetsu-ukaru":         ("面", "はじめての夜職"),
    "scout-mikiburi":         ("見", "スカウトの見極め"),
    "noruma-penalty":         ("制", "お金と制度"),
    "shimei-3months":         ("指", "売上と指名"),
    "kakuteishinkoku":        ("税", "お金と制度"),
    "cabaret-vs-lounge":      ("比", "業種の選び方"),
    "uriage-ageru-mindset":   ("売", "売上と指名"),
    "ueno-guide":             ("上", "エリアガイド"),
    "kabukicho-guide":        ("歌", "エリアガイド"),
    "ikebukuro-guide":        ("池", "エリアガイド"),
    "shimei-tips":            ("客", "売上と指名"),
    "ijyu-checklist":         ("確", "移籍・キャリア"),
    "hosho-shikumi":          ("保", "お金と制度"),
    "hirusyoku-barenai":      ("秘", "働き方"),
    "kinshicho-guide":        ("錦", "エリアガイド"),
    "saitama-guide":          ("埼", "エリアガイド"),
}

BREAK_CHARS = set("、。｜・ ,—」】？")   # この直後で改行OK（閉じ括弧含む）
OPENERS = set("「【（『")                  # この直前で改行OK（行末に来てはいけない）
PARTICLES = set("をはがの")

SERIF = "'Noto Serif JP','Hiragino Mincho ProN','Yu Mincho','BIZ UDPMincho',serif"
SANS = "'Noto Sans JP','Hiragino Sans','Yu Gothic','Meiryo',sans-serif"

def clean_title(t):
    """サムネ表示用にSEO付属物を刈り込む"""
    t = re.sub(r"【[^】]*】", "", t)          # 【身バレ対策】等
    t = t.split("｜")[0]                      # ｜以降のSEOサブタイトル
    t = re.split(r"——|――", t)[0]             # ダッシュ以降の補足
    t = t.strip("、 　")
    if len(t) > 26:                           # 長すぎる場合は文節で切る
        m = re.match(r"^(.{10,24}?[？。])", t)
        if m:
            t = m.group(1)
    return t

def est_width(s, fs):
    """CJK=1em / ASCII≈0.55em で行幅を推定"""
    units = sum(0.55 if ord(c) < 0x3000 else 1.0 for c in s)
    return units * fs

def split_title(t):
    """候補スコアリング式2行分割。禁則：行末に開き括弧NG・動詞途中の「が」で切らない"""
    t = t.strip()
    if len(t) <= 13:
        return t, ""
    mid = len(t) / 2
    cands = []  # (score, pos) posの直前で改行
    for i, ch in enumerate(t):
        if i == 0 or i >= len(t) - 1:
            continue
        if ch in BREAK_CHARS:
            cands.append((abs(i + 1 - mid), i + 1))
        if ch in OPENERS:
            cands.append((abs(i - mid), i))
        if ch in PARTICLES:
            nxt = t[i + 1]
            # 次がひらがなだと動詞・活用の途中（上が|らない等）→不可
            if not ("ぁ" <= nxt <= "ゟ"):
                cands.append((abs(i + 1 - mid) + 2, i + 1))
    best = min(cands)[1] if cands else int(mid)
    l1 = t[:best].rstrip("、。 　")
    l2 = t[best:].lstrip("、。 　")
    if not l1 or not l2:
        return t, ""
    return l1, l2

def font_size(n):
    if n <= 8:  return 100
    if n <= 12: return 84
    if n <= 16: return 64
    if n <= 20: return 52
    return 46

def esc(s):
    return html.escape(s, quote=True)

def make_svg(title, kanji, category):
    l1, l2 = split_title(clean_title(title))
    fs = font_size(max(len(l1), len(l2)))
    while fs > 40 and max(est_width(l1, fs), est_width(l2, fs)) > 1000:
        fs -= 4
    if l2:
        y1 = 302
        y2 = y1 + int(fs * 1.34)
        last = y2
    else:
        y1 = 348
        y2 = 0
        last = y1
    rule_y = max(last + 62, 452)
    foot_y = rule_y + 44
    # フレーム内に収める（内側下端 570）
    if foot_y > 560:
        shift = foot_y - 560
        y1 -= shift; y2 -= shift; rule_y -= shift; foot_y -= shift

    line2 = ""
    if l2:
        line2 = f'  <text x="96" y="{y2}" font-family="{SERIF}" font-size="{fs}" font-weight="600" fill="#F6F1E6" letter-spacing="2">{esc(l2)}</text>\n'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630" preserveAspectRatio="xMidYMid slice">
  <defs>
    <radialGradient id="warm" cx="26%" cy="30%" r="80%">
      <stop offset="0%" stop-color="#211A12"/>
      <stop offset="55%" stop-color="#120F0B"/>
      <stop offset="100%" stop-color="#0B0A08"/>
    </radialGradient>
    <radialGradient id="lift" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#C9A96E" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="#C9A96E" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="foil" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#F0DFAE"/>
      <stop offset="52%" stop-color="#C9A96E"/>
      <stop offset="100%" stop-color="#8E7040"/>
    </linearGradient>
    <linearGradient id="foilrule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#E8D5A3"/>
      <stop offset="100%" stop-color="#8E7040"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="630" fill="url(#warm)"/>
  <ellipse cx="985" cy="330" rx="420" ry="380" fill="url(#lift)"/>

  <!-- 一字（題材の漢字・箔ゴースト） -->
  <text x="1175" y="512" text-anchor="end" font-family="{SERIF}" font-size="560" font-weight="600" fill="url(#foil)" opacity="0.13">{esc(kanji)}</text>

  <!-- ヘアライン枠 -->
  <rect x="42" y="42" width="1116" height="546" fill="none" stroke="#C9A96E" stroke-opacity="0.34" stroke-width="1.5"/>

  <!-- カテゴリ -->
  <rect x="96" y="{y1 - fs - 74}" width="10" height="10" transform="rotate(45 101 {y1 - fs - 69})" fill="url(#foil)"/>
  <text x="122" y="{y1 - fs - 60}" font-family="{SANS}" font-size="24" letter-spacing="7" font-weight="500" fill="#C9A96E">{esc(category)}</text>

  <!-- タイトル -->
  <text x="96" y="{y1}" font-family="{SERIF}" font-size="{fs}" font-weight="600" fill="#F6F1E6" letter-spacing="2">{esc(l1)}</text>
{line2}
  <!-- ブランド -->
  <rect x="96" y="{rule_y}" width="104" height="2" fill="url(#foilrule)"/>
  <text x="96" y="{foot_y}" font-family="{SANS}" font-size="19" letter-spacing="4" font-weight="500" fill="url(#foil)">GRACE SELECTION<tspan fill="#A79E8C" letter-spacing="2" font-weight="400">　grace-sc.com</tspan></text>
</svg>
'''

def extract_title(slug):
    p = os.path.join(ROOT, "articles", slug + ".html")
    s = open(p, encoding="utf-8").read()
    m = re.search(r"(?s)<h1[^>]*>(.*?)</h1>", s)
    if not m:
        return None
    h1 = re.sub(r"<br[^>]*/?>", "", m.group(1))
    h1 = re.sub(r"<[^>]+>", "", h1)
    h1 = html.unescape(h1)
    h1 = re.sub(r"\s+", "", h1)
    return h1.strip()

os.makedirs(OUT, exist_ok=True)
n = 0
for slug, (kanji, cat) in META.items():
    title = extract_title(slug)
    if not title:
        print("WARN no h1:", slug)
        continue
    svg = make_svg(title, kanji, cat)
    with open(os.path.join(OUT, slug + ".svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    n += 1
    print(f"OK {slug}  [{kanji}|{cat}] {title[:24]}")
print(f"\ngenerated: {n}/{len(META)}")

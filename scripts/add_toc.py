#!/usr/bin/env python3
"""記事HTMLに目次（linked TOC）を追加する。

- .article-body 内の素の <h2> に id を振る（CTA用の class 付き h2 は除外）
- 最初の見出しの直前に <nav class="toc"> を挿入
- <style> ブロックに .toc 用CSSと scroll-margin-top を追記

冪等：既に nav.toc がある記事はCSS補完のみ行いスキップする。
"""
import re
import sys
from pathlib import Path

ART = Path(__file__).resolve().parent.parent / "articles"

TOC_CSS = """    .article-body h2{scroll-margin-top:5rem}
    .toc { background:#141414; border:1px solid rgba(255,255,255,0.1); border-radius:0.75rem; padding:1rem 1.25rem; margin:1rem 0 2rem; }
    .toc-title { font-size:0.75rem; font-weight:700; color:#34d399; margin-bottom:0.5rem; letter-spacing:0.1em; }
    .toc ol { list-style:decimal; margin-left:1.25rem; }
    .toc li { font-size:0.85rem; color:#d1d5db; margin:0.25rem 0; line-height:1.7; }
    .toc a { color:#d1d5db; text-decoration:none; transition:color 0.2s; }
    .toc a:hover { color:#c9a96e; }
"""

MIN_HEADINGS = 3


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def inject_css(html):
    """<style> の閉じタグ直前に TOC 用CSSを追記（未追加なら）。"""
    if ".toc-title" in html and "scroll-margin-top:5rem" in html:
        return html, False
    m = re.search(r"\n  </style>", html)
    if not m:
        return html, False
    add = TOC_CSS
    if ".toc-title" in html:  # CSSはあるが scroll-margin だけ無い
        add = "    .article-body h2{scroll-margin-top:5rem}\n"
    return html[: m.start()] + "\n" + add.rstrip("\n") + html[m.start() :], True


def process(path):
    html = path.read_text(encoding="utf-8")

    if "<nav class=\"toc\">" in html:
        html, changed = inject_css(html)
        if changed:
            path.write_text(html, encoding="utf-8")
        return "css-only" if changed else "skip(already)"

    # .article-body の範囲を特定
    bstart = html.find('<div class="article-body">')
    if bstart == -1:
        return "skip(no article-body)"

    # 素の <h2> のみ拾う（CTA h2 は class 付きなので除外される）
    heads = [m for m in re.finditer(r"<h2>(.*?)</h2>", html[bstart:], re.S)]
    if len(heads) < MIN_HEADINGS:
        return f"skip(h2={len(heads)})"

    items = []
    out = html[bstart:]
    # 後ろから id を振る（オフセットずれ防止）
    for i, m in enumerate(heads, 1):
        items.append((f"s{i}", strip_tags(m.group(1))))
    for i, m in reversed(list(enumerate(heads, 1))):
        out = out[: m.start()] + f'<h2 id="s{i}">' + out[m.start() + 4 :]

    lis = "\n".join(
        f'          <li><a href="#{hid}">{txt}</a></li>' for hid, txt in items
    )
    nav = (
        '        <nav class="toc">\n'
        '          <p class="toc-title">目次</p>\n'
        "          <ol>\n" + lis + "\n"
        "          </ol>\n"
        "        </nav>\n"
    )

    # 最初の見出し直前に挿入（行頭のインデントを保つ）
    first = re.search(r'[ \t]*<h2 id="s1">', out)
    out = out[: first.start()] + nav + out[first.start() :]

    html = html[:bstart] + out
    html, _ = inject_css(html)
    path.write_text(html, encoding="utf-8")
    return f"ok(h2={len(heads)})"


def main():
    files = sorted(p for p in ART.glob("*.html") if p.name != "index.html")
    for p in files:
        print(f"{p.name:34} {process(p)}")


if __name__ == "__main__":
    main()

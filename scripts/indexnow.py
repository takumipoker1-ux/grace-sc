# -*- coding: utf-8 -*-
"""IndexNow で「このページを更新した」とBing側へ通知する。

サイトマップに任せて待つと数日〜2週間クロールされないので、
記事を直したらこれを叩く。標準ライブラリだけで動く。

使い方:
    python scripts/indexnow.py --changed          直前のコミットで変わったHTMLを送る
    python scripts/indexnow.py --changed HEAD~3   3コミット分をまとめて送る
    python scripts/indexnow.py articles/kakuteishinkoku.html links.html
    python scripts/indexnow.py https://grace-sc.com/articles/taiken-nagare.html
    python scripts/indexnow.py --dry-run --changed   送らずに対象だけ表示

鍵はリポジトリ直下の <32桁>.txt。中身とファイル名が一致している必要があり、
公開URLとして読めることがIndexNow側の本人確認になっている（秘密情報ではない）。
"""
import glob
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "grace-sc.com"
BASE = "https://" + HOST + "/"
ENDPOINT = "https://api.indexnow.org/indexnow"


def load_key():
    """リポジトリ直下の鍵ファイルを探す。ファイル名と中身が一致するものだけ採用"""
    for path in glob.glob(os.path.join(ROOT, "*.txt")):
        name = os.path.splitext(os.path.basename(path))[0]
        if len(name) < 8 or len(name) > 128:
            continue
        with open(path, encoding="utf-8") as f:
            body = f.read().strip()
        if body == name:
            return name
    sys.exit("鍵ファイルが見つからない。リポジトリ直下に <鍵>.txt を置いて、中身も同じ鍵にすること")


def changed_html(rev):
    """指定リビジョンから今までに変わった（追加・変更された）HTMLのパス"""
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", rev, "HEAD"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if out.returncode != 0:
        sys.exit("git diff に失敗: " + (out.stderr or "").strip())
    return [p.strip() for p in out.stdout.splitlines() if p.strip().endswith(".html")]


def to_url(item):
    """リポジトリ相対パスでも絶対URLでも受ける。index.html は末尾を落とす"""
    if item.startswith("http://") or item.startswith("https://"):
        return item
    rel = item.replace("\\", "/").lstrip("/")
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    elif rel == "index.html":
        rel = ""
    return BASE + rel


def submit(urls, key):
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": BASE + key + ".txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# 200=受理 202=受理（鍵の確認待ち） それ以外は失敗
MEANING = {
    200: "受理された",
    202: "受理された（鍵の確認待ち）",
    400: "リクエストの形式が不正",
    403: "鍵が確認できない。鍵ファイルが公開URLで読めるか確認すること",
    422: "URLがhostと一致しないか、鍵が一致しない",
    429: "送りすぎ。時間を空けて再実行",
}


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv[1:]

    if args and args[0] == "--changed":
        rev = args[1] if len(args) > 1 else "HEAD~1"
        items = changed_html(rev)
        if not items:
            print("変更されたHTMLが無い。送信しない")
            return
    elif args:
        items = args
    else:
        sys.exit(__doc__)

    urls = []
    for it in items:
        u = to_url(it)
        if u not in urls:
            urls.append(u)

    print("対象 %d 件" % len(urls))
    for u in urls:
        print("  " + u)
    if dry:
        print("\n--dry-run のため送信しない")
        return

    code, body = submit(urls, load_key())
    print("\nHTTP %d  %s" % (code, MEANING.get(code, "想定外の応答")))
    if body.strip():
        print(body.strip()[:500])
    sys.exit(0 if code in (200, 202) else 1)


if __name__ == "__main__":
    main()

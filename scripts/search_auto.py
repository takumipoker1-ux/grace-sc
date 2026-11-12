# -*- coding: utf-8 -*-
"""grace-sc.com の変更を検索エンジンへ自動で伝える仕組みと、Google の登録チェック。
標準ライブラリだけで動く（pip で入れるものは無い）。

使い方:
  python scripts/search_auto.py sitemap
      Stop フックがコミットの直前に呼ぶ。本文（<body>）が変わったページの <lastmod> を今日にし、
      新しい記事・店舗ページ（noindex でなく、canonical が自分のURL）を足し、消えたページを外す。
      head だけの変更（書体・色など）では日付を変えない。
  python scripts/search_auto.py send
      Stop フックが毎回呼ぶ（数秒で終わる）。
        1. push から2分以上たった（＝公開に反映された）変更ページを IndexNow（Bing など）に送る
        2. Google にサイトマップを送り直す（鍵が無ければ保留して、鍵が置かれたら送る）
  python scripts/search_auto.py tick
      タスク スケジューラが15分ごとに呼ぶ。send と同じことに加えて、
        3. 1日1回、Google の登録状況を全ページ調べ、外れたページなどがあれば通知する（鍵が必要）
  python scripts/search_auto.py resync       コミット済みの履歴から <lastmod> を直す（取りこぼしの修正）
  python scripts/search_auto.py check        3 だけを今すぐ行う
  python scripts/search_auto.py status       いまの状態を表示する（鍵の中身は表示しない）
  python scripts/search_auto.py test-notify  通知のテスト
  --dry-run を付けると、書き込み・送信をしない。

鍵・記録・ログは ~/.grace-sc/ に置く（サイトのフォルダに置くと Stop フックで公開されるため）。
  gsc-key.json       Google のサービスアカウントの鍵。Search Console に「フル」の権限で追加しておく
  slack-webhook.txt  あれば通知を Slack に送る。無ければ Windows の通知に出す
  state.json / check_state.json / index_history.jsonl / log.txt / last_report.txt  記録（自動で作る）
"""
import base64
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.environ.get("GRACE_SC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("GRACE_SC_DATA") or os.path.join(os.path.expanduser("~"), ".grace-sc")
KEY = os.path.join(DATA, "gsc-key.json")
STATE = os.path.join(DATA, "state.json")              # 送信の記録
CHECK_STATE = os.path.join(DATA, "check_state.json")  # 登録チェックの記録（送信と同時に動いても上書きし合わないよう別ファイル）
HISTORY = os.path.join(DATA, "index_history.jsonl")
LOG = os.path.join(DATA, "log.txt")
SLACK = os.path.join(DATA, "slack-webhook.txt")
REPORT = os.path.join(DATA, "last_report.txt")

SITE = "https://grace-sc.com/"
GSC_SITE = "sc-domain:grace-sc.com"
SITEMAP_URL = SITE + "sitemap.xml"
JST = datetime.timezone(datetime.timedelta(hours=9))
NEW_PAGE_DIRS = {"articles": ("monthly", "0.7"), "stores": ("monthly", "0.8")}  # 自動で足すのはこの2つだけ
DEPLOY_WAIT = int(os.environ.get("GRACE_SC_DEPLOY_WAIT", "120"))  # push から公開に反映されるまで待つ秒数
GOOGLE_MIN_INTERVAL = 1800  # Google へのサイトマップ送信の最短間隔（秒）
NEW_PAGE_DAYS = 7           # 新しいページがこの日数たっても未登録なら通知する
CHECK_HOUR = 9              # 1日1回の登録チェックは、この時刻以降の最初の tick で行う
DRY = "--dry-run" in sys.argv
NOWIN = 0x08000000 if os.name == "nt" else 0  # 子プロセスの黒い窓を出さない
sys.dont_write_bytecode = True  # scripts/__pycache__ を作らない（作ると Stop フックで公開される）
GIT = shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"

if sys.stdout is not None:  # pythonw では None
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------- 共通
def now_jst():
    return datetime.datetime.now(JST)


def today():
    return now_jst().date().isoformat()


def log(msg):
    line = now_jst().strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line)
    if DRY:
        return
    try:
        os.makedirs(DATA, exist_ok=True)
        if os.path.exists(LOG) and os.path.getsize(LOG) > 1_000_000:
            with open(LOG, encoding="utf-8", errors="replace") as f:
                keep = f.read()[-200_000:]
            with open(LOG, "w", encoding="utf-8") as f:
                f.write(keep)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(st, path=STATE):
    if DRY:
        return
    os.makedirs(DATA, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


class Lock:
    """Stop フックとタスク スケジューラが同時に動いたとき、片方だけが進むようにする"""

    def __init__(self, name, stale=1800):
        self.path, self.stale, self.ok = os.path.join(DATA, name + ".lock"), stale, False

    def __enter__(self):
        try:
            os.makedirs(DATA, exist_ok=True)
            if os.path.exists(self.path) and time.time() - os.path.getmtime(self.path) > self.stale:
                os.remove(self.path)  # 途中で落ちた跡
            os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            self.ok = True
        except OSError:
            self.ok = False
        return self.ok

    def __exit__(self, *exc):
        if self.ok:
            try:
                os.remove(self.path)
            except OSError:
                pass


def run_git(*args):
    r = subprocess.run([GIT, *args], cwd=ROOT, capture_output=True, encoding="utf-8",
                       errors="replace", creationflags=NOWIN)
    return r.returncode, r.stdout


def git(*args):
    return run_git(*args)[1]


def name_status(*args):
    """git diff --name-status -z の結果を [(状態1文字, パス)] で返す"""
    parts = git("diff", "--name-status", "--no-renames", "-z", *args).split("\0")
    return [(parts[i][:1], parts[i + 1]) for i in range(0, len(parts) - 1, 2)]


def short(items, n=5):
    items = [("トップ" if i in ("", SITE) else i.replace(SITE, "")) for i in items]
    s = "、".join(items[:n])
    return s + ("ほか%d件" % (len(items) - n) if len(items) > n else "")


# ---------------------------------------------------------------- サイトマップ
ENTRY = re.compile(r"<url><loc>https://grace-sc\.com/([^<]*)</loc><lastmod>(\d{4}-\d{2}-\d{2})</lastmod>")


def sitemap_locs(text):
    return [m.group(1) for m in ENTRY.finditer(text)]


def file_to_loc(p):
    p = p.replace("\\", "/")
    if p == "index.html":
        return ""
    if p.endswith("/index.html"):
        return p[: -len("index.html")]
    return p


HEAD_PARTS = (r"<title\b[^>]*>.*?</title>",
              r"<meta\b[^>]*name=[\"'](?:description|robots)[\"'][^>]*>",
              r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*>",
              r"<script\b[^>]*application/ld\+json[^>]*>.*?</script>")


def signature(html):
    """検索エンジンが読む部分だけを取り出す：本文の文字・リンク先・画像、title・description・canonical・robots・構造化データ。
    CSS・フォント・class・JavaScript の変更は数えない（Google は大事な変更だけを lastmod にするよう求めている）"""
    h = html.replace("\r\n", "\n")
    m = re.search(r"<body.*?</body>", h, re.S | re.I)
    b = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ", m.group(0) if m else h, flags=re.S | re.I)
    links = re.findall(r"<a\b[^>]*href=[\"']([^\"']*)", b, re.I)
    imgs = [re.findall(r"(?:src|alt)=[\"']([^\"']*)", t, re.I) for t in re.findall(r"<img\b[^>]*>", b, re.I)]
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b)).strip()
    head = [re.sub(r"\s+", " ", x) for pat in HEAD_PARTS for x in re.findall(pat, h, re.S | re.I)]
    return json.dumps([text, links, imgs, head], ensure_ascii=False)


def indexable(html, loc):
    """noindex が無く、canonical が自分のURLを指しているページだけを本物のページとみなす"""
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        if re.search(r"name=[\"']robots[\"']", tag, re.I) and "noindex" in tag.lower():
            return False
    for tag in re.findall(r"<link\b[^>]*>", html, re.I):
        if re.search(r"rel=[\"']canonical[\"']", tag, re.I):
            m = re.search(r"href=[\"']([^\"']+)", tag, re.I)
            return bool(m) and m.group(1) == SITE + loc
    return False


def cmd_sitemap():
    path = os.path.join(ROOT, "sitemap.xml")
    try:
        mtime = os.path.getmtime(path)
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        log("sitemap: 読めない（%s）" % e)
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    day = today()
    entries = {m.group(1): m.group(2) for m in ENTRY.finditer(text)}

    changed = dict((p, st) for st, p in name_status("HEAD"))
    for p in git("ls-files", "--others", "--exclude-standard", "-z").split("\0"):
        if p:
            changed[p] = "A"

    updated, added, removed = [], [], []
    for p, st in sorted(changed.items()):
        if not p.endswith(".html"):
            continue
        loc = file_to_loc(p)
        full = os.path.join(ROOT, p)
        if st == "D" or not os.path.exists(full):
            if loc in entries:
                removed.append(loc)
            continue
        with open(full, encoding="utf-8", errors="replace") as f:
            html = f.read()
        if loc in entries:
            rc, old = run_git("show", "HEAD:" + p)
            if (rc != 0 or signature(old) != signature(html)) and entries[loc] != day:
                updated.append(loc)
        else:
            top = p.split("/", 1)[0] if "/" in p else ""
            if top in NEW_PAGE_DIRS and indexable(html, loc):
                added.append((loc, top))
    if not (updated or added or removed):
        return

    for loc in updated:
        text = text.replace("<loc>%s%s</loc><lastmod>%s</lastmod>" % (SITE, loc, entries[loc]),
                            "<loc>%s%s</loc><lastmod>%s</lastmod>" % (SITE, loc, day), 1)
    for loc in removed:
        text = re.sub(r"[ \t]*<url><loc>" + re.escape(SITE + loc) + r"</loc>.*?</url>[ \t]*\r?\n?", "", text, count=1)
    for loc, top in added:
        cf, pr = NEW_PAGE_DIRS[top]
        line = ("  <url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq>"
                "<priority>%s</priority></url>" % (SITE, loc, day, cf, pr))
        last = None
        for m in re.finditer(r"[ \t]*<url><loc>" + re.escape(SITE + top + "/") + r"[^<]*</loc>.*?</url>", text):
            last = m
        if last:
            text = text[: last.end()] + nl + line + text[last.end():]
        else:
            i = text.rfind("</urlset>")
            text = text[:i] + line + nl + text[i:]

    msg = "sitemap: 更新日を今日に %d（%s）／追加 %d（%s）／削除 %d（%s）" % (
        len(updated), short(updated), len(added), short([a for a, _ in added]), len(removed), short(removed))
    if DRY:
        log("[dry-run] " + msg)
        return
    if os.path.getmtime(path) != mtime:
        log("sitemap: 途中で別の作業が sitemap.xml を変えたので、今回は見送り")
        return
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)
    log(msg)


def cmd_resync():
    """コミット済みの履歴から <lastmod> を直す（フックを通らずに入った変更の取りこぼしを拾う）。
    サイトマップの日付より後のコミットを新しい順に見て、検索に効く部分が変わった最後の日にする"""
    path = os.path.join(ROOT, "sitemap.xml")
    mtime = os.path.getmtime(path)
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    fixed = []
    for m in list(ENTRY.finditer(text)):
        loc, lm = m.group(1), m.group(2)
        f = "index.html" if loc == "" else (loc + "index.html" if loc.endswith("/") else loc)
        for line in git("log", "--format=%H %cs", "--since=" + lm + "T23:59:59+09:00", "--", f).splitlines():
            h, d = line.split()
            rc_new, new = run_git("show", h + ":" + f)
            rc_old, old = run_git("show", h + "~1:" + f)
            if rc_new == 0 and (rc_old != 0 or signature(old) != signature(new)):
                if d > lm:
                    text = text.replace("<loc>%s%s</loc><lastmod>%s</lastmod>" % (SITE, loc, lm),
                                        "<loc>%s%s</loc><lastmod>%s</lastmod>" % (SITE, loc, d), 1)
                    fixed.append("%s %s→%s" % (label(loc), lm, d))
                break
    log("resync: %d 件%s" % (len(fixed), ("（" + "、".join(fixed[:8]) + ("ほか" if len(fixed) > 8 else "") + "）") if fixed else ""))
    if fixed and not DRY:
        if os.path.getmtime(path) != mtime:
            log("resync: 途中で別の作業が sitemap.xml を変えたので見送り")
            return
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)


# ---------------------------------------------------------------- 通知
TOAST_PS = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $x.GetElementsByTagName('text')
$t.Item(0).AppendChild($x.CreateTextNode($env:GSA_TITLE)) | Out-Null
$t.Item(1).AppendChild($x.CreateTextNode($env:GSA_BODY)) | Out-Null
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""


def notify(title, body):
    log("通知: %s / %s" % (title, body.replace("\n", " ／ ")))
    if DRY:
        return
    try:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write(now_jst().strftime("%Y-%m-%d %H:%M") + "\n" + title + "\n" + body + "\n")
    except OSError:
        pass
    if os.path.exists(SLACK):
        try:
            with open(SLACK, encoding="utf-8") as f:
                url = f.read().strip()
            req = urllib.request.Request(url, data=json.dumps({"text": "*%s*\n%s" % (title, body)}).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20).read()
            return
        except Exception as e:
            log("通知: Slack に送れなかった（%s）。Windows の通知に出す" % type(e).__name__)
    if os.name == "nt":
        env = dict(os.environ, GSA_TITLE=title, GSA_BODY=body[:250])
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", TOAST_PS], env=env,
                               capture_output=True, encoding="utf-8", errors="replace", timeout=60, creationflags=NOWIN)
            if r.returncode != 0:
                log("通知: Windows の通知を出せなかった（%s）" % r.stderr.strip()[:200])
        except Exception as e:
            log("通知: Windows の通知を出せなかった（%s）" % type(e).__name__)


def alert_once(st, kind, title, body):
    """同じ種類の警告は1日1回まで"""
    alerts = st.setdefault("alerts", {})
    if alerts.get(kind) == today():
        return
    alerts[kind] = today()
    notify(title, body)


# ---------------------------------------------------------------- Google（サービスアカウント・RS256 を標準ライブラリで署名）
def _der(buf, i):
    tag, ln = buf[i], buf[i + 1]
    i += 2
    if ln & 0x80:
        nb = ln & 0x7F
        ln = int.from_bytes(buf[i:i + nb], "big")
        i += nb
    return tag, buf[i:i + ln], i + ln


def _items(buf):
    out, i = [], 0
    while i < len(buf):
        tag, val, i = _der(buf, i)
        out.append((tag, val))
    return out


def rsa_key(pem):
    """PEM（PKCS#8 / PKCS#1）の秘密鍵から n と d を取り出す"""
    der = base64.b64decode("".join(l for l in pem.strip().splitlines() if not l.startswith("-----")))
    items = _items(_der(der, 0)[1])
    if len(items) >= 3 and items[2][0] == 0x04:  # PKCS#8 の中の PKCS#1
        items = _items(_der(items[2][1], 0)[1])
    ints = [int.from_bytes(v, "big") for t, v in items if t == 0x02]
    return ints[1], ints[3]


def rs256(data, n, d):
    """RSASSA-PKCS1-v1_5 + SHA-256 の署名"""
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(data).digest()
    k = (n.bit_length() + 7) // 8
    em = b"\x00\x01" + b"\xff" * (k - len(digest_info) - 3) + b"\x00" + digest_info
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(k, "big")


def google_token():
    with open(KEY, encoding="utf-8") as f:
        k = json.load(f)
    now = int(time.time())
    uri = k.get("token_uri") or "https://oauth2.googleapis.com/token"

    def b64(b):
        return base64.urlsafe_b64encode(b).rstrip(b"=")

    head = b64(json.dumps({"alg": "RS256", "typ": "JWT", "kid": k.get("private_key_id", "")},
                          separators=(",", ":")).encode())
    claim = b64(json.dumps({"iss": k["client_email"], "scope": "https://www.googleapis.com/auth/webmasters",
                            "aud": uri, "iat": now, "exp": now + 3600}, separators=(",", ":")).encode())
    n, d = rsa_key(k["private_key"])
    jwt = head + b"." + claim + b"." + b64(rs256(head + b"." + claim, n, d))
    data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": jwt.decode()}).encode()
    req = urllib.request.Request(uri, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        raise RuntimeError("Google の認証に失敗 HTTP %s %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))


def api(method, url, token, body=None):
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    else:
        data = b"" if method in ("PUT", "POST") else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def quote(s):
    return urllib.parse.quote(s, safe="")


def google_sitemap(st, force=False):
    """Google にサイトマップを送り直す。鍵が無い・間隔が短いときは保留にする"""
    st["google_pending"] = True
    if not os.path.exists(KEY):
        return
    if not force and time.time() - st.get("google_sent_at", 0) < GOOGLE_MIN_INTERVAL:
        return
    if DRY:
        log("[dry-run] Google: サイトマップを送信")
        return
    try:
        code, body = api("PUT", "https://www.googleapis.com/webmasters/v3/sites/%s/sitemaps/%s"
                         % (quote(GSC_SITE), quote(SITEMAP_URL)), google_token())
    except Exception as e:
        code, body = 0, "%s: %s" % (type(e).__name__, e)
    if code in (200, 204):
        st["google_sent_at"] = time.time()
        st["google_pending"] = False
        log("Google: サイトマップを送信した")
    else:
        log("Google: サイトマップの送信に失敗 HTTP %s %s" % (code, body[:300]))
        alert_once(st, "google_sitemap", "Google へのサイトマップ送信に失敗",
                   "HTTP %s。鍵と、Search Console の権限（フル）を確認。詳細は %s" % (code, LOG))


# ---------------------------------------------------------------- push 後の送信（IndexNow と Google）
def deployed_target():
    """push から DEPLOY_WAIT 秒以上たった origin/main のコミット（新しい順に見て最初のもの）"""
    now = time.time()
    for line in git("reflog", "show", "--format=%H %gd", "--date=unix", "refs/remotes/origin/main").splitlines():
        m = re.match(r"([0-9a-f]{40}) \S*@\{(\d+)\}", line)
        if m and now - int(m.group(2)) >= DEPLOY_WAIT:
            return m.group(1)
    return None


def indexnow_send(urls):
    if DRY:
        log("[dry-run] IndexNow: %d件 %s" % (len(urls), short(urls)))
        return True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import indexnow
        key = indexnow.load_key()
        code, body = indexnow.submit(urls, key)
    except SystemExit:
        log("IndexNow: 鍵ファイルが見つからない")
        return False
    except Exception as e:
        log("IndexNow: 送信できなかった（%s）" % type(e).__name__)
        return False
    ok = code in (200, 202)
    log("IndexNow: %d件 HTTP %s %s（%s）" % (len(urls), code, "受理" if ok else body[:200], short(urls)))
    return ok


def notify_changes(st):
    target = deployed_target()
    if not target:
        return
    base = st.get("notified_head")
    if not base:
        if not DRY:
            st["notified_head"] = target
        log("tick: 送信の起点を %s にした（これより前の変更は送らない）" % target[:7])
        return
    if base == target:
        return
    if run_git("merge-base", "--is-ancestor", base, target)[0] != 0:
        log("tick: 起点 %s が履歴に無いので %s から数え直す" % (base[:7], target[:7]))
        if not DRY:
            st["notified_head"] = target
        return
    cur = set(sitemap_locs(git("show", target + ":sitemap.xml")))
    prev = set(sitemap_locs(git("show", base + ":sitemap.xml")))
    urls, sitemap_changed = [], False
    for stc, p in name_status(base, target):
        if p == "sitemap.xml":
            sitemap_changed = True
        if not p.endswith(".html"):
            continue
        loc = file_to_loc(p)
        if stc == "D":
            if loc in prev:
                urls.append(SITE + loc)
        elif loc in cur:
            rc, old = run_git("show", base + ":" + p)
            if stc != "M" or rc != 0 or signature(old) != signature(git("show", target + ":" + p)):
                urls.append(SITE + loc)  # CSS・フォントだけの変更は送らない
    if urls and not indexnow_send(urls):
        fails = st.get("indexnow_fails", 0) + 1
        st["indexnow_fails"] = fails
        if fails < 8:  # 2時間ほど再挑戦する
            return
        alert_once(st, "indexnow", "IndexNow（Bing）への送信に失敗が続いている", "詳細は %s" % LOG)
    st["indexnow_fails"] = 0
    if urls or sitemap_changed:
        google_sitemap(st)
        if not os.path.exists(KEY):
            log("Google: 鍵が無いので、サイトマップの送信は保留（鍵を置いたら送る）")
    if not DRY:
        st["notified_head"] = target


# ---------------------------------------------------------------- 毎日の登録チェック
def label(loc):
    return "トップ" if loc == "" else loc


def index_check(st):
    day = today()
    st["last_check"] = day  # 失敗しても同じ日に何度も試さない
    with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as f:
        locs = sitemap_locs(f.read())
    if DRY:
        log("[dry-run] check: %d ページを調べる予定" % len(locs))
        return
    try:
        token = google_token()
    except Exception as e:
        log("check: %s" % e)
        alert_once(st, "google_token", "Google の登録チェックができない", str(e)[:200])
        return
    results, fails = {}, 0
    for loc in locs:
        req = {"inspectionUrl": SITE + loc, "siteUrl": GSC_SITE, "languageCode": "ja"}
        url = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
        code, raw = api("POST", url, token, req)
        if code == 429:
            time.sleep(60)
            code, raw = api("POST", url, token, req)
        if code != 200:
            fails += 1
            log("check: %s で HTTP %s %s" % (label(loc), code, raw[:200]))
            if code in (401, 403) or fails >= 10:
                alert_once(st, "google_inspect", "Google の登録チェックが止まった",
                           "HTTP %s。Search Console の権限を確認。詳細は %s" % (code, LOG))
                return
            continue
        r = json.loads(raw).get("inspectionResult", {}).get("indexStatusResult", {})
        results[loc] = {"on": r.get("verdict") == "PASS", "state": r.get("coverageState", ""),
                        "crawl": (r.get("lastCrawlTime") or "")[:10]}
        time.sleep(0.2)

    pages = st.setdefault("pages", {})
    first_run = not pages
    prev_on = sum(1 for p in pages.values() if p.get("on"))
    dropped, gained, stale = [], [], []
    for loc, r in results.items():
        p = pages.get(loc) or {"first": day, "baseline": first_run, "ever": False}
        if p.get("on") and not r["on"]:
            dropped.append(loc)
        if p.get("on") is False and r["on"]:
            gained.append(loc)
        if r["on"]:
            p["ever"] = True
        p.update(on=r["on"], state=r["state"], crawl=r["crawl"], checked=day)
        old_enough = (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(p["first"])).days >= NEW_PAGE_DAYS
        if not r["on"] and not p.get("baseline") and not p.get("ever") and old_enough and not p.get("alerted"):
            stale.append(loc)
            p["alerted"] = day
        pages[loc] = p
    for loc in [l for l in pages if l not in locs]:
        del pages[loc]

    n_on = sum(1 for p in pages.values() if p.get("on"))
    states = {}
    for p in pages.values():
        states[p.get("state", "")] = states.get(p.get("state", ""), 0) + 1
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps({"date": day, "total": len(pages), "indexed": n_on, "states": states},
                           ensure_ascii=False) + "\n")
    log("check: 登録 %d / %d（調べた %d・失敗 %d）" % (n_on, len(pages), len(results), fails))

    weekly = now_jst().weekday() == 0 or st.get("last_weekly", "") < (
        datetime.date.fromisoformat(day) - datetime.timedelta(days=7)).isoformat()
    lines = ["Google に登録されているページ：%d / %d%s" % (
        n_on, len(pages), "" if first_run else "（前回 %d）" % prev_on)]
    if dropped:
        lines.append("登録から外れた：" + short([label(l) for l in dropped]))
    if stale:
        lines.append("公開から%d日たっても未登録：%s" % (NEW_PAGE_DAYS, short([label(l) for l in stale])))
    if gained:
        lines.append("新しく登録された：" + short([label(l) for l in gained]))
    if first_run or dropped or stale or gained or weekly:
        if weekly:
            st["last_weekly"] = day
        notify("grace-sc.com の Google 登録チェック", "\n".join(lines))


# ---------------------------------------------------------------- コマンド
def cmd_send():
    """公開に反映された変更を IndexNow と Google に送る（Stop フックとタスクの両方から呼ぶ・数秒で終わる）"""
    with Lock("send", stale=600) as ok:
        if not ok:
            return
        st = load_state()
        notify_changes(st)
        if st.get("google_pending") and os.path.exists(KEY):
            google_sitemap(st)
        save_state(st)


def cmd_tick():
    cmd_send()
    if not os.path.exists(KEY):
        return
    with Lock("check") as ok:
        if not ok:
            return
        cst = load_state(CHECK_STATE)
        if cst.get("last_check") != today() and now_jst().hour >= CHECK_HOUR:
            index_check(cst)
            save_state(cst, CHECK_STATE)


def cmd_status():
    st, cst = load_state(), load_state(CHECK_STATE)
    sent = st.get("google_sent_at")
    print("記録の置き場       :", DATA)
    print("Google の鍵        :", "あり" if os.path.exists(KEY) else "なし（%s に置く）" % KEY)
    print("通知先             :", "Slack" if os.path.exists(SLACK) else "Windows の通知")
    print("IndexNow の起点    :", (st.get("notified_head") or "未設定")[:7])
    print("Google サイトマップ:", datetime.datetime.fromtimestamp(sent, JST).strftime("%m-%d %H:%M に送信")
          if sent else "まだ送っていない", "（保留あり）" if st.get("google_pending") else "")
    print("登録チェック       :", cst.get("last_check") or "まだ")
    pages = cst.get("pages", {})
    if pages:
        print("登録               : %d / %d" % (sum(1 for p in pages.values() if p.get("on")), len(pages)))
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8", errors="replace") as f:
            tail = f.read().splitlines()[-8:]
        print("最近のログ:\n  " + "\n  ".join(tail))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cmd = args[0] if args else ""
    if cmd == "sitemap":
        cmd_sitemap()
    elif cmd == "resync":
        cmd_resync()
    elif cmd == "send":
        cmd_send()
    elif cmd == "tick":
        cmd_tick()
    elif cmd == "check":
        if not os.path.exists(KEY):
            print("Google の鍵が無い（%s に置く）" % KEY)
            return
        with Lock("check") as ok:
            if ok:
                cst = load_state(CHECK_STATE)
                index_check(cst)
                save_state(cst, CHECK_STATE)
    elif cmd == "status":
        cmd_status()
    elif cmd == "test-notify":
        notify("grace-sc.com の自動送信", "通知のテストです。これが見えていれば、外れたページの通知もここに出ます。")
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("エラー: %s: %s" % (type(e).__name__, e))
        sys.exit(1)

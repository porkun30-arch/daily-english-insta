"""GitHub Issue / PR まわりの処理（GitHub Actions から実行。GITHUB_TOKEN と GITHUB_REPOSITORY が必要）。

  python scripts/gh_tasks.py inbox            # 体験談を inbox/experiences.md に書き出す
  python scripts/gh_tasks.py research-issue   # 最新の research/*.md から「ネタ候補」Issue を作成
  python scripts/gh_tasks.py close-used       # マージされた投稿で使った体験談 Issue を閉じる
  python scripts/gh_tasks.py pr-body BRANCH DATE...  # PR 本文を標準出力へ

ラベル：「体験談」＝つばさのメモ / 「ネタ候補」＝リサーチャーの週次 Issue
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import requests

from common import ROOT

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
HDR = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
       "Accept": "application/vnd.github+json"}
USED = ROOT / "data" / "used_experiences.json"
L_EXP, L_IDEA = "体験談", "ネタ候補"


def gh(method, path, **kw):
    r = requests.request(method, f"{API}/repos/{REPO}/{path}", headers=HDR, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub API {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def issues(label, state="open"):
    return [i for i in gh("GET", "issues", params={"labels": label, "state": state, "per_page": 100})
            if "pull_request" not in i]


def comments(num):
    return gh("GET", f"issues/{num}/comments", params={"per_page": 100})


def load_used() -> dict:
    return json.loads(USED.read_text()) if USED.exists() else {"issues": [], "comments": []}


# ---------------------------------------------------------------- inbox

def inbox():
    used = load_used()
    out = ["# 体験談の受信箱（自動生成・編集しない）", "",
           "post.json の experience に使ったら、issue / comment_id を必ず記録すること。", ""]
    for i in issues(L_EXP):
        if i["number"] in used["issues"]:
            continue
        out += [f"## 体験談Issue #{i['number']}：{i['title']}", "", (i.get("body") or "").strip()]
        for c in comments(i["number"]):
            out += ["", f"（追記）{c['body'].strip()}"]
        out += [""]
    for i in issues(L_IDEA):
        cs = [c for c in comments(i["number"]) if c["id"] not in used["comments"]
              and c["user"]["type"] != "Bot"]
        if not cs:
            continue
        out += [f"## ネタ候補Issue #{i['number']} へのコメント", ""]
        for c in cs:
            out += [f"### comment_id {c['id']}", c["body"].strip(), ""]
    path = ROOT / "inbox" / "experiences.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path}")


# ---------------------------------------------------------------- research issue

def research_issue():
    files = sorted((ROOT / "research").glob("20*.md"))
    if not files:
        print("research ファイルがありません")
        return
    latest = files[-1]
    text = latest.read_text(encoding="utf-8")
    m = re.search(r"^## 体験談の呼び水\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    prompts = m.group(1).strip() if m else "（呼び水セクションなし）"
    title = f"来週のネタ候補（{latest.stem}）"
    if any(i["title"] == title for i in issues(L_IDEA, "all")):
        print("既に作成済み")
        return
    # 古いネタ候補 Issue を閉じる。使われなかったコメントは体験談 Issue として残す
    used = load_used()
    for old in issues(L_IDEA):
        for c in comments(old["number"]):
            if c["id"] in used["comments"] or c["user"]["type"] == "Bot":
                continue
            gh("POST", "issues", json={"title": f"体験談（#{old['number']} から引き継ぎ）",
                                       "body": c["body"], "labels": [L_EXP]})
        gh("PATCH", f"issues/{old['number']}", json={"state": "closed"})
    body = (f"リサーチャーが来週のネタ候補をまとめました → [`{latest.relative_to(ROOT)}`]"
            f"(../blob/main/{latest.relative_to(ROOT).as_posix()})\n\n"
            "**心当たりがあれば、このIssueにコメントで一言書いてください。**"
            "土曜朝の生成で体験談として使います（1コメント＝1つの体験談）。\n\n" + prompts)
    r = gh("POST", "issues", json={"title": title, "body": body, "labels": [L_IDEA]})
    print(f"created #{r['number']}")


# ---------------------------------------------------------------- close used

def close_used():
    used = load_used()
    changed = False
    for f in sorted((ROOT / "queue").glob("*/post.json")):
        exp = json.loads(f.read_text(encoding="utf-8")).get("experience") or {}
        num, cid = exp.get("issue"), exp.get("comment_id")
        if cid and cid not in used["comments"]:
            used["comments"].append(cid)
            changed = True
        if num and not cid and num not in used["issues"]:
            used["issues"].append(num)
            changed = True
            try:
                gh("POST", f"issues/{num}/comments",
                   json={"body": f"{f.parent.name} の投稿で使用しました（{json.loads(f.read_text())['phrase']}）"})
                gh("PATCH", f"issues/{num}", json={"state": "closed"})
            except RuntimeError as e:
                print(f"close #{num} failed: {e}")
    if changed:
        USED.parent.mkdir(exist_ok=True)
        USED.write_text(json.dumps(used, indent=2))
        print("updated used_experiences.json")


# ---------------------------------------------------------------- PR body

def pr_body(branch: str, dates: list[str]):
    owner_repo = REPO or "OWNER/REPO"
    raw = f"https://raw.githubusercontent.com/{owner_repo}/{branch}"
    lines = ["## 来週の投稿（スマホで確認 → OKならマージ）", "",
             "- 表紙をタップすると原寸で見られます。全スライドは「Files changed」から",
             "- **体験談なし** の日は `post.json` の `experience.text` に追記してください（画像は自動で再生成されます）",
             "- 直したい点はコメントで指示 → 手元/次回の Claude Code で修正、または該当日のフォルダを削除してマージ", ""]
    for d in sorted(dates):
        f = ROOT / "queue" / d / "post.json"
        if not f.exists():
            continue
        p = json.loads(f.read_text(encoding="utf-8"))
        exp = (p.get("experience") or {}).get("text", "").strip()
        flag = "" if exp else " ⚠️ **体験談なし**"
        reel = " 🎬 リールあり" if (f.parent / "reel.mp4").exists() else ""
        lines += [f"### {d}（{p.get('genre', '')}・{p.get('level', '')}）{p['phrase']}{flag}{reel}", "",
                  f"<img src=\"{raw}/queue/{d}/01.png\" width=\"260\">", "",
                  "<details><summary>キャプション</summary>", "", p["caption"], "",
                  " ".join(p.get("hashtags", [])), "</details>", ""]
        review = f.parent / "review.md"
        if review.exists():
            lines += ["<details><summary>英語校閲のメモ</summary>", "",
                      review.read_text(encoding="utf-8").strip(), "</details>", ""]
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"inbox": inbox, "research-issue": research_issue, "close-used": close_used}.get(
        cmd, lambda: pr_body(sys.argv[2], sys.argv[3:]) if cmd == "pr-body" else sys.exit(__doc__))()

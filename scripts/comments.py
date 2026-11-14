"""直近30日の投稿についたコメントを research/comments.md にまとめる（リサーチャー用）。"""
from __future__ import annotations

import json
from datetime import date, timedelta

from common import ROOT, ig_request


def main():
    since = date.today() - timedelta(days=30)
    lines = ["# 直近30日のコメント（自動取得）", "",
             "フォロワーの質問・「〇〇って何て言うの？」はネタ候補として最優先で検討する。", ""]
    for f in sorted((ROOT / "posted").glob("*/result.json"), reverse=True):
        if date.fromisoformat(f.parent.name) < since:
            continue
        post = json.loads((f.parent / "post.json").read_text(encoding="utf-8"))
        res = json.loads(f.read_text())
        for kind, r in res.items():
            if not r.get("media_id"):
                continue
            try:
                data = ig_request("GET", f"{r['media_id']}/comments",
                                  {"fields": "text,timestamp,like_count", "limit": 100}).get("data", [])
            except RuntimeError as e:
                print(f"skip {f.parent.name} {kind}: {e}")
                continue
            if data:
                lines.append(f"## {f.parent.name} {kind}：{post['phrase']}")
                lines += [f"- {c['text'].strip()}" for c in data]
                lines.append("")
    out = ROOT / "research" / "comments.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

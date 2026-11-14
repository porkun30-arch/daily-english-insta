"""背景写真の一覧と、最後に使った日を表示する（同じ写真の使い回しを避けるため）。"""
import json

from common import ROOT

last = {}
for state in ("posted", "queue"):
    for f in sorted((ROOT / state).glob("*/post.json")):
        bg = json.loads(f.read_text(encoding="utf-8")).get("background")
        if bg:
            last[bg] = f.parent.name
exts = {".jpg", ".jpeg", ".png", ".webp"}
files = sorted(p for p in (ROOT / "templates" / "backgrounds").rglob("*") if p.suffix.lower() in exts)
if not files:
    print("templates/backgrounds/ に写真がありません（グラデーション背景になります）")
for p in files:
    rel = p.relative_to(ROOT).as_posix()
    print(f"{last.get(rel, '未使用'):<12}\t{rel}")

"""既出・予定済みのフレーズ一覧を表示する（重複防止用）。"""
import json

from common import ROOT

for state in ("posted", "queue"):
    for f in sorted((ROOT / state).glob("*/post.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        print(f"{state}\t{f.parent.name}\t{p.get('genre', '')}\t{p['phrase']}")

"""長期アクセストークン（60日有効）を延長し、新しいトークンを token.txt に書き出す。
workflow 側で `gh secret set IG_ACCESS_TOKEN < token.txt` を実行して Secret を更新する。
"""
import os
import sys

import requests

token = os.environ.get("IG_ACCESS_TOKEN")
if not token:
    sys.exit("IG_ACCESS_TOKEN が未設定です")
r = requests.get("https://graph.instagram.com/refresh_access_token",
                 params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=60)
data = r.json()
if r.status_code != 200 or "access_token" not in data:
    print(f"::error::トークン延長に失敗しました: {data}")
    sys.exit(1)
new = data["access_token"]
print(f"::add-mask::{new}")
with open("token.txt", "w") as f:
    f.write(new)
print(f"延長しました（有効期限: 約{int(data.get('expires_in', 0)) // 86400}日）")

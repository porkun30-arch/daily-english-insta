"""アクセストークンの延長。

- IGAA…（Instagram ログイン）: 60日トークンを延長し token.txt に書き出す
- EAA… （Meta 統合ログイン）: 有効期限を確認するだけ。期限が近ければ警告（再発行は手動）
"""
import os
import sys
from datetime import datetime, timezone

import requests

token = os.environ.get("IG_ACCESS_TOKEN")
if not token:
    sys.exit("IG_ACCESS_TOKEN が未設定です")

if token.startswith("EAA"):
    r = requests.get("https://graph.facebook.com/v23.0/debug_token",
                     params={"input_token": token, "access_token": token}, timeout=60)
    info = r.json().get("data", {})
    if not info.get("is_valid"):
        print(f"::error::トークンが無効です。Meta for Developers で再発行してください: {r.json()}")
        sys.exit(1)
    exp = info.get("expires_at", 0)
    if not exp:
        print("トークンは無期限です。延長は不要です。")
        sys.exit(0)
    days = (datetime.fromtimestamp(exp, timezone.utc) - datetime.now(timezone.utc)).days
    msg = f"トークンの残り日数: {days}日"
    if days < 14:
        print(f"::error::{msg}。Meta for Developers で再発行し、Secret IG_ACCESS_TOKEN を更新してください。")
        sys.exit(1)
    print(msg)
    sys.exit(0)

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

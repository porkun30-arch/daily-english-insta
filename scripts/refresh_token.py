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
    # 統合ログインのトークンは延長APIがないため、有効かどうかだけ確認する
    uid = os.environ.get("IG_USER_ID", "me")
    r = requests.get(f"https://graph.facebook.com/v23.0/{uid}",
                     params={"fields": "id,username", "access_token": token}, timeout=60)
    if r.status_code != 200:
        print(f"::error::トークンが無効か期限切れです。Meta for Developers で「トークンを生成」し直し、"
              f"Secret IG_ACCESS_TOKEN を更新してください: {r.text[:300]}")
        sys.exit(1)
    print("トークンは有効です。")
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

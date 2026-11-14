"""queue/<日付>/ の投稿を Instagram に公開する（GitHub Actions から実行）。

使い方:
    python scripts/publish.py carousel [--date YYYY-MM-DD] [--wait-until 07:00] [--dry-run]
    python scripts/publish.py reel     [--date YYYY-MM-DD] [--wait-until 21:00] [--dry-run]
    python scripts/publish.py whoami      # トークンとアカウントIDの確認

環境変数: IG_ACCESS_TOKEN, IG_USER_ID, PAGES_BASE_URL（例 https://<user>.github.io/daily-english-insta）
カルーセル公開後は queue/<日付> を posted/<日付> に移動する（コミットは workflow 側）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from common import JST, ROOT, ig_env, ig_request, load_post, today_jst


def wait_until(hhmm: str | None):
    if not hhmm:
        return
    now = datetime.now(JST)
    h, m = map(int, hhmm.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    sec = (target - now).total_seconds()
    if 0 < sec < 45 * 60:
        print(f"{hhmm} まで {int(sec)} 秒待機します")
        time.sleep(sec)


def public_url(path: Path) -> str:
    import os

    base = os.environ.get("PAGES_BASE_URL", "").rstrip("/")
    if not base:
        raise SystemExit("PAGES_BASE_URL が未設定です")
    return f"{base}/{path.relative_to(ROOT).as_posix()}"


def ensure_reachable(urls: list[str], tries: int = 20):
    """GitHub Pages のデプロイ待ち。全URLが200になるまで最大約10分待つ。"""
    for i in range(tries):
        bad = [u for u in urls if requests.head(u, timeout=30, allow_redirects=True).status_code != 200]
        if not bad:
            return
        print(f"公開URL待ち（{len(bad)}件未反映）… {i + 1}/{tries}")
        time.sleep(30)
    raise SystemExit(f"画像URLにアクセスできません: {bad[:3]}")


def wait_container(cid: str, timeout: int = 900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = ig_request("GET", cid, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"コンテナ処理失敗: {st}")
        time.sleep(10)
    raise TimeoutError(f"コンテナ処理がタイムアウト: {cid}")


def full_caption(caption: str, tags: list[str]) -> str:
    tags = tags[:5]  # Instagram の上限
    return caption.rstrip() + ("\n\n" + " ".join(tags) if tags else "")


def publish_carousel(folder: Path, dry: bool) -> dict:
    p = load_post(folder)
    images = sorted(folder.glob("[0-9][0-9].png"))
    if not 2 <= len(images) <= 20:
        raise SystemExit(f"画像枚数が不正です: {len(images)}")
    urls = [public_url(i) for i in images]
    caption = full_caption(p["caption"], p.get("hashtags", []))
    if dry:
        print(json.dumps({"images": urls, "caption": caption}, ensure_ascii=False, indent=2))
        return {}
    _, uid = ig_env()
    ensure_reachable(urls)
    children = []
    for u in urls:
        c = ig_request("POST", f"{uid}/media", {"image_url": u, "is_carousel_item": "true"})
        children.append(c["id"])
    for c in children:
        wait_container(c)
    parent = ig_request("POST", f"{uid}/media", {
        "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})
    wait_container(parent["id"])
    pub = ig_request("POST", f"{uid}/media_publish", {"creation_id": parent["id"]})
    info = ig_request("GET", pub["id"], {"fields": "permalink,timestamp"})
    return {"media_id": pub["id"], "permalink": info.get("permalink"), "timestamp": info.get("timestamp")}


def publish_reel(folder: Path, dry: bool) -> dict:
    p = load_post(folder)
    video = folder / "reel.mp4"
    if not video.exists():
        print(f"{folder.name}: reel.mp4 がないのでスキップ")
        return {}
    cover = folder / "reel_cover.jpg"
    caption = full_caption(p.get("reel_caption") or p["caption"], p.get("hashtags", []))
    params = {"media_type": "REELS", "video_url": public_url(video), "caption": caption,
              "share_to_feed": "true"}
    if cover.exists():
        params["cover_url"] = public_url(cover)
    if dry:
        print(json.dumps(params, ensure_ascii=False, indent=2))
        return {}
    _, uid = ig_env()
    # 朝の公開で queue→posted に移動済みだが、Pages の反映が遅れている場合に備えて旧パスも試す
    alt = public_url(video).replace("/posted/", "/queue/")
    for _ in range(20):
        ok = [u for u in (params["video_url"], alt)
              if requests.head(u, timeout=30, allow_redirects=True).status_code == 200]
        if ok:
            params["video_url"] = ok[0]
            if "cover_url" in params and ok[0] == alt:
                params["cover_url"] = params["cover_url"].replace("/posted/", "/queue/")
            break
        time.sleep(30)
    else:
        raise SystemExit("リール動画の公開URLにアクセスできません")
    c = ig_request("POST", f"{uid}/media", params)
    wait_container(c["id"])
    pub = ig_request("POST", f"{uid}/media_publish", {"creation_id": c["id"]})
    info = ig_request("GET", pub["id"], {"fields": "permalink,timestamp"})
    return {"media_id": pub["id"], "permalink": info.get("permalink"), "timestamp": info.get("timestamp")}


def save_result(folder: Path, kind: str, res: dict):
    path = folder / "result.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[kind] = res
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["carousel", "reel", "whoami"])
    ap.add_argument("--date")
    ap.add_argument("--wait-until")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.kind == "whoami":
        print(ig_request("GET", "me", {"fields": "user_id,username,account_type,followers_count"}))
        return

    d = a.date or today_jst()
    if a.kind == "carousel":
        folder = ROOT / "queue" / d
        if not folder.exists():
            print(f"::warning::{d} の投稿が queue にありません（未承認 or 未生成）。今日はスキップします。")
            return
        wait_until(a.wait_until)
        res = publish_carousel(folder, a.dry_run)
        if a.dry_run:
            return
        save_result(folder, "carousel", res)
        dest = ROOT / "posted" / d
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(folder), str(dest))
        print(f"公開しました: {res.get('permalink')}")
    else:
        folder = ROOT / "posted" / d  # 朝のカルーセルで移動済み
        if not folder.exists():
            folder = ROOT / "queue" / d
        if not folder.exists():
            print(f"{d} の投稿が見つかりません。スキップします。")
            return
        wait_until(a.wait_until)
        res = publish_reel(folder, a.dry_run)
        if a.dry_run or not res:
            return
        save_result(folder, "reel", res)
        # 動画はリポジトリ肥大化を防ぐため公開後に削除
        (folder / "reel.mp4").unlink(missing_ok=True)
        print(f"リールを公開しました: {res.get('permalink')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"::error::{e}")
        sys.exit(1)

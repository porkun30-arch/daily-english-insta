"""投稿ごとの反応データとアカウント情報を取得し、analytics/ に保存する。

出力:
  analytics/insights.csv   … 直近60日の投稿ごとの指標（保存率・送信率つき）
  analytics/account.json   … フォロワー数・フォロワー層
  analytics/media_kit.md   … 企業向けメディアキット（数字部分を自動更新）
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta

from common import JST, ROOT, ig_env, ig_request

METRICS = ["reach", "saved", "shares", "likes", "comments", "total_interactions", "views"]
OUT = ROOT / "analytics"


def media_insights(mid: str) -> dict:
    try:
        data = ig_request("GET", f"{mid}/insights", {"metric": ",".join(METRICS)})["data"]
        return {d["name"]: d["values"][0]["value"] if "values" in d else d.get("total_value", {}).get("value")
                for d in data}
    except RuntimeError:
        out = {}
        for m in METRICS:  # 一部の指標が未対応の場合は1つずつ取得
            try:
                d = ig_request("GET", f"{mid}/insights", {"metric": m})["data"][0]
                out[m] = d["values"][0]["value"] if "values" in d else d.get("total_value", {}).get("value")
            except RuntimeError:
                out[m] = None
        return out


def collect_posts() -> list[dict]:
    rows = []
    since = date.today() - timedelta(days=60)
    for f in sorted((ROOT / "posted").glob("*/result.json")):
        d = f.parent.name
        if date.fromisoformat(d) < since:
            continue
        post = json.loads((f.parent / "post.json").read_text(encoding="utf-8"))
        res = json.loads(f.read_text())
        for kind in ("carousel", "reel"):
            if kind not in res or not res[kind].get("media_id"):
                continue
            m = media_insights(res[kind]["media_id"])
            reach = m.get("reach") or 0
            rows.append({
                "date": d, "kind": kind, "phrase": post["phrase"], "genre": post.get("genre"),
                "level": post.get("level"), "has_experience": bool((post.get("experience") or {}).get("text")),
                **m,
                "save_rate": round((m.get("saved") or 0) / reach * 100, 2) if reach else None,
                "send_rate": round((m.get("shares") or 0) / reach * 100, 2) if reach else None,
                "permalink": res[kind].get("permalink"),
            })
    return rows


def account_info() -> dict:
    _, uid = ig_env()
    acc = ig_request("GET", uid, {"fields": "username,followers_count,media_count"})
    demo = {}
    for bd in ("age", "gender", "city", "country"):
        try:
            r = ig_request("GET", f"{uid}/insights", {
                "metric": "follower_demographics", "period": "lifetime",
                "metric_type": "total_value", "breakdown": bd})
            res = r["data"][0]["total_value"]["breakdowns"][0]["results"]
            demo[bd] = sorted(({"key": x["dimension_values"][0], "value": x["value"]} for x in res),
                              key=lambda x: -x["value"])[:8]
        except (RuntimeError, KeyError, IndexError):
            demo[bd] = []  # フォロワー100人未満などで取得できない場合
    acc["demographics"] = demo
    acc["fetched_at"] = datetime.now(JST).isoformat(timespec="minutes")
    return acc


def media_kit(acc: dict, rows: list[dict]) -> str:
    car = [r for r in rows if r["kind"] == "carousel" and r.get("reach")]
    rel = [r for r in rows if r["kind"] == "reel" and r.get("reach")]

    def avg(xs, k):
        v = [x[k] for x in xs if x.get(k) is not None]
        return round(sum(v) / len(v), 1) if v else "-"

    def demo(k):
        items = acc["demographics"].get(k) or []
        total = sum(i["value"] for i in items) or 1
        return " / ".join(f"{i['key']} {i['value'] * 100 // total}%" for i in items[:4]) or "（取得不可）"

    return f"""# @{acc.get('username')} メディアキット

最終更新：{acc['fetched_at']}（自動生成）

## アカウント概要
- テーマ：日常・海外旅行・英語会議ですぐ使える英語フレーズを毎日1つ
- 投稿：カルーセル 毎日 7:00 ／ リール（音声付き）週3本
- フォロワー数：**{acc.get('followers_count')}**　総投稿数：{acc.get('media_count')}

## 直近60日の平均（カルーセル {len(car)}本 / リール {len(rel)}本）
| | リーチ | 保存率 | 送信率 | コメント |
|---|---|---|---|---|
| カルーセル | {avg(car, 'reach')} | {avg(car, 'save_rate')}% | {avg(car, 'send_rate')}% | {avg(car, 'comments')} |
| リール | {avg(rel, 'reach')} | {avg(rel, 'save_rate')}% | {avg(rel, 'send_rate')}% | {avg(rel, 'comments')} |

## フォロワー層
- 年齢：{demo('age')}
- 性別：{demo('gender')}
- 地域：{demo('city')}

## 提供できるPRの形（例）
- 英語学習アプリ・オンライン英会話の体験レビュー（カルーセル＋リール）
- 旅行・留学サービスと連動した「現地で使えるフレーズ」特集
- 期間限定キャンペーンの告知（ストーリーズ）

## お問い合わせ
（ここに仕事用の連絡先を記入）
"""


def main():
    OUT.mkdir(exist_ok=True)
    rows = collect_posts()
    if rows:
        with open(OUT / "insights.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    acc = account_info()
    (OUT / "account.json").write_text(json.dumps(acc, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "media_kit.md").write_text(media_kit(acc, rows), encoding="utf-8")
    print(f"insights: {len(rows)} 件 / followers: {acc.get('followers_count')}")


if __name__ == "__main__":
    main()

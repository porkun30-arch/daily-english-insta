"""共通ユーティリティ：設定・フォント・日英混在テキストの折り返し描画・API呼び出し。"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------- 設定


def load_style() -> dict:
    return json.loads((ROOT / "templates" / "style.json").read_text(encoding="utf-8"))


def load_post(folder: Path) -> dict:
    return json.loads((folder / "post.json").read_text(encoding="utf-8"))


def today_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- フォント

_font_cache: dict = {}


def font(kind: str, size: int):
    """style.json の候補を上から順に探して最初に見つかったフォントを使う。"""
    from PIL import ImageFont

    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    for cand in load_style()["fonts"][kind]:
        p = Path(cand)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            f = ImageFont.truetype(str(p), size, index=0)  # .ttc は index 0 = JP
            _font_cache[key] = f
            return f
    raise FileNotFoundError(
        f"日本語フォントが見つかりません（{kind}）。templates/fonts/ に NotoSansJP を置くか、"
        "style.json の fonts を編集してください。"
    )


# ---------------------------------------------------------------- テキスト折り返し

# 英単語（記号込み）/ 空白 / それ以外は1文字ずつ
_TOKEN = re.compile(r"[A-Za-z0-9'’\-.,!?;:\"()/%$&]+|\s|.", re.S)


def _tokens_with_highlight(text: str, highlights: list[str]):
    """(token, highlighted) のリストを返す。highlights に一致する範囲をマーク。"""
    marked = [False] * len(text)
    low = text.lower()
    for h in highlights or []:
        h = h.strip().lower()
        if not h:
            continue
        start = 0
        while (i := low.find(h, start)) != -1:
            for k in range(i, i + len(h)):
                marked[k] = True
            start = i + len(h)
    out = []
    for m in _TOKEN.finditer(text):
        s, e = m.span()
        out.append((m.group(), any(marked[s:e])))
    return out


def layout(text: str, fnt, max_width: int, highlights=None):
    """折り返し済みの行リストを返す。各行は [(token, highlighted), ...]。"""
    lines = []
    for para in text.split("\n"):
        line, width = [], 0
        for tok, hl in _tokens_with_highlight(para, highlights or []):
            w = fnt.getlength(tok)
            if line and width + w > max_width and not tok.isspace():
                # 行頭禁則（簡易）：句読点は前の行にぶら下げる
                if tok in "、。，．！？」』）)":
                    line.append((tok, hl))
                    width += w
                    continue
                lines.append(line)
                line, width = [], 0
            if not line and tok.isspace():
                continue
            line.append((tok, hl))
            width += w
        lines.append(line)
    return lines


def text_height(text, fnt, max_width, line_gap=1.45, highlights=None) -> int:
    n = len(layout(text, fnt, max_width, highlights))
    return int(n * fnt.size * line_gap)


def draw_text(draw, xy, text, fnt, max_width, fill, line_gap=1.45,
              highlights=None, highlight_color=None, align="left") -> int:
    """日英混在テキストを折り返して描画し、使った高さを返す。"""
    x0, y = xy
    step = int(fnt.size * line_gap)
    for line in layout(text, fnt, max_width, highlights):
        lw = sum(fnt.getlength(t) for t, _ in line)
        x = x0 + (max_width - lw) / 2 if align == "center" else x0
        for tok, hl in line:
            w = fnt.getlength(tok)
            if hl and highlight_color and not tok.isspace():
                top = y + fnt.size * 0.55
                draw.rectangle([x - 2, top, x + w + 2, y + fnt.size * 1.12], fill=highlight_color)
            draw.text((x, y), tok, font=fnt, fill=fill)
            x += w
        y += step
    return y - xy[1]


# ---------------------------------------------------------------- Instagram API

API_VERSION = os.environ.get("IG_API_VERSION", "v23.0")
# EAA… で始まるトークン（Meta 統合ログイン / Facebook ログイン）は graph.facebook.com、
# IGAA… で始まるトークン（Instagram ログイン）は graph.instagram.com を使う
_HOST = "graph.instagram.com" if os.environ.get("IG_ACCESS_TOKEN", "").startswith("IG") else "graph.facebook.com"
API_BASE = os.environ.get("IG_API_BASE", f"https://{_HOST}/{API_VERSION}")


def ig_env(require_uid: bool = True):
    token = os.environ.get("IG_ACCESS_TOKEN")
    user_id = os.environ.get("IG_USER_ID")
    if not token or (require_uid and not user_id):
        raise SystemExit("環境変数 IG_ACCESS_TOKEN と IG_USER_ID を設定してください。")
    return token, user_id


def ig_request(method: str, path: str, params: dict | None = None, retries: int = 3):
    import requests

    token, _ = ig_env(require_uid=False)
    params = dict(params or {})
    params["access_token"] = token
    url = path if path.startswith("http") else f"{API_BASE}/{path.lstrip('/')}"
    for attempt in range(retries):
        r = requests.request(method, url, params=params if method == "GET" else None,
                             data=params if method != "GET" else None, timeout=60)
        if r.status_code < 500:
            break
        time.sleep(5 * (attempt + 1))
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text}
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram API error {r.status_code}: {data}")
    return data

"""post.json → カルーセル画像（01.png〜）を生成する。過去投稿（Canva 時代）のデザインに合わせたテンプレート。

構成: 表紙 → 導入（体験談 or 共感フック） → 英語フレーズ 1枚ずつ（3〜5枚） → まとめ表 → 締め
使い方:
    python scripts/render.py queue/2026-11-17 [queue/2026-11-18 ...]
文字が収まらない場合は自動で縮小し、それでも無理なら WARNING（終了コード 2）。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from common import ROOT, draw_text, font, layout, load_post, load_style

STYLE = load_style()
W, H = STYLE["size"]
C = STYLE["colors"]
M = 80
CW = W - 2 * M
warnings: list[str] = []


# ---------------------------------------------------------------- 背景

def cover_crop(img: Image.Image) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r + 1), int(img.height * r + 1)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def load_background(p: dict) -> Image.Image:
    bg = p.get("background")
    if bg and (ROOT / bg).exists():
        return cover_crop(Image.open(ROOT / bg).convert("RGB")).convert("RGBA")
    if bg:
        warnings.append(f"背景写真が見つかりません: {bg}（グラデーションで代用）")
    top = tuple(int(C["fallback_bg_top"][i:i + 2], 16) for i in (1, 3, 5))
    bot = tuple(int(C["fallback_bg_bottom"][i:i + 2], 16) for i in (1, 3, 5))
    g = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / H
        g.putpixel((0, y), tuple(int(top[k] * (1 - t) + bot[k] * t) for k in range(3)))
    return g.resize((W, H)).convert("RGBA")


def washed(bg: Image.Image) -> Image.Image:
    a = int(255 * STYLE.get("overlay_alpha", 0.78))
    return Image.alpha_composite(bg, Image.new("RGBA", (W, H), (255, 255, 255, a)))


# ---------------------------------------------------------------- 文字ユーティリティ

def fit_size(text, kind, max_size, min_size, width, max_lines):
    """max_lines 行以内に収まる最大のフォントサイズ。"""
    for s in range(max_size, min_size - 1, -4):
        if len(layout(text, font(kind, s), width)) <= max_lines:
            return s
    warnings.append(f"文字が長すぎます: {text[:20]}…")
    return min_size


def text_h(text, kind, size, width, gap):
    return len(layout(text, font(kind, size), width)) * int(size * gap)


def shadow_text(img, xy, text, kind, size, width, fill, shadow, align="center", gap=1.25, off=6):
    """少しぼかした濃い影つきの文字（表紙タイトル用）。"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_text(d, (xy[0] + off, xy[1] + off), text, font(kind, size), width, shadow + "AA",
              line_gap=gap, align=align)
    layer = layer.filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(layer)
    d = ImageDraw.Draw(img)
    return draw_text(d, xy, text, font(kind, size), width, fill, line_gap=gap, align=align)


# ---------------------------------------------------------------- 部品（アイコン類）

def tape(img, text):
    """「今日から使える!」のマスキングテープ風ラベル。"""
    tw, th = 660, 170
    layer = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(text)
    pts = [(20, 20)]
    for x in range(20, tw + 20, 22):  # 上辺は少しだけ揺らす
        pts.append((x, 20 + rnd.randint(-2, 2)))
    for y in range(20, th + 20, 14):  # 右端はギザギザに破れた感じ
        pts.append((tw + 20 + rnd.randint(-10, 6), y))
    for x in range(tw + 20, 20, -22):
        pts.append((x, th + 20 + rnd.randint(-2, 2)))
    for y in range(th + 20, 20, -14):
        pts.append((20 + rnd.randint(-6, 10), y))
    col = tuple(int(C["tape"][i:i + 2], 16) for i in (1, 3, 5))
    d.polygon(pts, fill=col + (238,))
    # 紙のざらつき
    for _ in range(2500):
        x, y = rnd.randint(25, tw + 10), rnd.randint(25, th + 15)
        v = rnd.randint(-18, 8)
        d.point((x, y), fill=tuple(max(0, min(255, c + v)) for c in col) + (238,))
    f = font("hand", 76)
    tx = (tw + 40 - f.getlength(text)) / 2
    d.text((tx, (th + 40 - 76) / 2 - 8), text, font=f, fill=C["red"], stroke_width=2, stroke_fill=C["red"])
    layer = layer.rotate(-2.5, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 60), mask=layer.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(sh, (34, 62))
    img.alpha_composite(layer, (20, 50))


def checkbox(d, x, y, s):
    w = max(6, s // 9)
    d.rounded_rectangle((x, y, x + s, y + s), radius=s // 8, outline=C["text"], width=w)
    d.line([(x + s * 0.22, y + s * 0.50), (x + s * 0.45, y + s * 0.74), (x + s * 1.0, y + s * 0.05)],
           fill=C["text"], width=w + 2, joint="curve")


def bulb(d, x, y, s):
    d.ellipse((x, y, x + s, y + s), fill=C["bulb"], outline=C["text"], width=3)
    d.rectangle((x + s * 0.32, y + s * 0.92, x + s * 0.68, y + s * 1.18), fill="#BBBBBB", outline=C["text"], width=3)
    for dx, dy, ex, ey in [(-0.25, 0.5, -0.05, 0.5), (1.05, 0.5, 1.25, 0.5), (0.5, -0.25, 0.5, -0.05),
                           (0.05, 0.05, -0.1, -0.1), (0.95, 0.05, 1.1, -0.1)]:
        d.line([(x + s * dx, y + s * dy), (x + s * ex, y + s * ey)], fill=C["text"], width=3)


def arrow_right(d, x, y, length, color):
    d.line([(x, y), (x + length - 50, y)], fill=color, width=22)
    d.polygon([(x + length - 70, y - 48), (x + length, y), (x + length - 70, y + 48)], fill=color)


def curly_arrow(d, color):
    """左上（プロフィール方向）を指す、くるっと一回転した手書き風の矢印。"""
    import math
    pts = [(335, 255), (300, 250), (262, 240)]
    cx, cy, r = 232, 212, 34
    a0 = math.atan2(240 - cy, 262 - cx)
    for i in range(1, 41):  # 時計回りに1周ループ
        a = a0 - 2 * math.pi * i / 40
        pts.append((cx + r * math.cos(a) * 1.1, cy + r * math.sin(a)))
    sx, sy = pts[-1]
    for i in range(1, 21):  # 左上へ伸ばす
        t = i / 20
        pts.append((sx + (75 - sx) * t, sy + (95 - sy) * t - 25 * math.sin(math.pi * t)))
    d.line(pts, fill=color, width=5, joint="curve")
    ex, ey = pts[-1]
    d.line([(ex, ey), (ex + 2, ey + 52)], fill=color, width=5)
    d.line([(ex, ey), (ex + 50, ey + 10)], fill=color, width=5)


# ---------------------------------------------------------------- キャラクター・シリーズ・メーター

def chara(expr="normal", size=260):
    """マスコット（ツバ吉）の画像。なければ None。"""
    cf = STYLE.get("character", {})
    path = ROOT / cf.get("dir", "templates/character") / f"{cf.get('prefix', 'tsubakichi_')}{expr}.png"
    if not path.exists():
        path = path.with_name(f"{cf.get('prefix', 'tsubakichi_')}normal.png")
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


def put_chara(img, expr, x, y, size):
    c = chara(expr, size)
    if c is not None:
        img.alpha_composite(c, (int(x), int(y)))


def bubble(img, box, text, tail_to, size=40):
    """白い吹き出し。tail_to=しっぽの先（キャラの口元）。"""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    cx = min(max(tail_to[0], x0 + 60), x1 - 60)
    base_y = y1 if tail_to[1] > y1 else y0
    d.polygon([(cx - 30, base_y), (cx + 30, base_y), tail_to], fill=C["white"], outline=C["text"])
    d.rounded_rectangle(box, radius=36, fill=C["white"], outline=C["text"], width=4)
    d.polygon([(cx - 27, base_y), (cx + 27, base_y), (tail_to[0], tail_to[1] - (8 if tail_to[1] > y1 else -8))],
              fill=C["white"])
    s = size
    while s > 28 and text_h(text, "bold", s, x1 - x0 - 60, 1.4) > (y1 - y0 - 40):
        s -= 2
    th = text_h(text, "bold", s, x1 - x0 - 60, 1.4)
    draw_text(d, (x0 + 30, y0 + (y1 - y0 - th) / 2), text, font("bold", s), x1 - x0 - 60, C["text"],
              line_gap=1.4, align="center")


def series_no(p) -> int | None:
    """シリーズ番号。post.json の series_no が優先。なければ posted/queue のうち日付が前の投稿数＋開始番号。"""
    if p.get("series_no"):
        return int(p["series_no"])
    try:
        cur = p["date"]
        n = 0
        for state in ("posted", "queue"):
            for f in (ROOT / state).glob("*/post.json"):
                if f.parent.name < cur:
                    n += 1
        return STYLE.get("series", {}).get("start", 1) + n
    except Exception:  # noqa: BLE001
        return None


def casual_meter(d, y, level):
    """フォーマル ○○●○○ カジュアル（level: 1=フォーマル … 5=カジュアル）。高さ約 56px。"""
    f = font("bold", 32)
    l, r = "フォーマル", "カジュアル"
    dots_w = 5 * 44 + 4 * 22
    total = f.getlength(l) + 30 + dots_w + 30 + f.getlength(r)
    x = (W - total) / 2
    d.text((x, y + 6), l, font=f, fill=C["sub"])
    x += f.getlength(l) + 30
    for i in range(1, 6):
        cx = x + 22 + (i - 1) * 66
        if i == level:
            d.ellipse((cx - 26, y + 2, cx + 26, y + 54), fill=C["red"])
        else:
            d.ellipse((cx - 16, y + 12, cx + 16, y + 44), outline="#9A9A9A", width=4)
    x += dots_w + 30
    d.text((x, y + 6), r, font=f, fill=C["sub"])


# ---------------------------------------------------------------- 各スライド

def slide_cover(p, bg):
    img = bg.copy()
    tape(img, p["cover"].get("tape") or STYLE["tape_text"])
    title, sub = p["cover"]["title"], p["cover"].get("sub", "")
    tw = W - 140
    # タイトルはできるだけ1行で（長ければ2行に）
    ts = None
    for s in range(200, 119, -4):
        if len(layout(title, font("title", s), tw)) == 1:
            ts = s
            break
    if ts is None:
        ts = fit_size(title, "title", 160, 96, tw, 2)
    ss = fit_size(sub, "title", 100, 56, tw, 2) if sub else 0
    th = text_h(title, "title", ts, tw, 1.18)
    sh = text_h(sub, "title", ss, tw, 1.25) if sub else 0
    gap = 60 if sub else 0
    inner = th + gap + sh
    box_bot = H - 140
    box_top = box_bot - inner - 170
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle((40, box_top, W - 40, box_bot), radius=48, fill=(255, 255, 255, 185))
    img.alpha_composite(ov)
    y = box_top + 75
    shadow_text(img, (70, y), title, "title", ts, tw, C["red"], C["red_shadow"], gap=1.18)
    if sub:
        shadow_text(img, (70, y + th + gap), sub, "title", ss, tw, C["red"], C["red_shadow"], gap=1.25, off=4)
    # シリーズ番号（白いボックスの上辺にタブ風に）
    no = series_no(p)
    d = ImageDraw.Draw(img)
    if no:
        t = f"{STYLE.get('series', {}).get('name', '')} No.{no}"
        f = font("title", 40)
        pw = f.getlength(t) + 60
        px = 80
        d.rounded_rectangle((px, box_top - 36, px + pw, box_top + 36), radius=36, fill=C["red"])
        d.text((px + 30, box_top - 24), t, font=f, fill=C["white"])
    # ツバ吉（ボックスの右上からひょっこり）
    put_chara(img, p["cover"].get("chara", "normal"), W - 330, box_top - 235, 280)
    return img


def slide_intro(p, bg):
    img = washed(bg)
    d = ImageDraw.Draw(img)
    intro = p.get("intro", {})
    exp = (p.get("experience") or {}).get("text", "").strip()
    body = exp or intro.get("body", "")
    n = len(p["phrases"])
    lead = intro.get("lead", f"「{p['phrase']}」")

    def blocks(s):
        lb = text_h(lead, "title", int(64 * s), CW, 1.3)
        bb = text_h(body, "bold", int(46 * s), CW, 1.65)
        return lb, bb

    for s in (1.0, 0.92, 0.85, 0.78, 0.72):
        lb, bb = blocks(s)
        total = lb + 40 + (70 if exp else 0) + bb + 90 + 150
        if total < H - 420:
            break
    else:
        warnings.append("導入スライドの文字量が多すぎます")
    y = max(90, (H - 330 - total) / 2)
    y += draw_text(d, (M, y), lead, font("title", int(64 * s)), CW, C["red"], line_gap=1.3, align="center")
    y += 40
    if exp:
        f = font("bold", 34)
        t = "つばさの体験談"
        tw = f.getlength(t) + 50
        d.rounded_rectangle(((W - tw) / 2, y, (W + tw) / 2, y + 56), radius=28, fill=C["red"])
        d.text(((W - f.getlength(t)) / 2, y + 7), t, font=f, fill=C["white"])
        y += 70
    y += draw_text(d, (M, y), body, font("bold", int(46 * s)), CW, C["text"], line_gap=1.65, align="center")
    y += 90
    # 「そんな時に使えるフレーズ N 個紹介します！」
    f1, fn, f2 = font("title", 50), font("title", 120), font("title", 50)
    l1 = "そんな時に使えるフレーズ"
    d.text(((W - f1.getlength(l1)) / 2, y), l1, font=f1, fill=C["text"])
    y += 80
    ns, l2 = str(n), "個紹介します！"
    tw = fn.getlength(ns) + 20 + f2.getlength(l2)
    x = (W - tw) / 2
    d.text((x, y - 40), ns, font=fn, fill=C["red"])
    d.text((x + fn.getlength(ns) + 20, y + 30), l2, font=f2, fill=C["text"])
    # ツバ吉のひと言（左下）＋次へ矢印（右下）
    says = intro.get("chara_says", "")
    put_chara(img, intro.get("chara", "trouble"), 40, H - 310, 270)
    if says:
        bubble(img, (330, H - 330, W - 60, H - 190), says, (290, H - 180), size=40)
    arrow_right(d, W - 300, H - 95, 240, C["red"])
    return img


def slide_phrase(p, bg, item):
    img = washed(bg)
    d = ImageDraw.Draw(img)
    ens = item["en"] if isinstance(item["en"], list) else [item["en"]]
    lead = item.get("lead", "")
    note = item.get("note", "")
    tip = item.get("tip")
    ex = item.get("example")

    # 英語フレーズのサイズ：一番長い行がチェックボックス込みで収まる大きさ
    box = 92
    size = 100
    while size > 56:
        fw = max(font("title", size).getlength(e) for e in ens)
        if fw + box + 36 <= CW:
            break
        size -= 4
    else:
        warnings.append(f"英語フレーズが長すぎます: {ens[0]}")
    line_h = int(size * 1.45)
    fw = max(font("title", size).getlength(e) for e in ens)
    block_w = box + 36 + fw

    note_s = 46
    while note_s > 34 and text_h(note, "bold", note_s, CW, 1.6) > 420:
        note_s -= 2
    parts = []
    if lead:
        parts.append(("lead", text_h(lead, "bold", 42, CW, 1.4)))
    parts.append(("en", line_h * len(ens)))
    if item.get("casual"):
        parts.append(("meter", 56))
    if note:
        parts.append(("note", text_h(note, "bold", note_s, CW, 1.6)))
    if tip:
        parts.append(("tip", 64 + text_h(tip.get("ja", ""), "bold", 40, CW, 1.4)))
    if ex:
        parts.append(("ex", text_h(ex["en"], "bold", 42, CW, 1.4) + text_h(ex["ja"], "regular", 36, CW, 1.4) + 10))
    gaps = {"lead": 50, "en": 50, "meter": 70, "note": 80, "tip": 60, "ex": 0}
    total = sum(h for _, h in parts) + sum(gaps[k] for k, _ in parts[:-1])
    if total > H - 200:
        warnings.append(f"フレーズスライドの文字量が多すぎます: {ens[0]}")
    y = max(90, (H - total) / 2 - 20)
    for k, h in parts:
        if k == "lead":
            draw_text(d, (M, y), lead, font("bold", 42), CW, C["text"], line_gap=1.4, align="center")
        elif k == "en":
            x0 = (W - block_w) / 2
            for i, e in enumerate(ens):
                yy = y + i * line_h
                checkbox(d, x0, yy + (size - box) / 2 + size * 0.12, box)
                d.text((x0 + box + 36, yy), e, font=font("title", size), fill=C["text"])
        elif k == "meter":
            casual_meter(d, y, int(item["casual"]))
        elif k == "note":
            draw_text(d, (M, y), note, font("bold", note_s), CW, C["red"], line_gap=1.6, align="center")
        elif k == "tip":
            fe = font("bold", 48)
            tw = 90 + fe.getlength(tip["en"])
            x0 = (W - tw) / 2
            bulb(d, x0, y + 4, 52)
            d.text((x0 + 90, y), tip["en"], font=fe, fill=C["text"])
            draw_text(d, (M, y + 64), tip.get("ja", ""), font("bold", 40), CW, C["text"],
                      line_gap=1.4, align="center")
        elif k == "ex":
            yy = y + draw_text(d, (M, y), ex["en"], font("bold", 42), CW, C["text"], line_gap=1.4, align="center")
            draw_text(d, (M, yy + 10), ex["ja"], font("regular", 36), CW, C["sub"], line_gap=1.4, align="center")
        y += h + gaps[k]
    return img


def slide_summary(p, bg):
    img = washed(bg)
    d = ImageDraw.Draw(img)
    rows = []
    for it in p["phrases"]:
        rows += it["en"] if isinstance(it["en"], list) else [it["en"]]
    y = 170
    y += draw_text(d, (M, y), "いかがでしたか？", font("title", 62), CW, C["red"], align="center")
    y += 10
    y += draw_text(d, (M, y), "使えそうなフレーズがあれば\nぜひ今日から使ってみてください！", font("title", 52),
                   CW, C["text"], line_gap=1.45, align="center")
    y += 70
    rh = min(100, int((H - 360 - y) / max(1, len(rows))))
    fs = min(44, int(rh * 0.45))
    tw = 760
    x0 = (W - tw) / 2
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle((x0, y, x0 + tw, y + rh * len(rows)), fill=(255, 255, 255, 120))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    for i, r in enumerate(rows):
        top = y + i * rh
        d.rectangle((x0, top, x0 + tw, top + rh), outline="#333333", width=2)
        f = font("bold", fs)
        while f.getlength(r) > tw - 50 and fs > 26:
            fs -= 2
            f = font("bold", fs)
        d.text((x0 + 26, top + (rh - fs) / 2 - 4), r, font=f, fill=C["text"])
    # ツバ吉のひと言（右下）
    says = p.get("summary_says", "")
    put_chara(img, p.get("summary_chara", "happy"), W - 310, H - 310, 270)
    if says:
        bubble(img, (60, H - 300, W - 340, H - 160), says, (W - 290, H - 190), size=40)
    return img


def slide_closing(p, bg):
    img = washed(bg)
    d = ImageDraw.Draw(img)
    cl = STYLE["closing"]
    curly_arrow(d, C["text"])
    d.text((350, 215), cl["check_more"], font=font("regular", 46), fill=C["text"])
    y = 480
    y += draw_text(d, (M, y), cl["intro"], font("regular", 46), CW, C["text"], align="center")
    y += 40
    for b in cl["bullets"]:
        y += draw_text(d, (M, y), "√" + b, font("title", 50), CW, C["text"], line_gap=1.45, align="center")
    y += 40
    draw_text(d, (M, y), cl["outro"], font("regular", 46), CW, C["text"], align="center")
    d.text((230, H - 205), cl["save"], font=font("regular", 48), fill=C["text"])
    # 保存アイコン（ブックマーク）
    x, yb, bw, bh = W - 260, H - 300, 150, 210
    notch = img.getpixel((int(x + bw / 2), int(yb + bh + 8)))
    d.rectangle((x, yb, x + bw, yb + bh), fill=C["bookmark"])
    d.polygon([(x - 1, yb + bh + 1), (x + bw / 2, yb + bh - 60), (x + bw + 1, yb + bh + 1)], fill=notch)
    return img


# ---------------------------------------------------------------- 組み立て

def build_slides(p):
    bg = load_background(p)
    slides = [slide_cover(p, bg), slide_intro(p, bg)]
    slides += [slide_phrase(p, bg, it) for it in p["phrases"]]
    slides += [slide_summary(p, bg), slide_closing(p, bg)]
    return [s.convert("RGB") for s in slides]


def validate(p, folder):
    errs = []
    for k in ["date", "phrase", "cover", "phrases", "caption", "hashtags"]:
        if k not in p:
            errs.append(f"{k} がありません")
    if not 3 <= len(p.get("phrases", [])) <= 5:
        errs.append("phrases は 3〜5 個にしてください")
    if "title" not in p.get("cover", {}):
        errs.append("cover.title がありません")
    if not 3 <= len(p.get("hashtags", [])) <= 5:
        errs.append("hashtags は 3〜5 個にしてください（Instagram の上限は5）")
    cap = p.get("caption", "") + "\n\n" + " ".join(p.get("hashtags", []))
    if len(cap) > 2200:
        errs.append(f"caption + hashtags が {len(cap)} 文字（上限 2,200）")
    if "#" in p.get("caption", ""):
        errs.append("caption 本文に # を入れないでください（hashtags に入れる）")
    if p.get("date") and p["date"] != folder.name:
        errs.append(f"date ({p['date']}) とフォルダ名 ({folder.name}) が一致しません")
    return errs


def render(folder: Path):
    p = load_post(folder)
    errs = validate(p, folder)
    if errs:
        for e in errs:
            print(f"ERROR [{folder.name}] {e}")
        return False
    for old in folder.glob("[0-9][0-9].png"):
        old.unlink()
    start = len(warnings)
    slides = build_slides(p)
    for i, img in enumerate(slides, 1):
        img.save(folder / f"{i:02d}.png", optimize=True)
    for w in warnings[start:]:
        print(f"WARNING [{folder.name}] {w}")
    print(f"OK [{folder.name}] {len(slides)} 枚を生成")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ok = all([render(Path(a)) for a in sys.argv[1:]])
    sys.exit(0 if ok and not warnings else (2 if ok else 1))

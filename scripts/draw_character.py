"""マスコット「ツバ吉」（つばめ）の表情差分 PNG を描き出す（仮デザイン）。

    python scripts/draw_character.py      → templates/character/tsubakichi_<表情>.png

イラストレーターに正式発注するまでのつなぎ。正式版ができたら同じファイル名で差し替えればよい。
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "templates" / "character"
S = 3            # 超解像で描いてから縮小（線をなめらかに）
N = 1000         # 設計上のキャンバス
NAVY = "#6E95D3"
NAVY_D = "#557DBD"
CREAM = "#FFF8EF"
WHITE = "#FFFFFF"
RED = "#F2463C"
BEAK = "#F6A623"
CHEEK = "#F9A8A0"
INK = "#1A1A1A"
SWEAT = "#7EC8F0"
YELLOW = "#FFD84D"

EXPRESSIONS = ["normal", "trouble", "idea", "happy", "surprised", "smug"]
LABELS = {"normal": "ふつう", "trouble": "困る", "idea": "ひらめき", "happy": "喜ぶ",
          "surprised": "驚く", "smug": "ドヤ"}


def P(*xy):
    return [v * S for v in xy]


def rot_ellipse(img, cx, cy, rx, ry, angle, fill):
    """回転した楕円（翼など）。"""
    w, h = int(rx * 2 * S), int(ry * 2 * S)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((0, 0, w - 1, h - 1), fill=fill)
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(layer, (int(cx * S - layer.width / 2), int(cy * S - layer.height / 2)))


def wing(img, root, length, width, angle, fill):
    """先のとがった長い翼（つばめらしさ）。root=付け根、angle=度（0=真下、+で右へ）。"""
    t = math.radians(angle)
    dx, dy = math.sin(t), math.cos(t)          # 翼の向き
    nx, ny = dy, -dx                           # 幅方向
    x0, y0 = root
    pts = [(x0 + nx * width, y0 + ny * width),
           (x0 + dx * length * 0.55 + nx * width * 0.9, y0 + dy * length * 0.55 + ny * width * 0.9),
           (x0 + dx * length, y0 + dy * length),
           (x0 + dx * length * 0.55 - nx * width * 0.6, y0 + dy * length * 0.55 - ny * width * 0.6),
           (x0 - nx * width * 0.6, y0 - ny * width * 0.6)]
    ImageDraw.Draw(img).polygon([v * S for p in pts for v in p], fill=fill)


def heart(d, cx, cy, r, fill):
    d.ellipse(P(cx - r, cy - r * 0.9, cx, cy + r * 0.1), fill=fill)
    d.ellipse(P(cx, cy - r * 0.9, cx + r, cy + r * 0.1), fill=fill)
    d.polygon(P(cx - r * 0.97, cy - r * 0.25, cx + r * 0.97, cy - r * 0.25, cx, cy + r * 1.0), fill=fill)


def draw(expr: str, size: int = 600) -> Image.Image:
    img = Image.new("RGBA", (N * S, N * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 丸い二股しっぽ（体の後ろからちょこっと）
    rot_ellipse(img, 400, 860, 40, 95, -35, NAVY_D)
    rot_ellipse(img, 600, 860, 40, 95, 35, NAVY_D)
    # 足
    for x in (425, 575):
        d.ellipse(P(x - 38, 835, x + 38, 880), fill=BEAK)

    # 翼（丸いミトン型）
    wing_up = expr in ("happy", "idea")
    if wing_up:
        rot_ellipse(img, 195, 460, 62, 118, 35, NAVY_D)
        rot_ellipse(img, 805, 460, 62, 118, -35, NAVY_D)
    else:
        rot_ellipse(img, 185, 650, 62, 112, -28, NAVY_D)
        if expr == "trouble":
            rot_ellipse(img, 770, 370, 50, 95, -140, NAVY_D)   # 頭をかく
        elif expr != "smug":
            rot_ellipse(img, 815, 650, 62, 112, 28, NAVY_D)

    # おもち型の体
    d.ellipse(P(180, 250, 820, 870), fill=NAVY)
    # アホ毛
    rot_ellipse(img, 485, 235, 22, 55, 20, NAVY)
    rot_ellipse(img, 525, 245, 18, 45, -25, NAVY)
    d = ImageDraw.Draw(img)
    # クリーム色のお腹
    d.ellipse(P(290, 560, 710, 875), fill=CREAM)
    # 赤いハートのよだれかけ（のどの赤＝ブランドの赤）
    heart(d, 500, 640, 60, RED)

    if expr == "smug":   # 胸に手（翼）
        rot_ellipse(img, 690, 690, 50, 95, 60, NAVY_D)
        d = ImageDraw.Draw(img)

    # ほっぺ（大きめ）
    bl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bl)
    bd.ellipse(P(255, 520, 345, 575), fill=(249, 140, 150, 200))
    bd.ellipse(P(655, 520, 745, 575), fill=(249, 140, 150, 200))
    img.alpha_composite(bl)
    d = ImageDraw.Draw(img)

    # 目（大きく・低め・離し気味）
    ey = 470
    for x in (370, 630):
        if expr == "happy":
            d.arc(P(x - 44, ey - 20, x + 44, ey + 55), 205, 335, fill=INK, width=16 * S)
            continue
        if expr == "smug" and x < 500:   # 左目だけウインク
            d.line(P(x - 42, ey + 12, x + 42, ey + 12), fill=INK, width=14 * S)
            continue
        rx, ry = (54, 64) if expr == "surprised" else (46, 56)
        d.ellipse(P(x - rx, ey - ry, x + rx, ey + ry), fill=INK)
        d.ellipse(P(x - rx * 0.05, ey - ry * 0.75, x + rx * 0.6, ey - ry * 0.15), fill=WHITE)
        if expr == "trouble":   # 困り眉
            d.line(P(x - 45, ey - 90 + (12 if x < 500 else -12), x + 45, ey - 90 - (12 if x < 500 else -12)),
                   fill=INK, width=12 * S)

    # くちばし（小さく）
    if expr in ("surprised", "idea", "happy"):
        d.ellipse(P(478, 505, 522, 550), fill="#E07A10")
        d.polygon(P(472, 500, 528, 500, 500, 525), fill=BEAK)
    else:
        d.polygon(P(474, 502, 526, 502, 500, 538), fill=BEAK)

    # 効果
    if expr == "trouble":
        d.ellipse(P(820, 300, 870, 370), fill=SWEAT)
        d.polygon(P(825, 320, 865, 320, 845, 270), fill=SWEAT)
    elif expr == "idea":
        cx, cy, r = 500, 95, 58
        d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=YELLOW, outline=INK, width=6 * S)
        d.rectangle(P(cx - 22, cy + r - 6, cx + 22, cy + r + 24), fill="#BBBBBB", outline=INK, width=5 * S)
        for a in range(-150, -20, 32):
            t = math.radians(a)
            d.line(P(cx + (r + 18) * math.cos(t), cy + (r + 18) * math.sin(t),
                     cx + (r + 46) * math.cos(t), cy + (r + 46) * math.sin(t)), fill=INK, width=6 * S)
    elif expr == "surprised":
        d.rounded_rectangle(P(850, 170, 890, 300), radius=18 * S, fill=RED)
        d.ellipse(P(848, 318, 892, 362), fill=RED)
    elif expr == "happy":
        for x, y, r in ((120, 260, 34), (880, 250, 30), (840, 130, 20)):
            d.polygon(P(x, y - r, x + r * 0.3, y - r * 0.3, x + r, y, x + r * 0.3, y + r * 0.3,
                        x, y + r, x - r * 0.3, y + r * 0.3, x - r, y, x - r * 0.3, y - r * 0.3), fill=YELLOW)
        heart(d, 160, 140, 26, "#F98C96")
    elif expr == "smug":
        d.polygon(P(830, 230, 842, 262, 875, 266, 850, 286, 858, 318, 830, 300, 802, 318, 810, 286,
                    785, 266, 818, 262), fill=YELLOW)

    return img.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for e in EXPRESSIONS:
        draw(e).save(OUT / f"tsubakichi_{e}.png")
    print(f"wrote {len(EXPRESSIONS)} images to {OUT}")


if __name__ == "__main__":
    main()

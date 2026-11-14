"""post.json → カルーセル画像（01.png〜）を生成する。

使い方:
    python scripts/render.py queue/2026-11-17 [queue/2026-11-18 ...]
文字が収まらない場合は自動で縮小し、それでも無理なら WARNING を出す（終了コード 2）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

from common import draw_text, font, load_post, load_style, text_height

STYLE = load_style()
W, H = STYLE["size"]
C = STYLE["colors"]
M = 90                      # 左右余白
CW = W - M * 2              # 本文幅
TOP, BOTTOM = 190, H - 150  # 本文エリア
SCALES = [1.0, 0.92, 0.85, 0.78, 0.72]
warnings: list[str] = []


# ---------------------------------------------------------------- 共通パーツ

def new_canvas(bg=None):
    img = Image.new("RGB", (W, H), bg or C["bg"])
    return img, ImageDraw.Draw(img)


def header(d, label, page, total, dark=False):
    col = C["card"] if dark else C["accent"]
    d.text((M, 90), label, font=font("bold", 34), fill=col)
    f = font("regular", 30)
    t = f"{page}/{total}"
    d.text((W - M - f.getlength(t), 92), t, font=f, fill=C["sub"] if not dark else C["card"])
    d.line([(M, 150), (W - M, 150)], fill=col, width=3)


def footer(d, dark=False):
    f = font("regular", 28)
    t = STYLE["handle"]
    d.text(((W - f.getlength(t)) / 2, H - 90), t, font=f, fill=C["card"] if dark else C["sub"])


def card(d, box, radius=28):
    d.rounded_rectangle(box, radius=radius, fill=C["card"])


def fit(name, builder):
    """builder(scale, offset) -> (img, bottom_y)。BOTTOM に収まる最大の scale を採用し、
    余白が大きい場合は本文を少し下げて上下のバランスを取る。"""
    for s in SCALES:
        img, bottom = builder(s, 0)
        if bottom <= BOTTOM:
            off = min(int((BOTTOM - bottom) * 0.4), 160)
            return builder(s, off)[0] if off > 20 else img
    warnings.append(f"{name}: 文字量が多すぎます（最小サイズでもはみ出し）")
    return img


# ---------------------------------------------------------------- 各スライド

def slide_cover(p, page, total):
    img, d = new_canvas(C["accent"])
    hook = p.get("hook", "")
    y = 300
    y += draw_text(d, (M, y), hook, font("bold", 52), CW, C["card"], align="center")
    y += 80
    fb = font("bold", 104)
    ph = text_height(p["phrase"], fb, CW - 40)
    card(d, (M - 10, y - 40, W - M + 10, y + ph + 30), radius=36)
    draw_text(d, (M + 10, y), p["phrase"], fb, CW - 40, C["accent"], line_gap=1.3, align="center",
              highlights=p.get("highlight"), highlight_color=C["highlight"])
    y += ph + 110
    chip = f"{p.get('genre', '')}  ·  {p.get('level', '')}".strip(" ·")
    fc = font("bold", 34)
    cw = fc.getlength(chip) + 60
    d.rounded_rectangle(((W - cw) / 2, y, (W + cw) / 2, y + 66), radius=33, fill=C["highlight"])
    d.text(((W - fc.getlength(chip)) / 2, y + 12), chip, font=fc, fill=C["accent"])
    fs = font("bold", 36)
    t = "スワイプして覚えよう  →"
    d.text(((W - fs.getlength(t)) / 2, H - 230), t, font=fs, fill=C["highlight"])
    footer(d, dark=True)
    return img


def slide_text(label, phrase, body, page, total, name, highlights=None, quote=False):
    def build(s, off):
        img, d = new_canvas()
        header(d, label, page, total)
        y = TOP + 30 + off
        y += draw_text(d, (M, y), phrase, font("bold", int(64 * s)), CW, C["accent"], line_gap=1.3,
                       highlights=highlights, highlight_color=C["highlight"])
        y += 50
        fb = font("regular", int(44 * s))
        bh = text_height(body, fb, CW - 100, line_gap=1.7)
        card(d, (M, y, W - M, y + bh + 100))
        if quote:
            d.text((M + 18, y - 10), "“", font=font("bold", 80), fill=C["highlight"])
        draw_text(d, (M + 50, y + 50), body, fb, CW - 100, C["text"], line_gap=1.7)
        footer(d)
        return img, y + bh + 100
    return fit(name, build)


def slide_examples(p, items, idx, n_ex, page, total):
    def build(s, off):
        img, d = new_canvas()
        header(d, f"例文 {idx}/{n_ex}", page, total)
        y = TOP + 40 + off
        fe, fj = font("bold", int(50 * s)), font("regular", int(38 * s))
        for it in items:
            eh = text_height(it["en"], fe, CW - 100, line_gap=1.4)
            jh = text_height(it["ja"], fj, CW - 100, line_gap=1.5)
            h = eh + jh + 130
            card(d, (M, y, W - M, y + h))
            yy = y + 45
            yy += draw_text(d, (M + 50, yy), it["en"], fe, CW - 100, C["text"], line_gap=1.4,
                            highlights=p.get("highlight"), highlight_color=C["highlight"])
            yy += 25
            draw_text(d, (M + 50, yy), it["ja"], fj, CW - 100, C["sub"], line_gap=1.5)
            y += h + 50
        footer(d)
        return img, y - 50
    return fit(f"例文{idx}", build)


def slide_compare(p, page, total):
    def build(s, off):
        img, d = new_canvas()
        header(d, "似た表現との違い", page, total)
        y = TOP + 40 + off
        fe, fj = font("bold", int(50 * s)), font("regular", int(38 * s))
        for i, it in enumerate(p["compare"]):
            if i:
                d.line([(M, y), (W - M, y)], fill="#E3DED5", width=2)
                y += 45
            is_main = it["en"].strip().lower() == p["phrase"].strip().lower()
            col = C["accent"] if is_main else C["text"]
            y += draw_text(d, (M, y), it["en"], fe, CW, col, line_gap=1.35,
                           highlights=p.get("highlight") if is_main else None,
                           highlight_color=C["highlight"])
            y += 12
            y += draw_text(d, (M, y), it["ja"], fj, CW, C["sub"], line_gap=1.5)
            y += 45
        footer(d)
        return img, y
    return fit("似た表現", build)


def slide_quiz(p, page, total):
    q = p["quiz"]

    def build(s, off):
        img, d = new_canvas()
        header(d, "練習問題", page, total)
        y = TOP + 40 + off
        y += draw_text(d, (M, y), q["situation"], font("regular", int(44 * s)), CW, C["text"], line_gap=1.6)
        y += 60
        fp = font("bold", int(60 * s))
        ph = text_height(q["prompt"], fp, CW - 100, line_gap=1.35)
        card(d, (M, y, W - M, y + ph + 110))
        draw_text(d, (M + 50, y + 55), q["prompt"], fp, CW - 100, C["accent"], line_gap=1.35, align="center")
        y += ph + 110 + 50
        if q.get("hint"):
            y += draw_text(d, (M, y), f"ヒント：{q['hint']}", font("regular", int(38 * s)), CW, C["sub"])
        fa = font("bold", 36)
        t = "答えは次のページ  →"
        d.text(((W - fa.getlength(t)) / 2, H - 230), t, font=fa, fill=C["accent"])
        footer(d)
        return img, y
    return fit("練習問題", build)


def slide_answer(p, page, total):
    a = p["answer"]

    def build(s, off):
        img, d = new_canvas()
        header(d, "答え", page, total)
        y = TOP + 40 + off
        y += draw_text(d, (M, y), a["answer"], font("bold", int(66 * s)), CW, C["accent"], line_gap=1.3,
                       highlights=p.get("highlight"), highlight_color=C["highlight"])
        y += 50
        y += draw_text(d, (M, y), a["explanation"], font("regular", int(42 * s)), CW, C["text"], line_gap=1.7)
        # 保存CTA帯
        band_top = H - 330
        d.rounded_rectangle((M, band_top, W - M, band_top + 150), radius=28, fill=C["accent"])
        draw_text(d, (M + 40, band_top + 48), a.get("cta", "保存して見返そう"),
                  font("bold", 42), CW - 80, C["card"], align="center")
        footer(d)
        # 本文が CTA 帯の 40px 手前までに収まれば OK（BOTTOM 基準に換算して返す）
        return img, y + (BOTTOM - (band_top - 40))
    return fit("答え", build)


# ---------------------------------------------------------------- 組み立て

def build_slides(p):
    exp = (p.get("experience") or {}).get("text", "").strip()
    ex = p["examples"]
    chunks = [ex[i:i + 2] for i in range(0, len(ex), 2)]
    total = 1 + 1 + (1 if exp else 0) + len(chunks) + 1 + 1 + 1
    slides, page = [], 1
    slides.append(slide_cover(p, page, total)); page += 1
    slides.append(slide_text("意味とニュアンス", p["phrase"], p["meaning"], page, total, "意味",
                             highlights=p.get("highlight"))); page += 1
    if exp:
        slides.append(slide_text("つばさの体験談", p.get("experience", {}).get("title", "実際にあった話"),
                                 exp, page, total, "体験談", quote=True)); page += 1
    for i, ch in enumerate(chunks, 1):
        slides.append(slide_examples(p, ch, i, len(chunks), page, total)); page += 1
    slides.append(slide_compare(p, page, total)); page += 1
    slides.append(slide_quiz(p, page, total)); page += 1
    slides.append(slide_answer(p, page, total))
    return slides


def validate(p, folder):
    errs = []
    for k in ["date", "phrase", "hook", "meaning", "examples", "compare", "quiz", "answer", "caption", "hashtags"]:
        if k not in p:
            errs.append(f"{k} がありません")
    if not 5 <= len(p.get("examples", [])) <= 7:
        errs.append("examples は 5〜7 個にしてください")
    if not 3 <= len(p.get("hashtags", [])) <= 5:
        errs.append("hashtags は 3〜5 個にしてください（Instagram の上限は5）")
    cap = p.get("caption", "") + "\n\n" + " ".join(p.get("hashtags", []))
    if len(cap) > 2200:
        errs.append(f"caption + hashtags が {len(cap)} 文字（上限 2,200）")
    if p.get("caption", "").count("#") > 0:
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

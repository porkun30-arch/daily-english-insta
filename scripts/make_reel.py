"""post.json → 音声付きリール動画（reel.mp4, 1080x1920）を生成する。

使い方:
    python scripts/make_reel.py queue/2026-11-18 [...]        # Google Cloud TTS を使う
    python scripts/make_reel.py --silent queue/2026-11-18      # 音声なしで動作確認

- リール対象日（style.json の reel_weekdays）かつ post.json に "reel" があるものだけ生成
- 環境変数 GOOGLE_TTS_API_KEY が必要（--silent 時は不要）
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from common import draw_text, font, load_post, load_style

STYLE = load_style()
C = STYLE["colors"]
W, H = 1080, 1920
M = 90
CW = W - 2 * M


def is_reel_day(p) -> bool:
    d = date.fromisoformat(p["date"])
    return "reel" in p and d.weekday() in STYLE.get("reel_weekdays", [1, 3, 5])


# ---------------------------------------------------------------- 画面

def _bg(p):
    from render import ROOT as R
    bgp = p.get("background")
    if bgp and (R / bgp).exists():
        im = Image.open(R / bgp).convert("RGB")
        r = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * r + 1), int(im.height * r + 1)))
        x, y = (im.width - W) // 2, (im.height - H) // 2
        return im.crop((x, y, x + W, y + H)).convert("RGBA")
    return Image.new("RGBA", (W, H), C["fallback_bg_top"])


def frame(kind, p, **kw) -> Image.Image:
    bg = _bg(p)
    if kind != "hook":
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (255, 255, 255, int(255 * STYLE.get("overlay_alpha", 0.78)))))
    img = bg
    d = ImageDraw.Draw(img)
    # Reels の UI に隠れない安全領域：上 250px / 下 420px を避ける
    if kind == "hook":
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle((50, 560, W - 50, 1320), radius=50, fill=(255, 255, 255, 190))
        img.alpha_composite(ov)
        d = ImageDraw.Draw(img)
        y = 640
        y += draw_text(d, (M, y), p["cover"]["title"], font("title", 120), CW, C["red"], line_gap=1.2, align="center")
        y += 50
        draw_text(d, (M, y), p["reel"]["hook"], font("title", 64), CW, C["red"], line_gap=1.35, align="center")
    elif kind == "phrase":
        y = 600
        for e in kw["ens"]:
            y += draw_text(d, (M, y), e, font("title", 96), CW, C["text"], line_gap=1.3,
                           align="center")
        y += 70
        draw_text(d, (M, y), kw["note"], font("bold", 44), CW, C["red"], line_gap=1.6, align="center")
    elif kind == "end":
        y = 660
        y += draw_text(d, (M, y), "解説とまとめ表は\n今朝のカルーセル投稿で", font("title", 66), CW, C["text"],
                       line_gap=1.5, align="center")
        y += 90
        draw_text(d, (M, y), "見返せるように保存！", font("title", 60), CW, C["red"], align="center")
        f = font("regular", 40)
        t = STYLE["handle"]
        d.text(((W - f.getlength(t)) / 2, H - 520), t, font=f, fill=C["text"])
    return img.convert("RGB")


# ---------------------------------------------------------------- 音声

def tts(text: str, lang: str, out: Path, silent: bool) -> float:
    """音声を生成して out(mp3) に保存し、長さ（秒）を返す。"""
    if silent:
        dur = max(1.5, len(text) * (0.07 if lang == "en" else 0.13))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=44100:cl=stereo", "-t", f"{dur:.2f}", str(out)], check=True)
        return dur
    import requests

    key = os.environ.get("GOOGLE_TTS_API_KEY")
    if not key:
        raise SystemExit("GOOGLE_TTS_API_KEY が未設定です（音声なしで試すなら --silent）")
    v = STYLE["voices"][lang]
    body = {"input": {"text": text},
            "voice": {"languageCode": v["languageCode"], "name": v["name"]},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": v.get("speakingRate", 1.0),
                            "sampleRateHertz": 44100}}
    r = requests.post(f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}",
                      json=body, timeout=60)
    r.raise_for_status()
    out.write_bytes(base64.b64decode(r.json()["audioContent"]))
    return duration(out)


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


# ---------------------------------------------------------------- 組み立て

def segment(img: Image.Image, audio: Path | None, dur: float, out: Path, tmp: Path):
    png = out.with_suffix(".png")
    img.save(png)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png)]
    if audio:
        cmd += ["-i", str(audio), "-af", "apad"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-t", f"{dur:.2f}", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(out)]
    subprocess.run(cmd, check=True)


def make(folder: Path, silent: bool) -> bool:
    p = load_post(folder)
    if not is_reel_day(p):
        print(f"SKIP [{folder.name}] リール対象日ではありません")
        return True
    src = json.dumps({k: p.get(k) for k in ("phrase", "cover", "phrases", "reel", "background")},
                     ensure_ascii=False, sort_keys=True) + json.dumps(STYLE, sort_keys=True) + str(silent)
    digest = hashlib.sha256(src.encode()).hexdigest()[:16]
    stamp = folder / ".reel_hash"
    if (folder / "reel.mp4").exists() and stamp.exists() and stamp.read_text().strip() == digest:
        print(f"SKIP [{folder.name}] 変更なし")
        return True
    idxs = p["reel"].get("phrase_indexes") or list(range(min(3, len(p["phrases"]))))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        segs = []

        def add(img, text=None, lang="en", pad=1.0, fixed=None):
            n = len(segs)
            audio = None
            dur = fixed or 2.5
            if text:
                audio = tmp / f"a{n}.mp3"
                dur = tts(text, lang, audio, silent) + pad
            out = tmp / f"s{n}.mp4"
            segment(img, audio, dur, out, tmp)
            segs.append(out)

        add(frame("hook", p), p["reel"]["hook"], "ja", pad=0.8)
        for i in idxs:
            it = p["phrases"][i]
            ens = it["en"] if isinstance(it["en"], list) else [it["en"]]
            add(frame("phrase", p, ens=ens, note=it.get("note", "")), "  ".join(ens), "en", pad=2.2)
        add(frame("end", p), fixed=3.0)

        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{s}'\n" for s in segs))
        out = folder / "reel.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
        frame("hook", p).save(folder / "reel_cover.jpg", quality=92)
    stamp.write_text(digest)
    print(f"OK [{folder.name}] reel.mp4 ({duration(out):.1f}秒)")
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    silent = "--silent" in args
    folders = [Path(a) for a in args if not a.startswith("--")]
    if not folders:
        sys.exit(__doc__)
    sys.exit(0 if all(make(f, silent) for f in folders) else 1)

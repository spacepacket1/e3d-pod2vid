#!/usr/bin/env python3
"""Render the cold-open sketch: faceless news-desk scene driven by per-line audio.
usage: render.py <timeline.json> <audio.wav> <out.mp4>
timeline.json: {"title": str, "ticker": [str], "lines": [{"speaker","text","start","end"}], "total": seconds}
"""
import json, math, subprocess, sys, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 24
tl = json.load(open(sys.argv[1])); wav = sys.argv[2]; out = sys.argv[3]
lines = tl["lines"]; total = tl["total"]

F = lambda p, s: ImageFont.truetype(p, s)
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
REG = "/System/Library/Fonts/Helvetica.ttc"
f_cap, f_name, f_title, f_tick, f_small, f_live = F(BOLD, 40), F(BLACK, 34), F(BLACK, 58), F(BOLD, 34), F(BOLD, 26), F(BLACK, 30)

CAST = {
    "ORACLE": dict(x=480, color=(70, 210, 190), label="ORACLE", sub="THE POLITE ONE"),
    "DANA":   dict(x=960, color=(255, 196, 90), label="DANA", sub="ANCHOR"),
    "GROK":   dict(x=1440, color=(235, 80, 80), label="GROK", sub="THE CONTRARIAN"),
}

# audio envelope -> per-frame loudness 0..1
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True).stdout
a = np.frombuffer(raw, dtype=np.float32)
spf = 16000 // FPS
nfr = int(math.ceil(total * FPS))
env = np.zeros(nfr)
for i in range(nfr):
    seg = a[i * spf:(i + 1) * spf]
    env[i] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
env = np.clip(env / (np.percentile(env, 97) + 1e-6), 0, 1)

def bg():
    img = Image.new("RGB", (W, H), (10, 14, 28))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(10 + 14 * t), int(14 + 16 * t), int(30 + 34 * t)))
    # studio wall panels
    for i, x in enumerate(range(-40, W, 260)):
        d.rectangle([x, 120, x + 230, 640], outline=(24, 34, 62), width=3)
    # desk
    d.rectangle([0, 700, W, 900], fill=(22, 26, 40)); d.rectangle([0, 700, W, 712], fill=(60, 70, 110))
    return img.filter(ImageFilter.GaussianBlur(0.6))
BG = bg()

def silhouette(d, cx, color, glow, pulse, who):
    base = 550
    g = int(30 + 90 * glow)
    c = tuple(int(v * (0.35 + 0.65 * glow)) for v in color)
    # glow halo
    for r, al in ((250, 14), (200, 22), (160, 34)):
        d.ellipse([cx - r, 340 - r, cx + r, 340 + r], fill=tuple(min(255, int(v * glow * al / 100 + 10)) for v in color))
    # shoulders + head
    d.ellipse([cx - 190, base - 120 + 0, cx + 190, base + 260], fill=(max(0, c[0] - 40), max(0, c[1] - 40), max(0, c[2] - 40)))
    hr = 92 + int(8 * pulse * glow)
    d.ellipse([cx - hr, 240 - hr // 2 + 20, cx + hr, 240 + hr + 20], fill=c)
    # identity flourish (no faces): ORACLE halo ring, GROK antenna slash, DANA headset arc
    if who == "ORACLE":
        d.ellipse([cx - 120, 112, cx + 120, 172], outline=c, width=7)
    elif who == "GROK":
        d.line([(cx + 40, 170), (cx + 120, 118)], fill=c, width=9); d.ellipse([cx + 108, 104, cx + 134, 130], fill=c)
    else:
        d.arc([cx - 105, 180, cx + 105, 380], 200, 340, fill=c, width=9)

def wrap(text, width=70):
    return textwrap.wrap(text, width=width)

def active_line(t):
    for L in lines:
        if L["start"] <= t < L["end"] + 0.25:
            return L
    return None

p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)

ticker = "   •   ".join(tl["ticker"]) + "   •   "
tw = int(f_tick.getlength(ticker))
for i in range(nfr):
    t = i / FPS
    img = BG.copy(); d = ImageDraw.Draw(img, "RGBA")
    L = active_line(t)
    spk = L["speaker"] if L else None
    for who, c in CAST.items():
        on = (who == spk)
        glow = (0.75 + 0.25 * env[i]) if on else 0.10
        silhouette(d, c["x"], c["color"], glow, env[i] if on else 0, who)
        # nameplate
        d.rounded_rectangle([c["x"] - 170, 650, c["x"] + 170, 730], 14, fill=(8, 10, 20, 230), outline=c["color"] if on else (70, 78, 110), width=4 if on else 2)
        d.text((c["x"], 677), c["label"], font=f_name, fill=c["color"] if on else (150, 158, 190), anchor="mm")
        d.text((c["x"], 711), c["sub"], font=f_small, fill=(210, 215, 235) if on else (110, 118, 150), anchor="mm")
        if on:  # audio bars
            for k in range(11):
                h = 8 + int(60 * env[i] * (0.4 + 0.6 * abs(math.sin(t * 9 + k * 1.3 + (hash(who) % 7)))))
                d.rectangle([c["x"] - 140 + k * 26, 640 - h, c["x"] - 140 + k * 26 + 14, 640], fill=c["color"])
    # top bar
    d.rectangle([0, 0, W, 96], fill=(8, 10, 22, 235))
    if int(t * 1.6) % 2 == 0: d.rounded_rectangle([40, 24, 150, 72], 8, fill=(220, 30, 40))
    else: d.rounded_rectangle([40, 24, 150, 72], 8, fill=(140, 20, 30))
    d.text((95, 48), "LIVE", font=f_live, fill=(255, 255, 255), anchor="mm")
    d.text((190, 48), tl["title"], font=f_title, fill=(255, 255, 255), anchor="lm")
    # caption
    if L:
        col = CAST[L["speaker"]]["color"]
        ls = wrap(L["text"])
        bh = 24 + 50 * len(ls)
        top = 926 - bh
        d.rounded_rectangle([90, top, W - 90, top + bh], 18, fill=(6, 8, 18, 225), outline=col, width=3)
        for j, s in enumerate(ls):
            d.text((130, top + 12 + 25 + 50 * j), s, font=f_cap, fill=(255, 255, 255), anchor="lm")
    # ticker
    d.rectangle([0, 936, W, 1020], fill=(190, 28, 38, 245)); d.rectangle([0, 936, W, 944], fill=(255, 255, 255, 230))
    off = int((t * 150) % tw)
    for x0 in (-off, -off + tw, -off + 2 * tw):
        d.text((x0, 980), ticker, font=f_tick, fill=(255, 255, 255), anchor="lm")
    d.text((W - 24, 1052), "AI-generated satire  •  voices and script are synthetic", font=f_small, fill=(170, 178, 205), anchor="rm")
    p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
print("rendered", out, f"{nfr} frames")

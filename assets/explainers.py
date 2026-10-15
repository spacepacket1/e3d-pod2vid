#!/usr/bin/env python3
"""Explainer animations for the e3d-brain film: each idea gets a purpose-built motion graphic.

Procedural (Pillow + numpy + ffmpeg). Each scene is f(p, t) -> RGB image on black, where p is progress 0..1.
The example notes, ids and lessons shown are illustrative samples, not real data.
"""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import ecosystem  # noqa: E402  (fonts and glow)

W, H = 1920, 1080
BG = np.array([4, 6, 14])
AMBER, ICE = (255, 176, 70), (130, 225, 255)
RED, GREEN = (255, 105, 105), (120, 235, 160)
TEXT, DIM = (236, 241, 250), (125, 140, 168)
CARD = (13, 19, 33)
MONO = next((c for c in ['/System/Library/Fonts/Menlo.ttc', '/System/Library/Fonts/Monaco.ttf',
                         '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'] if Path(c).exists()), None)


def mono(size):
    from PIL import ImageFont
    return ImageFont.truetype(MONO, size) if MONO else ImageFont.load_default()


def clip(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ramp(p, a, b):
    return clip((p - a) / (b - a)) if b > a else float(p >= a)


def ease(x):
    x = clip(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, x):
    return a + (b - a) * x


def fade(col, a):
    """Colour at opacity a over black (the glow pass adds the navy background)."""
    return tuple(int(c * clip(a)) for c in col)


def canvas():
    img = Image.new('RGB', (W, H), (0, 0, 0))
    return img, ImageDraw.Draw(img)


def title(d, text, a=1.0, y=70):
    d.text((W / 2, y), text, font=ecosystem.font(58, True), fill=fade(TEXT, a), anchor='ma')


def card(d, x, y, w, h, head=None, body=None, outline=ICE, a=1.0, headcol=None, bodycol=None, fillcol=CARD):
    d.rounded_rectangle([x, y, x + w, y + h], radius=22, fill=fade(fillcol, a), outline=fade(outline, a), width=4)
    if head:
        d.text((x + 28, y + 22), head, font=ecosystem.font(46, True), fill=fade(headcol or TEXT, a))
    if body:
        for k, line in enumerate(body.split('\n')):
            d.text((x + 28, y + 90 + 48 * k), line, font=ecosystem.font(35), fill=fade(bodycol or DIM, a))


def mark_x(d, cx, cy, r, col, a=1.0, w=9):
    c = fade(col, a)
    d.line([(cx - r, cy - r), (cx + r, cy + r)], fill=c, width=w)
    d.line([(cx - r, cy + r), (cx + r, cy - r)], fill=c, width=w)


def mark_check(d, cx, cy, r, col, a=1.0, w=9):
    d.line([(cx - r, cy), (cx - r * 0.3, cy + r * 0.8), (cx + r, cy - r * 0.8)], fill=fade(col, a), width=w)


def chip(d, x, y, text, col=AMBER, a=1.0, size=28):
    f = mono(size)
    w = d.textlength(text, font=f) + 36
    d.rounded_rectangle([x, y, x + w, y + size + 22], radius=16, outline=fade(col, a), width=3, fill=fade((20, 26, 40), a))
    d.text((x + 18, y + 10), text, font=f, fill=fade(col, a))
    return w


def thread(d, p0, p1, grow, col=AMBER, a=1.0, width=4, bend=0.1):
    mid = ((p0[0] + p1[0]) / 2 + (p1[1] - p0[1]) * bend, (p0[1] + p1[1]) / 2 - (p1[0] - p0[0]) * bend)
    pts = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * mid[0] + t * t * p1[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * mid[1] + t * t * p1[1]) for t in np.linspace(0, 1, 50)]
    n = max(2, int(len(pts) * clip(grow)))
    d.line(pts[:n], fill=fade(col, a), width=width)
    return pts[n - 1]


# ── scenes ────────────────────────────────────────────────────────────────────
def scene_what_if(p, t):
    """Scattered notes converge into one shared memory."""
    img, d = canvas()
    rng = np.random.default_rng(11)
    labels = ['decision', 'lesson', 'note', 'why', 'idea', 'dead end', 'decision', 'note', 'lesson', 'why', 'idea', 'note']
    cols, rows = 4, 3
    for i, lab in enumerate(labels):
        sx, sy = rng.uniform(150, W - 450), rng.uniform(150, H - 300)
        sx += 40 * math.sin(t * 0.9 + i); sy += 30 * math.cos(t * 0.7 + i * 1.7)
        gx = W / 2 - 520 + (i % cols) * 270
        gy = H / 2 - 190 + (i // cols) * 150
        k = ease(ramp(p, 0.30 + 0.015 * i, 0.68 + 0.01 * i))
        x, y = lerp(sx, gx, k), lerp(sy, gy, k)
        d.rounded_rectangle([x, y, x + 240, y + 110], radius=16, fill=fade(CARD, 1), outline=fade(ICE if k < 1 else AMBER, 1), width=3)
        d.text((x + 24, y + 34), lab, font=ecosystem.font(34, True), fill=fade(TEXT, 1))
    glow = ease(ramp(p, 0.68, 0.95))
    if glow > 0:
        d.rounded_rectangle([W / 2 - 560, H / 2 - 230, W / 2 + 560, H / 2 + 250], radius=40, outline=fade(AMBER, glow), width=6)
        d.text((W / 2, H / 2 + 300), 'one shared memory', font=ecosystem.font(60, True), fill=fade(TEXT, glow), anchor='ma')
    return img


def scene_vault(p, t):
    """Plain Markdown notes in a folder on your own machine."""
    img, d = canvas()
    title(d, 'plain Markdown, on your own machine', ease(ramp(p, 0, 0.12)))
    a0 = ease(ramp(p, 0, 0.1))
    d.rounded_rectangle([150, 190, 860, 850], radius=24, fill=fade(CARD, a0), outline=fade(ICE, a0), width=4)
    d.text((190, 215), 'Brain/', font=ecosystem.font(44, True), fill=fade(TEXT, a0))
    files = [('decisions/', 'use-sqlite.md'), ('why/', 'simple-to-run.md'), ('dead-ends/', 'tried-postgres.md')]
    for i, (dr, fn) in enumerate(files):
        a = ease(ramp(p, 0.12 + 0.17 * i, 0.26 + 0.17 * i))
        y = 320 + i * 140
        d.rounded_rectangle([190, y, 820, y + 100], radius=16, outline=fade(AMBER if i == 0 else DIM, a), width=3, fill=fade((18, 24, 40), a))
        d.text((220, y + 14), dr, font=mono(26), fill=fade(DIM, a))
        d.text((220, y + 52), fn, font=mono(32), fill=fade(TEXT, a))
    a1 = ease(ramp(p, 0.22, 0.34))
    d.rounded_rectangle([920, 190, 1780, 850], radius=24, fill=fade(CARD, a1), outline=fade(AMBER, a1), width=4)
    src = ('---\nkind: decision\nstatus: accepted\n---\n# Use SQLite\n\nSimpler to run: one file.\n'
           'We tried Postgres first.')
    n = int(len(src) * ease(ramp(p, 0.30, 0.88)))
    for k, line in enumerate(src[:n].split('\n')):
        col = AMBER if line.startswith('#') else (DIM if line in ('---',) or ':' in line else TEXT)
        d.text((960, 225 + 56 * k), line, font=mono(34), fill=fade(col, a1))
    return img


def scene_cite(p, t):
    """A note points back to where it came from."""
    img, d = canvas()
    title(d, 'every note points back to where it came from', ease(ramp(p, 0, 0.12)))
    a = ease(ramp(p, 0.04, 0.2))
    card(d, 170, 360, 620, 250, 'Use SQLite', 'status: accepted', AMBER, a)
    cw = chip(d, 190, 640, 'note:01J8Z4K@4f2a9c1e', AMBER, ease(ramp(p, 0.18, 0.3)), 30)
    srcs = [('commit', 'a3f9c21'), ('decision', 'ops simplicity'), ('outcome', 'oc_456')]
    for i, (kind, name) in enumerate(srcs):
        y = 250 + i * 230
        g = ease(ramp(p, 0.30 + 0.16 * i, 0.50 + 0.16 * i))
        end = thread(d, (790, 485), (1130, y + 80), g, AMBER, 1.0, 4)
        ca = ease(ramp(p, 0.42 + 0.16 * i, 0.55 + 0.16 * i))
        card(d, 1130, y, 600, 160, kind, name, ICE, ca)
        ck = ease(ramp(p, 0.55 + 0.16 * i, 0.66 + 0.16 * i))
        d.text((1690, y + 60), 'fresh', font=ecosystem.font(30, True), fill=fade(GREEN, ck), anchor='ra')
    return img


def scene_tried(p, t):
    """A new idea is checked against what was already tried."""
    img, d = canvas()
    title(d, 'it checks what we already tried', ease(ramp(p, 0, 0.12)))
    x = lerp(-700, 190, ease(ramp(p, 0.04, 0.26)))
    bad = ease(ramp(p, 0.52, 0.62))
    col = tuple(int(lerp(ICE[k], RED[k], bad)) for k in range(3))
    card(d, x, 390, 640, 220, 'New idea', 'use Postgres', col, 1.0)
    # scan sweep
    sw = ramp(p, 0.30, 0.50)
    if 0 < sw < 1:
        sx = 190 + 640 * sw
        d.line([(sx, 360), (sx, 640)], fill=fade(ICE, 1 - abs(sw - 0.5) * 1.2), width=6)
    ma = ease(ramp(p, 0.34, 0.5))
    card(d, 1090, 390, 640, 220, 'Memory', 'tried before. failed:\ntoo heavy to run', RED, ma, headcol=AMBER)
    thread(d, (830, 500), (1090, 500), ease(ramp(p, 0.42, 0.56)), RED, ma, 4, 0.0)
    if bad > 0:
        mark_x(d, x + 560, 480, 36, RED, bad)
    ra = ease(ramp(p, 0.70, 0.85))
    if ra > 0:
        card(d, 190, 700, 640, 200, 'Revised', 'use SQLite', GREEN, ra, headcol=GREEN)
        mark_check(d, 770, 800, 38, GREEN, ra)
    return img


def scene_tidy(p, t):
    """Replaced decisions, merged duplicates, stale notes."""
    img, d = canvas()
    title(d, 'it tidies itself', ease(ramp(p, 0, 0.1)))
    cw, ch = 480, 190
    xs = [150, 720, 1290]
    heads = ['replaced', 'merged', 'stale']
    for i, hx in enumerate(xs):
        d.text((hx + cw / 2, 200), heads[i], font=ecosystem.font(44, True), fill=fade(DIM, ease(ramp(p, 0, 0.1))), anchor='ma')
    # 1 replaced
    k = ease(ramp(p, 0.10, 0.30))
    oa = 1 - 0.65 * k
    card(d, xs[0], 300, cw, ch, 'Use Postgres', 'old decision', DIM if k > 0.5 else ICE, oa)
    if k > 0.4:
        chip(d, xs[0] + 30, 300 + ch + 18, 'superseded', AMBER, ease(ramp(p, 0.2, 0.3)), 26)
    na = ease(ramp(p, 0.16, 0.34))
    card(d, xs[0], 640, cw, ch, 'Use SQLite', 'newer decision', GREEN, na, headcol=GREEN)
    thread(d, (xs[0] + cw / 2, 300 + ch + 70), (xs[0] + cw / 2, 640), ease(ramp(p, 0.22, 0.34)), AMBER, 1.0, 4, 0.0)
    # 2 merged
    m = ease(ramp(p, 0.42, 0.62))
    ya = lerp(300, 420, m)
    yb = lerp(640, 420, m)
    card(d, xs[1], ya, cw, ch, 'Setup notes', 'how to install', ICE, 1.0 - 0.0 * m)
    if m < 0.98:
        card(d, xs[1], yb, cw, ch, 'Setup notes', 'how to install', ICE, 1.0)
    else:
        card(d, xs[1], 420, cw, ch, 'Setup notes', 'merged into one', GREEN, 1.0, headcol=GREEN)
    # 3 stale
    s = ease(ramp(p, 0.72, 0.90))
    card(d, xs[2], 420, cw, ch, 'API key rotation', 'last used long ago', DIM if s > 0.4 else ICE, 1.0 - 0.55 * s)
    if s > 0.4:
        chip(d, xs[2] + 30, 420 + ch + 18, 'stale', AMBER, ease(ramp(p, 0.8, 0.9)), 26)
    return img


def scene_lessons(p, t):
    """Real outcomes become a cited lesson that waits for a human."""
    img, d = canvas()
    title(d, 'it reads real outcomes and proposes lessons we can trust', ease(ramp(p, 0, 0.1)))
    cx, cy = 1080, 540
    for i in range(5):
        y = 270 + i * 130
        a = ease(ramp(p, 0.05 + 0.07 * i, 0.15 + 0.07 * i))
        d.ellipse([200, y, 260, y + 60], outline=fade(ICE, a), width=4, fill=fade(CARD, a))
        d.text((290, y + 14), f'outcome {i + 1}', font=ecosystem.font(30), fill=fade(DIM, a))
        g = ease(ramp(p, 0.28 + 0.05 * i, 0.50 + 0.05 * i))
        thread(d, (260, y + 30), (cx - 40, cy), g, AMBER, a, 3, 0.05)
    la = ease(ramp(p, 0.50, 0.66))
    card(d, cx - 40, cy - 150, 700, 300, 'Lesson (proposed)', 'small changes shipped\nsooner held up better', AMBER, la, headcol=AMBER, bodycol=TEXT)
    c1 = ease(ramp(p, 0.64, 0.76)); c2 = ease(ramp(p, 0.70, 0.82))
    chip(d, cx - 20, cy + 175, 'outcome:oc_456', AMBER, c1, 26)
    chip(d, cx + 330, cy + 175, 'thesis:th_123', AMBER, c2, 26)
    ba = ease(ramp(p, 0.82, 0.94))
    d.text((cx + 310, cy + 270), 'waits for a human to accept', font=ecosystem.font(36, True), fill=fade(GREEN, ba), anchor='ma')
    d.text((W / 2, H - 70), 'example', font=ecosystem.font(24), fill=fade(DIM, 0.7), anchor='ma')
    return img


def scene_speed(p, t):
    """Start from zero every time, versus start from what we know."""
    img, d = canvas()
    title(d, 'nobody starts from zero', ease(ramp(p, 0, 0.1)))
    for lane, (label, y) in enumerate([('without memory', 330), ('with memory', 650)]):
        d.text((200, y - 70), label, font=ecosystem.font(44, True), fill=fade(DIM if lane == 0 else AMBER, ease(ramp(p, 0.05, 0.15))))
        d.rounded_rectangle([200, y, 1720, y + 90], radius=24, outline=fade(DIM, 0.8), width=3)
    q = ramp(p, 0.12, 0.92)
    # lane 1: three attempts, each restarts at zero
    cyc = (q * 3) % 1.0
    run = 1 if q < 1 else 0
    d.rounded_rectangle([206, 336, 206 + 1500 * 0.5 * ease(cyc), 414], radius=18, fill=fade(DIM, 0.9))
    for k in range(int(q * 3)):
        d.text((1720 - 260 * k, 270), 'start over', font=ecosystem.font(34, True), fill=fade(RED, 0.9), anchor='ra')
    # lane 2: keeps what it learned
    d.rounded_rectangle([206, 656, 206 + 1500 * ease(q), 734], radius=18, fill=fade(AMBER, 0.95))
    if q > 0.9:
        d.text((1700, 790), 'keeps what it learned', font=ecosystem.font(36, True), fill=fade(GREEN, ramp(q, 0.9, 1)), anchor='ra')
    return img


_BRAIN = {}


def _brain():
    if not _BRAIN:
        sys.path.insert(0, str(Path(__file__).parent))
        import brain_motif as bm
        bm.W, bm.H = 1280, 720
        pts, edges = bm.build()
        R = bm.rot_y(0.15) @ bm.rot_x(0.28)
        q = pts @ R.T
        depth = (q[:, 2] - q[:, 2].min()) / (np.ptp(q[:, 2]) + 1e-9)
        scale = 0.62 * H
        xy = np.stack([W / 2 + q[:, 0] * scale, H / 2 - q[:, 1] * scale + 20], axis=1)
        rng = np.random.default_rng(5)
        scatter = np.stack([rng.uniform(100, W - 100, len(pts)), rng.uniform(100, H - 100, len(pts))], axis=1)
        _BRAIN.update(xy=xy, edges=edges, depth=depth, scatter=scatter, delay=rng.uniform(0, 0.45, len(pts)))
    return _BRAIN


def scene_assemble(p, t):
    """The brain assembles itself."""
    b = _brain()
    img, d = canvas()
    k = np.array([ease(ramp(p, 0.03 + 0.55 * dl, 0.03 + 0.55 * dl + 0.42)) for dl in b['delay']])
    pos = b['scatter'] + (b['xy'] - b['scatter']) * k[:, None]
    ea = ease(ramp(p, 0.50, 0.80))
    if ea > 0:
        for a_, b_ in b['edges']:
            kk = min(k[a_], k[b_])
            if kk > 0.95:
                d.line([tuple(pos[a_]), tuple(pos[b_])], fill=fade(AMBER, 0.5 * ea + 0.1), width=2)
    for i in np.argsort(b['depth']):
        x, y = pos[i]
        r = 2.0 + 3.0 * b['depth'][i]
        d.ellipse([x - r, y - r, x + r, y + r], fill=fade(ICE, 0.35 + 0.65 * b['depth'][i]))
    return img


SCENES = {'what_if': scene_what_if, 'vault': scene_vault, 'cite': scene_cite, 'tried': scene_tried,
          'tidy': scene_tidy, 'lessons': scene_lessons, 'speed': scene_speed, 'assemble': scene_assemble}


def render(name, dur, out_mp4, fps=24, ffmpeg='ffmpeg'):
    n = max(int(dur * fps), 2)
    fn = SCENES[name]
    with tempfile.TemporaryDirectory() as d:
        for f in range(n):
            p = f / (n - 1)
            ecosystem.with_glow(fn(p, f / fps)).save(f'{d}/f{f:05d}.jpg', quality=92)
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', f'{d}/f%05d.jpg',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', str(out_mp4)], check=True)


if __name__ == '__main__':
    # quick preview: python3 assets/explainers.py <scene> [p]  -> /tmp-style png in the cwd
    name = sys.argv[1]
    pp = float(sys.argv[2]) if len(sys.argv) > 2 else 0.9
    ecosystem.with_glow(SCENES[name](pp, pp * 6)).save(f'preview_{name}.png')
    print(f'preview_{name}.png')

#!/usr/bin/env python3
"""Ecosystem graph: e3d-brain at the centre, threads out to the systems that get a memory.

Used for the concept film (a timed video) and for docs/assets/ecosystem.png (a still).
Procedural: Pillow + numpy + ffmpeg. The spinning brain comes from brain_motif / render_brain.
"""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
CX, CY = W // 2, 450
RX, RY = 540, 222
BG = (4, 6, 14)
AMBER, ICE = np.array([255, 176, 70]), np.array([130, 225, 255])

NODES = [   # key, name, what the memory gives it
    ('claude', 'Claude Code', 'picks up where you left off'),
    ('pilot', 'e3d-pilot', 'checks what was already tried'),
    ('corp', 'e3d-corp', 'weighs past outcomes'),
    ('creative', 'e3d-creative', 'remembers audience and voice'),
    ('agent', 'e3d-agent', 'wakes up knowing yesterday'),
    ('stories', 'e3d.ai stories', 'recalls what it already covered'),
]
ANGLES = [-90, -30, 30, 90, 150, 210]


def font(size, bold=False):
    for c in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
              '/System/Library/Fonts/Helvetica.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def node_xy(i):
    a = math.radians(ANGLES[i])
    return CX + RX * math.cos(a), CY + RY * math.sin(a)


def bezier(p0, p1, p2, n=60):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def layer(t, grow=1.0, highlight=None, base=0.55, caption=None):
    """One frame of the graph WITHOUT the brain. grow: thread growth 0..1; highlight: node key or None;
    base: brightness of non-highlighted nodes (1.0 = all lit)."""
    img = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    fn, fd = font(46, True), font(28)
    for i, (key, name, sub) in enumerate(NODES):
        x, y = node_xy(i)
        hl = highlight == key
        k = 1.0 if hl else base
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (1.1 * t + i / 6))
        # thread, curved a little so it feels organic
        mid = ((CX + x) / 2 + (y - CY) * 0.12, (CY + y) / 2 - (x - CX) * 0.12)
        pts = bezier((CX, CY), mid, (x, y))
        upto = max(2, int(len(pts) * min(grow, 1.0)))
        col = tuple((AMBER * (0.25 + 0.75 * k)).astype(int))
        d.line(pts[:upto], fill=col, width=5 if hl else 3)
        if upto >= 4:   # a pulse of light travelling out along the thread
            j = int((t * 0.5 + i * 0.17) % 1.0 * (upto - 1))
            px, py = pts[j]
            r = 9 if hl else 6
            d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 245, 220))
        if grow < 0.98 and not hl:
            continue
        # node
        r = (30 + 8 * pulse) if hl else 18
        ncol = tuple((ICE * (0.35 + 0.65 * k)).astype(int)) if not hl else (255, 240, 205)
        d.ellipse([x - r, y - r, x + r, y + r], fill=ncol)
        d.ellipse([x - r - 10, y - r - 10, x + r + 10, y + r + 10], outline=ncol, width=3)
        # label, pushed outward from the centre
        tc = (255, 244, 225) if hl else tuple((np.array([210, 220, 235]) * (0.45 + 0.55 * k)).astype(int))
        sc = (255, 190, 90) if hl else tuple((np.array([170, 180, 200]) * (0.4 + 0.6 * k)).astype(int))
        a = ANGLES[i] % 360
        if a in (270,):            # top: label above
            d.text((x, y - r - 96), name, font=fn, fill=tc, anchor='ma')
            d.text((x, y - r - 40), sub, font=fd, fill=sc, anchor='ma')
        elif a == 90:              # bottom: label below
            d.text((x, y + r + 24), name, font=fn, fill=tc, anchor='ma')
            d.text((x, y + r + 76), sub, font=fd, fill=sc, anchor='ma')
        elif math.cos(math.radians(a)) > 0:   # right side: left-aligned beside the node
            d.text((x + r + 30, y - 40), name, font=fn, fill=tc, anchor='la')
            d.text((x + r + 30, y + 14), sub, font=fd, fill=sc, anchor='la')
        else:                       # left side: right-aligned beside the node
            d.text((x - r - 30, y - 40), name, font=fn, fill=tc, anchor='ra')
            d.text((x - r - 30, y + 14), sub, font=fd, fill=sc, anchor='ra')
    if caption:
        d.text((W / 2, H - 60), caption, font=font(26), fill=(150, 165, 190), anchor='ma')
    return img


def brain_mask(w=1280, h=720):
    """Soft elliptical falloff so the brain video's haze never shows a rectangle."""
    y, x = np.mgrid[0:h, 0:w]
    m = 1 - (((x - w / 2) / (w * 0.40)) ** 2 + ((y - h * 0.48) / (h * 0.47)) ** 2)
    return np.clip(m, 0, 1) ** 0.9


def masked_brain(src, dst, ffmpeg='ffmpeg'):
    with tempfile.TemporaryDirectory() as d:
        mp = Path(d) / 'mask.png'
        Image.fromarray((brain_mask() * 255).astype('uint8')).convert('RGB').save(mp)
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(src), '-loop', '1', '-i', str(mp), '-filter_complex',
                        '[1:v][0:v]scale2ref[m][a0];[a0]format=gbrp[a];[m]format=gbrp[mm];[a][mm]blend=all_mode=multiply:shortest=1,format=yuv420p',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', str(dst)], check=True)


def with_glow(img):
    small = img.resize((W // 4, H // 4), Image.LANCZOS).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.LANCZOS)
    arr = np.asarray(img, float) + np.asarray(small, float) * 1.3
    base = np.zeros((H, W, 3)) + np.array(BG)
    return Image.fromarray(np.clip(arr + base, 0, 255).astype('uint8'))


def static_png(out, brain_png_loader, caption=None):
    """Fully lit still with the brain at the centre."""
    g = with_glow(layer(0.35, grow=1.0, highlight=None, base=1.0, caption=caption))
    b = brain_png_loader()                      # RGB brain on near-black, ~ 700 px tall
    arr = np.asarray(g, float)
    bx, by = (W - b.width) // 2, (H - b.height) // 2
    arr[by:by + b.height, bx:bx + b.width] += np.asarray(b, float) * 1.1
    Image.fromarray(np.clip(arr, 0, 255).astype('uint8')).save(out)


def render_timeline(segments, out_mp4, brain_mp4, fps=20, ffmpeg='ffmpeg'):
    """segments: list of (duration_s, mode, node) with mode in 'grow' | 'all' | 'hl'."""
    total = sum(s[0] for s in segments)
    n = int(total * fps)
    t0, bounds = 0.0, []
    for dur, mode, node in segments:
        bounds.append((t0, t0 + dur, mode, node)); t0 += dur
    with tempfile.TemporaryDirectory() as d:
        for f in range(n):
            t = f / fps
            seg = next((b for b in bounds if b[0] <= t < b[1]), bounds[-1])
            lt = (t - seg[0]) / max(seg[1] - seg[0], 1e-6)
            mode, node = seg[2], seg[3]
            if mode == 'grow':
                img = layer(t, grow=min(1.0, lt * 1.3), base=0.55)
            elif mode == 'all':
                img = layer(t, grow=1.0, base=1.0)
            else:
                img = layer(t, grow=1.0, highlight=node, base=0.5)
            with_glow(img).save(f'{d}/g{f:05d}.jpg', quality=92)
        graph = Path(d) / 'graph.mp4'
        masked = Path(d) / 'brain_masked.mp4'
        masked_brain(brain_mp4, masked, ffmpeg)
        brain_mp4 = masked
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', f'{d}/g%05d.jpg',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', str(graph)], check=True)
        # add the spinning brain at the centre (additive, RGB), key out its navy backdrop
        fc = ("[1:v]lutrgb=r='clip(val*1.3-8,0,255)':g='clip(val*1.3-10,0,255)':b='clip(val*1.3-20,0,255)',"
              "scale=-2:560,format=yuv420p[b];color=black:s=1920x1080:r=%d,format=yuv420p[c];"
              "[c][b]overlay=x=(W-w)/2:y=%d-h/2:shortest=1,format=gbrp[h];"
              "[0:v]format=gbrp[g];[g][h]blend=all_mode=addition:shortest=1,format=yuv420p[v]" % (fps, CY))
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(graph), '-stream_loop', '-1', '-i', str(brain_mp4),
                        '-filter_complex', fc, '-map', '[v]', '-t', f'{total:.2f}', '-r', str(fps), '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', '-crf', '18', str(out_mp4)], check=True)

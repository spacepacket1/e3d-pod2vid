#!/usr/bin/env python3
"""Render docs/assets/brain-spin.gif: a glowing neural "brain" slowly spinning in 3D.

Procedural (numpy + Pillow + ffmpeg); no network, no paid services.
  python3 docs/assets/render_brain.py [out.gif]
The loop is seamless: one full rotation, and every pulse completes whole cycles.
"""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 640, 360
SS = 2                      # supersampling
FRAMES, FPS = 96, 16        # 6 second loop
N_NODES, K_NEAR = 1500, 3
BG = (4, 6, 14)
AMBER, ICE = np.array([255, 170, 60]), np.array([120, 220, 255])
rng = np.random.default_rng(7)


def hemisphere(n, side):
    """Points on a lumpy ellipsoid half; `side` = -1 left, +1 right."""
    v = rng.normal(size=(n * 3, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    v = v[(v[:, 0] * side) > 0.02][:n]
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    # gyri: layered sinusoidal folding on the surface
    fold = (0.055 * np.sin(9 * y + 4 * z) * np.cos(7 * x + 3 * z)
            + 0.04 * np.sin(14 * z + 5 * y) + 0.025 * np.sin(23 * x + 17 * y))
    r = 1.0 + fold
    pts = np.stack([x * 0.62 * r + side * 0.045, y * 0.66 * r - 0.02, z * 0.92 * r], axis=1)
    pts[:, 1] = np.where(pts[:, 1] < -0.36, -0.36 + (pts[:, 1] + 0.36) * 0.35, pts[:, 1])  # flat underside
    return pts


def build():
    left, right = hemisphere(N_NODES // 2, -1), hemisphere(N_NODES // 2, 1)
    cb = rng.normal(size=(170, 3))
    cb /= np.linalg.norm(cb, axis=1, keepdims=True)
    cb = cb * np.array([0.34, 0.2, 0.26]) + np.array([0.0, -0.45, -0.7])
    stem = np.stack([rng.normal(0, 0.05, 40), np.linspace(-0.4, -0.85, 40), rng.normal(0, 0.05, 40) - 0.35], axis=1)
    pts = np.vstack([left, right, cb, stem])
    # k-nearest-neighbour "synapses"
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
    np.fill_diagonal(d, 9)
    nn = np.argsort(d, axis=1)[:, :K_NEAR]
    edges = {tuple(sorted((i, int(j)))) for i in range(len(pts)) for j in nn[i]}
    return pts, np.array(sorted(edges))


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def frame(pts, edges, phase, t, tilt):
    R = rot_y(2 * math.pi * t) @ rot_x(tilt)
    p = pts @ R.T
    depth = (p[:, 2] - p[:, 2].min()) / (np.ptp(p[:, 2]) + 1e-9)          # 0 far .. 1 near
    scale = 0.6 * H * SS
    cx, cy = W * SS / 2, H * SS / 2
    persp = 1.0 / (1.0 + 0.25 * (1 - depth))
    sx, sy = cx + p[:, 0] * scale * persp * 1.0, cy - p[:, 1] * scale * persp * 1.0
    pulse = 0.5 + 0.5 * np.sin(2 * math.pi * (2 * t) + phase)             # 2 whole cycles per loop
    glow = Image.new('RGB', (W * SS, H * SS), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for a, b in edges:
        k = 0.5 * (depth[a] + depth[b])
        e = 0.5 * (pulse[a] + pulse[b])
        col = (AMBER * (0.25 + 0.7 * k) * (0.45 + 0.9 * e)).clip(0, 255).astype(int)
        gd.line([(sx[a], sy[a]), (sx[b], sy[b])], fill=tuple(col), width=max(1, int(SS * (0.6 + k))))
    for i in np.argsort(depth):
        k, e = depth[i], pulse[i]
        r = SS * (0.7 + 1.3 * k + 1.4 * e * e)
        mix = e * e
        col = ((ICE * (1 - mix) + np.array([255, 245, 220]) * mix) * (0.22 + 0.5 * k)).clip(0, 255).astype(int)
        gd.ellipse([sx[i] - r, sy[i] - r, sx[i] + r, sy[i] + r], fill=tuple(col))
    bloom = glow.filter(ImageFilter.GaussianBlur(SS * 6))
    wide = glow.filter(ImageFilter.GaussianBlur(SS * 22))
    base = Image.new('RGB', glow.size, BG)
    out = Image.blend(base, base, 0)
    arr = (np.asarray(base, float) + np.asarray(glow, float) * 0.85
           + np.asarray(bloom, float) * 0.95 + np.asarray(wide, float) * 0.6)
    out = Image.fromarray(arr.clip(0, 255).astype('uint8'))
    return out.resize((W, H), Image.LANCZOS)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'docs/assets/brain-spin.gif')
    pts, edges = build()
    phase = rng.uniform(0, 2 * math.pi, len(pts))
    # neighbours pulse in sympathy: smooth phase by position so firing "travels"
    phase = 0.5 * phase + 3.0 * (pts[:, 2] + pts[:, 1])
    with tempfile.TemporaryDirectory() as d:
        for f in range(FRAMES):
            frame(pts, edges, phase, f / FRAMES, 0.28).save(f'{d}/f{f:04d}.png')
        pal = f'{d}/pal.png'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{d}/f%04d.png',
                        '-vf', 'palettegen=max_colors=64:stats_mode=full', pal], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{d}/f%04d.png',
                        '-i', pal, '-lavfi', 'paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle', '-loop', '0', str(out)], check=True)
    print(out, f'{out.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()

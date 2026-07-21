#!/usr/bin/env python3
"""
make_registry_short.py  —  e3d-pod2vid

Hand-scripted, dramatic YouTube Short announcing e3d.ai's new positioning:
an intelligent token registry and listing service — for tokens ("scrips"),
autonomous AI agents, and the gamified leaderboard their on-chain proof
creates. Narrated in the "nova" OpenAI TTS voice.

Closing card: gold "REGISTRY VERIFIED" seal instead of the default blue CTA.

Usage:
  python3 make_registry_short.py [output.mp4]
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DIR    = Path(__file__).parent
OUTPUT = str(Path(sys.argv[1] if len(sys.argv) > 1 else 'output/e3d-registry-short.mp4').resolve())
W, H   = 1080, 1920

SITE_URL   = 'e3d.ai'
GOLD       = '#FFB800'

SEGMENTS = [
    # Problem — the anonymous graveyard of unclaimed tokens. Voice starts immediately
    # (no silent hook); both opening lines run over the same abandoned-building clip so
    # the first word of narration lands exactly when that footage appears.
    ('Every day, thousands of tokens are born on-chain.',
     'abandoned dark building empty forgotten interior'),
    ('And almost all of them die anonymous. No name claimed. No team standing behind them.',
     'abandoned dark building empty forgotten interior'),
    ('Somewhere out there is a real team, behind a real project — with no way on earth to prove it is theirs.',
     'person alone office late night working laptop'),
    # Turn — e3d.ai already sees everything
    ('e3d.ai already watches every wallet. Every trade. Every agent. The entire chain, alive.',
     'data visualization world network glowing map'),
    # Product — the registry
    ('Now it becomes the registry. Claim your token. Prove it is yours — on-chain, not on a form.',
     'golden verified badge checkmark glowing award ceremony'),
    # Agents
    ('And it is not only humans anymore. Autonomous agents claim their own tokens, spend their own treasury, prove their own worth.',
     'futuristic robot artificial intelligence control room technology'),
    # Gamification
    ('Every claim. Every burn. Every proof. It becomes score — a leaderboard the whole market can see.',
     'stadium scoreboard crowd cheering lights arena'),
    # Stakes
    ('This is not a gatekeeper. This is not a favor from a reviewer. This is proof that cannot be faked.',
     'chains breaking free dramatic light power'),
    # CTA
    ('e3d.ai. The intelligent registry for tokens, for agents, for the entire game.',
     'sunrise dawn city skyline hope new beginning'),
]

# ── Fonts ─────────────────────────────────────────────────────────────────────

def load_font(size):
    for p in [
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default(size)

# ── Closing card: gold registry seal ─────────────────────────────────────────

def draw_seal(draw, cx, cy, r):
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=GOLD, width=6)
    p1, p2, p3 = (cx - r * 0.45, cy), (cx - r * 0.1, cy + r * 0.35), (cx + r * 0.5, cy - r * 0.35)
    draw.line([p1, p2], fill=GOLD, width=8)
    draw.line([p2, p3], fill=GOLD, width=8)

def render_registry_card(out_path):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    band_top, band_bot = H // 2 - 280, H // 2 + 280
    draw.rectangle([(0, band_top), (W, band_bot)], fill=(0, 0, 0, 220))
    draw.rectangle([(50, band_top - 5), (W - 50, band_top)],    fill=GOLD)
    draw.rectangle([(50, band_bot),     (W - 50, band_bot + 5)], fill=GOLD)

    cx = W // 2
    y  = band_top + 40

    draw_seal(draw, cx, y + 34, 38)
    y += 100

    f_small = load_font(30)
    label   = 'REGISTRY VERIFIED'
    bbox    = draw.textbbox((0, 0), label, font=f_small)
    draw.text(((W - bbox[2]) // 2, y), label, font=f_small, fill=(200, 200, 200, 230))
    y += bbox[3] + 22

    f_big  = load_font(58)
    name   = 'e3d.ai'
    bbox   = draw.textbbox((0, 0), name, font=f_big)
    draw.text(((W - bbox[2]) // 2, y), name, font=f_big, fill=GOLD)
    y += bbox[3] + 24

    f_url = load_font(30)
    bbox  = draw.textbbox((0, 0), SITE_URL, font=f_url)
    draw.text(((W - bbox[2]) // 2, y), SITE_URL, font=f_url, fill=(255, 224, 150, 220))
    y += bbox[3] + 30

    draw.rectangle([(cx - 160, y), (cx + 160, y + 2)], fill=(255, 255, 255, 80))
    y += 20

    f_sub  = load_font(28)
    sub    = 'Tokens · Agents · Proof'
    bbox   = draw.textbbox((0, 0), sub, font=f_sub)
    draw.text(((W - bbox[2]) // 2, y), sub, font=f_sub, fill=(210, 210, 210, 220))

    img.save(out_path)

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    out_dir = Path(OUTPUT).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix='registry_short_'))

    spec = importlib.util.spec_from_file_location('make_short', DIR / 'make_short.py')
    ms   = importlib.util.module_from_spec(spec)
    os.environ.setdefault('SHORT_VOICE', 'nova')
    spec.loader.exec_module(ms)

    ms.OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
    ms.PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')
    ms.VOICE      = 'nova'
    ms.OUTPUT     = OUTPUT
    ms.OUT_DIR    = out_dir
    ms.BROLL_DIR  = out_dir / 'broll-registry'
    ms.TTS_DIR    = out_dir / 'tts-registry'
    ms.SCRATCH    = str(tmp_dir)
    ms.SEGMENTS   = SEGMENTS
    ms.CTA_TEXT   = SITE_URL
    ms.HOOK_SECS  = 2.5

    ms.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ms.BROLL_DIR.mkdir(parents=True, exist_ok=True)
    ms.TTS_DIR.mkdir(parents=True, exist_ok=True)

    registry_png = str(tmp_dir / 'registry_card.png')
    render_registry_card(registry_png)
    ms.render_cta = lambda out_path: Image.open(registry_png).save(out_path)

    print('[registry] Rendering with voice=nova...', flush=True)
    ms.run()

if __name__ == '__main__':
    run()

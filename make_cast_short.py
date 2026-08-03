#!/usr/bin/env python3
"""
make_cast_short.py  —  e3d-pod2vid

Hand-scripted YouTube/Facebook Short announcing cast.e3d.ai: type one
sentence and AI writes + renders a video — birthday and congratulations
video cards (with two voices and optional email delivery), or a full
podcast video from a transcript or an audio file. Narrated in the "nova"
OpenAI TTS voice.

Closing card: Cast's own brand accent color instead of the default blue CTA.

Usage:
  python3 make_cast_short.py [output.mp4]
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
OUTPUT = str(Path(sys.argv[1] if len(sys.argv) > 1 else 'output/e3d-cast-short.mp4').resolve())
W, H   = 1080, 1920

SITE_URL = 'cast.e3d.ai'
ACCENT   = '#bf4a2b'   # Cast's own brand accent (src/ui/styles.css --accent)

SEGMENTS = [
    # Hook — silent, no narration
    ('', 'confetti party phone screen celebration'),
    # Problem
    ("Your best friend's birthday is tomorrow.",
     'calendar reminder phone notification desk'),
    ("You don't have a card. You don't have time.",
     'person stressed looking at phone couch'),
    # Turn
    ('So open Cast, and type one sentence.',
     'hands typing laptop close up'),
    # Product — video cards
    ('AI writes the whole message, in two warm voices,',
     'friends laughing video call smiling warm'),
    ('then renders a real video card — and can email the link straight to them.',
     'phone sending message notification tap'),
    # Product — podcasts too
    ('Got a podcast instead? Same tool — paste a transcript, or drop in your audio.',
     'podcast microphone recording studio'),
    ('Cast turns it into a captioned, publish-ready video in minutes.',
     'video editing timeline fast motion screen'),
    # CTA line
    ('No editing software. No experience needed. Try your first render free.',
     'confident woman laptop coffee smiling'),
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

# ── Closing card: Cast brand band ────────────────────────────────────────────

def render_cast_card(out_path):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    band_top, band_bot = H // 2 - 220, H // 2 + 220
    draw.rectangle([(0, band_top), (W, band_bot)], fill=(0, 0, 0, 220))
    draw.rectangle([(50, band_top - 5), (W - 50, band_top)],    fill=ACCENT)
    draw.rectangle([(50, band_bot),     (W - 50, band_bot + 5)], fill=ACCENT)

    cx = W // 2
    y  = band_top + 50

    f_small = load_font(30)
    label   = 'MADE WITH CAST'
    bbox    = draw.textbbox((0, 0), label, font=f_small)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y), label, font=f_small, fill=(210, 210, 210, 230))
    y += (bbox[3] - bbox[1]) + 30

    f_big = load_font(58)
    bbox  = draw.textbbox((0, 0), SITE_URL, font=f_big)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y), SITE_URL, font=f_big, fill=ACCENT)
    y += (bbox[3] - bbox[1]) + 34

    draw.rectangle([(cx - 160, y), (cx + 160, y + 2)], fill=(255, 255, 255, 80))
    y += 24

    f_sub = load_font(28)
    sub   = 'AI Prompts · Video Cards · Podcasts'
    bbox  = draw.textbbox((0, 0), sub, font=f_sub)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y), sub, font=f_sub, fill=(230, 230, 230, 220))

    img.save(out_path)

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    out_dir = Path(OUTPUT).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix='cast_short_'))

    spec = importlib.util.spec_from_file_location('make_short', DIR / 'make_short.py')
    ms   = importlib.util.module_from_spec(spec)
    os.environ.setdefault('SHORT_VOICE', 'nova')
    spec.loader.exec_module(ms)

    ms.OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
    ms.PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')
    ms.VOICE      = 'nova'
    ms.OUTPUT     = OUTPUT
    ms.OUT_DIR    = out_dir
    ms.BROLL_DIR  = out_dir / 'broll-cast'
    ms.TTS_DIR    = out_dir / 'tts-cast'
    ms.SCRATCH    = str(tmp_dir)
    ms.SEGMENTS   = SEGMENTS
    ms.CTA_TEXT   = SITE_URL
    ms.HOOK_SECS  = 2.5

    ms.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ms.BROLL_DIR.mkdir(parents=True, exist_ok=True)
    ms.TTS_DIR.mkdir(parents=True, exist_ok=True)

    cast_png = str(tmp_dir / 'cast_card.png')
    render_cast_card(cast_png)
    ms.render_cta = lambda out_path: Image.open(cast_png).save(out_path)

    print('[cast] Rendering with voice=nova...', flush=True)
    ms.run()

if __name__ == '__main__':
    run()

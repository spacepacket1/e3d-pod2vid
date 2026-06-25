#!/usr/bin/env python3
"""
make_thumbnail.py  —  e3d-pod2vid

Generates a 1280x720 YouTube thumbnail entirely in-process (no browser, no
Puppeteer, no Figma). Requires only Pillow.

Usage:
  python3 make_thumbnail.py <title_text> <output.png> [logo.png]

Environment variables:
  THUMB_BG_COLOR    hex background (default: 111111)
  THUMB_TITLE_COLOR hex title text (default: FFFFFF)
  THUMB_ACCENT      hex accent/stripe color (default: 00C2FF)
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit('Pillow required: pip install Pillow')

W, H = 1280, 720

BG_COLOR    = '#' + os.environ.get('THUMB_BG_COLOR',    '111111')
TITLE_COLOR = '#' + os.environ.get('THUMB_TITLE_COLOR', 'FFFFFF')
ACCENT      = '#' + os.environ.get('THUMB_ACCENT',      '00C2FF')

TITLE_TEXT  = sys.argv[1] if len(sys.argv) > 1 else 'Podcast Title'
OUTPUT      = sys.argv[2] if len(sys.argv) > 2 else 'thumbnail.png'
LOGO_PATH   = sys.argv[3] if len(sys.argv) > 3 else ''

def load_font(size, bold=False):
    candidates_bold = [
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    candidates = [
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for p in (candidates_bold if bold else candidates):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default(size)

def wrap_text(draw, text, font, max_px):
    words, lines, line = text.split(), [], []
    for word in words:
        test = ' '.join(line + [word])
        if draw.textbbox((0, 0), test, font=font)[2] > max_px and line:
            lines.append(' '.join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(' '.join(line))
    return lines

def run():
    img  = Image.new('RGB', (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Accent stripe (left edge)
    draw.rectangle([(0, 0), (8, H)], fill=ACCENT)

    # Subtle diagonal gradient overlay
    for x in range(W):
        alpha = int(30 * (1 - x / W))
        draw.line([(x, 0), (x, H)], fill=f'#{alpha:02x}{alpha:02x}{alpha:02x}')

    # Logo (top-right corner)
    logo_size = 80
    if LOGO_PATH and Path(LOGO_PATH).exists():
        try:
            logo = Image.open(LOGO_PATH).convert('RGBA')
            logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
            img.paste(logo, (W - logo.width - 40, 30), mask=logo.split()[3])
        except Exception as e:
            print(f'[thumb] logo skipped: {e}')

    # Title text (centered vertically, left-aligned with margin)
    title_font = load_font(72, bold=True)
    margin = 60
    lines  = wrap_text(draw, TITLE_TEXT, title_font, W - margin * 2 - logo_size - 20)
    line_h = 84
    total  = len(lines) * line_h
    y0     = (H - total) // 2

    for i, line in enumerate(lines):
        x = margin
        y = y0 + i * line_h
        # Shadow
        draw.text((x + 2, y + 2), line, font=title_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=title_font, fill=TITLE_COLOR)

    # Accent underline under last title line
    bbox = draw.textbbox((0, 0), lines[-1], font=title_font)
    ux   = margin
    uy   = y0 + (len(lines) - 1) * line_h + bbox[3] + 10
    draw.rectangle([(ux, uy), (ux + min(bbox[2], W // 2), uy + 5)], fill=ACCENT)

    # URL / tagline (bottom-left)
    tag_font = load_font(28)
    tagline  = os.environ.get('THUMB_TAGLINE', 'maps.e3d.ai')
    draw.text((margin, H - 60), tagline, font=tag_font, fill=ACCENT)

    img.save(OUTPUT)
    print(f'[thumb] {OUTPUT}  ({W}x{H})')

if __name__ == '__main__':
    run()

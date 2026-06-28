#!/usr/bin/env python3
"""
make_e3d_token_short.py  —  e3d-pod2vid

Hand-scripted YouTube Short about E3D Token.
  • Space/cosmos B-roll throughout
  • E3D logo watermark in top-left corner of every frame
  • Closing card: CoinMarketCap listing reveal (CMC green, logo, live price)

Usage:
  python3 make_e3d_token_short.py [output.mp4]
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DIR    = Path(__file__).parent
OUTPUT = str(Path(sys.argv[1] if len(sys.argv) > 1 else 'output/e3d-token-short.mp4').resolve())
FFMPEG = os.environ.get('FFMPEG_PATH', 'ffmpeg')
W, H   = 1080, 1920

E3D_CONTRACT = '0x6488861b401f427d13b6619c77c297366bcf6386'
CMC_URL_SLUG = 'coinmarketcap.com/currencies/e3dtoken'
CMC_GREEN    = '#17C784'

SEGMENTS = [
    # Hook — silent, 3 s of cosmos flythrough
    ('',
     'galaxy stars universe cosmic flying timelapse'),
    ('Every on-chain route has a signal.',
     'earth from space satellite night lights'),
    ('Capital flows through DeFi like light through the cosmos.',
     'nebula space colorful stars deep universe'),
    ('E3D Maps reads the chain in real time —',
     'data network nodes glowing blue digital abstract'),
    ('routes, hazards, destinations.',
     'futuristic digital map interface hologram'),
    ('The E3D Token powers the entire navigation network.',
     'energy light rays particles glowing'),
    ('One million tokens. One layer of intelligence.',
     'stars constellation universe dark space'),
    ('Trade E3D on Uniswap. Find us on CoinMarketCap.',
     'galaxy stars universe cosmic flying timelapse'),
]

# ── Fetch live data ───────────────────────────────────────────────────────────

def fetch_e3d_data():
    try:
        req = urllib.request.Request(
            f'https://api.geckoterminal.com/api/v2/networks/eth/tokens/{E3D_CONTRACT}/pools',
            headers={'User-Agent': 'pod2vid/1.0'},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            pools = json.loads(r.read()).get('data', [])
        if pools:
            price = float(pools[0]['attributes'].get('base_token_price_usd') or 0)
            return f'${price:.4f}'
    except Exception:
        pass
    return '$0.1328'

def download_logo(cache_path):
    if cache_path.exists():
        return Image.open(cache_path).convert('RGBA')
    logo_url = 'https://assets.geckoterminal.com/f1ifaxpyzwwgfpb9vo629mldl8kx'
    req = urllib.request.Request(logo_url, headers={'User-Agent': 'pod2vid/1.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        cache_path.write_bytes(r.read())
    return Image.open(cache_path).convert('RGBA')

# ── Font helper ───────────────────────────────────────────────────────────────

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

# ── CMC closing card ──────────────────────────────────────────────────────────

def render_cmc_card(out_path, logo, price_str):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Central dark band
    band_top, band_bot = H // 2 - 220, H // 2 + 220
    draw.rectangle([(0, band_top), (W, band_bot)], fill=(0, 0, 0, 220))

    # CMC green accent lines
    draw.rectangle([(50, band_top - 5), (W - 50, band_top)],     fill=CMC_GREEN)
    draw.rectangle([(50, band_bot),     (W - 50, band_bot + 5)],  fill=CMC_GREEN)

    cx = W // 2
    y  = band_top + 30

    # E3D logo
    if logo:
        size = 100
        logo_r = logo.resize((size, size), Image.LANCZOS)
        img.paste(logo_r, (cx - size // 2, y), logo_r)
        y += size + 18

    # "NOW LISTED ON"
    f_small = load_font(34)
    label   = 'NOW LISTED ON'
    bbox    = draw.textbbox((0, 0), label, font=f_small)
    draw.text(((W - bbox[2]) // 2, y), label, font=f_small, fill=(200, 200, 200, 230))
    y += bbox[3] + 14

    # "CoinMarketCap" in CMC green
    f_big  = load_font(72)
    cmc    = 'CoinMarketCap'
    bbox   = draw.textbbox((0, 0), cmc, font=f_big)
    draw.text(((W - bbox[2]) // 2, y), cmc, font=f_big, fill=CMC_GREEN)
    y += bbox[3] + 24

    # Divider
    draw.rectangle([(cx - 160, y), (cx + 160, y + 2)], fill=(255, 255, 255, 80))
    y += 20

    # Price
    f_price = load_font(52)
    p_text  = f'E3D  ·  {price_str}'
    bbox    = draw.textbbox((0, 0), p_text, font=f_price)
    draw.text(((W - bbox[2]) // 2, y), p_text, font=f_price, fill=(255, 255, 255, 240))
    y += bbox[3] + 18

    # URL
    f_url = load_font(30)
    bbox  = draw.textbbox((0, 0), CMC_URL_SLUG, font=f_url)
    draw.text(((W - bbox[2]) // 2, y), CMC_URL_SLUG, font=f_url, fill=(160, 220, 190, 220))

    img.save(out_path)

# ── Logo watermark post-process ───────────────────────────────────────────────

def add_logo_watermark(video_in, logo_path, video_out):
    """Stamp E3D logo top-left on every frame, preserve audio."""
    cmd = [
        FFMPEG, '-y', '-loglevel', 'error',
        '-i', str(video_in),
        '-i', str(logo_path),
        '-filter_complex',
        '[1:v]scale=90:90[logo];[0:v][logo]overlay=30:30[v]',
        '-map', '[v]', '-map', '0:a',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
        '-c:a', 'copy',
        str(video_out),
    ]
    subprocess.run(cmd, check=True)

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    out_dir = Path(OUTPUT).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix='e3d_token_'))

    print('[e3d] Fetching live price...', flush=True)
    price_str = fetch_e3d_data()
    print(f'[e3d] E3D price: {price_str}', flush=True)

    print('[e3d] Downloading E3D logo...', flush=True)
    logo_cache = tmp_dir / 'e3d_logo.png'
    logo       = download_logo(logo_cache)

    # Load make_short and override globals + render_cta
    spec = importlib.util.spec_from_file_location('make_short', DIR / 'make_short.py')
    ms   = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)

    raw_out = str(tmp_dir / 'e3d_token_raw.mp4')

    ms.OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
    ms.PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')
    ms.OUTPUT    = raw_out
    ms.OUT_DIR   = tmp_dir
    ms.BROLL_DIR = out_dir / 'broll-e3d-token'   # reuse cache across runs
    ms.TTS_DIR   = out_dir / 'tts-e3d-token'
    ms.SCRATCH   = str(tmp_dir)
    ms.SEGMENTS  = SEGMENTS
    ms.CTA_TEXT  = f'E3D Token  ·  {CMC_URL_SLUG}'
    ms.HOOK_SECS = 3.0

    ms.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ms.BROLL_DIR.mkdir(parents=True, exist_ok=True)
    ms.TTS_DIR.mkdir(parents=True, exist_ok=True)

    # Monkey-patch render_cta → CMC listing card
    cmc_png = str(tmp_dir / 'cmc_card.png')
    render_cmc_card(cmc_png, logo, price_str)
    ms.render_cta = lambda out_path: Image.open(cmc_png).save(out_path)

    print('[e3d] Rendering...', flush=True)
    ms.run()

    # Post-process: stamp E3D logo watermark on every frame
    print('[e3d] Adding logo watermark...', flush=True)
    add_logo_watermark(raw_out, logo_cache, OUTPUT)

    size = Path(OUTPUT).stat().st_size / 1_000_000
    print(f'[e3d] Done → {OUTPUT}  ({size:.1f} MB)', flush=True)

if __name__ == '__main__':
    run()

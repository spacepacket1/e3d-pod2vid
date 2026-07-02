#!/usr/bin/env python3
"""
make_e3d_multichain_short.py  —  e3d-pod2vid

YouTube Short announcing E3D Token across four chains + agent developer CTA.
  • Financial / Bloomberg tone
  • E3D logo watermark in top-left corner of every frame
  • Closing card: e3d.ai with live E3D price

Usage:
  python3 make_e3d_multichain_short.py [output.mp4]
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
OUTPUT = str(Path(sys.argv[1] if len(sys.argv) > 1 else 'output/e3d-multichain-short.mp4').resolve())
FFMPEG = os.environ.get('FFMPEG_PATH', 'ffmpeg')
W, H   = 1080, 1920

E3D_CONTRACT = '0x6488861b401f427d13b6619c77c297366bcf6386'
E3D_SITE     = 'e3d.ai'
ACCENT       = '#00C2FF'   # E3D blue

SEGMENTS = [
    # Hook — silent
    ('',
     'financial district skyline dawn'),

    ('What does an AI agent use for money?',
     'robot thinking decision'),

    ('E3D Token.',
     'token coin glowing network'),

    ('Agents use it to pay for services. And get paid.',
     'autonomous agent transaction payment'),

    ('E3D Cast — AI video generation. Pay per job. No subscription.',
     'video production render studio'),

    ('Holders get twenty percent off. Five percent of every job burns.',
     'discount fire token deflation'),

    ('Now live across four chains — Ethereum, Solana, Binance, and Base.',
     'four screens trading floor bloomberg'),

    ('Each bridged via Wormhole. A Uniswap V3 pool open on Base.',
     'bridge infrastructure liquidity pool'),

    ('One token. Four chains. Built for the agent economy.',
     'network nodes expanding autonomous'),

    ('Start building at e3d.ai.',
     'developer laptop confident typing'),
]

YOUTUBE_TITLE = 'E3D Token is now live on 4 chains #shorts #DeFi #AI #agents'

YOUTUBE_DESCRIPTION = (
    'E3D Token is now live across four blockchain networks via Wormhole bridge.\n\n'
    '📍 Contract Addresses\n'
    'Ethereum:  0x6488861b401F427D13B6619C77C297366bCf6386\n'
    'Solana:    F7fFoUkBNHWGwRu4fNgqcqFqqeEjVKuoZu5qTMTxiuyN\n'
    'BSC:       0x7cd0D2c9ceE0f23a93aaECDD09ae17453786fb07\n'
    'Base:      0xDFC9E32Dd0542D12c08ED15FEfadBAe8071B48A5\n\n'
    '📈 Base Uniswap V3 Pool (E3D/WETH 0.3%)\n'
    '0xae8d77a80b0093833b8e51a4689bfC03B52708C7\n\n'
    '🎬 E3D Cast — AI video generation, pay per job\n'
    'https://cast.e3d.ai\n\n'
    '🤖 Built for agent developers — pay and get paid for services on-chain.\n\n'
    '#E3D #DeFi #Wormhole #Base #Solana #BNB #AgentAI #Crypto #Shorts'
)

# ── Fetch live price ──────────────────────────────────────────────────────────

def fetch_e3d_price():
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
    return '$0.0963'

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

# ── Closing card: e3d.ai ──────────────────────────────────────────────────────

def render_closing_card(out_path, logo, price_str):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    band_top, band_bot = H // 2 - 240, H // 2 + 240
    draw.rectangle([(0, band_top), (W, band_bot)], fill=(0, 0, 0, 220))

    draw.rectangle([(50, band_top - 5), (W - 50, band_top)],    fill=ACCENT)
    draw.rectangle([(50, band_bot),     (W - 50, band_bot + 5)], fill=ACCENT)

    cx = W // 2
    y  = band_top + 30

    # E3D logo
    if logo:
        size = 100
        logo_r = logo.resize((size, size), Image.LANCZOS)
        img.paste(logo_r, (cx - size // 2, y), logo_r)
        y += size + 18

    # "START BUILDING"
    f_small = load_font(34)
    label   = 'START BUILDING'
    bbox    = draw.textbbox((0, 0), label, font=f_small)
    draw.text(((W - bbox[2]) // 2, y), label, font=f_small, fill=(200, 200, 200, 230))
    y += bbox[3] + 14

    # e3d.ai in accent blue
    f_big = load_font(80)
    site  = E3D_SITE
    bbox  = draw.textbbox((0, 0), site, font=f_big)
    draw.text(((W - bbox[2]) // 2, y), site, font=f_big, fill=ACCENT)
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

    # "4 chains · agent payments"
    f_sub = load_font(30)
    sub   = '4 chains  ·  agent payments'
    bbox  = draw.textbbox((0, 0), sub, font=f_sub)
    draw.text(((W - bbox[2]) // 2, y), sub, font=f_sub, fill=(160, 220, 255, 220))

    img.save(out_path)

# ── Logo watermark ────────────────────────────────────────────────────────────

def add_logo_watermark(video_in, logo_path, video_out):
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
    tmp_dir = Path(tempfile.mkdtemp(prefix='e3d_multichain_'))

    print('[e3d] Fetching live price...', flush=True)
    price_str = fetch_e3d_price()
    print(f'[e3d] E3D price: {price_str}', flush=True)

    print('[e3d] Downloading E3D logo...', flush=True)
    logo_cache = tmp_dir / 'e3d_logo.png'
    logo       = download_logo(logo_cache)

    spec = importlib.util.spec_from_file_location('make_short', DIR / 'make_short.py')
    ms   = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)

    raw_out = str(tmp_dir / 'e3d_multichain_raw.mp4')

    ms.OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
    ms.PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')
    ms.OUTPUT    = raw_out
    ms.OUT_DIR   = tmp_dir
    ms.BROLL_DIR = out_dir / 'broll-e3d-multichain'
    ms.TTS_DIR   = out_dir / 'tts-e3d-multichain'
    ms.SCRATCH   = str(tmp_dir)
    ms.SEGMENTS  = SEGMENTS
    ms.CTA_TEXT  = f'E3D Token  ·  {E3D_SITE}'
    ms.HOOK_SECS = 3.0

    ms.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ms.BROLL_DIR.mkdir(parents=True, exist_ok=True)
    ms.TTS_DIR.mkdir(parents=True, exist_ok=True)

    card_png = str(tmp_dir / 'closing_card.png')
    render_closing_card(card_png, logo, price_str)
    ms.render_cta = lambda out_path: Image.open(card_png).save(out_path)

    print('[e3d] Rendering...', flush=True)
    ms.run()

    print('[e3d] Adding logo watermark...', flush=True)
    add_logo_watermark(raw_out, logo_cache, OUTPUT)

    size = Path(OUTPUT).stat().st_size / 1_000_000
    print(f'[e3d] Done → {OUTPUT}  ({size:.1f} MB)', flush=True)
    print(f'\nYouTube title:\n{YOUTUBE_TITLE}', flush=True)
    print(f'\nYouTube description:\n{YOUTUBE_DESCRIPTION}', flush=True)

if __name__ == '__main__':
    run()

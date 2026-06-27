#!/usr/bin/env python3
"""
make_short.py  —  e3d-pod2vid

Generates a YouTube Short (1080x1920, ≤60s) with:
  • OpenAI TTS voiceover
  • Semantically matched Pexels B-roll (vertical-cropped)
  • Burned-in subtitles
  • Opening hook clip + closing CTA card

Usage:
  python3 make_short.py [output.mp4]

Environment variables:
  OPENAI_API_KEY
  PEXELS_API_KEY
  SHORT_VOICE     (default: onyx)
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')
FFMPEG     = os.environ.get('FFMPEG_PATH', 'ffmpeg')
VOICE      = os.environ.get('SHORT_VOICE', 'onyx')

OUTPUT     = str(Path(sys.argv[1] if len(sys.argv) > 1 else 'output/pod2vid-short.mp4').resolve())
OUT_DIR    = Path(OUTPUT).parent
BROLL_DIR  = OUT_DIR / 'broll-short'
TTS_DIR    = OUT_DIR / 'tts-short'
SCRATCH    = tempfile.mkdtemp(prefix='short_')

W, H = 1080, 1920   # vertical 9:16

def log(msg): print(f'[short] {msg}', flush=True)

# ── Script ────────────────────────────────────────────────────────────────────
# Each segment: (text_for_tts, pexels_query)
# Empty text = silent visual hook (no TTS, just B-roll)

SEGMENTS = [
    # Hook — eye-catching opener, no narration
    ('',                                                          'woman luxury sports car sunset'),
    # Problem
    ('You just recorded the perfect podcast.',                    'podcast microphone recording studio'),
    ('Now comes the editing. The B-roll. The subtitles.',        'video editor timeline frustrated'),
    ('Four more hours of work.',                                  'clock deadline work stress'),
    # Pivot
    ('Or... one command.',                                        'woman laptop coffee confident'),
    # Product
    ('e3d-pod2vid takes your audio and builds the entire video.','terminal dark screen command line'),
    ('AI picks the perfect clip for every sentence.',            'artificial intelligence data abstract'),
    ('Subtitles burned in automatically. No plugins needed.',    'woman driving convertible freedom'),
    # Distribution
    ('Then posts to YouTube, X, LinkedIn — automatically.',      'social media phone notifications'),
    # CTA
    ('Open source. Free.',                                       'sports car speed highway night'),
]

CTA_TEXT  = 'github.com/spacepacket1/e3d-pod2vid'
HOOK_SECS = 2.5   # duration of silent hook clip

# ── Helpers ───────────────────────────────────────────────────────────────────

def http_get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def download(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': 'pod2vid/1.0'})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, 'wb') as f:
        while chunk := r.read(65536):
            f.write(chunk)

def tts(text, out_path):
    body = json.dumps({'model': 'tts-1-hd', 'input': text, 'voice': VOICE, 'response_format': 'mp3'}).encode()
    req  = urllib.request.Request(
        'https://api.openai.com/v1/audio/speech', data=body,
        headers={'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=60) as r, open(out_path, 'wb') as f:
        f.write(r.read())

def duration_ms(path):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return int(float(r.stdout.strip()) * 1000)

def pexels_clip(query):
    slug = hashlib.md5(query.encode()).hexdigest()[:10]
    safe = query.lower().replace(' ', '_')[:40]
    path = BROLL_DIR / f'{safe}_{slug}.mp4'
    if path.exists():
        return str(path)
    url = (f'https://api.pexels.com/videos/search'
           f'?query={urllib.parse.quote(query)}&per_page=5&orientation=portrait&size=medium')
    try:
        data = http_get_json(url, {'Authorization': PEXELS_KEY, 'User-Agent': 'pod2vid/1.0'})
        for v in data.get('videos', []):
            files = sorted(v.get('video_files', []), key=lambda f: f.get('height', 0), reverse=True)
            # prefer portrait/tall clips
            best = next((f for f in files if f.get('height', 0) >= 1280), files[0] if files else None)
            if best:
                log(f'  Pexels #{v["id"]}: {query}')
                download(best['link'], str(path))
                return str(path)
    except Exception as e:
        log(f'  Pexels error "{query}": {e}')
    return None

def load_font(size, bold=False):
    candidates = [
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    for p in candidates:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default(size)

def render_sub(text, out_path, large=False):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = load_font(52 if large else 42)
    max_px = W - 120
    words, lines, line = text.split(), [], []
    for word in words:
        test = ' '.join(line + [word])
        if draw.textbbox((0, 0), test, font=font)[2] > max_px and line:
            lines.append(' '.join(line)); line = [word]
        else:
            line.append(word)
    if line: lines.append(' '.join(line))
    line_h, pad = 60, 18
    total_h = len(lines) * line_h + pad * 2
    y0 = H - total_h - 120
    draw.rectangle([(0, y0), (W, y0 + total_h)], fill=(0, 0, 0, 160))
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font)
        x = (W - (bbox[2] - bbox[0])) // 2
        y = y0 + pad + i * line_h
        draw.text((x+2, y+2), ln, font=font, fill=(0,0,0,200))
        draw.text((x, y), ln, font=font, fill=(255,255,255,255))
    img.save(out_path)

def render_cta(out_path):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Dark band
    draw.rectangle([(0, H//2 - 80), (W, H//2 + 80)], fill=(0, 0, 0, 200))
    # Accent line
    draw.rectangle([(60, H//2 - 84), (W - 60, H//2 - 80)], fill='#00C2FF')
    draw.rectangle([(60, H//2 + 80), (W - 60, H//2 + 84)], fill='#00C2FF')
    font_big  = load_font(44)
    font_sub  = load_font(32)
    # Main CTA
    bbox = draw.textbbox((0,0), CTA_TEXT, font=font_big)
    draw.text(((W - (bbox[2]-bbox[0]))//2, H//2 - 55), CTA_TEXT, font=font_big, fill='#00C2FF')
    sub = 'Open source · Free · Link below'
    bbox2 = draw.textbbox((0,0), sub, font=font_sub)
    draw.text(((W - (bbox2[2]-bbox2[0]))//2, H//2 + 20), sub, font=font_sub, fill=(255,255,255,220))
    img.save(out_path)

def render_segment(broll, audio, sub_png, duration_s, out_path):
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setpts=PTS-STARTPTS[bg];"
        f"[1:v]scale={W}:{H}[sub];"
        f"[bg][sub]overlay=0:0[out]"
    )
    cmd = [
        FFMPEG, '-y', '-loglevel', 'error',
        '-stream_loop', '-1', '-i', broll,
        '-loop', '1', '-framerate', '30', '-i', sub_png,
        '-filter_complex', fc,
        '-map', '[out]',
        '-t', str(duration_s),
        '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-an',
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f'Video render failed:\n{r.stderr.decode()[-300:]}')

def render_hook(broll, out_path):
    """Silent hook clip — no audio, no subtitle."""
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setpts=PTS-STARTPTS[out]"
    )
    cmd = [
        FFMPEG, '-y', '-loglevel', 'error',
        '-stream_loop', '-1', '-i', broll,
        '-filter_complex', fc,
        '-map', '[out]',
        '-t', str(HOOK_SECS),
        '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-an',
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def render_cta_clip(broll, cta_png, duration_s, out_path):
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setpts=PTS-STARTPTS[bg];"
        f"[1:v]scale={W}:{H}[cta];"
        f"[bg][cta]overlay=0:0[out]"
    )
    cmd = [
        FFMPEG, '-y', '-loglevel', 'error',
        '-stream_loop', '-1', '-i', broll,
        '-loop', '1', '-framerate', '30', '-i', cta_png,
        '-filter_complex', fc,
        '-map', '[out]',
        '-t', str(duration_s),
        '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-an',
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def mux_audio(video, audio, out_path):
    subprocess.run([
        FFMPEG, '-y', '-loglevel', 'error',
        '-i', video, '-i', audio,
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-shortest', out_path,
    ], check=True)

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    if not OPENAI_KEY: sys.exit('Error: OPENAI_API_KEY not set')
    if not PEXELS_KEY: sys.exit('Error: PEXELS_API_KEY not set')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BROLL_DIR.mkdir(parents=True, exist_ok=True)
    TTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download Pexels clips
    log('Fetching Pexels clips...')
    clips = {}
    for text, query in SEGMENTS:
        if query not in clips:
            path = pexels_clip(query)
            clips[query] = path

    fallback = next((v for v in clips.values() if v), None)
    if not fallback:
        sys.exit('No Pexels clips downloaded')

    # 2. Synthesize TTS for non-empty segments
    log('Synthesizing TTS...')
    tts_files = {}
    for text, query in SEGMENTS:
        if not text:
            continue
        key  = hashlib.md5(f'{VOICE}:{text}'.encode()).hexdigest()[:12]
        path = TTS_DIR / f'line_{key}.mp3'
        if not path.exists():
            log(f'  TTS: {text[:60]}')
            tts(text, str(path))
        tts_files[text] = str(path)

    # 3. Render video-only segments (silent)
    log('Rendering video segments...')
    video_clips = []
    seg_idx = 0

    for i, (text, query) in enumerate(SEGMENTS):
        broll = clips.get(query) or fallback
        out   = str(Path(SCRATCH) / f'seg_{i:03d}_video.mp4')

        if not text:
            # Silent hook
            render_hook(broll, out)
            video_clips.append((out, None))
        else:
            tts_path = tts_files[text]
            dur_s    = duration_ms(tts_path) / 1000.0
            sub_png  = str(Path(SCRATCH) / f'sub_{i:03d}.png')
            render_sub(text, sub_png)
            render_segment(broll, tts_path, sub_png, dur_s, out)
            video_clips.append((out, tts_path))

    # CTA segment (3 seconds, last broll query)
    cta_broll = clips.get(SEGMENTS[-1][1]) or fallback
    cta_png   = str(Path(SCRATCH) / 'cta.png')
    cta_vid   = str(Path(SCRATCH) / 'seg_cta_video.mp4')
    render_cta(cta_png)
    render_cta_clip(cta_broll, cta_png, 3.0, cta_vid)
    video_clips.append((cta_vid, None))

    # 4. Build audio track (silence for hook/CTA, TTS for others)
    log('Building audio track...')
    silence_path = str(Path(SCRATCH) / 'silence.mp3')
    # Generate short silence
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                    '-t', str(HOOK_SECS + 0.1),
                    '-c:a', 'libmp3lame', '-b:a', '64k', silence_path], check=True)

    audio_list = str(Path(SCRATCH) / 'audio_list.txt')
    with open(audio_list, 'w') as f:
        for vid, audio in video_clips:
            if audio:
                f.write(f"file '{audio}'\n")
            else:
                f.write(f"file '{silence_path}'\n")
    # CTA: 3s silence
    cta_silence = str(Path(SCRATCH) / 'silence_cta.mp3')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                    '-t', '3.0',
                    '-c:a', 'libmp3lame', '-b:a', '64k', cta_silence], check=True)
    # Rewrite last entry for CTA silence
    lines = open(audio_list).readlines()
    lines[-1] = f"file '{cta_silence}'\n"
    open(audio_list, 'w').writelines(lines)

    audio_merged = str(Path(SCRATCH) / 'audio_merged.mp3')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error',
                    '-f', 'concat', '-safe', '0', '-i', audio_list,
                    '-c', 'copy', audio_merged], check=True)

    # 5. Concat video clips
    log('Concatenating...')
    vid_list = str(Path(SCRATCH) / 'vid_list.txt')
    with open(vid_list, 'w') as f:
        for vid, _ in video_clips:
            f.write(f"file '{vid}'\n")

    vid_merged = str(Path(SCRATCH) / 'video_merged.mp4')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error',
                    '-f', 'concat', '-safe', '0', '-i', vid_list,
                    '-c', 'copy', vid_merged], check=True)

    # 6. Mux
    mux_audio(vid_merged, audio_merged, OUTPUT)

    size = Path(OUTPUT).stat().st_size / 1_000_000
    log(f'Done → {OUTPUT}  ({size:.1f} MB)')
    log(f'Upload: node yt_upload.js {OUTPUT} "This AI turns podcasts into videos automatically #shorts"')

if __name__ == '__main__':
    run()

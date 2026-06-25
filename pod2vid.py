#!/usr/bin/env python3
"""
pod2vid.py  —  e3d-pod2vid

Converts a diarized audio file (NotebookLM, podcast, interview) into a
YouTube-ready MP4 with:
  • Semantically matched Pexels B-roll per utterance
  • Burned-in subtitles (no libfreetype/libass required)
  • Speaker-labelled lower-third overlays (optional)
  • SRT file for YouTube CC upload

Pipeline:
  1. Upload audio → AssemblyAI (speaker diarization + transcription)
  2. Merge micro-utterances into natural segments
  3. GPT-4o-mini generates a specific Pexels search query per segment
  4. Download one Pexels clip per unique query (cached)
  5. Render each segment: B-roll + subtitle overlay + audio
  6. Concatenate → final MP4 + SRT

Usage:
  python3 pod2vid.py <audio.m4a> [output.mp4]

Environment variables (set in .env or export):
  ASSEMBLYAI_API_KEY
  OPENAI_API_KEY
  PEXELS_API_KEY

Optional:
  SPEAKER_A_NAME   (default: "Host")
  SPEAKER_B_NAME   (default: "Guest")
  MIN_SEG_MS       (default: 2000 — merge utterances shorter than this ms)
  VIDEO_WIDTH      (default: 1920)
  VIDEO_HEIGHT     (default: 1080)
  FFMPEG_PATH      (default: ffmpeg)
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

ASSEMBLYAI_KEY = os.environ.get('ASSEMBLYAI_API_KEY', '')
OPENAI_KEY     = os.environ.get('OPENAI_API_KEY', '')
PEXELS_KEY     = os.environ.get('PEXELS_API_KEY', '')
FFMPEG         = os.environ.get('FFMPEG_PATH', 'ffmpeg')

AUDIO_IN   = sys.argv[1] if len(sys.argv) > 1 else ''
OUTPUT     = sys.argv[2] if len(sys.argv) > 2 else 'output/video.mp4'

OUT_DIR    = Path(OUTPUT).parent
BROLL_DIR  = OUT_DIR / 'broll'
DIAR_CACHE = OUT_DIR / (Path(AUDIO_IN).stem + '-diarization.json')
QUERY_CACHE= OUT_DIR / (Path(AUDIO_IN).stem + '-queries.json')
SCRATCH    = tempfile.mkdtemp(prefix='pod2vid_')

W          = int(os.environ.get('VIDEO_WIDTH',  '1920'))
H          = int(os.environ.get('VIDEO_HEIGHT', '1080'))
MIN_SEG_MS = int(os.environ.get('MIN_SEG_MS',  '2000'))

SPEAKER_NAME = {
    'A': os.environ.get('SPEAKER_A_NAME', 'Host'),
    'B': os.environ.get('SPEAKER_B_NAME', 'Guest'),
}

def log(msg): print(f'[pod2vid] {msg}', flush=True)

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http_json(url, *, method='GET', headers=None, body=None, timeout=60):
    data = body.encode() if isinstance(body, str) else body
    req  = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code} {url}: {e.read().decode()[:300]}') from e

def download_file(url, out_path):
    req = urllib.request.Request(url, headers={'User-Agent': 'pod2vid/1.0'})
    with urllib.request.urlopen(req, timeout=300) as res, open(out_path, 'wb') as f:
        while True:
            chunk = res.read(65536)
            if not chunk:
                break
            f.write(chunk)

# ── AssemblyAI ─────────────────────────────────────────────────────────────────

def aai_upload(path):
    log(f'Uploading to AssemblyAI ({Path(path).stat().st_size // 1_000_000} MB)...')
    with open(path, 'rb') as f:
        data = f.read()
    return http_json(
        'https://api.assemblyai.com/v2/upload',
        method='POST',
        headers={'authorization': ASSEMBLYAI_KEY, 'content-type': 'application/octet-stream'},
        body=data, timeout=300,
    )['upload_url']

def aai_transcribe(upload_url):
    log('Submitting transcription + diarization...')
    r = http_json(
        'https://api.assemblyai.com/v2/transcript',
        method='POST',
        headers={'authorization': ASSEMBLYAI_KEY, 'content-type': 'application/json'},
        body=json.dumps({'audio_url': upload_url, 'speaker_labels': True}),
    )
    log(f'Job ID: {r["id"]}')
    return r['id']

def aai_poll(job_id):
    log('Waiting for transcription...')
    while True:
        r = http_json(f'https://api.assemblyai.com/v2/transcript/{job_id}',
                      headers={'authorization': ASSEMBLYAI_KEY})
        log(f'  status: {r["status"]}')
        if r['status'] == 'completed':
            log(f'  {len(r.get("utterances", []))} utterances')
            return r
        if r['status'] == 'error':
            raise RuntimeError(f'AssemblyAI error: {r.get("error")}')
        time.sleep(10)

# ── Segment processing ────────────────────────────────────────────────────────

def merge_short(utterances, min_ms=MIN_SEG_MS):
    result = []
    for u in utterances:
        if (u['end'] - u['start']) < min_ms and result:
            result[-1]['end']   = u['end']
            result[-1]['text'] += ' ' + u['text']
        else:
            result.append(dict(u))
    return result

# ── GPT semantic query generation ─────────────────────────────────────────────

QUERY_SYSTEM = """You are a video editor selecting B-roll clips for a podcast.
For each transcript segment, return a specific 3-5 word Pexels video search query
that best visually represents what is being discussed. Be concrete and literal.

Examples:
  "autonomous car, no map"         -> "car driving highway fog"
  "GPS, navigation, routing"       -> "GPS map navigation route"
  "payment protocol, micropayment" -> "digital micropayment transaction"
  "air traffic control"            -> "air traffic control radar"
  "machine learning, training"     -> "machine learning training loop"
  "financial risk, lending"        -> "bank lending credit risk"
  "blockchain, network nodes"      -> "blockchain network visualization"
  "stampede, crowd rush"           -> "crowd stampede rushing people"
  "courtroom, witnesses"           -> "courtroom judge testimony"

Return ONLY a JSON array of query strings, one per segment, in order."""

def generate_queries_batch(batch, offset):
    items = [{'i': offset + i, 'speaker': s['speaker'], 'text': s['text'][:200]}
             for i, s in enumerate(batch)]
    body = json.dumps({
        'model': 'gpt-4o-mini',
        'max_tokens': 800,
        'messages': [
            {'role': 'system', 'content': QUERY_SYSTEM},
            {'role': 'user', 'content':
             f'Generate a Pexels query for each of these {len(items)} segments:\n' +
             json.dumps(items, indent=2)},
        ],
    })
    r = http_json(
        'https://api.openai.com/v1/chat/completions',
        method='POST',
        headers={'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'},
        body=body, timeout=60,
    )
    content = r['choices'][0]['message']['content'].strip()
    start, end = content.find('['), content.rfind(']') + 1
    queries = json.loads(content[start:end])
    while len(queries) < len(batch):
        queries.append('technology abstract background')
    return queries[:len(batch)]

def generate_queries(segments, batch_size=40):
    queries = []
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        log(f'  GPT batch {i // batch_size + 1}: segments {i}–{i + len(batch) - 1}')
        queries.extend(generate_queries_batch(batch, i))
    return queries

# ── Pexels B-roll ─────────────────────────────────────────────────────────────

def query_cache_name(query):
    slug = hashlib.md5(query.encode()).hexdigest()[:10]
    safe = query.lower().replace(' ', '_')[:40]
    return f'{safe}_{slug}.mp4'

def pexels_fetch(query):
    url = (f'https://api.pexels.com/videos/search'
           f'?query={urllib.parse.quote(query)}&per_page=5&orientation=landscape&size=medium')
    r = http_json(url, headers={'Authorization': PEXELS_KEY, 'User-Agent': 'pod2vid/1.0'}, timeout=30)
    for v in r.get('videos', []):
        files = sorted(v.get('video_files', []), key=lambda f: f.get('width', 0), reverse=True)
        hd = next((f for f in files if f.get('width', 0) >= 1280), files[0] if files else None)
        if hd:
            return hd['link'], v['id']
    return None, None

def download_clips(queries):
    BROLL_DIR.mkdir(parents=True, exist_ok=True)
    clip_map = {}
    unique   = list(dict.fromkeys(queries))
    log(f'Fetching clips for {len(unique)} unique queries...')
    for query in unique:
        path = BROLL_DIR / query_cache_name(query)
        if path.exists():
            log(f'  cached: "{query}"')
            clip_map[query] = str(path)
            continue
        try:
            url, vid_id = pexels_fetch(query)
            if url:
                log(f'  #{vid_id}: "{query}"')
                download_file(url, str(path))
                clip_map[query] = str(path)
            else:
                log(f'  no result: "{query}"')
        except Exception as e:
            log(f'  error "{query}": {e}')
    return clip_map

# ── PIL rendering ─────────────────────────────────────────────────────────────

def load_font(size):
    candidates = [
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default(size)

def render_subtitle(text, out_path):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = load_font(36)
    max_px = W - 160
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
    line_h, pad = 46, 14
    total_h = len(lines) * line_h + pad * 2
    y0 = H - total_h - 30
    draw.rectangle([(0, y0), (W, y0 + total_h)], fill=(0, 0, 0, 150))
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font)
        x = (W - (bbox[2] - bbox[0])) // 2
        y = y0 + pad + i * line_h
        draw.text((x + 1, y + 1), ln, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
    img.save(out_path)

# ── Per-segment rendering ─────────────────────────────────────────────────────

def make_clip(seg, idx, total, broll_path, subtitle_png):
    start_s  = seg['start'] / 1000.0
    end_s    = seg['end']   / 1000.0
    duration = end_s - start_s
    out_path = str(Path(SCRATCH) / f'seg_{idx:04d}.mp4')
    fc = (
        f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setpts=PTS-STARTPTS[bg];"
        f"[2:v]scale={W}:{H}[sub];"
        f"[bg][sub]overlay=0:0[out]"
    )
    cmd = [
        FFMPEG, '-y', '-loglevel', 'error',
        '-ss', str(start_s), '-to', str(end_s), '-i', AUDIO_IN,
        '-stream_loop', '-1', '-i', broll_path,
        '-loop', '1', '-framerate', '25', '-i', subtitle_png,
        '-filter_complex', fc,
        '-map', '[out]', '-map', '0:a',
        '-t', str(duration),
        '-r', '25',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest', out_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg seg {idx} failed:\n{result.stderr.decode()[-300:]}')
    log(f'  [{idx+1}/{total}] {seg["speaker"]} ({start_s:.0f}s–{end_s:.0f}s) ✓')
    return out_path

def concat_clips(clip_paths, output_path):
    list_file = Path(SCRATCH) / 'concat.txt'
    with open(list_file, 'w') as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
    result = subprocess.run([
        FFMPEG, '-y', '-loglevel', 'error',
        '-f', 'concat', '-safe', '0', '-i', str(list_file),
        '-c', 'copy', output_path,
    ], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f'concat failed:\n{result.stderr.decode()[-300:]}')

# ── SRT ───────────────────────────────────────────────────────────────────────

def write_srt(segments, srt_path):
    def fmt(ms):
        h, ms  = divmod(ms, 3_600_000)
        m, ms  = divmod(ms, 60_000)
        s, ms  = divmod(ms, 1_000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    with open(srt_path, 'w') as f:
        for i, seg in enumerate(segments, 1):
            name = SPEAKER_NAME.get(seg['speaker'], seg['speaker'])
            f.write(f'{i}\n{fmt(seg["start"])} --> {fmt(seg["end"])}\n'
                    f'[{name}] {seg["text"]}\n\n')
    log(f'SRT -> {srt_path}')

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    for key, name in [(ASSEMBLYAI_KEY, 'ASSEMBLYAI_API_KEY'),
                      (OPENAI_KEY, 'OPENAI_API_KEY'),
                      (PEXELS_KEY, 'PEXELS_API_KEY')]:
        if not key:
            sys.exit(f'Error: {name} not set. Copy .env.example to .env and fill in your keys.')
    if not AUDIO_IN or not Path(AUDIO_IN).exists():
        sys.exit(f'Error: audio file not found: {AUDIO_IN}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log(f'Audio:   {AUDIO_IN}')
    log(f'Output:  {OUTPUT}')

    # 1. Diarize
    if DIAR_CACHE.exists():
        log(f'Loading cached diarization -> {DIAR_CACHE.name}')
        utterances = json.loads(DIAR_CACHE.read_text())['utterances']
    else:
        upload_url = aai_upload(AUDIO_IN)
        job_id     = aai_transcribe(upload_url)
        result     = aai_poll(job_id)
        utterances = result.get('utterances', [])
        DIAR_CACHE.write_text(json.dumps({'utterances': utterances}, indent=2))
        log(f'Diarization cached -> {DIAR_CACHE.name}')

    segments = merge_short(utterances)
    log(f'{len(utterances)} utterances -> {len(segments)} segments')

    # 2. Generate Pexels queries
    if QUERY_CACHE.exists():
        log(f'Loading cached queries -> {QUERY_CACHE.name}')
        queries = json.loads(QUERY_CACHE.read_text())
    else:
        log(f'Generating {len(segments)} Pexels queries via GPT...')
        queries = generate_queries(segments)
        QUERY_CACHE.write_text(json.dumps(queries, indent=2))
        log(f'Queries cached -> {QUERY_CACHE.name}')

    # 3. Download Pexels clips
    clip_map = download_clips(queries)
    fallback = next(iter(clip_map.values())) if clip_map else None
    if not fallback:
        sys.exit('Error: no Pexels clips downloaded — check PEXELS_API_KEY')

    # 4. Pre-render subtitles
    log(f'Rendering {len(segments)} subtitle overlays...')
    subtitle_pngs = []
    for i, seg in enumerate(segments):
        png = str(Path(SCRATCH) / f'sub_{i:04d}.png')
        render_subtitle(seg['text'], png)
        subtitle_pngs.append(png)

    # 5. Render segments
    log(f'Rendering {len(segments)} clips...')
    clip_paths = []
    for i, (seg, query) in enumerate(zip(segments, queries)):
        broll = clip_map.get(query) or fallback
        clip_paths.append(make_clip(seg, i, len(segments), broll, subtitle_pngs[i]))

    # 6. Concat
    log('Concatenating...')
    concat_clips(clip_paths, OUTPUT)
    log(f'Video -> {OUTPUT}  ({Path(OUTPUT).stat().st_size / 1_000_000:.1f} MB)')

    # 7. SRT
    write_srt(segments, str(Path(OUTPUT).with_suffix('.srt')))
    log('Done.')

if __name__ == '__main__':
    run()

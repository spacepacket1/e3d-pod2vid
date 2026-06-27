#!/usr/bin/env python3
"""
signal_short.py  —  e3d-pod2vid

Fetches navigation signals from maps.e3d.ai, filters for video-worthy
anomalies, generates a compelling script + Pexels queries via GPT-4o-mini,
renders a YouTube Short, uploads, and announces on all social platforms.

Filtering criteria (any one qualifies):
  • confidence >= CONF_THRESHOLD (default 0.78)
  • risk_level == 'high' AND confidence >= 0.55
  • signal_strength == 'strong'
  • 3+ signals converging on the same destination (cluster)

Usage:
  python3 signal_short.py [--dry-run] [--force]

  --dry-run   Generate script + queries but skip render/upload
  --force     Skip dedup check (re-post even if signal was posted today)

Environment variables:
  MAPS_URL              (default: https://maps.e3d.ai)
  MAPS_INTERNAL_KEY     API key for maps.e3d.ai
  OPENAI_API_KEY
  PEXELS_API_KEY
  YT_CLIENT_SECRET      path to youtube-client-secret.json
  YT_TOKEN_FILE         path to youtube-tokens.json
  LINKEDIN_TOKEN_FILE   path to linkedin-tokens.json
  X_TOKEN_FILE          path to x-oauth2-tokens.json
  CONF_THRESHOLD        minimum confidence to trigger (default: 0.78)
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

MAPS_URL   = os.environ.get('MAPS_URL', 'https://maps.e3d.ai')
MAPS_KEY   = os.environ.get('MAPS_INTERNAL_KEY', '')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')

CONF_THRESHOLD = float(os.environ.get('CONF_THRESHOLD', '0.78'))
CLUSTER_MIN    = 3      # signals needed to trigger a cluster alert
MAX_SIGNALS    = 30     # fetch this many to scan

DIR      = Path(__file__).parent
OUT_DIR  = DIR / 'output' / 'signal-shorts'
STATE_FILE = DIR / 'output' / 'signal-short-state.json'

DRY_RUN = '--dry-run' in sys.argv
FORCE   = '--force'   in sys.argv

def log(msg): print(f'[signal] {msg}', flush=True)

# ── HTTP ──────────────────────────────────────────────────────────────────────

def http_get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def http_post(url, body, headers=None, timeout=60):
    data = json.dumps(body).encode() if not isinstance(body, bytes) else body
    h    = {'Content-Type': 'application/json', **(headers or {})}
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

# ── Signal fetching & filtering ───────────────────────────────────────────────

RISK_RANK = {'high': 3, 'medium': 2, 'low': 1}

def fetch_signals():
    url     = f'{MAPS_URL}/api/maps/signals?limit={MAX_SIGNALS}'
    headers = {'User-Agent': 'signal-short/1.0'}
    if MAPS_KEY:
        headers['Authorization'] = f'Bearer {MAPS_KEY}'
    try:
        data = http_get(url, headers)
        return data.get('signals', [])
    except Exception as e:
        log(f'Signal fetch error: {e}')
        return []

def score_signal(s):
    conf     = s.get('confidence', 0)
    risk     = s.get('risk_level', 'low')
    strength = s.get('signal_strength', 'weak')
    score    = 0
    if conf >= CONF_THRESHOLD:               score += 100
    if risk == 'high' and conf >= 0.55:      score += 80
    if strength == 'strong':                 score += 60
    if risk == 'high' and strength == 'moderate': score += 40
    score += conf * 30
    score += RISK_RANK.get(risk, 0) * 10
    return score

def find_clusters(signals):
    dest_map = {}
    for s in signals:
        d = s.get('destination')
        if d:
            dest_map.setdefault(d, []).append(s)
    return {d: sigs for d, sigs in dest_map.items() if len(sigs) >= CLUSTER_MIN}

def select_signal(signals):
    clusters = find_clusters(signals)
    if clusters:
        # pick cluster with highest avg confidence
        best_dest = max(clusters, key=lambda d: sum(s.get('confidence',0) for s in clusters[d]) / len(clusters[d]))
        cluster   = clusters[best_dest]
        avg_conf  = sum(s.get('confidence',0) for s in cluster) / len(cluster)
        log(f'Cluster alert: {len(cluster)} signals → {best_dest} (avg conf {avg_conf:.0%})')
        # Return the highest-confidence signal as primary, with cluster context
        primary = max(cluster, key=lambda s: s.get('confidence', 0))
        primary['_cluster'] = cluster
        return primary, 'cluster'

    # Score and pick best individual signal
    scored = sorted(signals, key=score_signal, reverse=True)
    if not scored:
        return None, None
    top = scored[0]
    s   = score_signal(top)
    if s == 0:
        log(f'No signal meets threshold (best: {top.get("confidence",0):.0%} {top.get("risk_level")} {top.get("signal_strength")})')
        return None, None
    return top, 'single'

# ── Dedup ─────────────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {'posted': []}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def already_posted(signal_id, state):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return any(p['id'] == signal_id and p['date'] == today for p in state['posted'])

def mark_posted(signal_id, video_url, state):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    state['posted'].append({'id': signal_id, 'date': today, 'url': video_url})
    state['posted'] = state['posted'][-100:]  # keep last 100

# ── Script generation ─────────────────────────────────────────────────────────

SCRIPT_SYSTEM = """You are writing a 45-second YouTube Short voiceover about a live on-chain navigation signal from E3D Maps.

Structure (6-8 segments, ~10 words each):
1. HOOK — one punchy anomaly statement. Make it sound urgent and specific.
2. WHAT — what's happening on-chain right now (one sentence)
3. EVIDENCE — cite 1-2 specific data points from the evidence (numbers, assets, %)
4. PATTERN — why this is unusual or significant compared to normal
5. IMPLICATION — what this means for capital flow in plain English
6. RISK — honest risk note (one short sentence)
7. CTA — "Full signal and live navigation at maps.e3d.ai"

Rules:
- Never say "crypto" or "investment advice"
- Use navigation metaphors (route, hazard, destination, congestion, signal)
- Be specific: use real asset names, real percentages from the evidence
- Each segment should be 8-14 words — short, punchy, speakable
- Sound like a Bloomberg anchor, not a crypto influencer

For each segment, also provide a 3-5 word Pexels search query for B-roll footage.
Financial/DeFi concepts should map to physical/visual analogies:
  capital rotation → "money flowing river current"
  high confidence → "target bullseye accuracy precision"
  route hazard → "warning sign road danger"
  L2 networks → "highway interchange traffic aerial"
  stablecoin inflows → "cash deposit bank vault"
  governance vote → "ballot box voting democracy"
  wallet activity → "city lights activity aerial night"
  DeFi protocols → "server room technology data center"
  market state risk_on → "stock market green gains"
  congestion → "traffic jam gridlock aerial"

Return ONLY valid JSON:
{
  "title": "short punchy YouTube title (max 60 chars, include #shorts)",
  "segments": [
    {"text": "...", "query": "..."},
    ...
  ]
}"""

def generate_script(signal, mode):
    conf    = round(signal.get('confidence', 0) * 100)
    cluster = signal.get('_cluster', [])

    context = {
        'signal_type':     signal.get('signal_type', '').replace('_', ' '),
        'origin':          signal.get('origin'),
        'destination':     signal.get('destination'),
        'confidence_pct':  conf,
        'risk_level':      signal.get('risk_level'),
        'signal_strength': signal.get('signal_strength'),
        'market_state':    signal.get('market_state'),
        'time_horizon_hrs':signal.get('time_horizon_hours'),
        'asset_scope':     signal.get('asset_scope', []),
        'answer':          signal.get('answer', '')[:500],
        'evidence':        [e.get('summary','') for e in signal.get('evidence', [])[:4]],
        'recommended_action': signal.get('recommended_action'),
    }

    if mode == 'cluster':
        context['cluster_size'] = len(cluster)
        context['cluster_types'] = list({s.get('signal_type') for s in cluster})
        context['note'] = f'{len(cluster)} independent agents converged on {signal.get("destination")}'

    user_msg = f'Generate the Short script for this signal:\n{json.dumps(context, indent=2)}'

    r = http_post('https://api.openai.com/v1/chat/completions', {
        'model': 'gpt-4o-mini',
        'max_tokens': 1000,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': SCRIPT_SYSTEM},
            {'role': 'user',   'content': user_msg},
        ],
    }, {'Authorization': f'Bearer {OPENAI_KEY}'})

    content = r['choices'][0]['message']['content']
    return json.loads(content)

# ── Render via make_short pipeline ────────────────────────────────────────────

def render_short(segments, output_path):
    """Load make_short.py as a module, override globals, call run()."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('make_short', DIR / 'make_short.py')
    ms   = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)  # runs top-level code; we override below

    ms.OPENAI_KEY = OPENAI_KEY
    ms.PEXELS_KEY = PEXELS_KEY
    ms.OUTPUT    = str(output_path)
    ms.OUT_DIR   = Path(output_path).parent
    ms.BROLL_DIR = ms.OUT_DIR / 'broll-signal'
    ms.TTS_DIR   = ms.OUT_DIR / 'tts-signal'
    ms.SCRATCH   = tempfile.mkdtemp(prefix='signal_short_')
    ms.SEGMENTS  = [(s['text'], s['query']) for s in segments]
    ms.CTA_TEXT  = 'maps.e3d.ai  |  Live DeFi Navigation'
    ms.HOOK_SECS = 2.5

    ms.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ms.BROLL_DIR.mkdir(parents=True, exist_ok=True)
    ms.TTS_DIR.mkdir(parents=True, exist_ok=True)

    ms.run()

# ── Upload & announce ─────────────────────────────────────────────────────────

def yt_upload(video_path, title, description):
    cmd = [
        'node', str(DIR / 'yt_upload.js'), str(video_path), title, description,
    ]
    env = os.environ.copy()
    env.setdefault('YT_PRIVACY', 'public')
    env.setdefault('YT_TAGS', 'DeFi,crypto,onchain,AI,navigation,e3d,shorts,blockchain')
    env.setdefault('YT_CLIENT_SECRET', str(DIR / 'youtube-client-secret.json'))
    env.setdefault('YT_TOKEN_FILE',    str(DIR / 'youtube-tokens.json'))
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    log(result.stdout.strip())
    if result.returncode != 0:
        log(f'Upload error: {result.stderr[-300:]}')
        return None
    for line in result.stdout.splitlines():
        if 'youtube.com/watch' in line:
            return line.split()[-1]
    return None

def announce(yt_url, message):
    env = os.environ.copy()
    env['X_TOKEN_FILE'] = env.get('X_TOKEN_FILE',
        str(Path.home() / 'e3d/agents/scripts/x-oauth2-tokens.json'))
    result = subprocess.run(
        ['node', str(DIR / 'announce.js'), yt_url, message],
        capture_output=True, text=True, env=env,
    )
    log(result.stdout.strip())

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    for key, name in [(OPENAI_KEY,'OPENAI_API_KEY'),(PEXELS_KEY,'PEXELS_API_KEY')]:
        if not key: sys.exit(f'Error: {name} not set')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()

    # 1. Fetch + filter signals
    log('Fetching signals...')
    signals = fetch_signals()
    if not signals:
        log('No signals available.'); return

    log(f'{len(signals)} signals fetched.')
    signal, mode = select_signal(signals)
    if not signal:
        log('No signal meets the threshold for a video today.'); return

    sig_id   = signal.get('id', 'unknown')
    conf_pct = round(signal.get('confidence', 0) * 100)
    log(f'Selected: [{mode}] {signal.get("signal_type")} → {signal.get("destination")} ({conf_pct}% conf, {signal.get("risk_level")} risk)')

    # 2. Dedup check
    if not FORCE and already_posted(sig_id, state):
        log(f'Signal {sig_id} already posted today. Use --force to override.'); return

    # 3. Generate script
    log('Generating script via GPT-4o-mini...')
    result  = generate_script(signal, mode)
    title   = result.get('title', f'E3D Signal: {signal.get("destination")} #{conf_pct}% #shorts')
    segs    = result.get('segments', [])

    log(f'Title: {title}')
    log(f'Segments ({len(segs)}):')
    for i, s in enumerate(segs):
        log(f'  {i+1}. "{s["text"]}"  →  [{s["query"]}]')

    if DRY_RUN:
        log('DRY RUN — skipping render/upload.'); return

    # 4. Render
    ts         = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    output_mp4 = OUT_DIR / f'signal_{ts}.mp4'
    log(f'Rendering → {output_mp4}')
    render_short(segs, output_mp4)

    # 5. Upload to YouTube
    description = (
        f'{signal.get("answer", "")}\n\n'
        f'Signal type: {signal.get("signal_type","").replace("_"," ").title()}\n'
        f'Confidence: {conf_pct}%  |  Risk: {signal.get("risk_level","").title()}\n'
        f'Time horizon: {signal.get("time_horizon_hours","?")}h\n\n'
        f'📍 Live navigation signals: {MAPS_URL}\n'
        f'🔗 Open source pipeline: github.com/spacepacket1/e3d-pod2vid\n\n'
        f'#shorts #DeFi #OnChain #Crypto #E3D #NavigationIntelligence'
    )
    log('Uploading to YouTube...')
    yt_url = yt_upload(output_mp4, title, description)
    if not yt_url:
        log('Upload failed.'); return
    log(f'YouTube: {yt_url}')

    # 6. Announce
    cluster = signal.get('_cluster', [])
    cluster_note = f'\n\n🔗 {len(cluster)} agents converged on {signal.get("destination")}.' if cluster else ''
    announce_msg = (
        f'🧭 E3D Maps Signal Alert\n\n'
        f'{segs[0]["text"] if segs else title}\n\n'
        f'Confidence: {conf_pct}%  |  Risk: {signal.get("risk_level","").title()}'
        f'{cluster_note}\n\n'
        f'▶️ {yt_url}\n'
        f'📍 maps.e3d.ai'
    )
    log('Announcing...')
    announce(yt_url, announce_msg)

    # 7. Save state
    mark_posted(sig_id, yt_url, state)
    save_state(state)
    log('Done.')

if __name__ == '__main__':
    run()

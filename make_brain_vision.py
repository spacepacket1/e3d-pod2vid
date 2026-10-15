#!/usr/bin/env python3
"""
make_brain_vision.py  —  e3d-pod2vid

A ~3 minute concept film about e3d-brain: ElevenLabs narration, Higgsfield
generated scenes (hard-capped), a procedurally rendered 3D brain as the
recurring motif, burned captions, and a quiet synthesized ambient bed.

Usage (stages are cached under output/brain-vision/):
  python3 make_brain_vision.py voice            # ElevenLabs narration (cheap)
  python3 make_brain_vision.py clips [N]        # Higgsfield scenes; N = max new generations (default 8)
  python3 make_brain_vision.py assemble         # build output/e3d-brain-vision.mp4
  python3 make_brain_vision.py all
Env: ELEVENLABS_VOICE (default George), HIGGSFIELD_MODEL, MUSIC=0 to skip the bed.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from providers import elevenlabs, higgsfield   # noqa: E402

ROOT = Path(__file__).parent
WORK = ROOT / 'output' / 'brain-vision'
OUT = ROOT / 'output' / 'e3d-brain-vision.mp4'
W, H, FPS = 1920, 1080, 30
VOICE = os.environ.get('ELEVENLABS_VOICE', 'JBFqnCBsd6RMkjVDRZzb')   # "George - Warm, Captivating Storyteller"
FFMPEG = os.environ.get('FFMPEG_PATH', 'ffmpeg')
STYLE = ('cinematic, deep navy and warm amber palette, soft volumetric light, shallow depth of field, '
         'slow dolly camera, photoreal, no text, no logos, no watermark, no recognizable faces')

# (kind, narration, caption, visual prompt / None)
SCENES = [
    ('brain', "Every AI you have ever used has the same flaw. It is brilliant. And it forgets.", None, None),
    ('hf', "You come back to your project after a week, and it greets you like a stranger. So you explain everything. Again.",
     None, 'A person returns to a laptop in a dim quiet room; the chat window on screen is empty and blinking, soft blue light'),
    ('brain', "What if it didn't? What if every tool you use shared one memory, a living record of what was decided, why, and what was already tried?", None, None),
    ('title', "This is e3d-brain. A memory that outlives the session.", 'e3d-brain', None),
    ('hf', "Your coding assistant opens the project and already knows last week's decision, and the reasoning behind it.",
     None, 'A developer at a desk at night; a single glowing amber note of light rises from a constellation of linked notes and settles beside the code on the screen'),
    ('hf', "Before a new idea is drafted, the system checks what was tried before, and what failed. Mistakes get made once.",
     None, 'A robotic arm pauses over a glowing blueprint as a luminous note slides in with an old attempt marked in red'),
    ('hf', "A business weighs a new opportunity against what past results actually taught. Not hunches. Evidence, with the source attached.",
     None, 'A boardroom table of holographic charts at dusk; one lit note reorders the charts, warm amber light'),
    ('hf', "Creative work remembers the audience, the voice, and the claims that held up. Consistency, without another briefing meeting.",
     None, "A designer's moodboard assembling itself around a single glowing phrase, wall of images and color swatches"),
    ('hf', "Autonomous agents wake up knowing who they were yesterday. Continuity from one run to the next.",
     None, 'A small friendly quadcopter drone wakes up on a softly lit charging pad in a warm amber-lit workshop, bright and clear, while a page of glowing journal text unfolds in the air in front of it'),
    ('hf', "A newsroom recalls what it already covered, and which questions are still unanswered.",
     None, 'A newsroom at night with a wall of connected story cards, threads of light linking related stories'),
    ('hf', "And it stays honest. The memory only proposes. A human says yes. And every claim points back to its source.",
     None, 'A hand approves a glowing card floating in the air; the card dissolves into light and becomes a permanent star in a constellation'),
    ('brain', "Quality goes up, because lessons stick. Speed goes up, because nobody starts from zero. And here is the part that still amazes us: this system helped design and build its own memory.", None, None),
    ('end', "e3d-brain. Your ecosystem, with a past, and a future that learns.", 'e3d-brain',
     None),
]
DISCLOSURE = 'Concept film. The memory layer is built and tested; ecosystem integrations are in progress.'


def log(m): print(f'[film] {m}', flush=True)


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def probe_dur(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def font(size, bold=False):
    for c in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
              '/System/Library/Fonts/Helvetica.ttc']:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


# ── stage: voice ──────────────────────────────────────────────────────────────
def stage_voice():
    WORK.mkdir(parents=True, exist_ok=True)
    total = sum(len(s[1]) for s in SCENES)
    log(f'narration: {len(SCENES)} lines, {total} characters')
    for i, s in enumerate(SCENES):
        out = WORK / f'vo_{i:02d}.mp3'
        if out.exists():
            continue
        elevenlabs.synthesize(s[1], VOICE, str(out), stability=0.45, similarity_boost=0.8, style=0.25)
        log(f'  vo_{i:02d} {probe_dur(out):.1f}s')


# ── stage: clips ──────────────────────────────────────────────────────────────
def stage_clips(cap):
    WORK.mkdir(parents=True, exist_ok=True)
    made = 0
    for i, s in enumerate(SCENES):
        if s[0] != 'hf':
            continue
        out = WORK / f'clip_{i:02d}.mp4'
        if out.exists():
            continue
        if made >= cap:
            log(f'  cap of {cap} new generations reached; scene {i} left for a later run')
            continue
        log(f'  generating scene {i}: {s[3][:70]}...')
        higgsfield.generate_video(f'{s[3]}, {STYLE}', str(out), duration=6)
        made += 1
        log(f'    saved {out.name} ({probe_dur(out):.1f}s, {out.stat().st_size/1e6:.1f} MB)')


# ── brain motif ───────────────────────────────────────────────────────────────
def render_brain_motif(path):
    import numpy as np
    sys.path.insert(0, str(ROOT / 'assets'))
    import brain_motif as bm
    bm.W, bm.H = 1280, 720
    pts, edges = bm.build()
    phase = bm.rng.uniform(0, 2 * math.pi, len(pts))
    phase = 0.5 * phase + 3.0 * (pts[:, 2] + pts[:, 1])
    n, fps = 192, 16                       # 12 s per slow revolution
    with tempfile.TemporaryDirectory() as d:
        for f in range(n):
            bm.frame(pts, edges, phase, f / n, 0.28).save(f'{d}/f{f:04d}.png')
        run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', f'{d}/f%04d.png',
             '-vf', f'scale={W}:{H}:flags=lanczos', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', str(path)])


# ── title / caption PNGs ──────────────────────────────────────────────────────
def caption_png(text, out):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(44)
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) > W - 360 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    lh = 60
    y = H - 90 - lh * len(lines)
    d.rectangle([140, y - 24, W - 140, H - 28], fill=(4, 6, 14, 150))
    for ln in lines:
        d.text((W / 2, y), ln, font=f, fill=(255, 244, 225, 255), anchor='ma')
        y += lh
    img.save(out)


def title_png(text, sub, out, small=None):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W / 2 - 700, H / 2 - 190, W / 2 + 700, H / 2 + 130], radius=40, fill=(4, 6, 14, 175))
    d.text((W / 2, H / 2 - 80), text, font=font(150, True), fill=(255, 190, 90, 255), anchor='mm')
    if sub:
        d.text((W / 2, H / 2 + 60), sub, font=font(46), fill=(220, 235, 255, 255), anchor='mm')
    if small:
        d.text((W / 2, H - 80), small, font=font(30), fill=(150, 165, 190, 255), anchor='mm')
    img.save(out)


# ── assemble ──────────────────────────────────────────────────────────────────
def fit_filter(dur):
    return (f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},'
            f'fade=t=in:st=0:d=0.5,fade=t=out:st={max(dur - 0.5, 0):.2f}:d=0.5,format=yuv420p')


def build_scene(i, s, brain_mp4):
    vo = WORK / f'vo_{i:02d}.mp3'
    dur = probe_dur(vo) + 0.6
    out = WORK / f'scene_{i:02d}.mp4'
    kind = s[0]
    overlay = None
    if kind == 'title':
        overlay = WORK / f'ov_{i:02d}.png'; title_png(s[2], 'A memory that outlives the session', overlay)
    elif kind == 'end':
        overlay = WORK / f'ov_{i:02d}.png'; title_png(s[2], 'Your ecosystem, with a past, and a future that learns.', overlay, DISCLOSURE)
    else:
        overlay = WORK / f'ov_{i:02d}.png'; caption_png(s[1], overlay)
    if kind == 'hf':
        clip = WORK / f'clip_{i:02d}.mp4'
        if not clip.exists():
            return None
        # boomerang (forward + reverse) then loop to cover the narration
        boom = WORK / f'boom_{i:02d}.mp4'
        if not boom.exists():
            run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(clip), '-filter_complex',
                 '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        src = ['-stream_loop', '-1', '-i', str(boom)]
    else:
        src = ['-stream_loop', '-1', '-i', str(brain_mp4)]
    run([FFMPEG, '-y', '-loglevel', 'error', *src, '-i', str(overlay), '-i', str(vo),
         '-filter_complex',
         f'[0:v]{fit_filter(dur)}[v0];[1:v]format=rgba[ov];[v0][ov]overlay=0:0:format=auto,format=yuv420p[v]',
         '-map', '[v]', '-map', '2:a', '-af', 'apad', '-t', f'{dur:.2f}', '-r', str(FPS),
         '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', str(out)])
    return out


def ambient_bed(total, out):
    """Quiet synthesized pad: stacked sines with slow tremolo, lowpassed. Original audio, no samples."""
    expr = '+'.join(f'sine=f={f}:d={total:.1f}' for f in ())  # placeholder to keep structure explicit
    notes = [55, 82.4, 110, 164.8, 220]
    ins = []
    for f in notes:
        ins += ['-f', 'lavfi', '-i', f'sine=f={f}:d={total:.1f}']
    mix = ''.join(f'[{k}:a]' for k in range(len(notes))) + f'amix=inputs={len(notes)}:normalize=0,' \
        f'tremolo=f=0.15:d=0.4,lowpass=f=900,volume=0.05,afade=t=in:d=3,afade=t=out:st={max(total - 4, 0):.1f}:d=4[a]'
    run([FFMPEG, '-y', '-loglevel', 'error', *ins, '-filter_complex', mix, '-map', '[a]', '-ar', '44100', str(out)])


def stage_assemble():
    WORK.mkdir(parents=True, exist_ok=True)
    brain = WORK / 'brain_loop.mp4'
    if not brain.exists():
        log('rendering brain motif (12 s loop)...')
        render_brain_motif(brain)
    scenes = []
    for i, s in enumerate(SCENES):
        sc = build_scene(i, s, brain)
        if sc is None:
            log(f'  scene {i} has no clip yet; using the brain motif as a stand-in')
            tmp = (s[0], s[1], s[2], None)
            s2 = ('brain',) + tuple(tmp[1:])
            sc = build_scene(i, s2, brain)
        scenes.append(sc)
        log(f'  scene {i:02d} {probe_dur(sc):.1f}s')
    lst = WORK / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in scenes))
    base = WORK / 'film_nomusic.mp4'
    run([FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(base)])
    total = probe_dur(base)
    if os.environ.get('MUSIC', '1') == '1':
        bed = WORK / 'bed.wav'
        ambient_bed(total, bed)
        run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-i', str(bed), '-filter_complex',
             '[0:a][1:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]', '-map', '0:v', '-map', '[a]',
             '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', str(OUT)])
    else:
        run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
             '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', str(OUT)])
    log(f'film -> {OUT}  ({total:.0f}s, {OUT.stat().st_size/1e6:.0f} MB)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    if cmd in ('voice', 'all'):
        stage_voice()
    if cmd in ('clips', 'all'):
        stage_clips(cap)
    if cmd in ('assemble', 'all'):
        stage_assemble()
    if cmd not in ('voice', 'clips', 'assemble', 'all'):
        sys.exit(__doc__)

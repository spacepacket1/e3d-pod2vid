#!/usr/bin/env python3
"""
make_brain_film4.py  —  e3d-pod2vid

Concept film v4. Every idea gets a purpose-built explainer animation (assets/explainers.py);
a few team shots (distinct engineers, Kling 2.6 Pro) bookend it; the ecosystem graph appears only
long enough to go through the list; the spinning brain appears at the open, as the hologram, and at the end.

  python3 make_brain_film4.py voice | clips | exp | eco | assemble
"""
import json
import sys
from pathlib import Path

import make_brain_control_room as room
import make_brain_vision as mv
from providers import elevenlabs, higgsfield

ROOT = mv.ROOT
V1, V2, V3 = ROOT / 'output' / 'brain-vision', ROOT / 'output' / 'brain-control-room', ROOT / 'output' / 'brain-film3'
WORK = ROOT / 'output' / 'brain-film4'
OUT = ROOT / 'output' / 'e3d-brain-film4.mp4'
W, H, FPS = mv.W, mv.H, mv.FPS
KLING = 'kling-video/v2.6/pro/image-to-video'

N = lambda i: V1 / f'vo_{i:02d}.mp3'
T = lambda i: V2 / f'vo_{i:02d}.mp3'
X = lambda k: WORK / f'xvo_{k}.mp3'
NEW_LINES = {   # shorter ecosystem lines, so the graph is only on screen as long as the list takes
    'claude': ('KAI', "Claude Code picks up where you left off."),
    'pilot': ('DEV', "Pilot drafts every spec knowing the history."),
    'corp': ('SAGE', "Corp weighs opportunities against what past results taught."),
    'creative': ('MARA', "Creative remembers the audience and the voice."),
    'stories': ('MARA', "And our stories remember what they've covered."),
}
CLIPS = {   # team shots (still chosen from candidates) -> animated with Kling 2.6 Pro
    'ring_a': 'locked-off static camera, the engineers stand in the ring, glance at one another and nod, their clothing and faces lit by shimmering light from the pad, haze drifting, subtle natural motion, mouths closed',
    'ring_b': 'locked-off static camera, the engineers lean slightly toward the pad and look up with quiet satisfaction, light flickers across their faces, haze drifting, mouths closed',
}

# (audio, speaker or None, caption, visual)
#   ('brain',) | ('file', path) | ('exp', name) | ('comp', clip, zoom[, 'title']) | ('eco', mode, node) | ('end',)
SCRIPT = [
    (N(0), None, "Every AI you have ever used has the same flaw. It is brilliant. And it forgets.", ('brain',)),
    (N(1), None, "You come back to your project after a week, and it greets you like a stranger. So you explain everything. Again.", ('file', V1 / 'clip_01.mp4')),
    (N(2), None, "What if it didn't? What if every tool you use shared one memory, a living record of what was decided, why, and what was already tried?", ('exp', 'what_if')),
    (N(3), None, "This is e3d-brain. A memory that outlives the session.", ('comp', 'ring_a', 'in', 'title')),
    (T(0), 'SAGE', "Okay. Everybody here? Let's show them what we built.", ('comp', 'ring_a', 'push')),
    (T(3), 'SAGE', "So we gave them a memory. Plain notes, on our own machines. Every decision, every reason, every dead end.", ('exp', 'vault')),
    (T(4), 'MARA', "And it remembers why, not just what. Every note points back to where it came from.", ('exp', 'cite')),
    (V3 / 'xvo_connect.mp3', 'SAGE', "And it isn't just for one tool. It connects everything we run.", ('eco', 'all', None)),
    (X('claude'), 'KAI', NEW_LINES['claude'][1], ('eco', 'hl', 'claude')),
    (X('pilot'), 'DEV', NEW_LINES['pilot'][1], ('eco', 'hl', 'pilot')),
    (X('corp'), 'SAGE', NEW_LINES['corp'][1], ('eco', 'hl', 'corp')),
    (X('creative'), 'MARA', NEW_LINES['creative'][1], ('eco', 'hl', 'creative')),
    (T(8), 'SAGE', "And agents wake up knowing who they were yesterday.", ('eco', 'hl', 'agent')),
    (X('stories'), 'MARA', NEW_LINES['stories'][1], ('eco', 'hl', 'stories')),
    (T(6), 'DEV', "Before we draft anything new, it checks what we already tried. Each mistake gets made once.", ('exp', 'tried')),
    (T(9), 'DEV', "It even tidies itself. It spots decisions that were replaced, merges duplicates, and flags what has gone stale.", ('exp', 'tidy')),
    (T(10), 'KAI', "It reads real outcomes, and proposes lessons we can trust. With citations.", ('exp', 'lessons')),
    (T(11), 'MARA', "But nothing becomes memory until a human says yes.", ('file', V2 / 'clip_11.mp4')),
    (T(12), 'SAGE', "Quality goes up, because lessons stick. Speed goes up, because nobody starts from zero.", ('exp', 'speed')),
    (T(13), 'DEV', "And the wildest part? Our system helped build its own memory.", ('exp', 'assemble')),
    (T(14), 'SAGE', "Alright. Let's give the rest of the ecosystem a past.", ('comp', 'ring_b', 'out')),
    (N(12), None, "e3d-brain. Your ecosystem, with a past, and a future that learns.", ('end',)),
]


def log(m): print(f'[film4] {m}', flush=True)


def shot_dur(i):
    return mv.probe_dur(SCRIPT[i][0]) + (2.2 if SCRIPT[i][3][0] == 'end' else 0.45)


def stage_voice():
    WORK.mkdir(parents=True, exist_ok=True)
    for k, (who, line) in NEW_LINES.items():
        if not X(k).exists():
            elevenlabs.synthesize(line, room.CAST[who][0], str(X(k)), stability=0.45, similarity_boost=0.8, style=0.25)
            log(f'  {k} {who} {mv.probe_dur(X(k)):.1f}s')


def stage_clips():
    from concurrent.futures import ThreadPoolExecutor
    urls = json.loads((WORK / 'chosen.json').read_text())      # {'ring': url}
    todo = [k for k in CLIPS if not (WORK / f'{k}.mp4').exists()]

    def one(k):
        try:
            log(f'  animating {k} (Kling 2.6 Pro)')
            higgsfield.generate_video(f'{CLIPS[k]}, cinematic, no text', str(WORK / f'{k}.mp4'), model=KLING,
                                      duration=5, image_url=urls['ring'])
            log(f'  {k} done')
        except Exception as e:
            log(f'  {k} FAILED: {e}')
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(one, todo))


def stage_exp():
    sys.path.insert(0, str(ROOT / 'assets'))
    import explainers
    for i, (_, _, _, vis) in enumerate(SCRIPT):
        if vis[0] == 'exp':
            out = WORK / f'exp_{vis[1]}.mp4'
            log(f'  explainer {vis[1]} ({shot_dur(i):.1f}s)')
            explainers.render(vis[1], shot_dur(i), out)


def stage_eco():
    sys.path.insert(0, str(ROOT / 'assets'))
    import ecosystem
    brain = WORK / 'brain_loop.mp4'
    if not brain.exists():
        mv.render_brain_motif(brain)
    segs = [(shot_dur(i), SCRIPT[i][3][1], SCRIPT[i][3][2]) for i in range(len(SCRIPT)) if SCRIPT[i][3][0] == 'eco']
    log(f'ecosystem timeline: {len(segs)} segments, {sum(s[0] for s in segs):.0f}s')
    ecosystem.render_timeline(segs, WORK / 'eco.mp4', brain)


def lower_third_title(out):
    """Title in the lower third over a dark gradient, so the hologram above it stays unobscured."""
    import numpy as np
    from PIL import Image, ImageDraw
    img = np.zeros((H, W, 4), dtype='uint8')
    y0 = int(H * 0.60)
    ramp_ = np.linspace(0, 210, H - y0)[:, None]
    img[y0:, :, 3] = ramp_.astype('uint8')
    img[y0:, :, :3] = (4, 6, 14)
    im = Image.fromarray(img, 'RGBA')
    d = ImageDraw.Draw(im)
    d.text((W / 2, H - 250), 'e3d-brain', font=mv.font(150, True), fill=(255, 190, 90, 255), anchor='mm')
    d.text((W / 2, H - 120), 'A memory that outlives the session', font=mv.font(52), fill=(225, 235, 250, 255), anchor='mm')
    im.save(out)


def build_shot(i, brain_mp4, eco_off, holo):
    import make_brain_film as f2
    audio, who, text, vis = SCRIPT[i]
    dur = shot_dur(i)
    out = WORK / f'shot_{i:02d}.mp4'
    ov = WORK / f'ov_{i:02d}.png'
    kind = vis[0]
    if kind == 'end':
        mv.title_png('e3d-brain', 'Your ecosystem, with a past, and a future that learns.', ov, room.END_SMALL)
    elif kind == 'comp' and len(vis) > 3 and vis[3] == 'title':
        lower_third_title(ov)
    elif who:
        room.speaker_caption(who, text, ov)
    else:
        mv.caption_png(text, ov)
    fade = f'fade=t=in:st=0:d=0.4,fade=t=out:st={max(dur - 0.4, 0):.2f}:d=0.4,format=yuv420p'
    inputs, fc = [], ''
    if kind in ('brain', 'end'):
        drift = ("scale=2304:1296,crop=1920:1080:x='(iw-ow)/2+sin(t*0.5)*70':y='(ih-oh)/2+cos(t*0.4)*30'"
                 if kind == 'brain' else f'scale={W}:{H}')
        inputs += ['-stream_loop', '-1', '-ss', str((i * 2.3) % 9), '-i', str(brain_mp4)]
        fc = f'[0:v]{drift},fps={FPS},{fade}[v0];'
    elif kind == 'file':
        boom = WORK / f'boom_{i:02d}.mp4'
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(vis[1]), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        inputs += ['-stream_loop', '-1', '-i', str(boom)]
        fc = f'[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},{fade}[v0];'
    elif kind == 'exp':
        inputs += ['-i', str(WORK / f'exp_{vis[1]}.mp4')]
        fc = f'[0:v]scale={W}:{H},fps={FPS},{fade}[v0];'
    elif kind == 'eco':
        inputs += ['-ss', f'{eco_off[i]:.2f}', '-t', f'{dur:.2f}', '-i', str(WORK / 'eco.mp4')]
        fc = f'[0:v]scale={W}:{H},fps={FPS},{fade}[v0];'
    elif kind == 'comp':
        name, zoom = vis[1], vis[2]
        boom = WORK / f'boom_{i:02d}.mp4'
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(WORK / f'{name}.mp4'), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        cx, cy, hh = holo['ring']
        inputs += ['-stream_loop', '-1', '-i', str(boom), '-stream_loop', '-1', '-ss', str((i * 1.7) % 9), '-i', str(brain_mp4)]
        fc = (f'[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p[base];'
              f"[1:v]lutrgb=r='clip(val*1.35-8,0,255)':g='clip(val*1.35-10,0,255)':b='clip(val*1.35-20,0,255)',"
              f'scale=-2:{int(hh * 1.67)},fps={FPS},format=yuv420p[brain];'
              f'color=black:s={W}x{H}:r={FPS},format=yuv420p[canvas];'
              f'[canvas][brain]overlay=x={cx}-w/2:y={cy}-h/2:shortest=1,format=gbrp[holo];'
              f'[base]eq=brightness=-0.06:saturation=0.95,format=gbrp[bg];'
              f'[bg][holo]blend=all_mode=addition:shortest=1,format=yuv420p{f2.zoom_chain(zoom, dur)},{fade}[v0];')
    ov_idx = len([x for x in inputs if x == '-i'])
    inputs += ['-i', str(ov), '-i', str(audio)]
    fc += f'[{ov_idx}:v]format=rgba[ov];[v0][ov]overlay=0:0:format=auto,format=yuv420p[v]'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', *inputs, '-filter_complex', fc,
            '-map', '[v]', '-map', f'{ov_idx + 1}:a', '-af', 'apad', '-t', f'{dur:.2f}', '-r', str(FPS),
            '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', str(out)])
    return out


def stage_assemble():
    import make_brain_film as f2
    holo = json.loads((WORK / 'holo.json').read_text())
    brain = WORK / 'brain_loop.mp4'
    if not brain.exists():
        mv.render_brain_motif(brain)
    off, t = {}, 0.0
    for i in range(len(SCRIPT)):
        if SCRIPT[i][3][0] == 'eco':
            off[i] = t; t += shot_dur(i)
    shots = []
    for i in range(len(SCRIPT)):
        shots.append(build_shot(i, brain, off, holo))
        log(f'  shot {i:02d} {SCRIPT[i][3][0]:5s} {mv.probe_dur(shots[-1]):.1f}s')
    (WORK / 'concat.txt').write_text(''.join(f"file '{p}'\n" for p in shots))
    base = WORK / 'film_dry.mp4'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(WORK / 'concat.txt'), '-c', 'copy', str(base)])
    total = mv.probe_dur(base)
    voice, tone = WORK / 'voice.wav', WORK / 'tone.wav'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-vn', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
            '-ar', '44100', str(voice)])
    f2.room_tone(total, tone)
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-i', str(voice), '-i', str(tone),
            '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]',
            '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', str(OUT)])
    log(f'film -> {OUT}  ({total:.0f}s, {OUT.stat().st_size / 1e6:.0f} MB)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'voice': stage_voice, 'clips': stage_clips, 'exp': stage_exp, 'eco': stage_eco,
     'assemble': stage_assemble}.get(cmd, lambda: sys.exit(__doc__))()

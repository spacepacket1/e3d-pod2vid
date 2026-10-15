#!/usr/bin/env python3
"""
make_brain_film3.py  —  e3d-pod2vid

Concept film v3. Avatar-style command center: a circular emitter pad, a ring of
six people lit by the hologram, listener close-ups, and an ecosystem graph that
shows how e3d-brain connects the other E3D systems. The project's own
procedural spinning brain is the hologram, used sparingly.

  python3 make_brain_film3.py voice | stills | clips | eco | assemble
Reuses audio from film 1 (output/brain-vision) and film 2 (output/brain-control-room).
"""
import json
import sys
from pathlib import Path

import make_brain_control_room as room
import make_brain_vision as mv
from providers import elevenlabs, higgsfield

ROOT = mv.ROOT
V1 = ROOT / 'output' / 'brain-vision'
V2 = ROOT / 'output' / 'brain-control-room'
WORK = ROOT / 'output' / 'brain-film3'
OUT = ROOT / 'output' / 'e3d-brain-film3.mp4'
W, H, FPS = mv.W, mv.H, mv.FPS
I2V = room.I2V

LOOK3 = ('vast futuristic command center with a domed ceiling and tall glass walls over a night city, a wide circular '
         'floor emitter pad glowing at the centre with open empty space above it, volumetric haze, cool cyan and warm '
         'amber light, cinematic sci-fi, anamorphic lens, photoreal, no readable text, no logos, no watermark')
STILLS = {
    'ring_wide': f'Wide shot: six people in dark tactical jackets standing in a ring around the glowing circular emitter pad, all facing inward, their faces and clothes lit by cool light rising from the pad, {LOOK3}, symmetrical, epic scale',
    'group_med': f'Medium shot: three people in the left foreground looking toward the glowing circular emitter pad, their faces lit by cool cyan and warm amber light, two more people blurred on the far side of the pad, {LOOK3}, shallow depth of field, empty space above the pad',
    'face_a': 'Extreme close-up of a woman in profile, lit by cool cyan and warm amber light from a hologram off-screen, eyes wide with wonder reflecting tiny glowing points, mouth closed, volumetric haze, cinematic sci-fi, shallow depth of field',
    'face_b': 'Extreme close-up of a man in three-quarter view, lit by warm amber and cool cyan light from a hologram off-screen, intense focused expression, mouth closed, volumetric haze, cinematic sci-fi, shallow depth of field',
    'face_c': 'Close-up of an older woman with short grey hair and glasses, lit by cyan and amber light from a hologram off-screen, a faint smile, mouth closed, reflections of glowing light in her glasses, cinematic sci-fi, shallow depth of field',
}
STATIC = 'locked-off static camera, mouths stay closed, '
CLIPS = {
    'ring_a': ('ring_wide', STATIC + 'the six people stand in the ring and slowly turn their heads, light shimmers on their faces'),
    'ring_b': ('ring_wide', STATIC + 'the six people shift their weight and glance at one another, haze drifts through the light'),
    'ring_c': ('ring_wide', STATIC + 'the people lean slightly inward toward the pad, light flickers softly'),
    'group_a': ('group_med', STATIC + 'the three people glance up and across the pad, slight breathing motion, glowing light on their faces'),
    'group_b': ('group_med', STATIC + 'the people nod slowly and look toward the centre, light flickers'),
    'face_a': ('face_a', STATIC + 'a slow blink, light flickers across her face, tiny reflections shimmer in her eyes'),
    'face_b': ('face_b', STATIC + 'a slow blink and a slight nod, light flickers across his face'),
    'face_c': ('face_c', STATIC + 'a faint smile grows, light flickers across her glasses'),
}

N = lambda i: V1 / f'vo_{i:02d}.mp3'
T = lambda i: V2 / f'vo_{i:02d}.mp3'
X = lambda k: WORK / f'xvo_{k}.mp3'          # new lines, voiced in this film
NEW_LINES = {   # key -> (speaker, text)
    'connect': ('SAGE', "And it isn't just for one tool. It connects everything we run."),
    'claude': ('KAI', "Claude Code picks up exactly where you left off."),
    'corp': ('SAGE', "Corp weighs every opportunity against what past results actually taught."),
    'stories': ('MARA', "And our stories remember what they have already covered."),
}


def log(m): print(f'[film3] {m}', flush=True)


def stage_voice():
    WORK.mkdir(parents=True, exist_ok=True)
    for k, (who, line) in NEW_LINES.items():
        out = X(k)
        if out.exists():
            continue
        elevenlabs.synthesize(line, room.CAST[who][0], str(out), stability=0.45, similarity_boost=0.8, style=0.25)
        log(f'  {k} {who} {mv.probe_dur(out):.1f}s')


def stage_stills():
    WORK.mkdir(parents=True, exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    meta = WORK / 'stills.json'
    urls = json.loads(meta.read_text()) if meta.exists() else {}

    def one(name):
        out = WORK / f'still_{name}.png'
        try:
            urls[name] = higgsfield.generate_image(STILLS[name], str(out))
            log(f'  still {name} done')
        except Exception as e:
            log(f'  still {name} FAILED: {e}')
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(one, [n for n in STILLS if not (WORK / f'still_{n}.png').exists() or n not in urls]))
    meta.write_text(json.dumps(urls, indent=2))


def stage_clips():
    from concurrent.futures import ThreadPoolExecutor
    urls = json.loads((WORK / 'stills.json').read_text())
    todo = [k for k in CLIPS if not (WORK / f'{k}.mp4').exists()]

    def one(k):
        still, motion = CLIPS[k]
        try:
            log(f'  animating {k}')
            higgsfield.generate_video(f'{motion}, cinematic, no text', str(WORK / f'{k}.mp4'), model=I2V,
                                      duration=6, image_url=urls[still])
            log(f'  {k} done')
        except Exception as e:
            log(f'  {k} FAILED: {e}')
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(one, todo))


# ── shot list ─────────────────────────────────────────────────────────────────
# (audio, speaker or None, caption text, visual)
#   ('brain',) full-frame spinning brain | ('title',) | ('end',) | ('file', path) | ('clip', name)
#   ('comp', clipname, zoom) brain hologram composited into a locked-off clip | ('eco', mode, node)
SCRIPT = [
    (N(0), None, "Every AI you have ever used has the same flaw. It is brilliant. And it forgets.", ('brain',)),
    (N(1), None, "You come back to your project after a week, and it greets you like a stranger. So you explain everything. Again.", ('file', V1 / 'clip_01.mp4')),
    (N(2), None, "What if it didn't? What if every tool you use shared one memory, a living record of what was decided, why, and what was already tried?", ('eco', 'grow', None)),
    (N(3), None, "This is e3d-brain. A memory that outlives the session.", ('title',)),
    (T(0), 'SAGE', "Okay. Everybody here? Let's show them what we built.", ('comp', 'ring_a', 'in')),
    (T(3), 'SAGE', "So we gave them a memory. Plain notes, on our own machines. Every decision, every reason, every dead end.", ('comp', 'group_a', 'in')),
    (T(4), 'MARA', "And it remembers why, not just what. Every note points back to where it came from.", ('clip', 'face_a')),
    (X('connect'), 'SAGE', NEW_LINES['connect'][1], ('eco', 'all', None)),
    (X('claude'), 'KAI', NEW_LINES['claude'][1], ('eco', 'hl', 'claude')),
    (T(6), 'DEV', "Before we draft anything new, it checks what we already tried. Each mistake gets made once.", ('eco', 'hl', 'pilot')),
    (X('corp'), 'SAGE', NEW_LINES['corp'][1], ('eco', 'hl', 'corp')),
    (T(7), 'MARA', "Creative can remember the audience, the voice, the claims that held up. No more briefing meetings.", ('eco', 'hl', 'creative')),
    (T(8), 'SAGE', "And agents wake up knowing who they were yesterday.", ('eco', 'hl', 'agent')),
    (X('stories'), 'MARA', NEW_LINES['stories'][1], ('eco', 'hl', 'stories')),
    (T(9), 'DEV', "It even tidies itself. It spots decisions that were replaced, merges duplicates, and flags what has gone stale.", ('comp', 'group_b', 'in')),
    (T(10), 'KAI', "It reads real outcomes, and proposes lessons we can trust. With citations.", ('clip', 'face_b')),
    (T(11), 'MARA', "But nothing becomes memory until a human says yes.", ('file', V2 / 'clip_11.mp4')),
    (T(12), 'SAGE', "Quality goes up, because lessons stick. Speed goes up, because nobody starts from zero.", ('comp', 'ring_b', 'pull')),
    (T(13), 'DEV', "And the wildest part? Our system helped build its own memory.", ('clip', 'face_c')),
    (T(14), 'SAGE', "Alright. Let's give the rest of the ecosystem a past.", ('comp', 'ring_c', 'out')),
    (N(12), None, "e3d-brain. Your ecosystem, with a past, and a future that learns.", ('end',)),
]


def shot_dur(i):
    return mv.probe_dur(SCRIPT[i][0]) + (2.2 if SCRIPT[i][3][0] == 'end' else 0.55)


def stage_eco():
    """One continuous graph timeline covering every 'eco' shot, in script order."""
    sys.path.insert(0, str(ROOT / 'assets'))
    import ecosystem
    brain = WORK / 'brain_loop.mp4'
    if not brain.exists():
        mv.render_brain_motif(brain)
    segs = [(shot_dur(i), SCRIPT[i][3][1], SCRIPT[i][3][2]) for i in range(len(SCRIPT)) if SCRIPT[i][3][0] == 'eco']
    log(f'ecosystem timeline: {len(segs)} segments, {sum(s[0] for s in segs):.0f}s')
    ecosystem.render_timeline(segs, WORK / 'eco.mp4', brain)


def build_shot(i, brain_mp4, eco_offsets, holo):
    import make_brain_film as f2
    audio, who, text, vis = SCRIPT[i]
    dur = shot_dur(i)
    out = WORK / f'shot_{i:02d}.mp4'
    ov = WORK / f'ov_{i:02d}.png'
    kind = vis[0]
    if kind == 'title':
        mv.title_png('e3d-brain', 'A memory that outlives the session', ov)
    elif kind == 'end':
        mv.title_png('e3d-brain', 'Your ecosystem, with a past, and a future that learns.', ov, room.END_SMALL)
    elif who:
        room.speaker_caption(who, text, ov)
    else:
        mv.caption_png(text, ov)
    inputs, fc = [], ''
    fade = f'fade=t=in:st=0:d=0.5,fade=t=out:st={max(dur - 0.5, 0):.2f}:d=0.5,format=yuv420p'
    if kind in ('brain', 'title', 'end'):
        drift = "scale=2304:1296,crop=1920:1080:x='(iw-ow)/2+sin(t*0.5)*70':y='(ih-oh)/2+cos(t*0.4)*30'" if kind == 'brain' else f'scale={W}:{H}'
        inputs += ['-stream_loop', '-1', '-ss', str((i * 2.3) % 9), '-i', str(brain_mp4)]
        fc = f'[0:v]{drift},fps={FPS},{fade}[v0];'
    elif kind in ('file', 'clip'):
        src = vis[1] if kind == 'file' else WORK / f'{vis[1]}.mp4'
        boom = WORK / f'boom_{i:02d}.mp4'
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(src), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        inputs += ['-stream_loop', '-1', '-i', str(boom)]
        fc = f'[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},{fade}[v0];'
    elif kind == 'eco':
        inputs += ['-ss', f'{eco_offsets[i]:.2f}', '-t', f'{dur:.2f}', '-i', str(WORK / 'eco.mp4')]
        fc = f'[0:v]scale={W}:{H},fps={FPS},{fade}[v0];'
    elif kind == 'comp':
        name, zoom = vis[1], vis[2]
        boom = WORK / f'boom_{i:02d}.mp4'
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(WORK / f'{name}.mp4'), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        cx, cy, hh = holo[CLIPS[name][0]]
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
    lst = WORK / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in shots))
    base = WORK / 'film_dry.mp4'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(base)])
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
    {'voice': stage_voice, 'stills': stage_stills, 'clips': stage_clips, 'eco': stage_eco,
     'assemble': stage_assemble}.get(cmd, lambda: sys.exit(__doc__))()

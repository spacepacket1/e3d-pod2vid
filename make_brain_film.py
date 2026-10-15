#!/usr/bin/env python3
"""
make_brain_film.py  —  e3d-pod2vid

Final cut of the e3d-brain concept film. Weaves the narrated open/close (film 1)
with the control-room team dialogue (film 2), and puts the project's own
procedurally rendered spinning brain on the table as the hologram (composited,
not invented by the video model).

  python3 make_brain_film.py stills     # control-room stills with an EMPTY table centre
  python3 make_brain_film.py clips      # animate them with a locked-off camera
  python3 make_brain_film.py assemble
Reuses audio and clips from output/brain-vision (film 1) and output/brain-control-room (film 2).
"""
import json
import sys
from pathlib import Path

import make_brain_control_room as room
import make_brain_vision as mv
from providers import higgsfield

ROOT = mv.ROOT
V1 = ROOT / 'output' / 'brain-vision'
V2 = ROOT / 'output' / 'brain-control-room'
WORK = ROOT / 'output' / 'brain-film'
OUT = ROOT / 'output' / 'e3d-brain-film.mp4'
W, H, FPS = mv.W, mv.H, mv.FPS
I2V = room.I2V

EMPTY_LOOK = room.LOOK + ', nothing floating above the table'
STILLS = {
    'wide_empty': f'A small team of four people in dark clothing standing around a large round glass table, seen in silhouette from a distance, the table has a softly glowing empty disc of light at its centre with open space above it, {EMPTY_LOOK}, wide establishing shot, symmetrical composition',
    'shoulder_empty': f'Over-the-shoulder shot from behind two people in dark clothing looking at a round glass table with a softly glowing empty disc of light at its centre and open space above it, we see only their backs, {EMPTY_LOOK}, shallow depth of field',
}
# base clips: locked-off camera so the composited hologram stays on the table
CLIPS = {
    'wide_a': ('wide_empty', 'locked-off static camera, the four silhouetted people shift their weight slightly and gesture, soft light flicker on the glass'),
    'wide_b': ('wide_empty', 'locked-off static camera, the silhouetted people turn their heads toward the centre of the table and nod, subtle ambient light'),
    'wide_c': ('wide_empty', 'locked-off static camera, the silhouetted people lean in slightly toward the table, city lights twinkle beyond the glass'),
    'shoulder_a': ('shoulder_empty', 'locked-off static camera, the two people lean in slightly, slow breathing motion, soft light'),
    'shoulder_b': ('shoulder_empty', 'locked-off static camera, one person points toward the table and the other nods, subtle motion'),
}
# where the hologram sits in each still (1920x1080 coords: centre x, centre y, height); set after viewing the stills
HOLO = json.loads((WORK / 'holo.json').read_text()) if (WORK / 'holo.json').exists() else {}

# Shot list: (audio file, speaker or None, caption, visual)
#   visual: ('brain', zoom) | ('title',) | ('clip', path) | ('comp', clipname, zoom)  zoom: 'in'|'out'|None
N = lambda i: V1 / f'vo_{i:02d}.mp3'
T = lambda i: V2 / f'vo_{i:02d}.mp3'
SCRIPT = [
    (N(0), None, "Every AI you have ever used has the same flaw. It is brilliant. And it forgets.", ('brain', 'drift')),
    (N(1), None, "You come back to your project after a week, and it greets you like a stranger. So you explain everything. Again.", ('clip', V1 / 'clip_01.mp4')),
    (N(2), None, "What if it didn't? What if every tool you use shared one memory, a living record of what was decided, why, and what was already tried?", ('brain', 'tilt')),
    (N(3), None, "This is e3d-brain. A memory that outlives the session.", ('title',)),
    (T(0), 'SAGE', "Okay. Everybody here? Let's show them what we built.", ('comp', 'wide_a', 'in')),
    (T(3), 'SAGE', "So we gave them a memory. Plain notes, on our own machines. Every decision, every reason, every dead end.", ('comp', 'wide_b', 'push')),
    (T(4), 'MARA', "And it remembers why, not just what. Every note points back to where it came from.", ('brain', 'drift')),
    (T(5), 'KAI', "My coding assistant can open a project already knowing last week's call, and the reasoning behind it.", ('clip', V2 / 'clip_05.mp4')),
    (T(6), 'DEV', "Before we draft anything new, it checks what we already tried. Each mistake gets made once.", ('comp', 'wide_c', 'push')),
    (T(7), 'MARA', "Creative can remember the audience, the voice, the claims that held up. No more briefing meetings.", ('clip', V2 / 'clip_07.mp4')),
    (T(8), 'SAGE', "And agents wake up knowing who they were yesterday.", ('comp', 'wide_a', 'pull')),
    (T(9), 'DEV', "It even tidies itself. It spots decisions that were replaced, merges duplicates, and flags what has gone stale.", ('brain', 'tilt')),
    (T(10), 'KAI', "It reads real outcomes, and proposes lessons we can trust. With citations.", ('brain', 'drift')),
    (T(11), 'MARA', "But nothing becomes memory until a human says yes.", ('clip', V2 / 'clip_11.mp4')),
    (T(12), 'SAGE', "Quality goes up, because lessons stick. Speed goes up, because nobody starts from zero.", ('comp', 'wide_b', 'out')),
    (T(13), 'DEV', "And the wildest part? Our system helped build its own memory.", ('brain', 'tilt')),
    (T(14), 'SAGE', "Alright. Let's give the rest of the ecosystem a past.", ('comp', 'wide_c', 'pull')),
    (N(12), None, "e3d-brain. Your ecosystem, with a past, and a future that learns.", ('end',)),
]


def log(m): print(f'[film] {m}', flush=True)


def stage_stills():
    WORK.mkdir(parents=True, exist_ok=True)
    meta = WORK / 'stills.json'
    urls = json.loads(meta.read_text()) if meta.exists() else {}
    for name, prompt in STILLS.items():
        out = WORK / f'still_{name}.png'
        if out.exists() and name in urls:
            continue
        log(f'  still {name}')
        urls[name] = higgsfield.generate_image(prompt, str(out))
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


def zoom_chain(mode, dur):
    n = max(int(dur * FPS), 1)
    if mode == 'in':
        z = f'1+0.14*on/{n}'
    elif mode == 'out':
        z = f'1.14-0.14*on/{n}'
    elif mode == 'push':
        z = f'1+0.32*on/{n}'
    elif mode == 'pull':
        z = f'1.32-0.32*on/{n}'
    else:
        return ''
    # centre on the table/hologram (about 55% down the frame), clamped inside the picture
    return (f",zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='max(0,min(ih-ih/zoom,ih*0.52-(ih/zoom/2)))':d=1:s={W}x{H}:fps={FPS}")


def build_shot(i, audio, who, text, vis, brain_mp4):
    dur = mv.probe_dur(audio) + (2.2 if vis[0] == 'end' else 0.55)
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
    fit = mv.fit_filter(dur)
    inputs, fc = [], ''
    if kind in ('brain', 'title', 'end'):
        drift = ("scale=2304:1296,crop=1920:1080:x='(iw-ow)/2+sin(t*0.5)*70':y='(ih-oh)/2+cos(t*0.4)*30'"
                 if vis[-1] == 'drift' and kind == 'brain' else f'scale={W}:{H}')
        if kind == 'brain' and vis[-1] == 'tilt':
            drift = "scale=2112:1188,crop=1920:1080:x='(iw-ow)/2-sin(t*0.35)*90':y='(ih-oh)/2'"
        inputs += ['-stream_loop', '-1', '-ss', str((i * 2.3) % 9), '-i', str(brain_mp4)]
        base = f'[0:v]{drift},{fit.split(",", 2)[-1] if False else ""}'
        fc = f'[0:v]{drift},fps={FPS},fade=t=in:st=0:d=0.5,fade=t=out:st={max(dur - 0.5, 0):.2f}:d=0.5,format=yuv420p[v0];'
    elif kind == 'clip':
        boom = WORK / f'boom_{i:02d}.mp4'
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(vis[1]), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        inputs += ['-stream_loop', '-1', '-i', str(boom)]
        fc = f'[0:v]{fit}[v0];'
    elif kind == 'comp':
        name, zoom = vis[1], vis[2]
        base = WORK / f'{name}.mp4'
        boom = WORK / f'boom_{i:02d}.mp4'
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
        cx, cy, hh = HOLO[CLIPS[name][0]]
        inputs += ['-stream_loop', '-1', '-i', str(boom), '-stream_loop', '-1', '-ss', str((i * 1.7) % 9), '-i', str(brain_mp4)]
        fc = (f'[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p[base];'
              f"[1:v]lutrgb=r='clip(val*1.35-8,0,255)':g='clip(val*1.35-10,0,255)':b='clip(val*1.35-20,0,255)',scale=-2:{int(hh * 1.67)},fps={FPS},format=yuv420p[brain];"
              f'color=black:s={W}x{H}:r={FPS},format=yuv420p[canvas];'
              f'[canvas][brain]overlay=x={cx}-w/2:y={cy}-h/2:shortest=1,format=gbrp[holo];'
              f'[base]eq=brightness=-0.07:saturation=0.9,format=gbrp[bg];'
              f'[bg][holo]blend=all_mode=addition:shortest=1,format=yuv420p{zoom_chain(zoom, dur)},'
              f'fade=t=in:st=0:d=0.5,fade=t=out:st={max(dur - 0.5, 0):.2f}:d=0.5,format=yuv420p[v0];')
    ov_idx = len(inputs and [x for x in inputs if x == '-i'])
    inputs += ['-i', str(ov), '-i', str(audio)]
    fc += f'[{ov_idx}:v]format=rgba[ov];[v0][ov]overlay=0:0:format=auto,format=yuv420p[v]'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', *inputs, '-filter_complex', fc,
            '-map', '[v]', '-map', f'{ov_idx + 1}:a', '-af', 'apad', '-t', f'{dur:.2f}', '-r', str(FPS),
            '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', str(out)])
    return out


def room_tone(total, out):
    """Quiet, non-tonal room tone (low-passed pink noise). No pitched content, so it can never sound like a note."""
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
            f'anoisesrc=color=pink:amplitude=0.5:d={total:.1f}:r=44100',
            '-af', f'lowpass=f=500,highpass=f=60,volume=0.045,afade=t=in:d=2,afade=t=out:st={max(total - 3, 0):.1f}:d=3',
            '-ar', '44100', str(out)])


def stage_assemble():
    WORK.mkdir(parents=True, exist_ok=True)
    brain = WORK / 'brain_loop.mp4'
    if not brain.exists():
        log('rendering brain motif (12 s loop)...')
        mv.render_brain_motif(brain)
    shots = []
    for i, (audio, who, text, vis) in enumerate(SCRIPT):
        shots.append(build_shot(i, audio, who, text, vis, brain))
        log(f'  shot {i:02d} {vis[0]:5s} {mv.probe_dur(shots[-1]):.1f}s')
    lst = WORK / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in shots))
    base = WORK / 'film_dry.mp4'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(base)])
    total = mv.probe_dur(base)
    # 1) normalise the VOICES only
    voice = WORK / 'voice.wav'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-vn', '-af',
            'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '44100', str(voice)])
    # 2) then add a fixed-level, non-tonal room tone (never re-normalised)
    tone = WORK / 'tone.wav'
    room_tone(total, tone)
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-i', str(voice), '-i', str(tone),
            '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]',
            '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', str(OUT)])
    log(f'film -> {OUT}  ({total:.0f}s, {OUT.stat().st_size / 1e6:.0f} MB)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'stills': stage_stills, 'clips': stage_clips, 'assemble': stage_assemble}.get(cmd, lambda: sys.exit(__doc__))()

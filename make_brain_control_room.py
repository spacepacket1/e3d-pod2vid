#!/usr/bin/env python3
"""
make_brain_control_room.py  —  e3d-pod2vid

Concept film v2: a small team around a round table in a futuristic control room,
a holographic brain hovering at the centre, talking about what they built.
Dialogue is split across four ElevenLabs voices; shots are Higgsfield stills
(Soul) animated with Hailuo image-to-video so the room stays consistent.
Faces are never shown speaking (silhouettes, backs, profiles, hands) because
generated video cannot lip-sync.

  python3 make_brain_control_room.py voice
  python3 make_brain_control_room.py stills
  python3 make_brain_control_room.py clips [N]     # max new generations (default 15)
  python3 make_brain_control_room.py assemble
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import make_brain_vision as mv
from providers import elevenlabs, higgsfield

WORK = mv.ROOT / 'output' / 'brain-control-room'
OUT = mv.ROOT / 'output' / 'e3d-brain-control-room.mp4'
W, H, FPS = mv.W, mv.H, mv.FPS
I2V = 'minimax/hailuo-2.3/standard/image-to-video'

LOOK = ('futuristic circular control room at night, curved glass walls with a glittering city beyond, deep navy shadows, '
        'warm amber and cool cyan light, cinematic anamorphic, photoreal, no readable text, no logos, no watermark')

CAST = {   # speaker -> (ElevenLabs voice id, caption colour)
    'SAGE': ('EXAVITQu4vr4xnSDxMaL', (255, 190, 90)),     # Sarah  - mature, reassuring, confident
    'KAI':  ('IKne3meq5aSn9XLyUdCD', (120, 220, 255)),    # Charlie - deep, confident, energetic
    'MARA': ('FGY2WhTYpPnrIDTdsKH5', (255, 150, 170)),    # Laura  - enthusiast
    'DEV':  ('CwhRBWXzGAHq8TQ4Fs17', (170, 255, 190)),    # Roger  - laid-back, resonant
}

STILLS = {
    'wide': f'A small team of four people in dark clothing standing around a large round glass table, seen in silhouette from a distance, a glowing holographic neural-network brain hovering above the centre of the table, {LOOK}, wide establishing shot',
    'shoulder': f'Over-the-shoulder shot from behind two people in dark clothing looking at a large glowing holographic neural-network brain floating above a round table, we see only their backs, {LOOK}, shallow depth of field',
    'brain': f'Close-up of a glowing amber and cyan holographic neural-network brain hovering above a dark glass round table, hands reaching toward it from the edges of frame, reflections on the table, {LOOK}',
    'profile': f'A person in profile silhouette gesturing with one hand toward floating glowing holographic notes connected by threads of light, face in shadow, rim light, {LOOK}, medium shot',
    'approve': f'Close-up of a hand pressing a glowing approval card that floats above a glass table, soft amber light, blurred team in silhouette behind, {LOOK}',
}

# (speaker, line, still, motion prompt)
SHOTS = [
    ('SAGE', "Okay. Everybody here? Let's show them what we built.", 'wide',
     'slow push in toward the table, the holographic brain rotates slowly, subtle light flicker'),
    ('DEV', "Every one of our AIs used to start each day with amnesia.", 'shoulder',
     'the hologram flickers and dims, then holds, slight camera drift'),
    ('KAI', "Brilliant. Fast. And completely forgetful. We kept explaining the same decisions, over and over.", 'profile',
     'the person gestures, blank floating windows fade away one by one'),
    ('SAGE', "So we gave them a memory. Plain notes, on our own machines. Every decision, every reason, every dead end.", 'brain',
     'scattered glowing notes drift together and assemble into the brain, which brightens'),
    ('MARA', "And it remembers why, not just what. Every note points back to where it came from.", 'brain',
     'a thread of light traces from one glowing note out to a distant source node'),
    ('KAI', "My coding assistant can open a project already knowing last week's call, and the reasoning behind it.", 'profile',
     'a glowing rectangular document panel of light rises and settles beside a floating code window, no musical symbols'),
    ('DEV', "Before we draft anything new, it checks what we already tried. Each mistake gets made once.", 'shoulder',
     'on the hologram a path branches, one branch glows red and fades, another is chosen; camera drifts'),
    ('MARA', "Creative can remember the audience, the voice, the claims that held up. No more briefing meetings.", 'profile',
     'cards and colour swatches assemble around a single glowing phrase'),
    ('SAGE', "And agents wake up knowing who they were yesterday.", 'wide',
     'small glowing holographic figures flicker awake around the table'),
    ('DEV', "It even tidies itself. It spots decisions that were replaced, merges duplicates, and flags what has gone stale.", 'brain',
     'two glowing rectangular document panels of light merge into one while an older panel dims and fades, no musical symbols'),
    ('KAI', "It reads real outcomes, and proposes lessons we can trust. With citations.", 'brain',
     'lines of light flow from outcome nodes into a single lesson card'),
    ('MARA', "But nothing becomes memory until a human says yes.", 'approve',
     'the hand presses the card, it dissolves into a star that flies into the brain'),
    ('SAGE', "Quality goes up, because lessons stick. Speed goes up, because nobody starts from zero.", 'wide',
     'bright, well lit, slow pull back as the team in silhouette nods around the table and the glowing holographic brain brightens, filling the room with warm amber light'),
    ('DEV', "And the wildest part? Our system helped build its own memory.", 'brain',
     'the brain flares brighter and rotates faster'),
    ('SAGE', "Alright. Let's give the rest of the ecosystem a past.", 'wide',
     'slow pull back to reveal the whole glittering city beyond the glass walls, then slowly darken'),
]
END_SMALL = 'The memory and cognition layers are built and tested. Connecting the wider ecosystem is next.'


def log(m): print(f'[room] {m}', flush=True)


def stage_voice():
    WORK.mkdir(parents=True, exist_ok=True)
    log(f'{len(SHOTS)} lines, {sum(len(s[1]) for s in SHOTS)} characters')
    for i, (who, line, *_ ) in enumerate(SHOTS):
        out = WORK / f'vo_{i:02d}.mp3'
        if out.exists():
            continue
        elevenlabs.synthesize(line, CAST[who][0], str(out), stability=0.45, similarity_boost=0.8, style=0.25)
        log(f'  {i:02d} {who:4s} {mv.probe_dur(out):.1f}s')


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


def stage_clips(cap):
    from concurrent.futures import ThreadPoolExecutor
    urls = json.loads((WORK / 'stills.json').read_text())
    todo = [i for i in range(len(SHOTS)) if not (WORK / f'clip_{i:02d}.mp4').exists()][:cap]

    def one(i):
        who, line, still, motion = SHOTS[i]
        out = WORK / f'clip_{i:02d}.mp4'
        try:
            log(f'  animating shot {i} ({still}): {motion[:60]}')
            higgsfield.generate_video(f'{motion}, cinematic, smooth, no text', str(out), model=I2V, duration=6,
                                      image_url=urls[still])
            log(f'  shot {i} done')
        except Exception as e:      # rerun the stage to retry failed shots
            log(f'  shot {i} FAILED: {e}')

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(one, todo))


def speaker_caption(who, line, out):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f, ft = mv.font(44), mv.font(30, True)
    words, lines, cur = line.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) > W - 360 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    lh = 60
    y = H - 90 - lh * len(lines)
    d.rectangle([140, y - 62, W - 140, H - 28], fill=(4, 6, 14, 160))
    d.text((170, y - 52), who, font=ft, fill=CAST[who][1] + (255,))
    for ln in lines:
        d.text((W / 2, y), ln, font=f, fill=(255, 244, 225, 255), anchor='ma')
        y += lh
    img.save(out)


def build_shot(i, who, line):
    vo = WORK / f'vo_{i:02d}.mp3'
    dur = mv.probe_dur(vo) + 0.55
    clip = WORK / f'clip_{i:02d}.mp4'
    boom = WORK / f'boom_{i:02d}.mp4'
    if not boom.exists():
        mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(clip), '-filter_complex',
                '[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]', '-map', '[v]', '-an', str(boom)])
    ov = WORK / f'ov_{i:02d}.png'
    speaker_caption(who, line, ov)
    out = WORK / f'shot_{i:02d}.mp4'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', str(boom), '-i', str(ov), '-i', str(vo),
            '-filter_complex', f'[0:v]{mv.fit_filter(dur)}[v0];[1:v]format=rgba[ov];[v0][ov]overlay=0:0:format=auto,format=yuv420p[v]',
            '-map', '[v]', '-map', '2:a', '-af', 'apad', '-t', f'{dur:.2f}', '-r', str(FPS),
            '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', str(out)])
    return out


def end_card():
    brain = WORK / 'brain_loop.mp4'
    if not brain.exists():
        mv.render_brain_motif(brain)
    ov = WORK / 'ov_end.png'
    mv.title_png('e3d-brain', 'Your ecosystem, with a past, and a future that learns.', ov, END_SMALL)
    out = WORK / 'shot_end.mp4'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', str(brain), '-i', str(ov),
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-filter_complex', f'[0:v]{mv.fit_filter(6.0)}[v0];[1:v]format=rgba[ov];[v0][ov]overlay=0:0:format=auto,format=yuv420p[v]',
            '-map', '[v]', '-map', '2:a', '-t', '6.0', '-r', str(FPS), '-c:v', 'libx264', '-crf', '19',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', str(out)])
    return out


def stage_assemble():
    shots = []
    for i, (who, line, *_ ) in enumerate(SHOTS):
        if not (WORK / f'clip_{i:02d}.mp4').exists():
            raise SystemExit(f'shot {i} has no clip yet; run clips first')
        shots.append(build_shot(i, who, line))
        log(f'  shot {i:02d} {mv.probe_dur(shots[-1]):.1f}s')
    shots.append(end_card())
    lst = WORK / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in shots))
    base = WORK / 'film_nomusic.mp4'
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(base)])
    total = mv.probe_dur(base)
    bed = WORK / 'bed.wav'
    mv.ambient_bed(total, bed)
    mv.run([mv.FFMPEG, '-y', '-loglevel', 'error', '-i', str(base), '-i', str(bed), '-filter_complex',
            '[0:a][1:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
            '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', str(OUT)])
    log(f'film -> {OUT}  ({total:.0f}s, {OUT.stat().st_size / 1e6:.0f} MB)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    {'voice': stage_voice, 'stills': stage_stills, 'clips': lambda: stage_clips(cap),
     'assemble': stage_assemble}.get(cmd, lambda: sys.exit(__doc__))()

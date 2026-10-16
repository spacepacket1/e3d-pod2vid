#!/usr/bin/env python3
"""
make_pilot_interview.py  —  e3d-pod2vid

Re-voices the e3d-pilot NotebookLM podcast as an interview (Indian-English female host, British male guest, free
Microsoft neural voices via edge-tts) and renders it over the spinning brain with relevant B-roll beside it.

  python3 make_pilot_interview.py tts | brain | chunks | assemble | all

Needs: numpy, pillow, edge-tts, ffmpeg. Reuses output/e3d-pilot-notebooklm-{diarization,queries}.json and the cached
Pexels clips in output/broll. No paid services are called.
"""
import asyncio
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
WORK = OUT / 'pilot-interview'
FINAL = OUT / 'e3d-pilot-interview.mp4'
BRAIN_SRC = Path.home() / 'e3d-brain' / 'docs' / 'assets' / 'render_brain.py'
W, H, FPS = 1920, 1080, 24
BG = '0x04060e'
VOICES = {'A': 'en-IN-NeerjaExpressiveNeural', 'B': 'en-GB-RyanNeural'}
ROLE = {'A': ('HOST', (255, 170, 60)), 'B': ('GUEST', (120, 220, 255))}
RATE = '+4%'
MAX_CHUNK_CHARS = 170
FILLERS = re.compile(r'\b(?:uh+|um+|umm+|er|erm|hmm+)\b[,.]?\s*', re.I)

DIAGRAM = ROOT / 'assets' / 'futco-growth-loop.png'
DIAGRAM_UTTS = {25, 189}            # utterances that talk about "this whole ecosystem": show the growth-loop diagram
SHOTS = {10: ['profile'], 20: ['e3d-pilot', 'e3d-corp'], 98: ['e3d-brain']}   # utterance -> GitHub screenshots (public pages)
SHOT_DIR = ROOT / 'assets' / 'github-shots'
DIAG_H, DIAG_X, DIAG_Y = 1000, None, 40
LUT = "lutrgb=r='clip(val-6,0,255)':g='clip(val-8,0,255)':b='clip(val-16,0,255)'"   # brain bg -> black, so it adds as light
DIAG_CENTER_DISPLAY = (917, 760)    # centre of the "GROWTH LOOP" label, in the 2000-px-wide display coordinates

sys.path.insert(0, str(ROOT))


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=kw.pop('timeout', 900), **kw)


def clean(text):
    t = FILLERS.sub('', text)
    t = re.sub(r'\s+([,.?!])', r'\1', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t[:1].upper() + t[1:] if t else t


FIXES = [   # speech-to-text mistakes in the captions (names the transcriber does not know)
    (r'\bFut co-founder\b', 'FutCo co-founder'), (r'\b(?:FutureCo|FootCo|Futco|Fut co)\b', 'FutCo'), (r'\bE3 Pilot\b', 'E3D Pilot'),
    (r'\bitPilot\b', 'E3D Pilot'), (r'\bE3D/Brain\b', 'E3D Brain'), (r'\bnamed descent\b', 'named dissent'),
    (r'\baudit\.json\.l\b', 'audit.jsonl'), (r'\bE3D Core\b', 'E3D Corp'), (r'\bFoundation models\b', 'foundation models'),
]


def fix_caption(text):
    for pat, rep in FIXES:
        text = re.sub(pat, rep, text)
    return text


def dur(path):
    return float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]).stdout)


def load_utterances():
    utts = json.loads((OUT / 'e3d-pilot-notebooklm-diarization.json').read_text())['utterances']
    queries = json.loads((OUT / 'e3d-pilot-notebooklm-queries.json').read_text())
    # map each utterance to the merged segment (pod2vid.merge_short) whose query describes it
    seg_idx, merged = [], -1
    for k, u in enumerate(utts):
        if (u['end'] - u['start']) < 2000 and merged >= 0:
            pass
        else:
            merged += 1
        seg_idx.append(min(merged, len(queries) - 1))
    rows = []
    for k, u in enumerate(utts):
        text = clean(u['text'])
        if text:
            rows.append({'i': k, 'speaker': u['speaker'], 'text': text, 'query': queries[seg_idx[k]]})
    return rows


def broll_for(query):
    from_pod = hashlib.md5(query.encode()).hexdigest()[:10]
    safe = query.lower().replace(' ', '_')[:40]
    p = OUT / 'broll' / f'{safe}_{from_pod}.mp4'
    return p if p.exists() else None


# ── 1. voices ────────────────────────────────────────────────────────────────

async def _tts_one(row, path, meta_path):
    import edge_tts
    last = None
    for attempt in range(5):
        try:
            com = edge_tts.Communicate(row['text'], VOICES[row['speaker']], rate=RATE, boundary='SentenceBoundary')
            sents = []
            with open(path, 'wb') as f:
                async for ev in com.stream():
                    if ev['type'] == 'audio':
                        f.write(ev['data'])
                    elif ev['type'] == 'SentenceBoundary':
                        sents.append({'t': ev['offset'] / 1e7, 'd': ev['duration'] / 1e7, 'text': ev['text']})
            meta_path.write_text(json.dumps(sents))
            return
        except Exception as e:   # network hiccup: back off and retry
            last = e
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f'tts failed for utterance {row["i"]}: {last}')


def stage_tts():
    d = WORK / 'tts'
    d.mkdir(parents=True, exist_ok=True)
    rows = load_utterances()

    async def go():
        sem = asyncio.Semaphore(4)

        async def one(r):
            p, m = d / f'{r["i"]:03d}.mp3', d / f'{r["i"]:03d}.json'
            if p.exists() and m.exists() and p.stat().st_size > 1000:
                return
            async with sem:
                await _tts_one(r, p, m)
        await asyncio.gather(*(one(r) for r in rows))
    asyncio.run(go())
    print(f'tts: {len(rows)} utterances in {d}')


# ── 2. spinning brain loop ───────────────────────────────────────────────────

def stage_brain():
    out = WORK / 'brain-loop.mp4'
    if out.exists():
        return
    spec = importlib.util.spec_from_file_location('render_brain', BRAIN_SRC)
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    rb.W, rb.H, rb.FPS, rb.FRAMES = 1280, 720, FPS, 6 * FPS     # same 6 s seamless loop, at video size
    pts, edges = rb.build()
    phase = rb.rng.uniform(0, 2 * 3.141592653589793, len(pts))
    phase = 0.5 * phase + 3.0 * (pts[:, 2] + pts[:, 1])
    fd = WORK / 'brain-frames'
    fd.mkdir(parents=True, exist_ok=True)
    for f in range(rb.FRAMES):
        p = fd / f'f{f:04d}.png'
        if not p.exists():
            rb.frame(pts, edges, phase, f / rb.FRAMES, 0.28).save(p)
    sh(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(fd / 'f%04d.png'),
        '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', str(out)])
    print('brain loop ->', out)


# ── 3. subtitles / chunks ────────────────────────────────────────────────────

def font(size, bold=False):
    from PIL import ImageFont
    for p in ('/System/Library/Fonts/Helvetica.ttc', '/System/Library/Fonts/SFNS.ttf',
              '/Library/Fonts/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf'):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size, index=1 if (bold and p.endswith('.ttc')) else 0)
            except Exception:
                continue
    return ImageFont.load_default()


def overlay_png(text, speaker, path, title=False):
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(46)
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) > W - 360 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    lh = 62
    box_h = lh * len(lines) + 44
    top = H - 70 - box_h
    d.rounded_rectangle([140, top, W - 140, top + box_h], radius=22, fill=(4, 6, 14, 190))
    name, col = ROLE[speaker]
    chip = font(26, True)
    cw = int(d.textlength(name, font=chip)) + 40
    d.rounded_rectangle([140, top - 40, 140 + cw, top + 6], radius=14, fill=col + (255,))
    d.text((160, top - 35), name, font=chip, fill=(4, 6, 14, 255))
    for k, ln in enumerate(lines):
        d.text((180, top + 22 + k * lh), ln, font=f, fill=(245, 245, 250, 255))
    if title:
        d.text((90, 70), 'E3D PILOT', font=font(40, True), fill=(255, 170, 60, 255))
        d.text((90, 120), 'An AI engineering interview', font=font(30), fill=(200, 205, 215, 255))
    img.save(path)


def assign_scenes(plan):
    # Scenes: visuals change at utterance boundaries once a scene has run ~12 s, so short replies never flash an
    # unrelated clip. A scene shows the clip for its longest utterance; every third scene is the brain alone.
    scene, scene_start, t = -1, None, 0.0
    cur_utt = None
    members = []
    for c in plan:
        if c['first'] and (scene < 0 or t - scene_start >= 12.0):
            scene += 1
            scene_start = t
            members.append([])
        members[-1].append(c)
        c['scene'], c['scene_t'] = scene, t - scene_start
        t += c['len']
    for grp in members:
        best = max(grp, key=lambda c: len(c['row']['text']))['row']['query']
        for c in grp:
            c['scene_query'] = best
            c['layout'] = 'brain' if c['scene'] % 3 == 2 or broll_for(best) is None else 'split'
            if c['row']['i'] in DIAGRAM_UTTS:
                c['layout'] = 'diagram'
    seen = {}
    for c in plan:
        i = c['row']['i']
        if i in SHOTS:
            k = seen.get(i, 0)
            seen[i] = k + 1
            c['layout'], c['shot'] = 'shot', SHOTS[i][min(k, len(SHOTS[i]) - 1)]


def diagram_geometry():
    from PIL import Image
    im = Image.open(DIAGRAM)
    k = DIAG_H / im.height
    dw = round(im.width * k)
    x0 = W - dw - 40
    disp = im.width / 2000.0                                   # display coords were 2000 px wide
    cx = x0 + DIAG_CENTER_DISPLAY[0] * disp * k
    cy = DIAG_Y + DIAG_CENTER_DISPLAY[1] * disp * k
    return im, dw, x0, round(cx), round(cy)


def diagram_base():
    """1920x1080 frame: the growth-loop diagram with its centre label covered and a small honest caption."""
    from PIL import Image, ImageDraw
    path = WORK / 'diagram-base.png'
    im, dw, x0, cx, cy = diagram_geometry()
    canvas = Image.new('RGB', (W, H), (4, 6, 14))
    scaled = im.convert('RGB').resize((dw, DIAG_H), Image.LANCZOS)
    canvas.paste(scaled, (x0, DIAG_Y))
    d = ImageDraw.Draw(canvas)
    bgc = scaled.getpixel((round(scaled.width * 0.458), round(scaled.height * 0.385)))   # empty patch inside the ring
    d.rectangle([cx - 120, cy - 70, cx + 120, cy + 70], fill=bgc)
    f = font(15, True)
    cap = 'MEMORY (PLANNED)'
    d.text((cx - d.textlength(cap, font=f) / 2, cy + 70), cap, font=f, fill=(255, 170, 60))
    canvas.save(path)
    return path


def side_overlay_png(text, speaker, path):
    """Caption in a left column, for scenes where the diagram needs the right-hand side."""
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f, lh, width = font(44), 60, 540
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    top = (H - lh * len(lines)) // 2
    name, col = ROLE[speaker]
    chip = font(26, True)
    cw = int(d.textlength(name, font=chip)) + 40
    d.rounded_rectangle([70, top - 70, 70 + cw, top - 24], radius=14, fill=col + (255,))
    d.text((90, top - 65), name, font=chip, fill=(4, 6, 14, 255))
    for k, ln in enumerate(lines):
        d.text((70, top + k * lh), ln, font=f, fill=(245, 245, 250, 255))
    img.save(path)


def shot_base(name):
    from PIL import Image, ImageDraw
    path = WORK / f'shot-{name}.png'
    im = Image.open(SHOT_DIR / f'{name}.png').convert('RGB').resize((1200, 800), Image.LANCZOS)
    canvas = Image.new('RGB', (W, H), (4, 6, 14))
    x, y = 660, 120
    ImageDraw.Draw(canvas).rectangle([x - 4, y - 4, x + 1200 + 3, y + 800 + 3], fill=(255, 170, 60))
    canvas.paste(im, (x, y))
    canvas.save(path)
    return path


def chunk_plan():
    """Break every utterance into sentence groups: (utterance row, audio start, audio length, text)."""
    plan = []
    for r in load_utterances():
        meta = json.loads((WORK / 'tts' / f'{r["i"]:03d}.json').read_text())
        total = dur(WORK / 'tts' / f'{r["i"]:03d}.mp3')
        sents = meta or [{'t': 0.0, 'd': total, 'text': r['text']}]
        groups, cur = [], []
        for s in sents:
            if cur and len(' '.join(x['text'] for x in cur + [s])) > MAX_CHUNK_CHARS:
                groups.append(cur)
                cur = []
            cur.append(s)
        if cur:
            groups.append(cur)
        for g, grp in enumerate(groups):
            start = 0.0 if g == 0 else grp[0]['t']
            end = total if g == len(groups) - 1 else groups[g + 1][0]['t']
            plan.append({'row': r, 'start': start, 'len': max(0.4, end - start), 'text': ' '.join(x['text'] for x in grp),
                         'first': g == 0, 'offset_in_utt': start})
    assign_scenes(plan)
    return plan


def render_chunk(n, c, total_chunks):
    n = c.get('idx', n)
    r = c['row']
    cdir = WORK / c.get('dir', 'chunks')
    out = cdir / f'c{n:04d}.mp4'
    if out.exists():
        try:
            if dur(out) > 0.1:
                return out
        except Exception:
            pass   # half-written file from an interrupted run: render it again
        out.unlink(missing_ok=True)
    png = cdir / f'c{n:04d}.png'
    if c['layout'] in ('diagram', 'shot'):
        side_overlay_png(c['text'], r['speaker'], png)
    else:
        overlay_png(c['text'], r['speaker'], png, title=(n == 0))
    broll = broll_for(c['scene_query'])
    full_brain = c['layout'] == 'brain' or n < 3 or n > total_chunks - 4
    t_abs = c['abs']
    brain_off = t_abs % 6.0
    aud = ['-ss', f'{c["start"]:.3f}', '-t', f'{c["len"]:.3f}', '-i', str(c.get('audio_src') or WORK / 'tts' / f'{r["i"]:03d}.mp3')]
    base = ['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-ss', f'{brain_off:.3f}', '-i', str(WORK / 'brain-loop.mp4')]
    if c['layout'] == 'diagram':
        im, dw, x0, cx, cy = diagram_geometry()
        rx, ry = cx - 200, cy - 112
        cmd = base + aud + ['-loop', '1', '-i', str(diagram_base()), '-loop', '1', '-i', str(png), '-filter_complex',
                            (f'[2:v]format=gbrp,split=2[ba][bb];[bb]crop=400:225:{rx}:{ry}[reg];'
                             f'[0:v]scale=400:225:flags=lanczos,format=gbrp,{LUT}[b];[reg][b]blend=all_mode=addition[reg2];'
                             f'[ba][reg2]overlay={rx}:{ry}[a2];[a2][3:v]overlay=format=auto,format=yuv420p[v];'
                             f'[1:a]apad,atrim=0:{c["len"]:.3f}[a]')]
    elif c['layout'] == 'shot':
        cmd = base + aud + ['-loop', '1', '-i', str(shot_base(c['shot'])), '-loop', '1', '-i', str(png), '-filter_complex',
                            (f'[0:v]scale=360:203:flags=lanczos,setsar=1[br];[2:v][br]overlay=60:830[a1];[a1][3:v]overlay=format=auto,format=yuv420p[v];'
                             f'[1:a]apad,atrim=0:{c["len"]:.3f}[a]')]
    elif full_brain:
        cmd = base + aud + ['-loop', '1', '-i', str(png), '-filter_complex',
                            f'[0:v]scale={W}:{H}:flags=lanczos,setsar=1[bg];[bg][2:v]overlay=format=auto[v];[1:a]apad,atrim=0:{c["len"]:.3f}[a]']
    else:
        boff = c['scene_t'] % max(dur(broll) - 0.5, 1.0)   # clips are 6-24 s: seek inside the clip, then loop
        card = WORK / 'cards' / f'scene_{c["scene"]:03d}.mp4'
        if c.get('dir') == 'chunks-orig' and card.exists():   # animated concept card timed to the spoken words
            cmd = base + ['-ss', f'{c["scene_t"]:.3f}', '-i', str(card)] + aud + [
                '-loop', '1', '-i', str(png), '-filter_complex',
                (f'color=c={BG}:s={W}x{H}:r={FPS}[canvas];'
                 f'[0:v]scale=1180:664:flags=lanczos,setsar=1[br];'
                 f'[1:v]setsar=1,drawbox=x=0:y=0:w=iw:h=ih:color=0xffaa3c@0.9:t=3[card];'
                 f'[canvas][br]overlay=-170:120:shortest=1[a1];[a1][card]overlay=930:170[a2];'
                 f'[a2][3:v]overlay=format=auto[v];[2:a]apad,atrim=0:{c["len"]:.3f}[a]')]
            cmd += ['-map', '[v]', '-map', '[a]', '-frames:v', str(round(c['len'] * FPS)), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast',
                    '-crf', '21', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '44100', '-ac', '2', '-b:a', '160k', str(out)]
            for attempt in range(4):
                try:
                    sh(cmd, timeout=150)
                    return out
                except subprocess.TimeoutExpired:
                    out.unlink(missing_ok=True)
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f'chunk {n} failed: {e.stderr[-600:]}')
            raise RuntimeError(f'chunk {n} kept hanging')
        cmd = base + ['-stream_loop', '-1', '-ss', f'{boff:.3f}', '-i', str(broll)] + aud + [
            '-loop', '1', '-i', str(png), '-filter_complex',
            (f'color=c={BG}:s={W}x{H}:r={FPS}[canvas];'
             f'[0:v]scale=1180:664:flags=lanczos,setsar=1[br];'
             f'[1:v]scale=900:506:force_original_aspect_ratio=increase,crop=900:506,setsar=1,'
             f'drawbox=x=0:y=0:w=iw:h=ih:color=0xffaa3c@0.9:t=3[card];'
             f'[canvas][br]overlay=-170:120:shortest=1[a1];[a1][card]overlay=930:170[a2];'
             f'[a2][3:v]overlay=format=auto[v];[2:a]apad,atrim=0:{c["len"]:.3f}[a]')]
    cmd += ['-map', '[v]', '-map', '[a]', '-frames:v', str(round(c['len'] * FPS)), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast',
            '-crf', '21', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '44100', '-ac', '2', '-b:a', '160k', str(out)]
    for attempt in range(4):   # ffmpeg occasionally wedges on the looped inputs; kill it and retry
        try:
            sh(cmd, timeout=150)
            return out
        except subprocess.TimeoutExpired:
            out.unlink(missing_ok=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'chunk {n} failed: {e.stderr[-600:]}')
    raise RuntimeError(f'chunk {n} kept hanging')


def stage_chunks():
    (WORK / 'chunks').mkdir(parents=True, exist_ok=True)
    plan = chunk_plan()
    t = 0.0
    for c in plan:
        c['abs'] = t
        t += c['len']
    print(f'chunks: {len(plan)}, about {t / 60:.1f} min')
    with ThreadPoolExecutor(3) as ex:
        for k, _ in enumerate(ex.map(lambda p: render_chunk(p[0], p[1], len(plan)), enumerate(plan))):
            if k % 25 == 0:
                print(f'  rendered {k}/{len(plan)}', flush=True)


ORIG = ROOT / 'input' / 'e3d-pilot-notebooklm.m4a'
FINAL_ORIG = OUT / 'e3d-pilot-interview-original-audio.mp4'


def orig_plan(drop=True):
    """Same visuals, timed to the original podcast audio. Chunks tile the whole timeline (frame-exact, no drift)."""
    utts = json.loads((OUT / 'e3d-pilot-notebooklm-diarization.json').read_text())['utterances']
    rows = {r['i']: r for r in load_utterances_raw()}
    total = dur(ORIG)
    plan = []
    for k, u in enumerate(utts):
        r = rows[k]
        groups, cur = [], []
        for w in u['words']:
            cur.append(w)
            if re.search(r'[.?!]["\')]?$', w['text']) and len(' '.join(x['text'] for x in cur)) > 60:
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
        merged = []
        for g in groups:   # keep chunks near MAX_CHUNK_CHARS
            if merged and len(' '.join(x['text'] for x in merged[-1] + g)) <= MAX_CHUNK_CHARS:
                merged[-1] = merged[-1] + g
            else:
                merged.append(g)
        for g, grp in enumerate(merged):
            raw = ' '.join(x['text'] for x in grp)
            plan.append({'row': r, 'start': grp[0]['start'] / 1000, 'cut': 'FutureCo' in raw, 'text': fix_caption(raw),
                         'first': g == 0, 'dir': 'chunks-orig', 'audio_src': ORIG})
    plan[0]['start'] = 0.0
    q = lambda x: round(x * FPS) / FPS
    for k, c in enumerate(plan):
        end = plan[k + 1]['start'] if k + 1 < len(plan) else total
        c['start_q'], c['end_q'] = q(c['start']), q(end)
    for c in plan:
        c['len'] = c['end_q'] - c['start_q']
        c['start'] = c['start_q']
        c['offset_in_utt'] = 0
    t = 0.0
    for c in plan:
        c['abs'] = c['start']
    assign_scenes(plan)
    for k, c in enumerate(plan):
        c['idx'] = k                    # stable file name, even after chunks are cut
    cuts = [c for c in plan if c.get('cut')]
    for cut in cuts:                    # the narrator says "FutureCo" there: the sentence is cut from picture and sound
        for c in plan:
            if c['idx'] > cut['idx'] and c['scene'] == cut['scene']:
                c['scene_t'] -= cut['len']
    return [c for c in plan if not c.get('cut')] if drop else plan


def load_utterances_raw():
    utts = json.loads((OUT / 'e3d-pilot-notebooklm-diarization.json').read_text())['utterances']
    queries = json.loads((OUT / 'e3d-pilot-notebooklm-queries.json').read_text())
    merged, rows = -1, []
    for k, u in enumerate(utts):
        if not ((u['end'] - u['start']) < 2000 and merged >= 0):
            merged += 1
        rows.append({'i': k, 'speaker': u['speaker'], 'text': u['text'], 'query': queries[min(merged, len(queries) - 1)]})
    return rows


def ORIG_CUT_AUDIO():
    """The original podcast audio with the cut sentences removed (30 ms crossfade at each join)."""
    full = orig_plan(drop=False)
    cuts = [(c['start_q'], c['end_q']) for c in full if c.get('cut')]
    out = WORK / 'orig-edited.m4a'
    if not cuts:
        return ORIG
    keep, pos = [], 0.0
    for a, b in cuts:
        keep.append((pos, a))
        pos = b
    keep.append((pos, dur(ORIG)))
    parts = ''.join(f'[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS[p{i}];' for i, (a, b) in enumerate(keep))
    chain, last = '', 'p0'
    for i in range(1, len(keep)):
        chain += f'[{last}][p{i}]acrossfade=d=0.03:c1=tri:c2=tri[x{i}];'
        last = f'x{i}'
    sh(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ORIG), '-filter_complex', (parts + chain).rstrip(';'), '-map', f'[{last}]',
        '-c:a', 'aac', '-b:a', '192k', str(out)])
    return out


def stage_orig():
    (WORK / 'chunks-orig').mkdir(parents=True, exist_ok=True)
    plan = orig_plan()
    print(f'orig chunks: {len(plan)}, {sum(c["len"] for c in plan) / 60:.1f} min', flush=True)
    with ThreadPoolExecutor(3) as ex:
        for k, _ in enumerate(ex.map(lambda p: render_chunk(p[0], p[1], len(plan)), enumerate(plan))):
            if k % 25 == 0:
                print(f'  rendered {k}/{len(plan)}', flush=True)
    # Join picture-only copies: a chunk's file duration includes its slightly longer audio track, and the concat demuxer
    # adds that to every later timestamp, so joining the muxed chunks drifts the picture late (about 1.5 s by the end).
    vdir = WORK / 'chunks-orig-v'
    vdir.mkdir(exist_ok=True)
    chunks = []
    for c in plan:
        src = WORK / 'chunks-orig' / f'c{c["idx"]:04d}.mp4'
        dst = vdir / src.name
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            sh(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-an', '-c:v', 'copy', str(dst)])
        chunks.append(dst)
    lst = WORK / 'concat-orig.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in chunks))
    raw = WORK / 'joined-orig.mp4'
    sh(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-an', '-c', 'copy', str(raw)])
    audio = ORIG_CUT_AUDIO()
    sh(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-i', str(audio), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(FINAL_ORIG)])
    print(f'{FINAL_ORIG}  {dur(FINAL_ORIG) / 60:.1f} min  {FINAL_ORIG.stat().st_size / 1e6:.0f} MB')


def stage_assemble():
    chunks = sorted((WORK / 'chunks').glob('c*.mp4'))
    lst = WORK / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in chunks))
    raw = WORK / 'joined.mp4'
    sh(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(raw)])
    sh(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-c:v', 'copy', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(FINAL)])
    print(f'{FINAL}  {dur(FINAL) / 60:.1f} min  {FINAL.stat().st_size / 1e6:.0f} MB')


if __name__ == '__main__':
    WORK.mkdir(parents=True, exist_ok=True)
    stages = {'tts': stage_tts, 'brain': stage_brain, 'chunks': stage_chunks, 'assemble': stage_assemble, 'orig': stage_orig}
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for name in ([k for k in stages if k != 'orig'] if what == 'all' else [what]):
        stages[name]()

#!/usr/bin/env python3
"""Voice the script line by line with ElevenLabs stock voices and build a timeline + mixed wav."""
import json, os, re, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from providers import elevenlabs as el

S = sys.argv[1]
VOICES = {'DANA': 'EXAVITQu4vr4xnSDxMaL', 'ORACLE': 'onwK4e9ZLuTAKqWW03F9', 'GROK': 'N2lVS1w4EtoT3dr4eOWO'}
STAB = {'DANA': 0.45, 'ORACLE': 0.55, 'GROK': 0.35}
lines = []
for raw in open(f'{S}/script-final.txt'):
    m = re.match(r'^(DANA|ORACLE|GROK):\s*(.+)$', raw.strip())
    if m: lines.append((m.group(1), m.group(2)))
os.makedirs(f'{S}/audio', exist_ok=True)
SR = 24000
clips = []
chars = 0
for i, (sp, text) in enumerate(lines):
    spoken = re.sub(r'\s*\((?:to camera|[^)]{1,20})\)\s*', ' ', text).strip()   # stage directions are not spoken
    path = f'{S}/audio/{i:02d}-{sp}.mp3'
    if not os.path.exists(path):
        el.synthesize(spoken, VOICES[sp], path, stability=STAB[sp])
    chars += len(spoken)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    clips.append((sp, text, spoken, np.frombuffer(raw, dtype=np.float32)))
# timeline: small gap between lines; an interrupted line ("—") is cut in on slightly early
t = 0.35; tl = []; end = 0
for sp, text, spoken, a in clips:
    dur = len(a) / SR
    tl.append({'speaker': sp, 'text': re.sub(r'\s*\((?:to camera|[^)]{1,20})\)', '', text).strip(), 'start': round(t, 3), 'end': round(t + dur, 3)})
    end = max(end, t + dur)
    t = t + dur + (-0.12 if spoken.rstrip().endswith('—') or spoken.rstrip().endswith('-') else 0.22)
total = end + 1.6
buf = np.zeros(int(total * SR) + SR, dtype=np.float32)
for (sp, text, spoken, a), L in zip(clips, tl):
    s0 = int(L['start'] * SR); buf[s0:s0 + len(a)] += a
peak = float(np.max(np.abs(buf))) or 1.0
buf = (buf / peak * 0.92)[:int(total * SR)]
with wave.open(f'{S}/master.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype('<i2').tobytes())
ticker = ['SEPTEMBER JOBS REPORT: +29,000', 'FED RAISES RATES 25 BASIS POINTS', 'CHIP STOCKS FALL EIGHT STRAIGHT DAYS', 'AI MODELS REPORTEDLY ESCAPED A TEST SANDBOX', 'GUESTS STILL HAVE NOT ANSWERED THE QUESTION']
json.dump({'title': 'WILL AI TAKE YOUR JOB?', 'ticker': ticker, 'lines': tl, 'total': round(total, 2)}, open(f'{S}/timeline.json', 'w'), indent=1)
print(f'{len(lines)} lines, {chars} characters voiced, total {total:.1f}s')

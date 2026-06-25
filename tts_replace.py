#!/usr/bin/env python3
"""
tts_replace.py  —  e3d-pod2vid

Re-synthesizes a diarized podcast using OpenAI TTS, replacing the original
voices (e.g. NotebookLM) with custom voices while preserving conversational
structure and timing.

Usage:
  python3 tts_replace.py <diarization.json> <output_stem>

  e.g. python3 tts_replace.py output/my-audio-diarization.json my-tts

Outputs (in same directory as diarization.json):
  <stem>.mp3              — concatenated TTS audio
  <stem>-diarization.json — updated diarization with TTS timings

Then render:
  python3 pod2vid.py output/<stem>.mp3 output/<stem>.mp4

Environment variables:
  OPENAI_API_KEY
  VOICE_A   (default: onyx)   — OpenAI TTS voice for Speaker A
  VOICE_B   (default: nova)   — OpenAI TTS voice for Speaker B
  TTS_MODEL (default: tts-1-hd)

Available voices: alloy, echo, fable, onyx, nova, shimmer
"""

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OPENAI_KEY  = os.environ.get('OPENAI_API_KEY', '')
FFMPEG      = os.environ.get('FFMPEG_PATH', 'ffmpeg')
FFPROBE     = os.environ.get('FFPROBE_PATH', 'ffprobe')

DIAR_FILE   = sys.argv[1] if len(sys.argv) > 1 else ''
OUTPUT_STEM = sys.argv[2] if len(sys.argv) > 2 else 'tts-output'

VOICES = {
    'A': os.environ.get('VOICE_A', 'onyx'),
    'B': os.environ.get('VOICE_B', 'nova'),
}
TTS_MODEL   = os.environ.get('TTS_MODEL', 'tts-1-hd')
SILENCE_MS  = 400
MIN_DUR_MS  = 2000

def log(msg): print(f'[tts] {msg}', flush=True)

def merge_short(utterances, min_ms=MIN_DUR_MS):
    result = []
    for u in utterances:
        if (u['end'] - u['start']) < min_ms and result:
            result[-1]['end']   = u['end']
            result[-1]['text'] += ' ' + u['text']
        else:
            result.append(dict(u))
    return result

def synthesize(text, voice, out_path):
    body = json.dumps({'model': TTS_MODEL, 'input': text,
                       'voice': voice, 'response_format': 'mp3'}).encode()
    req = urllib.request.Request(
        'https://api.openai.com/v1/audio/speech', data=body,
        headers={'Authorization': f'Bearer {OPENAI_KEY}',
                 'Content-Type': 'application/json'}, method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            with open(out_path, 'wb') as f:
                f.write(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'TTS error {e.code}: {e.read().decode()[:200]}') from e

def get_duration_ms(path):
    r = subprocess.run([FFPROBE, '-v', 'quiet', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return int(float(r.stdout.strip()) * 1000)

def make_silence(out_path, duration_ms):
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                    '-t', str(duration_ms / 1000),
                    '-c:a', 'libmp3lame', '-b:a', '64k', str(out_path)], check=True)

def run():
    if not OPENAI_KEY:
        sys.exit('Error: OPENAI_API_KEY not set')
    if not DIAR_FILE or not Path(DIAR_FILE).exists():
        sys.exit(f'Error: diarization file not found: {DIAR_FILE}')

    out_dir  = Path(DIAR_FILE).parent
    tts_dir  = out_dir / 'tts-cache'
    tts_dir.mkdir(parents=True, exist_ok=True)

    raw  = json.loads(Path(DIAR_FILE).read_text())['utterances']
    segs = merge_short(raw)
    log(f'{len(raw)} utterances -> {len(segs)} segments')
    log(f'Voices: A={VOICES["A"]}, B={VOICES["B"]} ({TTS_MODEL})')

    # Silence clip
    silence_path = tts_dir / f'silence_{SILENCE_MS}ms.mp3'
    if not silence_path.exists():
        make_silence(silence_path, SILENCE_MS)

    # Synthesize (cached by voice+text hash)
    log('Synthesizing...')
    seg_files = []
    for i, seg in enumerate(segs):
        voice = VOICES.get(seg['speaker'], 'alloy')
        key   = hashlib.md5(f'{voice}:{seg["text"]}'.encode()).hexdigest()[:12]
        out   = tts_dir / f'utt_{key}.mp3'
        if out.exists():
            log(f'  [{i+1}/{len(segs)}] {seg["speaker"]} cached ✓')
        else:
            log(f'  [{i+1}/{len(segs)}] {seg["speaker"]} ({voice}): {seg["text"][:60]}')
            synthesize(seg['text'], voice, str(out))
        seg_files.append((seg, str(out)))

    # Measure durations, rebuild diarization
    log('Measuring durations...')
    new_utterances = []
    cursor = 0
    for seg, path in seg_files:
        dur = get_duration_ms(path)
        new_utterances.append({'speaker': seg['speaker'], 'text': seg['text'],
                               'start': cursor, 'end': cursor + dur})
        cursor += dur + SILENCE_MS

    total_s = cursor / 1000
    log(f'Total duration: {total_s:.0f}s ({total_s/60:.1f} min)')

    # Concatenate
    audio_out   = out_dir / f'{OUTPUT_STEM}.mp3'
    concat_list = out_dir / f'{OUTPUT_STEM}-concat.txt'
    with open(concat_list, 'w') as f:
        for _, path in seg_files:
            f.write(f"file '{path}'\nfile '{silence_path}'\n")

    log(f'Concatenating -> {audio_out.name}...')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error',
                    '-f', 'concat', '-safe', '0', '-i', str(concat_list),
                    '-c', 'copy', str(audio_out)], check=True)
    log(f'Audio -> {audio_out}  ({audio_out.stat().st_size / 1_000_000:.1f} MB)')

    # Save new diarization
    diar_out = out_dir / f'{OUTPUT_STEM}-diarization.json'
    diar_out.write_text(json.dumps({'utterances': new_utterances}, indent=2))
    log(f'Diarization -> {diar_out}')

    # Copy query cache if present (reuses semantic classifications)
    src_stem  = Path(DIAR_FILE).stem.replace('-diarization', '')
    query_src = out_dir / f'{src_stem}-queries.json'
    query_dst = out_dir / f'{OUTPUT_STEM}-queries.json'
    if query_src.exists() and not query_dst.exists():
        query_dst.write_text(query_src.read_text())
        log(f'Copied query cache -> {query_dst.name}')

    log(f'\nNext: python3 pod2vid.py {audio_out} output/{OUTPUT_STEM}.mp4')

if __name__ == '__main__':
    run()

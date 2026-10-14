"""ElevenLabs text-to-speech and voice cloning (stdlib only).

Auth: `xi-api-key` header from ELEVENLABS_API_KEY.
"""

import json
import os
import urllib.error
import urllib.request
import uuid

BASE_URL = 'https://api.elevenlabs.io'
DEFAULT_MODEL = 'eleven_multilingual_v2'
DEFAULT_FORMAT = 'mp3_44100_128'


class ElevenLabsError(RuntimeError):
    pass


def api_key():
    key = os.environ.get('ELEVENLABS_API_KEY', '')
    if not key:
        raise ElevenLabsError('ELEVENLABS_API_KEY not set')
    return key


def _request(method, path, *, body=None, headers=None, timeout=120, raw=False):
    hdrs = {'xi-api-key': api_key(), 'User-Agent': 'pod2vid/1.0'}
    hdrs.update(headers or {})
    req = urllib.request.Request(BASE_URL + path, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = res.read()
    except urllib.error.HTTPError as e:
        raise ElevenLabsError(f'{method} {path} -> {e.code}: {e.read().decode(errors="replace")[:300]}') from e
    return data if raw else json.loads(data)


def synthesize(text, voice_id, out_path, *, model=None, stability=0.5,
               similarity_boost=0.8, style=0.15, output_format=DEFAULT_FORMAT):
    """Write speech for `text` in `voice_id` to `out_path` (mp3). Returns out_path."""
    body = json.dumps({
        'text': text,
        'model_id': model or os.environ.get('ELEVENLABS_MODEL', DEFAULT_MODEL),
        'voice_settings': {'stability': stability, 'similarity_boost': similarity_boost,
                           'style': style, 'use_speaker_boost': True},
    }).encode()
    audio = _request('POST', f'/v1/text-to-speech/{voice_id}?output_format={output_format}',
                     body=body, headers={'Content-Type': 'application/json',
                                         'Accept': 'audio/mpeg'}, raw=True)
    with open(out_path, 'wb') as f:
        f.write(audio)
    return out_path


def list_voices():
    return _request('GET', '/v2/voices?page_size=100').get('voices', [])


def subscription():
    """Character quota and tier; also serves as a cheap credential check."""
    return _request('GET', '/v1/user/subscription', timeout=30)


def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, content, ctype) in files:
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                      f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n').encode()
                     + content + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def clone_voice(name, sample_paths, description='', remove_background_noise=True):
    """Instant voice clone from the speaker's OWN audio samples. Returns voice_id.

    Only use audio of a person who has consented to being cloned (e.g. yourself).
    """
    files = []
    for p in sample_paths:
        with open(p, 'rb') as f:
            files.append(('files', (os.path.basename(p), f.read(), 'audio/mpeg')))
    fields = {'name': name, 'description': description,
              'remove_background_noise': 'true' if remove_background_noise else 'false'}
    body, ctype = _multipart(fields, files)
    return _request('POST', '/v1/voices/add', body=body,
                    headers={'Content-Type': ctype}, timeout=300)['voice_id']


if __name__ == '__main__':
    import sys
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'voices':
        for v in list_voices():
            print(f'{v["voice_id"]}  {v.get("name", "")}  [{v.get("category", "")}]')
    elif cmd == 'status':
        s = subscription()
        print(f'tier={s.get("tier")} chars={s.get("character_count")}/{s.get("character_limit")} '
              f'instant_clone={s.get("can_use_instant_voice_cloning")}')
    elif cmd == 'clone' and len(sys.argv) >= 4:
        print(clone_voice(sys.argv[2], sys.argv[3:]))
    else:
        sys.exit('usage: python3 -m providers.elevenlabs voices | status | clone NAME sample.mp3 [...]')

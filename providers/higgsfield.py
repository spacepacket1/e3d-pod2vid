"""Higgsfield video generation (stdlib only).

Auth: `Authorization: Key <key_id>:<key_secret>`; HIGGSFIELD_API_KEY holds
"key_id:key_secret". Submit -> poll -> download, per
https://docs.higgsfield.ai (requests lifecycle).
"""

import json
import os
import time
import urllib.error
import urllib.request
import uuid

BASE_URL = 'https://api.higgsfield.ai'
DEFAULT_MODEL = 'kling-video/v2.5-turbo/standard/text-to-video'
TERMINAL = {'completed', 'failed', 'nsfw', 'canceled'}


class HiggsfieldError(RuntimeError):
    pass


def credentials():
    key = os.environ.get('HIGGSFIELD_API_KEY', '')
    if ':' not in key:
        raise HiggsfieldError('HIGGSFIELD_API_KEY must be "key_id:key_secret"')
    return key


def _request(method, url, *, body=None, headers=None, timeout=60):
    hdrs = {'Authorization': f'Key {credentials()}', 'User-Agent': 'pod2vid/1.0',
            'Content-Type': 'application/json'}
    hdrs.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise HiggsfieldError(f'{method} {url} -> {e.code}: {e.read().decode(errors="replace")[:300]}') from e


def check_credentials():
    """True if the key is accepted. Probes a random request id: 404 means authenticated."""
    try:
        _request('GET', f'{BASE_URL}/requests/{uuid.uuid4()}/status', timeout=30)
        return True
    except HiggsfieldError as e:
        msg = str(e)
        if ' 401' in msg or ' 403' in msg:
            return False
        return True   # 404 / 422: authenticated, request simply doesn't exist


def submit(model, arguments):
    """Enqueue a generation. Returns the response (request_id, status_url, ...)."""
    return _request('POST', f'{BASE_URL}/{model}', body=arguments,
                    headers={'Idempotency-Key': str(uuid.uuid4())})


def wait(submitted, *, timeout_s=900, poll_s=5, sleep=time.sleep, clock=time.monotonic):
    """Poll until a terminal status; returns the final response."""
    url = submitted.get('status_url') or f'{BASE_URL}/requests/{submitted["request_id"]}/status'
    deadline = clock() + timeout_s
    delay = poll_s
    while True:
        res = _request('GET', url, timeout=30)
        if res.get('status') in TERMINAL:
            return res
        if clock() > deadline:
            raise HiggsfieldError(f'timed out waiting for {submitted.get("request_id")}')
        sleep(delay)
        delay = min(delay * 1.3, 20)


def download(url, out_path):
    req = urllib.request.Request(url, headers={'User-Agent': 'pod2vid/1.0'})
    with urllib.request.urlopen(req, timeout=300) as res, open(out_path, 'wb') as f:
        while chunk := res.read(1 << 20):
            f.write(chunk)
    return out_path


def generate_video(prompt, out_path, *, model=None, duration=5, image_url=None,
                   negative_prompt='text, watermark, logo, distorted faces'):
    """Generate one clip and save it as `out_path`. Output URLs live >= 7 days upstream."""
    model = model or os.environ.get('HIGGSFIELD_MODEL', DEFAULT_MODEL)
    args = {'prompt': prompt, 'duration': duration}
    if 'kling' in model:
        args['negative_prompt'] = negative_prompt
    if image_url:
        args['image_url'] = image_url
    res = wait(submit(model, args))
    if res.get('status') != 'completed':
        raise HiggsfieldError(f'generation {res.get("status")}: {res.get("error", "")}')
    url = (res.get('video') or {}).get('url')
    if not url:
        raise HiggsfieldError('completed response had no video.url')
    return download(url, out_path)

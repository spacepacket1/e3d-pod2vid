import json
import os
import unittest
from unittest import mock

from providers import elevenlabs, higgsfield


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def read(self, *a):
        data, self.payload = self.payload, b''
        return data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ElevenLabsTests(unittest.TestCase):
    def test_requires_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(elevenlabs.ElevenLabsError):
                elevenlabs.api_key()

    def test_synthesize_posts_voice_and_writes_audio(self):
        seen = {}

        def fake_urlopen(req, timeout=0):
            seen['url'], seen['body'] = req.full_url, json.loads(req.data)
            seen['key'] = req.get_header('Xi-api-key')
            return FakeResponse(b'AUDIO')

        import tempfile
        with mock.patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'k'}), \
             mock.patch('urllib.request.urlopen', fake_urlopen), \
             tempfile.TemporaryDirectory() as d:
            out = elevenlabs.synthesize('hello', 'VOICE1', f'{d}/a.mp3')
            self.assertEqual(open(out, 'rb').read(), b'AUDIO')
        self.assertIn('/v1/text-to-speech/VOICE1', seen['url'])
        self.assertEqual(seen['body']['text'], 'hello')
        self.assertEqual(seen['key'], 'k')

    def test_multipart_contains_fields_and_file(self):
        body, ctype = elevenlabs._multipart({'name': 'Me'}, [('files', ('a.mp3', b'xyz', 'audio/mpeg'))])
        self.assertIn('boundary=', ctype)
        self.assertIn(b'name="name"', body)
        self.assertIn(b'filename="a.mp3"', body)
        self.assertIn(b'xyz', body)


class HiggsfieldTests(unittest.TestCase):
    def test_requires_id_secret_format(self):
        with mock.patch.dict(os.environ, {'HIGGSFIELD_API_KEY': 'nocolon'}):
            with self.assertRaises(higgsfield.HiggsfieldError):
                higgsfield.credentials()

    def test_wait_polls_until_terminal(self):
        statuses = iter([{'status': 'queued'}, {'status': 'in_progress'},
                         {'status': 'completed', 'video': {'url': 'u'}}])
        with mock.patch.object(higgsfield, '_request', lambda *a, **k: next(statuses)):
            res = higgsfield.wait({'request_id': 'r'}, sleep=lambda s: None)
        self.assertEqual(res['video']['url'], 'u')

    def test_wait_times_out(self):
        ticks = iter(range(0, 10000, 400))
        with mock.patch.object(higgsfield, '_request', lambda *a, **k: {'status': 'queued'}):
            with self.assertRaises(higgsfield.HiggsfieldError):
                higgsfield.wait({'request_id': 'r'}, timeout_s=600, sleep=lambda s: None,
                                clock=lambda: next(ticks))

    def test_generate_video_failure_status_raises(self):
        with mock.patch.object(higgsfield, 'submit', lambda *a, **k: {'request_id': 'r'}), \
             mock.patch.object(higgsfield, 'wait', lambda *a, **k: {'status': 'nsfw'}):
            with self.assertRaises(higgsfield.HiggsfieldError):
                higgsfield.generate_video('p', '/tmp/x.mp4')

    def test_check_credentials_detects_401(self):
        def boom(*a, **k):
            raise higgsfield.HiggsfieldError('GET x -> 401: Invalid credentials')
        with mock.patch.object(higgsfield, '_request', boom):
            self.assertFalse(higgsfield.check_credentials())


if __name__ == '__main__':
    unittest.main()

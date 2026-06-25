# e3d-pod2vid

**AI-powered podcast-to-video pipeline.** Converts a diarized audio file (NotebookLM, podcast, interview) into a YouTube-ready MP4 with:

- Semantically matched Pexels B-roll per utterance (GPT-4o-mini picks the clip)
- Burned-in subtitles (no ffmpeg libass required — pure Pillow)
- Optional OpenAI TTS voice replacement (swap out NotebookLM / AI voices)
- YouTube upload + description/thumbnail update
- One-shot multi-platform social posting (Discord, Telegram, X, Moltbook)

---

## Quick Start

```bash
git clone https://github.com/spacepacket1/e3d-pod2vid.git
cd e3d-pod2vid

# Python deps
pip install -r requirements.txt

# Node deps (YouTube + social posting only)
npm install

# Copy and fill in your API keys
cp .env.example .env
$EDITOR .env
```

---

## Workflow

### 1. Convert audio to video

```bash
python3 pod2vid.py episode.m4a output/episode.mp4
```

This single command:
1. Uploads audio to AssemblyAI for speaker diarization
2. Asks GPT-4o-mini for a specific Pexels search query per utterance
3. Downloads matching B-roll clips (cached per query)
4. Renders each segment with burned-in subtitles
5. Concatenates into a final MP4 + SRT subtitle file

Caches diarization and queries as JSON so re-runs are fast.

---

### 2. (Optional) Replace voices with OpenAI TTS

If you want custom voices instead of the original audio (e.g. replace NotebookLM voices):

```bash
# Synthesize with OpenAI TTS voices
python3 tts_replace.py output/episode-diarization.json episode-tts

# Render video using TTS audio
python3 pod2vid.py output/episode-tts.mp3 output/episode-tts.mp4
```

Default voices: **onyx** (Speaker A) and **nova** (Speaker B). Override with `VOICE_A` / `VOICE_B`.

Available voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

---

### 3. Generate a thumbnail

```bash
python3 make_thumbnail.py "Predictive GPS for Autonomous AI Agents" thumbnail.png /path/to/logo.png
```

Outputs a 1280×720 PNG with title, accent stripe, and optional logo overlay. Pure Pillow — no browser or design tool required.

---

### 4. Upload to YouTube

**First time: authorize your account**

```bash
node yt_auth.js
```

The script prints a URL. Open it on any device (phone, browser — the machine running the script doesn't need a browser). After approving, paste the redirect URL back into the terminal. Tokens are saved to `youtube-tokens.json`.

**Upload the video**

```bash
node yt_upload.js output/episode-tts.mp4 "My Episode Title"
```

Prints the video URL and ID when done.

**Update description and thumbnail**

```bash
YT_DESCRIPTION="Check out maps.e3d.ai — AI-powered GPS for autonomous vehicles.

Follow us:
• X: @e3dmaps
• Discord: https://discord.gg/your-server" \
node yt_update.js VIDEO_ID thumbnail.png
```

---

### 5. Announce on social media

```bash
node announce.js https://www.youtube.com/watch?v=VIDEO_ID "New episode: Predictive GPS for Autonomous AI Agents"
```

Posts simultaneously to every platform that has credentials configured in `.env`. Platforms with no credentials are silently skipped.

---

## Configuration

Copy `.env.example` to `.env` and fill in the keys you need.

| Variable | Required for | Notes |
|---|---|---|
| `ASSEMBLYAI_API_KEY` | `pod2vid.py` | [assemblyai.com](https://www.assemblyai.com) |
| `OPENAI_API_KEY` | `pod2vid.py`, `tts_replace.py` | GPT-4o-mini + TTS |
| `PEXELS_API_KEY` | `pod2vid.py` | [pexels.com/api](https://www.pexels.com/api/) — free |
| `DISCORD_BOT_TOKEN` | `announce.js` | Optional |
| `DISCORD_CHANNEL_ID` | `announce.js` | Optional |
| `TELEGRAM_BOT_TOKEN` | `announce.js` | Optional |
| `TELEGRAM_CHAT_ID` | `announce.js` | Optional |
| `X_ACCESS_TOKEN` | `announce.js` | OAuth2 bearer token |
| `MOLTBOOK_API_KEY` | `announce.js` | Optional |
| `VOICE_A` | `tts_replace.py` | Default: `onyx` |
| `VOICE_B` | `tts_replace.py` | Default: `nova` |
| `SPEAKER_A_NAME` | `pod2vid.py` | Subtitle label (default: `Host`) |
| `SPEAKER_B_NAME` | `pod2vid.py` | Subtitle label (default: `Guest`) |
| `YT_PRIVACY` | `yt_upload.js` | `public` / `unlisted` / `private` |
| `YT_DESCRIPTION` | `yt_update.js` | Full video description text |

---

## How semantic B-roll works

Instead of rotating through a fixed clip library, this pipeline asks GPT-4o-mini to generate a specific Pexels search query for each utterance:

```
"EZPass saved us 90 seconds at every toll plaza"
  → "toll booth highway payment"

"the dual-witness problem"
  → "courtroom judge testimony"

"machine learning position predictions"
  → "machine learning data training loop"
```

Queries are cached so re-runs or TTS voice swaps don't re-spend API credits. ~82 unique clips across a 90-segment episode is typical.

---

## Requirements

**Python 3.8+**
- Pillow >= 10.0
- python-dotenv >= 1.0
- ffmpeg (any version — subtitle rendering does not require libfreetype/libass)

**Node.js 18+**
- dotenv

**External APIs**
- AssemblyAI (diarization)
- OpenAI (GPT-4o-mini + TTS)
- Pexels (B-roll clips, free tier fine for personal use)
- YouTube Data API v3 (via Google Cloud Console)

---

## Output files

```
output/
  episode.mp4                    final video
  episode.srt                    subtitle file for YouTube CC
  episode-diarization.json       cached AssemblyAI result
  episode-queries.json           cached GPT Pexels queries
  broll/                         cached B-roll clips (one per unique query)
  tts-cache/                     cached TTS utterances (per voice+text hash)
```

---

## Credits

Built by [E3D Maps](https://maps.e3d.ai) — AI-powered navigation for autonomous vehicles.

---

## License

MIT

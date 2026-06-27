# e3d-pod2vid

**AI-powered podcast-to-video pipeline.** Converts a diarized audio file (NotebookLM, podcast, interview) into a YouTube-ready MP4 with:

- Semantically matched Pexels B-roll per utterance (GPT-4o-mini picks the clip)
- Burned-in subtitles (no ffmpeg libass required — pure Pillow)
- Optional OpenAI TTS voice replacement (swap out NotebookLM / AI voices)
- YouTube upload + description/thumbnail update
- One-shot multi-platform social posting (Discord, Telegram, X, Moltbook, LinkedIn)

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

Posts simultaneously to all configured platforms. Platforms with no credentials are silently skipped.

| Platform | Credential(s) needed |
|---|---|
| Discord | `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |
| X (Twitter) | `X_ACCESS_TOKEN` |
| Moltbook | `MOLTBOOK_API_KEY` |
| LinkedIn | `linkedin-tokens.json` with `person_urn` (run `node linkedin_auth.js`) |

---

### 6. (Optional) LinkedIn setup

LinkedIn's API requires a few one-time setup steps before `announce.js` can post there.

**Step 1 — Create a LinkedIn app**

Go to [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps/new) and create an app. Under the **Auth** tab, add this as an authorized redirect URL:

```
https://www.linkedin.com/developers/tools/oauth/redirect
```

**Step 2 — Add required products**

Under the **Products** tab, request access to both:
- **Share on LinkedIn** — grants `w_member_social` scope (post on behalf of user)
- **Sign In with LinkedIn using OpenID Connect** — grants `openid profile` scopes (needed to resolve your person URN)

Both are typically approved instantly for personal apps.

**Step 3 — Verify company association** *(if prompted)*

LinkedIn may ask you to verify a company page association. Open the verification URL while logged in as a Page Admin and approve it.

**Step 4 — Authorize and get tokens**

Add your app credentials to `.env`:

```
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```

Then run:

```bash
node linkedin_auth.js
```

Open the printed URL on any device. After approving, paste the redirect URL back. Tokens are saved to `linkedin-tokens.json`.

**Step 5 — Add your person URN**

LinkedIn's API requires your encoded person ID (not your numeric member ID). To find it:

1. Go to your LinkedIn profile in a browser
2. View Page Source (Cmd+U / Ctrl+U) and search for `urn:li:member:`
3. Note the numeric ID (e.g. `4435724`)
4. Make a test API call — the error response will reveal your encoded person URN (e.g. `urn:li:person:2KqUAyg4oY`)

Or run this one-liner after getting a token:

```bash
node -e "
const https = require('https');
const t = JSON.parse(require('fs').readFileSync('linkedin-tokens.json'));
// Replace MEMBER_ID with your numeric ID from page source
const body = JSON.stringify({author:'urn:li:member:MEMBER_ID',commentary:'test',visibility:'PUBLIC',distribution:{feedDistribution:'MAIN_FEED',targetEntities:[],thirdPartyDistributionChannels:[]},lifecycleState:'PUBLISHED',isReshareDisabledByAuthor:false});
const u = require('url').parse('https://api.linkedin.com/rest/posts');
const r = https.request(Object.assign(u,{method:'POST',headers:{'Authorization':'Bearer '+t.access_token,'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),'LinkedIn-Version':'202506','X-Restli-Protocol-Version':'2.0.0'}}),res=>{let d='';res.on('data',c=>d+=c);res.on('end',()=>console.log(d.slice(0,300)));});
r.write(body);r.end();
"
```

The error message will contain your encoded URN. Save it:

```bash
node -e "
const fs = require('fs');
const t = JSON.parse(fs.readFileSync('linkedin-tokens.json'));
t.person_urn = 'urn:li:person:YOUR_ENCODED_ID';
fs.writeFileSync('linkedin-tokens.json', JSON.stringify(t, null, 2));
"
```

Once `linkedin-tokens.json` contains `person_urn`, `announce.js` will post to LinkedIn automatically.

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
| `MOLTBOOK_SUBMOLT` | `announce.js` | Submolt name (default: `agentfinance`) |
| `LINKEDIN_CLIENT_ID` | `linkedin_auth.js` | From [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) |
| `LINKEDIN_CLIENT_SECRET` | `linkedin_auth.js` | From LinkedIn Developer Portal |
| `LINKEDIN_TOKEN_FILE` | `announce.js` | Default: `linkedin-tokens.json` — must contain `person_urn` |
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
- LinkedIn API (via [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)) — optional, for posting

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

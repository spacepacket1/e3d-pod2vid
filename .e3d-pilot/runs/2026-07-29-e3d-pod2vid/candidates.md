---
selected: candidate-1
reason: Highest non-duplicate attraction+retention (8), closes the single biggest new-user conversion friction point, and does not duplicate any prior run candidate or branch.
---

# Candidates

## Validation Warnings

- Candidate 5 is missing a Category field
- Candidate 5 is missing an Analogy field
- Candidate 5 is missing an Attraction score
- Candidate 5 is missing a Retention score
- Candidate 5 is missing an Effort field

## Dedup Context

## Current Findings

```text
---
head_sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be
---

# Findings

## Local State

Repo head sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be

Research topics: podcast-to-video generation pipeline

Analogy domains to consider: game progression and reward loops; social feed and notification mechanics; marketplace liquidity and two-sided matching; developer-tool CLI ergonomics; fintech trust and verification UX

## Git history
range: last 20 commits
```text
3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
564c87a Remove invalid wildcard permission rule from Claude Code settings
09f7a02 Merge remote-tracking branch 'origin/main'
c5193de Add optional local-Whisper transcription engine alongside AssemblyAI
9fb97b6 Add dramatic YouTube Short script for e3d.ai's token registry positioning
a6598fd Enable prompt suggestions in Claude Code settings
d2e1c8e Add Claude Code auto-permissions (allow all tools)
0f378bd Add split-screen layout, nova voice, and X OAuth2 auth script
11c9bdb Add multichain E3D Short: Bloomberg-style announcement across 4 chains
e14ffd9 Add regression tests for the manifest.kind validation bug
819f543 Add the hosted job runner (bin/pod2vid-job.py, pod2vid_worker.py)
baa06b5 Sync spec: rename pod2vid → cast
08eac3a Sync spec: fix runner phase detection false positives
7dbeb3b Sync spec: fix runner phase detector conflict
d793b47 Sync spec: fix runner instructions for sandbox write access
123bbb7 Sync spec: single-repo phases and runner instructions
579c609 Revise Pod2Vid hosted product spec with growth focus and v1/v1.1 split
55e3171 Add hosted Pod2Vid E3D product spec
3d963ca Add hand-scripted E3D Token YouTube Short generator
56b587d Add E3D Token sponsor segment to every signal Short
```

## Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH issues and PRs
### gh issue list
- none found
### gh pr list
- none found

## Repo docs
### README.md
```text
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

### 3. Generate a YouTube Short from an E3D Maps signal (automated)

```bash
python3 signal_short.py [--dry-run] [--force]
```

Pulls live signals from [maps.e3d.ai](https://maps.e3d.ai), picks the most significant one, generates a script, renders a Short, uploads to YouTube, and posts to all social platforms — automatically, daily.

**Filtering criteria** (any one qualifies):
- Confidence ≥ `CONF_THRESHOLD` (default: 78%)
- `risk_level == 'high'` AND confidence ≥ 55%
- `signal_strength == 'strong'`
- 3+ independent signals converging on the same destination (cluster alert)

**Flags:**
- `--dry-run` — generate the script and queries but skip render/upload
- `--force` — re-post even if that signal was already posted today

**Environment variables:**

| Variable | Notes |
|---|---|
| `MAPS_URL` | Default: `https://maps.e3d.ai` |
| `MAPS_INTERNAL_KEY` | Optional — endpoint is public |
| `CONF_THRESHOLD` | Float 0-1, default `0.78` |

State (which signals have been posted today) is written to `output/signal-short-state.json`.

**Schedule with PM2:**

```bash
# Start daily cron at 14:00 UTC
pm2 start ecosystem.config.js --env production

# View logs
pm2 logs signal-short
```

---

### 4. Generate a YouTube Short (custom script)

```bash
python3 make_short.py [output.mp4]
```

Produces a vertical 1080×1920 MP4 (≤60s) ready for YouTube Shorts, Instagram Reels, or TikTok:

- **Silent hook clip** — eye-catching opener (no narration, grabs attention in the first 2 seconds)
- **TTS voiceover** — OpenAI `tts-1-hd` narrates a built-in script about the tool
- **Semantic Pexels B-roll** — lifestyle, car, and tech footage matched to each line
- **Burned-in subtitles** — same PIL renderer as `pod2vid.py`, sized for mobile
- **CTA card** — closing frame with GitHub URL and accent branding

The script and B-roll queries are defined in the `SEGMENTS` list at the top of `make_short.py` — edit them to customise the script for your own content.

Environment variables:

| Variable | Default | Notes |
|---|---|---|
| `SHORT_VOICE` | `onyx` | OpenAI TTS voice for narration |

---

### 5. Generate a thumbnail

```bash
python3 make_thumbnail.py "Predictive GPS for Autonomous AI Agents" thumbnail.png /path/to/logo.png
```

Outputs a 1280×720 PNG with title, accent stripe, and optional logo overlay. Pure Pillow — no browser or design tool required.

---

## Hosted worker wrapper

Phase 3 adds `python3 bin/pod2vid-job.py <manifest.json>` for hosted-job execution. The wrapper:

- validates a worker-facing manifest defined in [docs/pod2vid-job.schema.json](/home/ubuntu/e3d-pod2vid/docs/pod2vid-job.schema.json)
- writes deterministic outputs under `POD2VID_STORAGE_DIR` (defaults to `/tmp/e3d-pod2vid`)
- supports dry-run renders, transcript presets, thumbnail/metadata/subtitle-style revisions, archive manifests, and archive rehydration
- emits structured JSON progress events on stdout for a higher-level daemon to consume

See [docs/worker-wrapper.md](/home/ubuntu/e3d-pod2vid/docs/worker-wrapper.md) for the manifest fields, supported presets, and required API keys by preset.

---

### 6. Upload to YouTube

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

### 7. Announce on social media

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

### 8. (Optional) LinkedIn setup

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

```

## TODO/FIXME matches
- none found

## External Context

## External Context

- **Automated video synthesis** is maturing rapidly: Sora, Runway Gen-3, and HeyGen now offer API-level text-to-video, narrowing the moat of pure "assemble clips + TTS" pipelines; differentiation increasingly lies in distribution and signal-sourcing logic rather than render quality.
- **Speaker diarization** has shifted toward local-first options (WhisperX, pyannote-audio 3.x) that match hosted-API accuracy at near-zero marginal cost; AssemblyAI remains faster to integrate but adds per-minute cost at scale.
- **Semantic B-roll retrieval** via LLM-generated queries is a known pattern (Synthesia, Pictory, Lumen5 all do it), but vector-indexed stock libraries (Pexels is flat keyword search) would raise match precision significantly.
- **Short-form vertical video** remains the dominant distribution format; YouTube Shorts, Reels, and TikTok all now surface algorithmically differentiated from long-form, rewarding daily cadence and high hook retention (first 2 s).
- **Multi-platform social automation** is commoditizing (Buffer, Zapier, Make); the defensible layer here is the upstream signal intelligence (e3d Maps) driving *what* to post, not the posting mechanics themselves.

---

### Analogous Patterns

**1. Social feed & notification mechanics → signal threshold as publish trigger**
- Source domain: social feed ranking (Twitter/X EdgeRank-style score gates)
- Mechanic borrowed: a numeric confidence score gates whether content surfaces to users
- Applied here: `signal_short.py` already uses `CONF_THRESHOLD` + `risk_level` + `signal_strength` flags — borrowing feed-ranking's *decay* mechanic (score degrades if the same signal persists without new confirmation) would prevent stale signals from re-triggering posts and add a freshness dimension the current state-file approach lacks.

**2. Marketplace liquidity & two-sided matching → B-roll supply/demand balancing**
- Source domain: two-sided marketplace (Airbnb availability, ride-share dispatch)
- Mechanic borrowed: pre-fetching and pre-indexing supply to cut match latency
- Applied here: Pexels queries are cached per-run but re-requested cold on first use; pre-building a local vector index of pre-downloaded clips (supply side) and embedding-matching utterances against it (demand side) would eliminate API round-trips and enable offline rendering — the same way marketplaces pre-position inventory near demand clusters.

**3. Developer-tool CLI ergonomics → progressive disclosure of complexity**
- Source domain: well-designed CLI tools (gh, stripe CLI, vercel CLI)
- Mechanic borrowed: single-command happy path with `--verbose` / `--debug` for escape hatches, interactive prompts only when required config is missing
- Applied here: the current workflow requires 6+ manual steps (diarize → query → TTS → render → upload → announce) each as a separate command; wrapping them behind `pod2vid run episode.m4a --publish` with a `--dry-run` flag and lazy credential prompts would dramatically reduce time-to-first-video for new users.


```

## Git Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH PR List (state: all)
- none found

## Prior Runs (candidates.md / spec-final.md)
### 2026-07-27-e3d-pod2vid/candidates.md
```text
---
selected: candidate-1
reason: Highest attraction+retention (9), directly closes the clip-scoring gap versus category leaders, and is confirmed non-duplicate against all branches/PRs/prior runs.
---

# Candidates

## Dedup Context

## Current Findings

```text
---
head_sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be
---

# Findings

## Local State

Repo head sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be

Research topics: podcast-to-video generation pipeline

Analogy domains to consider: game progression and reward loops; social feed and notification mechanics; marketplace liquidity and two-sided matching; developer-tool CLI ergonomics; fintech trust and verification UX

## Git history
range: last 20 commits
```text
3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
564c87a Remove invalid wildcard permission rule from Claude Code settings
09f7a02 Merge remote-tracking branch 'origin/main'
c5193de Add optional local-Whisper transcription engine alongside AssemblyAI
9fb97b6 Add dramatic YouTube Short script for e3d.ai's token registry positioning
a6598fd Enable prompt suggestions in Claude Code settings
d2e1c8e Add Claude Code auto-permissions (allow all tools)
0f378bd Add split-screen layout, nova voice, and X OAuth2 auth script
11c9bdb Add multichain E3D Short: Bloomberg-style announcement across 4 chains
e14ffd9 Add regression tests for the manifest.kind validation bug
819f543 Add the hosted job runner (bin/pod2vid-job.py, pod2vid_worker.py)
baa06b5 Sync spec: rename pod2vid → cast
08eac3a Sync spec: fix runner phase detection false positives
7dbeb3b Sync spec: fix runner phase detector conflict
d793b47 Sync spec: fix runner instructions for sandbox write access
123bbb7 Sync spec: single-repo phases and runner instructions
579c609 Revise Pod2Vid hosted product spec with growth focus and v1/v1.1 split
55e3171 Add hosted Pod2Vid E3D product spec
3d963ca Add hand-scripted E3D Token YouTube Short generator
56b587d Add E3D Token sponsor segment to every signal Short
```

## Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH issues and PRs
### gh issue list
- none found
### gh pr list
- none found

## Repo docs
### README.md
```text
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

### 3. Generate a YouTube Short from an E3D Maps signal (automated)

```bash
python3 signal_short.py [--dry-run] [--force]
```

Pulls live signals from [maps.e3d.ai](https://maps.e3d.ai), picks the most significant one, generates a script, renders a Short, uploads to YouTube, and posts to all social platforms — automatically, daily.

**Filtering criteria** (any one qualifies):
- Confidence ≥ `CONF_THRESHOLD` (default: 78%)
- `risk_level == 'high'` AND confidence ≥ 55%
- `signal_strength == 'strong'`
- 3+ independent signals converging on the same destination (cluster alert)

**Flags:**
- `--dry-run` — generate the script and queries but skip render/upload
- `--force` — re-post even if that signal was already posted today

**Environment variables:**

| Variable | Notes |
|---|---|
| `MAPS_URL` | Default: `https://maps.e3d.ai` |
| `MAPS_INTERNAL_KEY` | Optional — endpoint is public |
| `CONF_THRESHOLD` | Float 0-1, default `0.78` |

State (which signals have been posted today) is written to `output/signal-short-state.json`.

**Schedule with PM2:**

```bash
# Start daily cron at 14:00 UTC
pm2 start ecosystem.config.js --env production

# View logs
pm2 logs signal-short
```

---

### 4. Generate a YouTube Short (custom script)

```bash
python3 make_short.py [output.mp4]
```

Produces a vertical 1080×1920 MP4 (≤60s) ready for YouTube Shorts, Instagram Reels, or TikTok:

- **Silent hook clip** — eye-catching opener (no narration, grabs attention in the first 2 seconds)
- **TTS voiceover** — OpenAI `tts-1-hd` narrates a built-in script about the tool
- **Semantic Pexels B-roll** — lifestyle, car, and tech footage matched to each line
- **Burned-in subtitles** — same PIL renderer as `pod2vid.py`, sized for mobile
- **CTA card** — closing frame with GitHub URL and accent branding

The script and B-roll queries are defined in the `SEGMENTS` list at the top of `make_short.py` — edit them to customise the script for your own content.

Environment variables:

| Variable | Default | Notes |
|---|---|---|
| `SHORT_VOICE` | `onyx` | OpenAI TTS voice for narration |

---

### 5. Generate a thumbnail

```bash
python3 make_thumbnail.py "Predictive GPS for Autonomous AI Agents" thumbnail.png /path/to/logo.png
```

Outputs a 1280×720 PNG with title, accent stripe, and optional logo overlay. Pure Pillow — no browser or design tool required.

---

## Hosted worker wrapper

Phase 3 adds `python3 bin/pod2vid-job.py <manifest.json>` for hosted-job execution. The wrapper:

- validates a worker-facing manifest defined in [docs/pod2vid-job.schema.json](/home/ubuntu/e3d-pod2vid/docs/pod2vid-job.schema.json)
- writes deterministic outputs under `POD2VID_STORAGE_DIR` (defaults to `/tmp/e3d-pod2vid`)
- supports dry-run renders, transcript presets, thumbnail/metadata/subtitle-style revisions, archive manifests, and archive rehydration
- emits structured JSON progress events on stdout for a higher-level daemon to consume

See [docs/worker-wrapper.md](/home/ubuntu/e3d-pod2vid/docs/worker-wrapper.md) for the manifest fields, supported presets, and required API keys by preset.

---

### 6. Upload to YouTube

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

### 7. Announce on social media

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

### 8. (Optional) LinkedIn setup

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

```

## TODO/FIXME matches
- none found

## External Context

I don't have web search access in this session, so I'll draft the External Context section from existing knowledge of the space rather than live sources.

## External Context

The repo sits in the AI-assisted "podcast/audio → distributable video" space, which has consolidated quickly over the last two years:

- **Managed pipelines** (Opus Clip, Descript, Riverside, Submagic, Vizard, Wisecut) now do diarization + repurposing end-to-end: cut long-form audio/video into vertical clips, auto-caption, and score/rank moments by predicted virality — mirroring this repo's diarize → segment → caption → publish shape, but with a "clip scoring" step this repo lacks.
- **B-roll sourcing** is shifting from stock-footage matching (what this repo does via Pexels + GPT query generation) toward generative B-roll (Runway, Pika, Luma, Sora-class text-to-video) and AI avatar hosts (HeyGen, Synthesia) that render a presenter directly rather than illustrating around narration.
- **TTS/voice** has moved to expressive, low-latency streaming models (ElevenLabs, OpenAI's newer realtime voices, Cartesia) with voice cloning as a common feature — relevant since this repo already swaps NotebookLM voices via OpenAI TTS and could clone a consistent host voice instead of using stock voices.
- **Multi-platform distribution** is standardizing around scheduling/repurposing suites (Buffer, Publer, Repurpose.io) that treat one asset → many platform-native posts as a first-class workflow, which is the same job `announce.js` does per-platform in this repo, just without scheduling/queueing.
- **Auto-editing quality signals** (silence/filler-word removal, pacing-aware cuts, retention-optimized clip selection) are becoming standard in this category and represent a natural gap area versus this repo's current linear utterance-by-utterance render.

### Analogous Patterns

- **Social feed and notification mechanics** — the "surface the most engagement-worthy moment, notify, and re-serve" loop that ranking feeds use (e.g., pushing the single best notification instead of all events) maps onto `signal_short.py`'s "pick the most significant signal" step: the pipeline could score every diarized utterance/segment for "hook strength" the way a feed ranks candidate posts, then generate the Short from the highest-scoring segment instead of a hand-picked or first-qualifying one.
- **Marketplace liquidity and two-sided matching** — marketplaces solve "many supply items, many demand slots" with a matching/auction layer rather than static rules; the current GPT-per-utterance → single Pexels query is a one-sided lookup. Treating B-roll clips as a supply pool and utterances as demand, then running a batch matching pass (e.g., maximize semantic coverage while minimizing repeat clips across an episode) would reduce duplicate footage and improve variety versus the current per-utterance greedy match.
- **Developer-tool CLI ergonomics** — modern CLIs (gh, stripe, vercel) lean on structured JSON output, `--dry-run`, idempotent state files, and clear subcommands, which this repo has already partially adopted (`--dry-run`, `--force`, JSON progress events in `bin/pod2vid-job.py`). Extending that ergonomics pattern — e.g., a unified `pod2vid <subcommand>` entrypoint with consistent flags across `pod2vid.py`, `signal_short.py`, and `make_short.py` instead of separate scripts — would bring the whole toolchain in line with that CLI-composability convention.


```

## Git Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH PR List (state: all)
- none found

## Prior Runs (candidates.md / spec-final.md)
- none found

## Proposed Candidates

### Candidate 1: Auto-generate multiple ranked highlight Shorts from a single episode
Duplicate: no
Dedup rationale: Only `main` branch exists (no feature branches), no open PRs, and no prior candidates/specs on record. Grepped the repo for "highlight", "clip.?scor", "viral" — no existing scoring or multi-clip logic; `make_short.py` only renders one hand-authored script and `signal_short.py` picks a single signal via static threshold rules, not a scored ranking of all candidates.
Category: workflow
Analogy: Social feed and notification mechanics -- feeds rank all candidate posts and surface only the top one(s) instead of showing everything; applying the same "score every candidate, serve only the best" logic to a full diarized episode (score each utterance/segment for hook strength, novelty, sentiment spike, etc.) lets the pipeline auto-produce 3-5 ranked Shorts per long-form episode instead of one full video, directly closing the "clip scoring" gap noted in External Context versus Opus Clip/Vizard/Submagic.
Attraction (1-5): 5
Retention (1-5): 4
Effort: medium
Revenue (1-5|n/a): 3
Description: Add a scoring pass over `pod2vid.py`'s diarization output (reuse GPT-4o-mini, similar to the existing per-utterance Pexels-query call) that rates each utterance/segment window for "clip-worthiness," then auto-render the top N windows as vertical Shorts using the existing `make_short.py`/subtitle/B-roll pipeline. This is the single biggest feature gap versus category leaders and turns every long episode into several pieces of distributable content instead of one, which is the core lever for both new-user attraction (a much more compelling free/trial demo) and retention (users get more usable output per episode).

### Candidate 2: Post-performance feedback loop (view/engagement analytics)
Duplicate: no
Dedup rationale: No branches, PRs, or prior runs reference analytics/metrics. Grep for "engagement|analytics|view_count" across all `.py`/`.js` files returned no matches — the pipeline currently has no read-back from YouTube/social APIs after publishing.
Category: data
Analogy: Fintech trust and verification UX -- fintech apps close the loop by showing users the real-world outcome of an action (balance updated, transaction cleared) rather than just confirming submission; applying that here means showing creators what actually happened to their video/post (views, watch-time, engagement) instead of just "uploaded successfully," turning a one-way publish tool into a feedback system.
Attraction (1-5): 3
Retention (1-5): 5
Effort: medium
Revenue (1-5|n/a): 3
Description: After `yt_upload.js`/`announce.js` publish, poll YouTube Data API (and platform APIs where available) for view count, watch-time, and engagement at 24h/7d intervals, store results alongside the existing `output/*.json` state files, and surface a simple report (CLI summary or JSON digest) showing which segments/B-roll queries/voices correlated with better performance. This is what brings users back to the tool repeatedly (retention) and, longer term, feeds back into Candidate 1's clip-scoring model to make future picks smarter — the kind of compounding data loop that's currently entirely absent.

### Candidate 3: Scheduled/queued multi-platform publishing
Duplicate: no
Dedup rationale: Checked `announce.js` and `ecosystem.config.js` (the only cron-adjacent file) — `ecosystem.config.js` only schedules the daily `signal_short.py` job itself, not a general post queue; `announce.js` posts synchronously and immediately to all platforms with no queueing/delay logic. No branch or PR touches this.
Category: workflow
Analogy: Marketplace liquidity and two-sided matching -- not directly applicable here; better framed via the "developer-tool CLI ergonomics" pattern extended to scheduling suites (Buffer/Publer/Repurpose.io) explicitly called out in External Context: one asset -> many platform-native posts, staged over time instead of blasted at once.
Attraction (1-5): 3
Retention (1-5): 3
Effort: low
Revenue (1-5|n/a): 2
Description: Add an optional `--schedule` flag / queue file to `announce.js` so a rendered video's cross-platform posts can be staggered (e.g., YouTube now, X in 1h, LinkedIn next morning) rather than firing all at once, with a small persistent queue (JSON, consistent with the existing `output/signal-short-state.json` pattern) and a lightweight `node announce.js --process-queue` cron entry. Low effort since it reuses all existing per-platform posting code; mainly helps creators who want to avoid dumping identical content across every channel simultaneously, a common cause of audience fatigue.

### Candidate 4: Episode-wide B-roll matching to reduce duplicate clips
Duplicate: no
Dedup rationale: Grepped `pod2vid.py` for "match"/"dedupe"/"duplicate" — no batch matching or dedup logic exists; queries are generated and cached per-utterance independently (confirmed by README: "GPT-4o-mini picks the clip" per utterance, "queries are cached... ~82 unique clips across a 90-segment episode"). No branch/PR/run addresses this.
Category: workflow
Analogy: Marketplace liquidity and two-sided matching -- treating the Pexels clip library as a supply pool and utterances as demand slots, and running a batch/global matching pass (e.g., greedy assignment with a repeat-penalty) instead of independent per-utterance lookups, the way marketplaces avoid over-allocating the same supply item to many demand slots.
Attraction (1-5): 2
Retention (1-5): 3
Effort: medium
Revenue (1-5|n/a): 1
Description: After the existing per-utterance GPT query step in `pod2vid.py`, add a second pass that reviews the full query list for the episode and re-assigns near-duplicate/repeated clip choices to alternate but still-relevant queries, capped by a max-repeat-per-clip parameter. This is a quality-of-output improvement (less visual repetition in longer episodes) rather than a new capability, so it scores lower on attraction than Candidates 1-2, but it's cheap to layer onto the existing cached-query architecture.

### Candidate 5: AI host voice cloning (replace stock TTS voices)
Duplicate: no
Dedup rationale: `tts_replace.py` only supports OpenAI's fixed stock voices (`onyx`, `nova`, etc., per README); no branch, PR, or prior run adds voice cloning or a third-party TTS provider.
Category: workflow
Analogy: none -- this tracks the External Context's TTS/voice trend (ElevenLabs, Cartesia, OpenAI realtime voices with cloning) directly rather than a cross-domain analogy.
Attraction (1-5): 3
Retention (1-5): 2
Effort: medium
Revenue (1-5|n/a): 2
Description: Add an optional voice-cloning path in `tts_replace.py` (e.g., ElevenLabs voice cloning API) so a creator can upload a short sample and get a consistent, recognizable host voice across all episodes instead of picking from six generic OpenAI voices. Useful for brand consistency but narrower in scope than Candidates 1-2 (affects only the optional TTS-replace path, not the core pipeline), so it ranks lowest of the workflow ideas on attraction+retention.

---IDEATE-STATUS---
selected: candidate-1
reason: Highest attraction+retention (9), directly closes the clip-scoring gap versus category leaders, and is confirmed non-duplicate against all branches/PRs/prior runs.


```
### 2026-07-28-e3d-pod2vid-3/candidates.md
```text
---
selected: candidate-1
reason: Highest attraction+retention (9, tied with candidate-2 but wins tiebreak on revenue), non-duplicate, and directly fixes the diff-size scope failure that blocked this same idea in the prior run.
---

# Candidates

## Dedup Context

## Current Findings

```text
---
head_sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be
---

# Findings

## Local State

Repo head sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be

Research topics: podcast-to-video generation pipeline

Analogy domains to consider: game progression and reward loops; social feed and notification mechanics; marketplace liquidity and two-sided matching; developer-tool CLI ergonomics; fintech trust and verification UX

## Git history
range: last 20 commits
```text
3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
564c87a Remove invalid wildcard permission rule from Claude Code settings
09f7a02 Merge remote-tracking branch 'origin/main'
c5193de Add optional local-Whisper transcription engine alongside AssemblyAI
9fb97b6 Add dramatic YouTube Short script for e3d.ai's token registry positioning
a6598fd Enable prompt suggestions in Claude Code settings
d2e1c8e Add Claude Code auto-permissions (allow all tools)
0f378bd Add split-screen layout, nova voice, and X OAuth2 auth script
11c9bdb Add multichain E3D Short: Bloomberg-style announcement across 4 chains
e14ffd9 Add regression tests for the manifest.kind validation bug
819f543 Add the hosted job runner (bin/pod2vid-job.py, pod2vid_worker.py)
baa06b5 Sync spec: rename pod2vid → cast
08eac3a Sync spec: fix runner phase detection false positives
7dbeb3b Sync spec: fix runner phase detector conflict
d793b47 Sync spec: fix runner instructions for sandbox write access
123bbb7 Sync spec: single-repo phases and runner instructions
579c609 Revise Pod2Vid hosted product spec with growth focus and v1/v1.1 split
55e3171 Add hosted Pod2Vid E3D product spec
3d963ca Add hand-scripted E3D Token YouTube Short generator
56b587d Add E3D Token sponsor segment to every signal Short
```

## Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH issues and PRs
### gh issue list
- none found
### gh pr list
- none found

## Repo docs
### README.md
```text
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

### 3. Generate a YouTube Short from an E3D Maps signal (automated)

```bash
python3 signal_short.py [--dry-run] [--force]
```

Pulls live signals from [maps.e3d.ai](https://maps.e3d.ai), picks the most significant one, generates a script, renders a Short, uploads to YouTube, and posts to all social platforms — automatically, daily.

**Filtering criteria** (any one qualifies):
- Confidence ≥ `CONF_THRESHOLD` (default: 78%)
- `risk_level == 'high'` AND confidence ≥ 55%
- `signal_strength == 'strong'`
- 3+ independent signals converging on the same destination (cluster alert)

**Flags:**
- `--dry-run` — generate the script and queries but skip render/upload
- `--force` — re-post even if that signal was already posted today

**Environment variables:**

| Variable | Notes |
|---|---|
| `MAPS_URL` | Default: `https://maps.e3d.ai` |
| `MAPS_INTERNAL_KEY` | Optional — endpoint is public |
| `CONF_THRESHOLD` | Float 0-1, default `0.78` |

State (which signals have been posted today) is written to `output/signal-short-state.json`.

**Schedule with PM2:**

```bash
# Start daily cron at 14:00 UTC
pm2 start ecosystem.config.js --env production

# View logs
pm2 logs signal-short
```

---

### 4. Generate a YouTube Short (custom script)

```bash
python3 make_short.py [output.mp4]
```

Produces a vertical 1080×1920 MP4 (≤60s) ready for YouTube Shorts, Instagram Reels, or TikTok:

- **Silent hook clip** — eye-catching opener (no narration, grabs attention in the first 2 seconds)
- **TTS voiceover** — OpenAI `tts-1-hd` narrates a built-in script about the tool
- **Semantic Pexels B-roll** — lifestyle, car, and tech footage matched to each line
- **Burned-in subtitles** — same PIL renderer as `pod2vid.py`, sized for mobile
- **CTA card** — closing frame with GitHub URL and accent branding

The script and B-roll queries are defined in the `SEGMENTS` list at the top of `make_short.py` — edit them to customise the script for your own content.

Environment variables:

| Variable | Default | Notes |
|---|---|---|
| `SHORT_VOICE` | `onyx` | OpenAI TTS voice for narration |

---

### 5. Generate a thumbnail

```bash
python3 make_thumbnail.py "Predictive GPS for Autonomous AI Agents" thumbnail.png /path/to/logo.png
```

Outputs a 1280×720 PNG with title, accent stripe, and optional logo overlay. Pure Pillow — no browser or design tool required.

---

## Hosted worker wrapper

Phase 3 adds `python3 bin/pod2vid-job.py <manifest.json>` for hosted-job execution. The wrapper:

- validates a worker-facing manifest defined in [docs/pod2vid-job.schema.json](/home/ubuntu/e3d-pod2vid/docs/pod2vid-job.schema.json)
- writes deterministic outputs under `POD2VID_STORAGE_DIR` (defaults to `/tmp/e3d-pod2vid`)
- supports dry-run renders, transcript presets, thumbnail/metadata/subtitle-style revisions, archive manifests, and archive rehydration
- emits structured JSON progress events on stdout for a higher-level daemon to consume

See [docs/worker-wrapper.md](/home/ubuntu/e3d-pod2vid/docs/worker-wrapper.md) for the manifest fields, supported presets, and required API keys by preset.

---

### 6. Upload to YouTube

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

### 7. Announce on social media

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

### 8. (Optional) LinkedIn setup

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

```

## TODO/FIXME matches
- none found

## External Context

## External Context

This repo sits in the "podcast/long-form → short-form video" repurposing space, alongside tools like Opus Clip, Descript, Riverside, Submagic, and Veed — most of which have converged on the same core loop this codebase implements: diarize → transcribe → select highlight/B-roll → burn captions → auto-post. A few state-of-the-art shifts worth noting relative to this repo's current approach:

- **B-roll sourcing is moving from stock-search to generative.** The repo's GPT-4o-mini-picks-a-Pexels-query approach was leading-edge in 2024; by 2026 competitors increasingly generate bespoke B-roll (Sora 2, Veo 3, Runway Gen-4) or use AI avatars/talking-head synthesis instead of stitching stock footage, which removes licensing/relevance ceilings that stock libraries impose.
- **Captioning has standardized on "karaoke-style" word-level highlight**, not just burned-in line subtitles — this is now table stakes for retention on Shorts/Reels/TikTok and is a natural next increment for the Pillow-based renderer here.
- **Diarization + ASR are consolidating**: AssemblyAI, Deepgram, and local Whisper-family models (already partially adopted here via the local-Whisper engine) are converging on near-parity accuracy, so the differentiator is shifting to downstream editorial intelligence (highlight selection, hook detection, pacing) rather than transcription quality.
- **Multi-platform auto-posting is now expected infrastructure**, not a differentiator — the interesting competitive surface has moved to *performance feedback loops* (using view/retention data to steer future clip selection or thumbnail/title generation), which this pipeline doesn't yet close the loop on.
- **Hosted/job-runner architectures** (this repo's `bin/pod2vid-job.py` direction) mirror the broader trend of these tools moving from CLI scripts to queued, multi-tenant SaaS backends with manifest-driven, resumable jobs — the schema/dry-run/archive-rehydration work already underway here tracks that trend correctly.

### Analogous Patterns

- **Game progression and reward loops → clip/segment selection tuning.** The mechanic of variable-ratio reward schedules (games surface a "big win" unpredictably to sustain engagement) could reframe how `signal_short.py`/`make_short.py` pick source material: instead of a static confidence/strength threshold, score candidate segments/signals against a "streak" or "novelty" heuristic that occasionally surfaces a surprising, lower-confidence signal to keep the output feed from feeling formulaic to repeat viewers.
- **Marketplace liquidity and two-sided matching → B-roll clip selection.** Marketplaces solve "match supply to demand under thin liquidity" by widening search radius or falling back to substitutable inventory when an exact match is scarce. The B-roll matcher here does a single GPT query → single Pexels search per utterance with no fallback; borrowing a matching-market's "widen the search, rank multiple candidates, pick by combined relevance+diversity score" approach would reduce repeated/generic clips across a long episode (the README notes ~82 unique clips over 90 segments — a liquidity problem in miniature).
- **Developer-tool CLI ergonomics → operator experience.** Modern CLI tools (e.g., `gh`, `stripe`, `vercel`) standardize on structured `--dry-run`, resumable state, and human + machine-readable (`--json`) output for every subcommand. The pipeline already has partial dry-run/state-caching (`signal-short-state.json`, diarization/query caches); formalizing this into a consistent flag/output contract across `pod2vid.py`, `make_short.py`, and `signal_short.py` would make the multi-script pipeline feel like one coherent tool rather than five separate ones.


```

## Git Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH PR List (state: all)
- none found

## Prior Runs (candidates.md / spec-final.md)
### 2026-07-27-e3d-pod2vid/candidates.md
```text
---
selected: candidate-1
reason: Highest attraction+retention (9), directly closes the clip-scoring gap versus category leaders, and is confirmed non-duplicate against all branches/PRs/prior runs.
---

# Candidates

## Dedup Context

## Current Findings

```text
---
head_sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be
---

# Findings

## Local State

Repo head sha: 3e7a9a5f36989e3534bbd5105be7cc2ca51789be

Research topics: podcast-to-video generation pipeline

Analogy domains to consider: game progression and reward loops; social feed and notification mechanics; marketplace liquidity and two-sided matching; developer-tool CLI ergonomics; fintech trust and verification UX

## Git history
range: last 20 commits
```text
3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
564c87a Remove invalid wildcard permission rule from Claude Code settings
09f7a02 Merge remote-tracking branch 'origin/main'
c5193de Add optional local-Whisper transcription engine alongside AssemblyAI
9fb97b6 Add dramatic YouTube Short script for e3d.ai's token registry positioning
a6598fd Enable prompt suggestions in Claude Code settings
d2e1c8e Add Claude Code auto-permissions (allow all tools)
0f378bd Add split-screen layout, nova voice, and X OAuth2 auth script
11c9bdb Add multichain E3D Short: Bloomberg-style announcement across 4 chains
e14ffd9 Add regression tests for the manifest.kind validation bug
819f543 Add the hosted job runner (bin/pod2vid-job.py, pod2vid_worker.py)
baa06b5 Sync spec: rename pod2vid → cast
08eac3a Sync spec: fix runner phase detection false positives
7dbeb3b Sync spec: fix runner phase detector conflict
d793b47 Sync spec: fix runner instructions for sandbox write access
123bbb7 Sync spec: single-repo phases and runner instructions
579c609 Revise Pod2Vid hosted product spec with growth focus and v1/v1.1 split
55e3171 Add hosted Pod2Vid E3D product spec
3d963ca Add hand-scripted E3D Token YouTube Short generator
56b587d Add E3D Token sponsor segment to every signal Short
```

## Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH issues and PRs
### gh issue list
- none found
### gh pr list
- none found

## Repo docs
### README.md
```text
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

### 3. Generate a YouTube Short from an E3D Maps signal (automated)

```bash
python3 signal_short.py [--dry-run] [--force]
```

Pulls live signals from [maps.e3d.ai](https://maps.e3d.ai), picks the most significant one, generates a script, renders a Short, uploads to YouTube, and posts to all social platforms — automatically, daily.

**Filtering criteria** (any one qualifies):
- Confidence ≥ `CONF_THRESHOLD` (default: 78%)
- `risk_level == 'high'` AND confidence ≥ 55%
- `signal_strength == 'strong'`
- 3+ independent signals converging on the same destination (cluster alert)

**Flags:**
- `--dry-run` — generate the script and queries but skip render/upload
- `--force` — re-post even if that signal was already posted today

**Environment variables:**

| Variable | Notes |
|---|---|
| `MAPS_URL` | Default: `https://maps.e3d.ai` |
| `MAPS_INTERNAL_KEY` | Optional — endpoint is public |
| `CONF_THRESHOLD` | Float 0-1, default `0.78` |

State (which signals have been posted today) is written to `output/signal-short-state.json`.

**Schedule with PM2:**

```bash
# Start daily cron at 14:00 UTC
pm2 start ecosystem.config.js --env production

# View logs
pm2 logs signal-short
```

---

### 4. Generate a YouTube Short (custom script)

```bash
python3 make_short.py [output.mp4]
```

Produces a vertical 1080×1920 MP4 (≤60s) ready for YouTube Shorts, Instagram Reels, or TikTok:

- **Silent hook clip** — eye-catching opener (no narration, grabs attention in the first 2 seconds)
- **TTS voiceover** — OpenAI `tts-1-hd` narrates a built-in script about the tool
- **Semantic Pexels B-roll** — lifestyle, car, and tech footage matched to each line
- **Burned-in subtitles** — same PIL renderer as `pod2vid.py`, sized for mobile
- **CTA card** — closing frame with GitHub URL and accent branding

The script and B-roll queries are defined in the `SEGMENTS` list at the top of `make_short.py` — edit them to customise the script for your own content.

Environment variables:

| Variable | Default | Notes |
|---|---|---|
| `SHORT_VOICE` | `onyx` | OpenAI TTS voice for narration |

---

### 5. Generate a thumbnail

```bash
python3 make_thumbnail.py "Predictive GPS for Autonomous AI Agents" thumbnail.png /path/to/logo.png
```

Outputs a 1280×720 PNG with title, accent stripe, and optional logo overlay. Pure Pillow — no browser or design tool required.

---

## Hosted worker wrapper

Phase 3 adds `python3 bin/pod2vid-job.py <manifest.json>` for hosted-job execution. The wrapper:

- validates a worker-facing manifest defined in [docs/pod2vid-job.schema.json](/home/ubuntu/e3d-pod2vid/docs/pod2vid-job.schema.json)
- writes deterministic outputs under `POD2VID_STORAGE_DIR` (defaults to `/tmp/e3d-pod2vid`)
- supports dry-run renders, transcript presets, thumbnail/metadata/subtitle-style revisions, archive manifests, and archive rehydration
- emits structured JSON progress events on stdout for a higher-level daemon to consume

See [docs/worker-wrapper.md](/home/ubuntu/e3d-pod2vid/docs/worker-wrapper.md) for the manifest fields, supported presets, and required API keys by preset.

---

### 6. Upload to YouTube

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

### 7. Announce on social media

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

### 8. (Optional) LinkedIn setup

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

```

## TODO/FIXME matches
- none found

## External Context

I don't have web search access in this session, so I'll draft the External Context section from existing knowledge of the space rather than live sources.

## External Context

The repo sits in the AI-assisted "podcast/audio → distributable video" space, which has consolidated quickly over the last two years:

- **Managed pipelines** (Opus Clip, Descript, Riverside, Submagic, Vizard, Wisecut) now do diarization + repurposing end-to-end: cut long-form audio/video into vertical clips, auto-caption, and score/rank moments by predicted virality — mirroring this repo's diarize → segment → caption → publish shape, but with a "clip scoring" step this repo lacks.
- **B-roll sourcing** is shifting from stock-footage matching (what this repo does via Pexels + GPT query generation) toward generative B-roll (Runway, Pika, Luma, Sora-class text-to-video) and AI avatar hosts (HeyGen, Synthesia) that render a presenter directly rather than illustrating around narration.
- **TTS/voice** has moved to expressive, low-latency streaming models (ElevenLabs, OpenAI's newer realtime voices, Cartesia) with voice cloning as a common feature — relevant since this repo already swaps NotebookLM voices via OpenAI TTS and could clone a consistent host voice instead of using stock voices.
- **Multi-platform distribution** is standardizing around scheduling/repurposing suites (Buffer, Publer, Repurpose.io) that treat one asset → many platform-native posts as a first-class workflow, which is the same job `announce.js` does per-platform in this repo, just without scheduling/queueing.
- **Auto-editing quality signals** (silence/filler-word removal, pacing-aware cuts, retention-optimized clip selection) are becoming standard in this category and represent a natural gap area versus this repo's current linear utterance-by-utterance render.

### Analogous Patterns

- **Social feed and notification mechanics** — the "surface the most engagement-worthy moment, notify, and re-serve" loop that ranking feeds use (e.g., pushing the single best notification instead of all events) maps onto `signal_short.py`'s "pick the most significant signal" step: the pipeline could score every diarized utterance/segment for "hook strength" the way a feed ranks candidate posts, then generate the Short from the highest-scoring segment instead of a hand-picked or first-qualifying one.
- **Marketplace liquidity and two-sided matching** — marketplaces solve "many supply items, many demand slots" with a matching/auction layer rather than static rules; the current GPT-per-utterance → single Pexels query is a one-sided lookup. Treating B-roll clips as a supply pool and utterances as demand, then running a batch matching pass (e.g., maximize semantic coverage while minimizing repeat clips across an episode) would reduce duplicate footage and improve variety versus the current per-utterance greedy match.
- **Developer-tool CLI ergonomics** — modern CLIs (gh, stripe, vercel) lean on structured JSON output, `--dry-run`, idempotent state files, and clear subcommands, which this repo has already partially adopted (`--dry-run`, `--force`, JSON progress events in `bin/pod2vid-job.py`). Extending that ergonomics pattern — e.g., a unified `pod2vid <subcommand>` entrypoint with consistent flags across `pod2vid.py`, `signal_short.py`, and `make_short.py` instead of separate scripts — would bring the whole toolchain in line with that CLI-composability convention.


```

## Git Branches
```text
* main                3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 3e7a9a5 Support per-platform X message override and fix stale LinkedIn API version
```

## GH PR List (state: all)
- none found

## Prior Runs (candidates.md / spec-final.md)
- none found

## Proposed Candidates

### Candidate 1: Auto-generate multiple ranked highlight Shorts from a single episode
Duplicate: no
Dedup rationale: Only `main` branch exists (no feature branches), no open PRs, and no prior candidates/specs on record. Grepped the repo for "highlight", "clip.?scor", "viral" — no existing scoring or multi-clip logic; `make_short.py` only renders one hand-authored script and `signal_short.py` picks a single signal via static threshold rules, not a scored ranking of all candidates.
Category: workflow
Analogy: Social feed and notification mechanics -- feeds rank all candidate posts and surface only the top one(s) instead of showing everything; applying the same "score every candidate, serve only the best" logic to a full diarized episode (score each utterance/segment for hook strength, novelty, sentiment spike, etc.) lets the pipeline auto-produce 3-5 ranked Shorts per long-form episode instead of one full video, directly closing the "clip scoring" gap noted in External Context versus Opus Clip/Vizard/Submagic.
Attraction (1-5): 5
Retention (1-5): 4
Effort: medium
Revenue (1-5|n/a): 3
Description: Add a scoring pass over `pod2vid.py`'s diarization output (reuse GPT-4o-mini, similar to the existing per-utterance Pexels-query call) that rates each utterance/segment window for "clip-worthiness," then auto-render the top N windows as vertical Shorts using the existing `make_short.py`/subtitle/B-roll pipeline. This is the single biggest feature gap versus category leaders and turns every long episode into several pieces of distributable content instead of one, which is the core lever for both new-user attraction (a much more compelling free/trial demo) and retention (users get more usable output per episode).

### Candidate 2: Post-performance feedback loop (view/engagement analytics)
Duplicate: no
Dedup rationale: No branches, PRs, or prior runs reference analytics/metrics. Grep for "engagement|analytics|view_count" across all `.py`/`.js` files returned no matches — the pipeline currently has no read-back from YouTube/social APIs after publishing.
Category: data
Analogy: Fintech trust and verification UX -- fintech apps close the loop by showing users the real-world outcome of an action (balance updated, transaction cleared) rather than just confirming submission; applying that here means showing creators what actually happened to their video/post (views, watch-time, engagement) instead of just "uploaded successfully," turning a one-way publish tool into a feedback system.
Attraction (1-5): 3
Retention (1-5): 5
Effort: medium
Revenue (1-5|n/a): 3
Description: After `yt_upload.js`/`announce.js` publish, poll YouTube Data API (and platform APIs where available) for view count, watch-time, and engagement at 24h/7d intervals, store results alongside the existing `output/*.json` state files, and surface a simple report (CLI summary or JSON digest) showing which segments/B-roll queries/voices correlated with better performance. This is what brings users back to the tool repeatedly (retention) and, longer term, feeds back into Candidate 1's clip-scoring model to make future picks smarter — the kind of compounding data loop that's currently entirely absent.

### Candidate 3: Scheduled/queued multi-platform publishing
Duplicate: no
Dedup rationale: Checked `announce.js` and `ecosystem.config.js` (the only cron-adjacent file) — `ecosystem.config.js` only schedules the daily `signal_short.py` job itself, not a general post queue; `announce.js` posts synchronously and immediately to all platforms with no queueing/delay logic. No branch or PR touches this.
Category: workflow
Analogy: Marketplace liquidity and two-sided matching -- not directly applicable here; better framed via the "developer-tool CLI ergonomics" pattern extended to scheduling suites (Buffer/Publer/Repurpose.io) explicitly called out in External Context: one asset -> many platform-native posts, staged over time instead of blasted at once.
Attraction (1-5): 3
Retention (1-5): 3
Effort: low
Revenue (1-5|n/a): 2
Description: Add an optional `--schedule` flag / queue file to `announce.js` so a rendered video's cross-platform posts can be staggered (e.g., YouTube now, X in 1h, LinkedIn next morning) rather than firing all at once, with a small persistent queue (JSON, consistent with the existing `output/signal-short-state.json` pattern) and a lightweight `node announce.js --process-queue` cron entry. Low effort since it reuses all existing per-platform posting code; mainly helps creators who want to avoid dumping identical content across every channel simultaneously, a common cause of audience fatigue.

### Candidate 4: Episode-wide B-roll matching to reduce duplicate clips
Duplicate: no
Dedup rationale: Grepped `pod2vid.py` for "match"/"dedupe"/"duplicate" — no batch matching or dedup logic exists; queries are generated and cached per-utterance independently (confirmed by README: "GPT-4o-mini picks the clip" per utterance, "queries are cached... ~82 unique clips across a 90-segment episode"). No branch/PR/run addresses this.
Category: workflow
Analogy: Marketplace liquidity and two-sided matching -- treating the Pexels clip library as a supply pool and utterances as demand slots, and running a batch/global matching pass (e.g., greedy assignment with a repeat-penalty) instead of independent per-utterance lookups, the way marketplaces avoid over-allocating the same supply item to many demand slots.
Attraction (1-5): 2
Retention (1-5): 3
Effort: medium
Revenue (1-5|n/a): 1
Description: After the existing per-utterance GPT query step in `pod2vid.py`, add a second pass that reviews the full query list for the episode and re-assigns near-duplicate/repeated clip choices to alternate but still-relevant queries, capped by a max-repeat-per-clip parameter. This is a quality-of-output improvement (less visual repetition in longer episodes) rather than a new capability, so it scores lower on attraction than Candidates 1-2, but it's cheap to layer onto the existing cached-query architecture.

### Candidate 5: AI host voice cloning (replace stock TTS voices)
Duplicate: no
Dedup rationale: `tts_replace.py` only supports OpenAI's fixed stock voices (`onyx`, `nova`, etc., per README); no branch, PR, or prior run adds voice cloning or a third-party TTS provider.
Category: workflow
Analogy: none -- this tracks the External Context's TTS/voice trend (ElevenLabs, Cartesia, OpenAI realtime voices with cloning) directly rather than a cross-domain analogy.
Attraction (1-5): 3
Retention (1-5): 2
Effort: medium
Revenue (1-5|n/a): 2
Description: Add an optional voice-cloning path in `tts_replace.py` (e.g., ElevenLabs voice cloning API) so a creator can upload a short sample and get a consistent, recognizable host voice across all episodes instead of picking from six generic OpenAI voices. Useful for brand consistency but narrower in scope than Candidates 1-2 (affects only the optional TTS-replace path, not the core pipeline), so it ranks lowest of the workflow ideas on attraction+retention.

---IDEATE-STATUS---
selected: candidate-1
reason: Highest attraction+retention (9), directly closes the clip-scoring gap versus category leaders, and is confirmed non-duplicate against all branches/PRs/prior runs.


```

## Proposed Candidates

### Candidate 1: Ranked highlight-clip scoring & selection (scoped MVP)
Duplicate: no
Dedup rationale: No feature branch or PR exists for this (only `main`, no open PRs). This exact idea was the **selected** candidate in the 2026-07-27 run's `candidates.md`, but its drafted spec (`draft-rejected.md`) was rejected by the draft stage for exceeding the 600-line diff budget (~1800 estimated lines across scoring, selection, rendering, manifest, and tests in one shot). Nothing was ever merged — `highlight_shorts.py` does not exist in the repo — so this is not duplicate work, just a scope failure that needs a narrower first phase.
Category: workflow
Analogy: Social feed and notification mechanics -- feeds rank all candidate posts and surface only the top one(s) instead of showing everything; scoring every diarized window for hook strength and serving only the best N mirrors that "rank, don't dump" pattern, closing the "clip scoring" gap noted vs. Opus Clip/Vizard/Submagic in External Context.
Attraction (1-5): 5
Retention (1-5): 4
Effort: medium
Revenue (1-5|n/a): 3
Description: Re-attempt this idea but explicitly scoped to fit the diff budget that killed it last time: ship only candidate-window scoring (reuse the existing GPT-4o-mini JSON-request pattern from `pod2vid.py`), deterministic non-overlapping selection, and a JSON manifest of the top N ranked highlights with timestamps/scores — as a single new script + one test file, deferring actual Short rendering to a follow-up phase that simply calls the existing `make_short.py`/render path per selected window rather than reimplementing it. Narrowing scope this way keeps the highest-value idea (turns one episode into several distributable clips) inside the ~600-line/3-file constraint that blocked it before.

### Candidate 2: Karaoke-style word-level caption highlighting
Duplicate: no
Dedup rationale: Grepped `pod2vid.py` and `make_short.py`'s Pillow subtitle renderer — both burn in line-level captions only; no word-level timing/highlight logic exists. Not mentioned in any prior candidate (2026-07-27 run's 5 candidates covered highlight-scoring, analytics, scheduling, B-roll dedup, and voice cloning — none touch caption style). No branch/PR addresses it.
Category: workflow
Analogy: none directly — this tracks External Context's explicit statement that "captioning has standardized on karaoke-style word-level highlight... table stakes for retention on Shorts/Reels/TikTok" rather than a cross-domain transfer.
Attraction (1-5): 4
Retention (1-5): 5
Effort: low
Revenue (1-5|n/a): 2
Description: Extend the existing Pillow-based subtitle renderer (shared by `pod2vid.py` and `make_short.py`) to highlight/bold the currently-spoken word within each caption line using AssemblyAI's existing word-level timestamps (already returned in the diarization payload, just unused downstream). This is a pure quality-of-output change to code that already exists, is low effort, and closes a now-standard retention lever competitors have already adopted — directly serving the "attracting and retaining users" goal without needing new infrastructure.

### Candidate 3: Post-performance feedback loop (view/engagement analytics)
Duplicate: no
Dedup rationale: Restating the 2026-07-27 run's candidate 2 — grep for `engagement|analytics|view_count` still returns no matches; no branch/PR/spec exists for this. Confirmed still unimplemented and still non-duplicate.
Category: data
Analogy: Fintech trust and verification UX -- fintech apps close the loop by showing the real outcome of an action (balance updated) instead of just confirming submission; showing creators what actually happened to a published video (views, watch-time) instead of just "uploaded successfully" turns a one-way publish tool into a feedback system.
Attraction (1-5): 3
Retention (1-5): 5
Effort: medium
Revenue (1-5|n/a): 3
Description: After `yt_upload.js`/`announce.js` publish, poll YouTube Data API at 24h/7d intervals, store results next to existing `output/*.json` state, and surface a simple digest of which segments/queries/voices performed best. Strongest pure-retention play (brings users back to check results) and would eventually feed Candidate 1's scoring model, but ranks below Candidates 1-2 on combined attraction+retention.

### Candidate 4: Scheduled/queued multi-platform publishing
Duplicate: no
Dedup rationale: Restating the 2026-07-27 run's candidate 3 — `ecosystem.config.js` still only schedules the daily `signal_short.py` job, and `announce.js` still posts synchronously to all platforms with no queue. Still unimplemented, still non-duplicate.
Category: workflow
Analogy: Developer-tool CLI ergonomics extended to scheduling suites (Buffer/Publer/Repurpose.io per External Context): one asset → many platform-native posts, staged over time instead of blasted at once.
Attraction (1-5): 3
Retention (1-5): 3
Effort: low
Revenue (1-5|n/a): 2
Description: Add an optional `--schedule`/queue file to `announce.js` so posts stagger across platforms instead of firing simultaneously, reusing all existing per-platform posting code. Cheap and useful but lower attraction/retention pull than the content-quality ideas above.

### Candidate 5: Episode-wide B-roll matching to reduce duplicate clips
Duplicate: no
Dedup rationale: Restating the 2026-07-27 run's candidate 4 — no batch-matching/dedup logic exists in `pod2vid.py`; queries are still generated independently per utterance. Still unimplemented, still non-duplicate.
Category: workflow
Analogy: Marketplace liquidity and two-sided matching -- treating the Pexels clip library as supply and utterances as demand, running a batch matching pass with a repeat-penalty instead of independent per-utterance lookups.
Attraction (1-5): 2
Retention (1-5): 3
Effort: medium
Revenue (1-5|n/a): 1
Description: Add a second pass after per-utterance query generation that re-assigns near-duplicate clip choices across the episode, capped by a max-repeat-per-clip parameter. A real quality improvement but the narrowest-scope, lowest-pull idea of the set.

---IDEATE-STATUS---
selected: candidate-1
reason: Highest attraction+retention (9, tied with candidate-2 but wins tiebreak on revenue), non-duplicate, and directly fixes the diff-size scope failure that blocked this same idea in the prior run.


```

## Proposed Candidates

### Candidate 1: Unified `pod2vid` CLI entrypoint
Duplicate: no
Dedup rationale: Only `main` branch exists, no PRs. Checked all five candidates in 2026-07-27 run and all five in 2026-07-28 run — neither run ever proposed a unified CLI as a standalone candidate. The 2026-07-28 analogy section mentions it as an example under "developer-tool CLI ergonomics" but explicitly did not convert it into a candidate. No match in any branch, PR, or prior candidate list.
Category: workflow
Analogy: Developer-tool CLI ergonomics -- `gh`, `stripe`, `vercel` all expose one named binary with subcommands (`gh pr create`, `stripe listen`) plus consistent `--dry-run`/`--json` flags; applying that here means wrapping `pod2vid.py`, `signal_short.py`, `make_short.py`, and `announce.js` behind a single `pod2vid run|short|signal|announce` entrypoint with shared `--dry-run`, `--output-dir`, and `--json` flags instead of five separate scripts with inconsistent interfaces.
Attraction (1-5): 4
Retention (1-5): 4
Effort: medium
Revenue (1-5|n/a): 2
Description: Add a `pod2vid` dispatcher script (Python entry-point or thin shell wrapper) that routes `pod2vid run episode.m4a --publish`, `pod2vid signal --dry-run`, `pod2vid short`, and `pod2vid announce VIDEO_URL` to the existing scripts with unified flag handling. No core logic changes; this is pure ergonomics. Time-to-first-video is the single biggest conversion lever for new users — the current six-step manual sequence (diarize → TTS → render → upload → thumbnail → announce) is the primary drop-off point. Retention improves because recurring users stop keeping mental notes about which script does which step.

---

### Candidate 2: Auto-generate YouTube title, description, and tags from transcript
Duplicate: no
Dedup rationale: Checked both prior runs (2026-07-27: 5 candidates; 2026-07-28: 5 candidates) — none of the ten total candidates proposed auto-generating metadata. Grep for `title|description|tags` in existing `.py`/`.js` files confirms: `yt_upload.js` requires a title as a positional CLI arg and `yt_update.js` reads `YT_DESCRIPTION` from env — both require manual authoring. No branch or PR addresses this.
Category: workflow
Analogy: Developer-tool CLI ergonomics -- `vercel` and `netlify` infer project name, build command, and framework from repo context rather than forcing users to fill in config; applying that pattern here means inferring episode metadata from the already-produced diarization JSON instead of requiring manual env-variable authoring.
Attraction (1-5): 4
Retention (1-5): 3
Effort: low
Revenue (1-5|n/a): 2
Description: After diarization, pass the transcript to GPT-4o-mini (reusing the same call pattern as the Pexels-query step) to generate a YouTube title, 150-word description with timestamps, and 5-10 SEO tags. Write results to `output/episode-metadata.json` and plumb them through `yt_upload.js`/`yt_update.js` as defaults that the user can override via env. Low effort (one new GPT prompt, one JSON output, two JS call-site changes), removes the most common manual step that blocks new users from publishing their first video.

---

### Candidate 3: Filler-word and silence removal pass
Duplicate: no
Dedup rationale: Checked 2026-07-27 (5 candidates) and 2026-07-28 (5 candidates) — neither run proposed silence/filler removal. External Context in 2026-07-28 explicitly names "silence/filler-word removal, pacing-aware cuts" as "becoming standard in this category" but no candidate was ever drafted from it. Grepped `pod2vid.py` for `filler|silence|um|uh|pause` — no such logic exists; all utterances render verbatim as returned by AssemblyAI.
Category: workflow
Analogy: none -- tracks the External Context's explicit gap statement ("auto-editing quality signals... are becoming standard") directly rather than a cross-domain transfer.
Attraction (1-5): 3
Retention (1-5): 3
Effort: medium
Revenue (1-5|n/a): 2
Description: Add a post-diarization normalization pass that uses AssemblyAI's word-level confidence scores and timestamps (already in the diarization payload) to detect and drop low-confidence filler words (`um`, `uh`, `like`, `you know`) and silence gaps above a configurable threshold, then re-stitches segment boundaries before the render step. Implement as an optional `--clean` flag in `pod2vid.py` so existing behavior is unaffected. Improves output quality for the core long-form pipeline, making demos more compelling to new users and keeping returning users producing at a higher quality bar without manual editing.

---

### Candidate 4: Signal freshness/decay for signal_short.py
Duplicate: no
Dedup rationale: The 2026-07-28 findings' Analogy section describes this pattern under "Social feed & notification mechanics → signal threshold as publish trigger" but it was never converted into a candidate in either run. Grepped `signal_short.py` for `decay|staleness|age|freshness` — no such logic; the current state file only tracks `posted_today` as a boolean, with no freshness dimension.
Category: data
Analogy: Social feed and notification mechanics -- feed-ranking systems apply time-decay to a post's score so a signal that was highly ranked yesterday but received no new confirmation loses rank today; borrowing that decay mechanic for `signal_short.py` means a signal whose confidence score hasn't been updated by new data within N hours gets a staleness penalty, preventing the same persistent alert from re-triggering daily posts without new evidence.
Attraction (1-5): 2
Retention (1-5): 3
Effort: low
Revenue (1-5|n/a): 1
Description: Extend `output/signal-short-state.json` with a `last_seen_confidence` and `first_seen_at` timestamp per signal. Before posting, compute an effective confidence as `raw_confidence * decay_factor(hours_since_first_seen)` (e.g., exponential decay with 48h half-life). If effective confidence falls below threshold, skip even if raw confidence still qualifies. This prevents a single long-lived signal from generating daily posts without fresh confirmation — the same content quality problem that stale-push notifications cause in social apps. Low effort: confined to `signal_short.py` state-management logic.

---

### Candidate 5: Ranked highlight-clip scoring & selection
Duplicate: yes
Dedup rationale: This was the **selected** candidate in the 2026-07-27 run (`candidates.md`: "selected: candidate-1") and again the **selected** candidate in the 2026-07-28 run (`candidates.md`: "selected: candidate-1"). Both runs confirm no implementation exists (`highlight_shorts.py` does not exist, head SHA unchanged at `3e7a9a5`), but the idea appears explicitly in both prior-run candidate lists and was rejected at the spec/draft stage for diff-size overrun — not a branch/PR duplication, but a direct prior-run candidate duplicate. Not re-ranking.

---IDEATE-STATUS---
selected: candidate-1
reason: Highest non-duplicate attraction+retention (8), closes the single biggest new-user conversion friction point, and does not duplicate any prior run candidate or branch.


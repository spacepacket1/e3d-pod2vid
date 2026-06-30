# Feature Spec: Hosted Cast on E3D

**Project:** e3d-pod2vid  
**Feature:** Hosted `cast.e3d.ai` product, E3D-paid API endpoints, wallet UI, and agent automation  
**Target repos:** `/home/ubuntu/e3d-pod2vid`, `/home/ubuntu/e3d-pod2vid-service`, `/home/ubuntu/spacepacket/server`, `/home/ubuntu/e3d-agent`  
**Status:** Draft for discussion  
**Priority:** High  
**Implementation mode:** Phased, suitable for codex-spec-runner  

---

## Codex-Spec-Runner Instructions

Each phase in this spec targets exactly one repo. **Launch `codex-spec-runner` from the repo listed under `Repo:` for that phase.** Sandbox write access is determined at launch time — `cd` inside the session does not grant additional write access.

Launch directory by repo:

| Repo | Launch from |
|---|---|
| `/home/ubuntu/spacepacket/server` | `cd /home/ubuntu/spacepacket/server` |
| `/home/ubuntu/e3d-pod2vid` | `cd /home/ubuntu/e3d-pod2vid` |
| `/home/ubuntu/e3d-pod2vid-service` | `cd /home/ubuntu/e3d-pod2vid-service` |
| `/home/ubuntu/e3d-agent` | `cd /home/ubuntu/e3d-agent` |

Always pass the spec as an absolute path:

```bash
cd <repo listed in the target phase>
codex-spec-runner /home/ubuntu/e3d-pod2vid-service/docs/pod2vid-hosted-e3d-spec.md <number>
```

Each phase may assume all preceding phases are complete and committed. If the target repo does not exist, create it before launching.

---

## 1. Product Vision

### 1.1 The Hook

> **Paste audio or a transcript. Get a publishable video package. Pay per job with E3D.**

Cast is an agent-native, wallet-paid media rendering product. No subscription is required for render jobs. A wallet, some E3D, and an HTTP call should be enough to quote, pay for, render, and retrieve a video package.

Human creators use the web workspace. AI agents call the API directly. Both pay the same way: E3D Token.

### 1.2 Target Users

**Primary — AI developers and agent builders**

The defensible wedge: wallet-native, pay-per-job media rendering for autonomous agents and crypto-native workflows. An agent can hold E3D, discover capabilities from a single endpoint, quote a job, pay, submit, poll or receive a webhook, and retrieve a finished video package without a browser or subscription account.

Target behaviors:
- Autonomous content pipelines that convert research, signals, or transcripts into video
- Agent frameworks that need media output as a first-class capability
- Developers building creator tools who need a hosted render backend they can pay for per-job

**Secondary — Podcast creators and content teams**

People who have audio or transcripts and want YouTube-ready video or short-form content without hiring a video editor. They use the web workspace. They see results before they pay. They share what they make.

### 1.3 Why E3D Token

E3D Token is the product's payment and incentive mechanism:

- **E3D holders get a 20% discount** on all paid job tiers when the wallet qualifies.
- **Every paid job records a 5% burn allocation** in E3D accounting.
- **Agents that accumulate E3D can run more jobs.** Token acquisition is a natural part of building on E3D infrastructure.

The utility loop: Cast attracts users and agents -> users acquire E3D to pay for jobs -> usage records spend and burn allocations -> E3D becomes a visible unit of account for media work across the E3D ecosystem.

### 1.4 Why Cast, Not Descript, Riverside, or OpusClip

Existing services such as Descript, Riverside, Podcastle, and OpusClip are strong creator tools. Some already expose API, MCP, automation, or integration surfaces. Cast should not claim they are human-only or that agent video APIs do not exist.

Cast's narrower position:

- **Wallet-paid and pay-per-job**: no subscription required for render jobs.
- **Agent-native by design**: capabilities, pricing, limits, schemas, and examples are machine-readable before first spend.
- **Crypto-native**: wallet connects, E3D pays, product credits settle through E3D Product Payments.
- **Open artifact model**: every job produces a manifest with inputs, options, timing, checksums, retention, and artifact metadata.
- **Composable infrastructure**: developers can treat video rendering as a deterministic paid capability inside agent workflows.

Cast does not need to beat full creative suites on editing depth in v1. It must beat them on agent onboarding, payment simplicity for wallet-native users, API clarity, and artifact transparency.

### 1.5 Competitive Launch Bar

Cast must clear a concrete product-quality bar before public launch. Architecture alone is not enough.

Minimum human-facing bar:

- at least 3 public sample outputs: transcript short, audio short, and YouTube-style video;
- output quality good enough to share publicly without explaining that it is a demo;
- support 9:16, 16:9, and 1:1 exports;
- at least 6 caption/style templates:
  - clean podcast;
  - bold mobile;
  - finance signal;
  - developer demo;
  - news brief;
  - minimal subtitles;
- at least 4 visual style presets for B-roll selection:
  - editorial;
  - tech;
  - finance;
  - cinematic;
- generated metadata package: title, description, tags, chapters where applicable, and social copy;
- basic brand kit: logo upload, primary color, end card toggle, and watermark rules by tier;
- a preview step showing sample frame/caption styling before paid submission;
- revision support for common low-cost changes after render;
- optional IPFS archive for completed artifact packages;
- optional NFT mint for users who explicitly want an on-chain provenance/collectible record.

Minimum agent-facing bar:

- hosted OpenAPI document;
- `GET /api/cast/capabilities` with tiers, presets, input schemas, artifact schemas, limits, pricing metadata, and example requests;
- `GET /llms.txt` with concise usage guidance and endpoint links;
- `GET /.well-known/agent-capabilities.json` with machine-readable product summary, auth modes, payment flow, and OpenAPI URL;
- cURL examples for quote, submit, webhook, poll, artifact list, artifact download, and revision;
- `e3d-agent cast render` example that works end to end before launch;
- webhook support for job completion/failure so agents do not have to rely only on polling;
- artifact checksums, byte sizes, content types, and expiration timestamps;
- optional archive/mint commands with explicit delegated-wallet safeguards.

### 1.6 Revision and Iteration Promise

Users should not have to re-upload and repay for a full job to fix small creative choices.

V1 should support revision jobs for:

- regenerate thumbnail;
- regenerate platform metadata/social copy;
- change subtitle style;
- toggle or regenerate the end card;
- regenerate B-roll choices for a short;
- regenerate transcript narration voice when the source is transcript text.

Revision jobs may cost fewer credits than full renders and should preserve a parent-child relationship in the job manifest.

### 1.7 IPFS Archive and NFT Provenance

Cast should support E3D/IPFS artifact archiving, but IPFS is an additional export/archive layer, not a replacement for the render working store.

Storage model:

```text
Local storage = working files, previews, publishing source, short-term retention
IPFS archive = optional durable/content-addressed artifact package
NFT mint = optional on-chain provenance record pointing to IPFS metadata
```

All jobs write local artifacts first under `CAST_STORAGE_DIR`. If the user opts into IPFS archive, the completed artifact package is pinned to E3D-managed IPFS storage and the job manifest records both local artifact IDs and IPFS CIDs/gateway URLs. Local files remain available for preview, revision, and publishing until the tier retention window expires, then may be deleted while IPFS references remain.

NFT minting must be separate from IPFS archiving:

- IPFS archive stores the media package and returns durable references.
- NFT mint creates an on-chain record whose token metadata points to the IPFS archive.
- Archiving to IPFS must not imply public social publishing.
- Minting an NFT must require explicit wallet confirmation or delegated-wallet opt-in.
- Private uploads/transcripts must not be archived or minted without clear user consent.

This gives users and agents portable artifact URLs while still keeping the operational render pipeline simple.

### 1.8 The Viral Loop

Every Cast output carries distribution back to the product:

- **Free-tier outputs** include a visible `cast.e3d.ai` end card and watermark. Creators share their free renders and they become ads.
- **Paid outputs** carry an optional "Made with Cast" end card (on by default, opt-out in options). Users who leave it on get a small credit rebate per published video — rewarding sharing.
- **Social publishing** (YouTube, Discord, Telegram, X, LinkedIn) is a first-class paid add-on, not an afterthought. Every published video is an impression for Cast and for E3D.
- **Agent examples** in the UI are copyable one-liners. Developers who copy and run them become users. Good agent examples spread through readmes and blog posts.

### 1.9 The "Get E3D" Path

The product must never leave a user stuck. When wallet balance or credits are insufficient, the UI shows:

1. Exact E3D/wE3D amount needed
2. Supported chains and treasury addresses (from the quote response)
3. A direct link to **e3d.ai/token** — the canonical E3D acquisition page
4. Wallet-connect flow to bridge or swap if the user already holds ETH/USDC

This path is resolved before Phase 3 begins, not after. It is part of Phase 2 acceptance.

### 1.10 The One Metric

**E3D Token volume consumed by Cast jobs per week.** Everything — tier design, pricing, free trial, agent examples, social publishing — serves this number. Render count and registered wallets are supporting indicators.

---

## 2. Goal

Create a hosted Cast product at:

```text
https://cast.e3d.ai
```

The service lets users and agents turn podcast audio or transcripts into publishable video outputs using the existing `e3d-pod2vid` pipeline. Access is paid with E3D through the existing E3D Product Payments system in `/home/ubuntu/spacepacket/server`.

The final system must support both:

- a browser UI where a user connects a wallet, buys or uses Cast credits, submits jobs, and downloads outputs;
- a fully automated agent/script path where an agent can buy credits, submit work, poll jobs, retrieve artifacts, and optionally publish through existing Cast social/upload scripts.

The hosted product is the primary example of E3D Token utility for media work. Its growth directly drives token volume.

### 2.1 Product Promise

Cast should feel like a finished media workspace, not a thin wrapper around scripts.

Human promise:

```text
Upload audio or write a transcript, choose a format, and get a publishable video package.
```

Agent promise:

```text
A wallet-native paid media-rendering API with predictable pricing, explicit limits, durable jobs,
and machine-readable artifacts. Discover capabilities, quote, pay, render, and retrieve — no browser required.
```

The default output package should be clear before a user pays:

- final MP4;
- captions/SRT when applicable;
- thumbnail when requested and included by tier;
- render manifest with inputs, options, timing, and artifact metadata;
- optional platform metadata such as title, description, tags, and social copy.

The first-run experience should include:

- a built-in sample audio/transcript job that can be quoted and rendered without uploading private media;
- a limited free tier so new users can see a real result before buying credits;
- visible expected render time and artifact size before submission;
- a plain explanation of what E3D credits pay for and why holding E3D is cheaper;
- copyable API and `e3d-agent` examples generated from the current job options.

### 2.2 v1 Scope

This table is the authoritative boundary between what Phase 1–6 implement and what Phase 7 defers. The full product spec (sections 1–11) describes both v1 and v1.1 together as the intended product. Only the items marked **v1.1** below are deferred; everything else is in scope for the current implementation run.

| Feature | v1 | v1.1 |
|---|:---:|:---:|
| Payment/credits with holder discount and burn tracking | ✓ | |
| Core job API: quote, submit, status, artifacts, cancel | ✓ | |
| Webhooks: submit with URL, delivery, retry, fallback polling | ✓ | |
| OpenAPI + `llms.txt` + `.well-known/agent-capabilities.json` | ✓ | |
| IPFS archive: `archive-ipfs` endpoint + Pinata integration | ✓ | |
| `mint-nft` endpoint scaffolded (returns 501 until v1.1) | ✓ | |
| Revisions: thumbnail, metadata/social copy, subtitle style | ✓ | |
| 6 caption/style templates | ✓ | |
| Preview step before paid submission | ✓ | |
| 3 public sample outputs at share-worthy quality | ✓ | |
| Brand kit: end card toggle, watermark by tier | ✓ | |
| `e3d-agent cast` commands including archive | ✓ | |
| NFT mint full implementation (ERC-721, E3DNFTManager, wallet confirmation) | | ✓ |
| `e3d-agent cast mint-nft` command | | ✓ |
| NFT provenance panel in UI | | ✓ |
| Revisions: end card regen, B-roll regen, voice regen | | ✓ |
| Brand kit: logo upload, primary color | | ✓ |
| 4 visual style presets beyond default | | ✓ |
| Output variants (up to 3 candidate cuts per short) | | ✓ |

The `capabilities` response should reflect actual v1 availability: set `nftMintAvailable: false` until Phase 7 ships.

---

## 3. Non-Goals

Do not rebuild the media pipeline from scratch. Preserve the existing Python and Node scripts where practical.

Do not put private keys into the browser path.

Do not make the hosted UI dependent on local files on a user's machine after upload.

Do not enable unrestricted autonomous public posting by default. Publishing can be supported as an explicit, opt-in agent/script capability after render completion.

Do not deploy to production until the implementation has passing tests, a dry-run path, and operator-reviewed environment variables.

Do not offer the free tier as an unbounded render farm. Free usage must have strict attempt, duration, artifact size, concurrency, and retention limits.

Do not leave the "Get E3D" path as an open question. It must be resolved and linked before Phase 3.

---

## 4. Current State

### 4.1 `e3d-pod2vid`

Existing repo:

```text
/home/ubuntu/e3d-pod2vid
```

Key scripts:

```text
pod2vid.py              audio -> MP4 + SRT with diarization, B-roll, subtitles
tts_replace.py          optional OpenAI TTS replacement
make_short.py           script -> short video
signal_short.py         automated E3D Maps signal short workflow
yt_upload.js            YouTube upload
yt_update.js            YouTube metadata/thumbnail update
announce.js             Discord/Telegram/X/Moltbook/LinkedIn posting
ecosystem.config.js     existing PM2 schedule for signal_short.py
```

The current product is script-first. It has no hosted API, job queue, web UI, user upload flow, payment enforcement, or product-scoped E3D credit key.

### 4.2 `spacepacket/server`

Existing server:

```text
/home/ubuntu/spacepacket/server
```

Relevant files:

```text
productRegistry.js         product definitions; currently includes maps
productPaymentsRoutes.js   /api/payments/products, quote, purchase, balance, spend
productPaymentsService.js  product credit issuance, balance, spend, audit
spacepacket.js             main Express server entry point
```

Existing shared payment API:

```http
GET  /api/payments/products
POST /api/payments/credits/quote
POST /api/payments/credits/purchase
GET  /api/payments/credits/balance
POST /api/payments/credits/spend
```

The implementation should extend this system with a new product:

```text
product = "cast"
credit key prefix = "e3d_cast_pay_"
```

### 4.3 `e3d-agent`

Existing agent scaffold:

```text
/home/ubuntu/e3d-agent
```

Relevant files:

```text
src/e3d/payments-client.ts
src/cli.ts
src/wallet/walletconnect.ts
src/wallet/delegated.ts
src/wallet/erc20-transfer.ts
examples/
docs/
```

The current agent supports Maps payments and Maps API usage. It should be enhanced so Cast becomes the next clear example of a paid E3D product that can be driven by humans or agents.

---

## 5. Product Behavior

### 5.1 Agent/Script Path (Primary Differentiator)

The agent path is the primary competitive advantage of Cast. It must work completely without a browser after wallet onboarding.

Agents must be able to:

1. connect or provide a wallet;
2. call `GET /api/cast/capabilities` and receive machine-readable tier limits, pricing, presets, and artifact schemas;
3. call `POST /api/cast/jobs/quote` and receive an exact credit cost with no spend;
4. buy Cast credits using E3D Product Payments;
5. submit a render job with input metadata;
6. upload input media, provide a source URL, or submit transcript text;
7. poll status via `GET /api/cast/jobs/:jobId`;
8. retrieve output artifacts via `GET /api/cast/jobs/:jobId/artifacts`;
9. optionally publish through YouTube and announcement scripts when credentials are present;
10. handle 402/insufficient-credit errors with machine-readable `upgradePath` fields and recover without human intervention.

The agent path must support dry-run mode and explicit delegated-wallet transaction opt-in, matching the existing safety posture in `e3d-agent`.

A working `e3d-agent cast render` command — from credit purchase through artifact download — is required before the product is considered launched. It is the proof that the agent promise is real.

### 5.2 Human UI

The first screen at `cast.e3d.ai` should be the usable Cast workspace, not a marketing landing page. The product is the marketing.

Required UI capabilities:

- connect wallet;
- show connected wallet address, product credit balance, active tier, and E3D holder discount status;
- quote required E3D/wE3D cost for a requested credit purchase;
- present supported payment methods returned by `/api/payments/credits/quote`;
- show E3D holder discount (20% off) prominently next to the spot price;
- register a confirmed payment transaction through `/api/payments/credits/purchase`;
- upload an audio file, provide a source URL, or write/paste a transcript;
- choose output type:
  - full YouTube-ready video;
  - short vertical video;
  - transcript-to-short video;
  - transcript-to-narrated video;
  - audio-to-TTS replacement plus video;
- configure basic render options:
  - speaker names;
  - aspect ratio or output preset;
  - subtitle style preset;
  - voice preset for transcript/TTS jobs;
  - B-roll intensity or visual style preset;
  - optional thumbnail generation;
  - "Made with Cast" end card toggle (on by default on paid tier; earns credit rebate);
- submit a paid render job;
- show job status and logs at a user-safe level;
- download output artifacts when complete;
- show a clear path to get E3D Token when the wallet or credit balance is insufficient, linking to e3d.ai/token.

The UI should be dense and operational. Avoid a marketing-only hero. Use the product itself as the first-viewport signal.

---

## 6. Proposed Architecture

### 6.1 Components

```text
e3d-pod2vid-service  (/home/ubuntu/e3d-pod2vid-service)
  -> UI: Vite/React app served from cast.e3d.ai
  -> Worker daemon: PM2 process that picks jobs from queue and shells out to e3d-pod2vid
  -> Nginx config and deployment scripts

e3d-pod2vid  (/home/ubuntu/e3d-pod2vid)
  -> Pipeline scripts: pod2vid.py, make_short.py, tts_replace.py, announce.js, yt_upload.js, etc.
  -> Job runner wrapper: bin/pod2vid-job.py — the stable interface the worker calls
  -> Used directly by developers who want to run the pipeline locally

spacepacket/server  (/home/ubuntu/spacepacket/server)
  -> Cast API routes: /api/cast/*
  -> Product payment quote/purchase/balance/spend
  -> Job creation/status/artifact endpoints
  -> Internal service auth for spend operations
  -> E3D holder discount logic (20% off for qualifying wallets)
  -> Burn tracking (5% of each job's credit cost flagged for burn)
  -> IPFS archive orchestration

e3d-agent  (/home/ubuntu/e3d-agent)
  -> CLI and reusable client for automated credit purchase and job execution
```

The worker in `e3d-pod2vid-service` calls into `e3d-pod2vid` by path:

```bash
python3 /home/ubuntu/e3d-pod2vid/bin/pod2vid-job.py <manifest-path>
```

The pipeline repo has no knowledge of the service. The service depends on the pipeline being present on the same server.

### 6.2 Payment Model

Cast must use the shared E3D Product Payments API.

Add `cast` to `PRODUCT_REGISTRY` with:

```text
displayName: Cast
creditRate: "1 credit = 0.001 E3D or wE3D before discounts"
paymentMethods: same shape as maps unless product-specific treasury is introduced
minimumBaseCredits: use existing minimum unless product economics require a higher minimum
defaultRouteCost: explicit, not inherited accidentally from maps
holderDiscount: 0.20 (20% off for qualifying E3D holders)
burnRate: 0.05 (5% of each job's credit cost flagged for burn)
pricing:
  /cast/jobs/quote      0
  /cast/jobs            configured job submission cost
  /cast/jobs/status     0 or very low
  /cast/jobs/artifacts  0 or very low
  /cast/shorts          configured short render cost
```

The implementation may use coarse v1 pricing by job type. Dynamic pricing based on duration can be added in a later phase, but the API should include estimated duration and estimated credit cost now.

The quote response must show:
- base price;
- holder discount applied (if wallet qualifies);
- effective price after discount;
- E3D burn amount for this job;
- remaining balance after spend.

### 6.2.1 Tiers and Limits

Cast should expose tiers in both the UI and `GET /api/cast/capabilities`. The exact credit prices can be tuned, but v1 should launch with concrete limits so users and agents know what work is acceptable before upload or spend.

Proposed tiers:

| Tier | Intended user | Included usage | Max input | Max output duration | Max artifact package | Retention | Concurrency |
|---|---|---:|---:|---:|---:|---:|---:|
| Free | first-time trial | 3 lifetime renders per wallet/session | 25 MB audio or 3,000 transcript chars | 45 seconds | 100 MB | 24 hours | 1 |
| Starter | individual creators and agents testing automation | paid per job | 250 MB audio or 20,000 transcript chars | 10 minutes | 1 GB | 7 days | 1 |
| Pro | regular creators and production agents | paid per job with better limits | 1 GB audio or 75,000 transcript chars | 60 minutes | 5 GB | 30 days | 3 |
| Studio | teams/operators | custom credits or allowlist | 3 GB audio or 200,000 transcript chars | 2 hours | 15 GB | 90 days | 5+ configured |

Tier rules:

- free renders must use a visible watermark and `cast.e3d.ai` end card;
- free renders must not support public social publishing;
- free artifact downloads should expire quickly and should not be indexed;
- paid jobs should reject inputs that would exceed tier limits before spending credits;
- artifact package size means the combined size of all downloadable outputs for one job;
- agents must receive machine-readable limit errors with `tier`, `limit`, `actual`, and `upgradePath` fields.

Recommended v1 pricing units:

| Job type | Free | Starter | Pro | Notes |
|---|---:|---:|---:|---|
| short/transcript short | 1 free attempt | 100 credits | 75 credits | <= 60s output |
| short/audio short | 1 free attempt | 150 credits | 125 credits | includes audio analysis |
| full video | not available | 500 credits base + duration factor | 400 credits base + duration factor | duration factor can be coarse in v1 |
| TTS replacement | not available | +250 credits | +200 credits | charged as an add-on |
| thumbnail package | included on paid | included | included | free tier can use a simple generated still |
| social publishing package | not available | +100 credits | +75 credits | explicit opt-in only |
| IPFS archive package | not available | +50 credits | +25 credits | pins completed artifact package; local retention can be shorter |
| NFT mint package | not available | mint fee + 100 credits | mint fee + 75 credits | explicit wallet/delegated-wallet confirmation |
| "Made with Cast" rebate | n/a | -10 credits on publish | -10 credits on publish | applied after confirmed publish |

The UI should display prices as estimates until the final quote response is returned. The API remains the source of truth.

### 6.3 Credit Spend

Render submission must spend credits before queueing expensive work.

For v1:

- `POST /api/cast/jobs` spends a configured number of `cast` credits.
- `POST /api/cast/shorts` spends the short render cost.
- quote/status/artifact reads should be free or near-free.
- if render fails due to service error before media processing begins, the system should record a refund or avoid spend; if refund support is not available, fail before spend whenever possible.

The Cast API should call:

```http
POST /api/payments/credits/spend
Authorization: Internal <E3D_CAST_INTERNAL_SERVICE_KEY>
```

with:

```json
{
  "product": "cast",
  "creditKey": "<raw product credit key>",
  "route": "/cast/jobs",
  "requestId": "<idempotency key>",
  "metadata": {
    "jobId": "...",
    "wallet": "...",
    "inputKind": "upload|url|transcript",
    "preset": "youtube|short|tts",
    "holderDiscountApplied": true,
    "burnAmount": 5
  }
}
```

### 6.4 Job Model

Create a durable job model owned by Spacepacket or by a lightweight Cast service with a Spacepacket-facing API.

Minimum job fields:

```text
jobId
parentJobId
wallet
productCreditKeyHash
status: queued | running | succeeded | failed | canceled
inputKind: upload | url | transcript
inputUri
transcriptTextHash
inputDurationSeconds
inputSizeBytes
outputPreset
tier
options
estimatedCredits
spentCredits
holderDiscountApplied
burnAmount
estimatedArtifactBytes
actualArtifactBytes
createdAt
startedAt
finishedAt
errorCode
errorMessage
artifactUris
artifactChecksums
artifactExpiresAt
ipfsArchiveRequested
ipfsArchiveStatus: none | pending | pinned | failed
ipfsArchiveUris
ipfsGatewayUrls
nftMintRequested
nftMintStatus: none | pending | minted | failed
nftContract
nftTokenId
nftTokenUri
workerLogTail
idempotencyKey
webhookUrl
webhookStatus
publishedAt
rebateApplied
```

Use ClickHouse only if it is consistent with local server patterns. A JSONL/SQLite queue is acceptable for a scoped v1 if codex-spec-runner documents the operational limits and tests idempotency.

### 6.5 Artifact Storage

For v1, all render jobs use local disk as the working and short-term operational store:

```text
CAST_STORAGE_DIR=/var/lib/e3d-pod2vid
```

Do not store user uploads or output files in the repo.

IPFS archive is optional and additive. It should use E3D core storage infrastructure where available, including the existing Pinata/IPFS helpers in `/home/ubuntu/spacepacket/server/uploadToIPFS.js` or a product-safe wrapper around them.

Artifacts:

```text
input audio
source transcript when user supplied or generated
final mp4
srt
thumbnail
metadata json
social copy json
job manifest json
```

Downloads must use opaque job/artifact identifiers, not direct arbitrary filesystem paths.

When IPFS archive is enabled, the archive package should include:

```text
final mp4
thumbnail/poster image
srt/captions
metadata json
social copy json
job manifest json
archive manifest json
```

The archive manifest should include:

```json
{
  "kind": "cast_archive",
  "jobId": "cast_job_...",
  "createdAt": "2026-06-30T00:00:00.000Z",
  "artifacts": [
    {
      "artifactId": "video",
      "type": "mp4",
      "contentType": "video/mp4",
      "bytes": 123456789,
      "sha256": "..."
    }
  ],
  "localRetentionExpiresAt": "2026-07-07T00:00:00.000Z",
  "ipfs": {
    "video": "ipfs://...",
    "thumbnail": "ipfs://...",
    "manifest": "ipfs://..."
  }
}
```

NFT metadata should follow standard ERC-721-style metadata conventions:

```json
{
  "name": "Cast: Episode Title",
  "description": "Generated video package by Cast.",
  "image": "ipfs://<thumbnail-cid>",
  "animation_url": "ipfs://<video-cid>",
  "properties": {
    "kind": "cast_render",
    "job_id": "cast_job_...",
    "manifest": "ipfs://<manifest-cid>",
    "captions": "ipfs://<captions-cid>",
    "metadata": "ipfs://<metadata-cid>",
    "source_hash": "sha256:...",
    "preset": "youtube",
    "created_by": "cast.e3d.ai"
  }
}
```

Local retention rules:

- local files are always used for rendering, previews, revisions, and immediate publishing;
- if IPFS archive succeeds, local retention may be shortened by tier policy;
- if publishing happens after local retention expires, the worker may rehydrate the MP4 from IPFS/gateway into temp storage and then upload;
- IPFS archive failure should not fail an otherwise successful render unless the user explicitly paid for archive and requested strict archive success.

### 6.6 Worker Execution

Wrap existing scripts instead of rewriting media logic.

The worker should expose a deterministic command or module entry point, for example:

```bash
python3 pod2vid.py <input-audio> <output-mp4>
python3 tts_replace.py <diarization-json> <output-prefix>
python3 make_short.py <output-mp4>
node yt_upload.js <video> <title>
node announce.js <url> <message>
```

Add a higher-level automation script in `e3d-pod2vid`:

```text
bin/pod2vid-job.js or scripts/pod2vid_job.py
```

Responsibilities:

- read one job manifest;
- validate required environment variables;
- run the selected pipeline;
- write structured status updates;
- produce artifact manifest;
- exit non-zero on failure.

The hosted worker can call this script. `e3d-agent` can also use it as a local automation example.

---

## 7. API Requirements

All API routes should live in `/home/ubuntu/spacepacket/server` and be mounted by `spacepacket.js`.

### 7.1 Public Product Payment Routes

Use existing routes:

```http
GET  /api/payments/products
POST /api/payments/credits/quote
POST /api/payments/credits/purchase
GET  /api/payments/credits/balance?product=cast
```

Expected quote body:

```json
{
  "product": "cast",
  "wallet": "0x...",
  "requestedIssuedCredits": 1000,
  "promotionCode": "FIRST_100_AGENTS"
}
```

Quote response must include holder discount and effective price:

```json
{
  "basePrice": "1.000 E3D",
  "holderDiscount": "0.200 E3D",
  "effectivePrice": "0.800 E3D",
  "burnAmount": "0.050 E3D",
  "paymentOptions": [...]
}
```

Expected purchase body:

```json
{
  "product": "cast",
  "wallet": "0x...",
  "txHash": "0x...",
  "paymentMethod": "base-we3d"
}
```

### 7.2 Cast Routes

Add:

```http
GET  /api/cast/health
GET  /api/cast/capabilities
GET  /llms.txt
GET  /.well-known/agent-capabilities.json
GET  /openapi/e3d-cast.yaml
POST /api/cast/jobs/quote
POST /api/cast/jobs
GET  /api/cast/jobs/:jobId
GET  /api/cast/jobs/:jobId/artifacts
GET  /api/cast/jobs/:jobId/artifacts/:artifactId
POST /api/cast/jobs/:jobId/cancel
POST /api/cast/jobs/:jobId/revise
POST /api/cast/jobs/:jobId/publish
POST /api/cast/jobs/:jobId/archive-ipfs
POST /api/cast/jobs/:jobId/mint-nft
```

`POST /api/cast/jobs/quote` returns an estimated credit cost without spending credits.

`POST /api/cast/jobs` requires:

```http
Authorization: Bearer <e3d_cast_pay_...>
Idempotency-Key: <stable client generated key>
```

Request shape:

```json
{
  "input": {
    "kind": "url",
    "url": "https://..."
  },
  "preset": "youtube",
  "options": {
    "speakerAName": "Host",
    "speakerBName": "Guest",
    "subtitleStyle": "default",
    "generateThumbnail": true,
    "brandEndCard": true,
    "archiveToIpfs": false,
    "mintNft": false,
    "publish": false
  },
  "webhookUrl": "https://agent.example.com/hooks/cast"
}
```

Supported input shapes:

```json
{
  "input": {
    "kind": "transcript",
    "text": "Speaker 1: ...\nSpeaker 2: ..."
  },
  "preset": "short",
  "options": {
    "voicePreset": "host_guest",
    "subtitleStyle": "bold_mobile",
    "visualStyle": "tech_editorial",
    "generateThumbnail": true,
    "brandEndCard": true,
    "archiveToIpfs": true
  }
}
```

```json
{
  "input": {
    "kind": "upload",
    "uploadId": "cast_upload_..."
  },
  "preset": "youtube",
  "options": {
    "speakerAName": "Host",
    "speakerBName": "Guest"
  }
}
```

Response shape:

```json
{
  "jobId": "cast_job_...",
  "status": "queued",
  "spentCredits": 80,
  "holderDiscountApplied": true,
  "burnAmount": 5,
  "tier": "starter",
  "estimatedDurationSeconds": 600,
  "estimatedArtifactBytes": 750000000,
  "balance": {
    "credits": 920
  }
}
```

`POST /api/cast/jobs/:jobId/revise` creates a child job for low-cost changes.

Request shape:

```json
{
  "revisionType": "subtitle_style",
  "options": {
    "subtitleStyle": "bold_mobile"
  }
}
```

Supported `revisionType` values for v1:

```text
thumbnail
metadata
subtitle_style
brand_end_card
broll
voice
```

`POST /api/cast/jobs/:jobId/publish` should be explicit and separate from render submission unless the caller supplies a confirmed publish option and credentials. Public publishing must never be the default.

`POST /api/cast/jobs/:jobId/archive-ipfs` pins a completed artifact package to E3D-managed IPFS storage.

Request shape:

```json
{
  "include": ["video", "thumbnail", "captions", "manifest", "metadata", "social_copy"],
  "strict": false
}
```

Response shape:

```json
{
  "jobId": "cast_job_...",
  "status": "pinned",
  "ipfs": {
    "video": "ipfs://...",
    "thumbnail": "ipfs://...",
    "manifest": "ipfs://..."
  },
  "gatewayUrls": {
    "video": "https://...",
    "manifest": "https://..."
  }
}
```

`POST /api/cast/jobs/:jobId/mint-nft` creates an NFT provenance record for an already archived job. It should require IPFS archive first.

Request shape:

```json
{
  "wallet": "0x...",
  "metadataUri": "ipfs://...",
  "confirm": true
}
```

Minting behavior:

- browser users should confirm through wallet;
- headless agents must require delegated-wallet opt-in, `--send`, and `--yes`;
- minting should use E3D core NFT infrastructure, such as `E3DNFTManager`, rather than Cast-specific contracts unless a product-specific contract is introduced later;
- minting must not expose private transcript text in token metadata.

Webhook behavior:

- job submit may include `webhookUrl`;
- webhook delivery must be best-effort with retry;
- webhook payloads must not include raw private transcript text;
- webhook payloads should include `jobId`, `status`, `artifactManifestUrl`, `errorCode`, and `errorMessage`;
- agents must still be able to poll if webhook delivery fails.

### 7.3 Uploads

If direct browser uploads are implemented, use one of these v1 approaches:

- `POST /api/cast/uploads` multipart upload with size/type limits;
- presigned local upload token followed by `POST /api/cast/jobs`.

Minimum limits:

```text
allowed types: audio/mpeg, audio/mp4, audio/wav, audio/x-m4a, video/mp4 for input extraction if supported
max upload size: configurable, default 500 MB
max duration: configurable, default 2 hours
max transcript length: tier-dependent, default 20,000 characters for Starter
```

Reject unsupported or oversized files before spending credits.

### 7.4 Capabilities Response

`GET /api/cast/capabilities` should be self-describing enough for agents to decide whether to use the service without reading any documentation.

Minimum response fields:

```json
{
  "product": "cast",
  "version": "1.0",
  "inputs": ["upload", "url", "transcript"],
  "presets": ["short", "youtube", "tts_video", "transcript_short", "transcript_video"],
  "tiers": [
    {
      "id": "free",
      "maxInputBytes": 25000000,
      "maxTranscriptChars": 3000,
      "maxOutputDurationSeconds": 45,
      "maxArtifactBytes": 100000000,
      "freeAttempts": 3,
      "retentionHours": 24,
      "watermarked": true,
      "publishingAllowed": false
    }
  ],
  "pricing": {
    "holderDiscountRate": 0.20,
    "burnRate": 0.05,
    "getE3DUrl": "https://e3d.ai/token",
    "ipfsArchiveAvailable": true,
    "nftMintAvailable": true
  },
  "artifactTypes": ["mp4", "srt", "thumbnail", "manifest", "metadata", "social_copy", "ipfs_archive", "nft_metadata"],
  "artifactSchema": {
    "requiredFields": ["artifactId", "type", "contentType", "bytes", "sha256", "expiresAt", "downloadUrl"],
    "optionalFields": ["ipfsUri", "gatewayUrl", "nftContract", "nftTokenId", "tokenUri"]
  },
  "auth": ["wallet", "product_credit_key"],
  "openapiUrl": "https://cast.e3d.ai/openapi/e3d-cast.yaml",
  "llmsTxtUrl": "https://cast.e3d.ai/llms.txt",
  "agentCapabilitiesUrl": "https://cast.e3d.ai/.well-known/agent-capabilities.json",
  "webhooks": {
    "supported": true,
    "events": ["job.succeeded", "job.failed", "job.canceled"]
  },
  "revisions": ["thumbnail", "metadata", "subtitle_style", "brand_end_card", "broll", "voice"],
  "storage": {
    "localRequired": true,
    "ipfsArchiveOptional": true,
    "nftMintOptional": true
  }
}
```

---

## 8. UI Requirements

The UI can be implemented as a minimal Vite/React app, static HTML/JS, or an existing local pattern if one is found during implementation. It must be hosted from `cast.e3d.ai`.

The UI should be compelling, modern, and easy to use while staying operational. The first screen should be the product workspace: a user should immediately understand that they can make a video, see the expected cost, and start with upload, URL, transcript, or sample content. The product itself is the landing page.

Required views:

- Workspace: wallet, credits, upload/source, options, quote, submit.
- Samples: public example outputs for each main preset.
- Jobs: recent jobs for the connected wallet or local session.
- Job Detail: status, progress, artifacts, errors.
- Payments: quote, E3D holder discount display, payment method selection, purchase registration, balance refresh, link to e3d.ai/token.
- Agent Mode: copyable CLI/API examples using the connected product and selected options.

### 8.1 First Screen Workspace

The first viewport should include:

- a compact header with product name, wallet state, credit balance, tier, and E3D holder discount badge if applicable;
- a central creation panel with input mode tabs:
  - Upload;
  - Source URL;
  - Transcript;
  - Sample;
- a preset selector with clear output cards:
  - Short;
  - YouTube video;
  - Transcript video;
  - TTS replacement;
- a live quote panel showing estimated credits, holder discount applied, expected render time, tier limit fit, and estimated artifact size;
- a compact sample gallery showing real outputs, not abstract marketing art;
- a primary action that changes state clearly: `Try free render`, `Buy credits`, `Submit job`, or `Upgrade tier`;
- a recent jobs strip or compact list so returning users can resume work.

The interface should look like a polished creative tool, not an admin form. Use high-quality sample output thumbnails or generated previews where possible. Do not hide the actual product behind a marketing landing page.

### 8.2 Preview, Styles, and Brand Kit

Before paid submission, users should see enough of the creative result to trust the render.

Required:

- preview frame showing selected aspect ratio, subtitle style, title treatment, watermark/end card state, and brand colors;
- style template selector with at least:
  - clean podcast;
  - bold mobile;
  - finance signal;
  - developer demo;
  - news brief;
  - minimal subtitles;
- visual style selector with at least:
  - editorial;
  - tech;
  - finance;
  - cinematic;
- brand kit controls:
  - logo upload or no-logo option;
  - primary color;
  - end card toggle;
  - watermark behavior by tier;
- archive controls:
  - archive to IPFS;
  - mint archive as NFT;
  - show privacy/permanence warnings before either option is enabled;
- output variant option for shorts: generate up to 3 candidate cuts or style variants when tier and credits allow;
- platform metadata preview: title, description, tags, chapters if applicable, and social copy.

The sample gallery should include at least one public render for transcript input, one for audio input, and one for agent-generated content. These examples should be used in empty states and onboarding.

### 8.3 Transcript Input

Transcript mode must support users who do not have an audio file.

Required transcript capabilities:

- paste or write transcript text directly in the browser;
- show character count and tier limit in real time;
- support plain text and simple speaker labels such as `Host:` and `Guest:`;
- allow optional title, topic, tone, and call-to-action fields;
- choose whether the transcript should become:
  - a narrated short;
  - a YouTube-style video with generated narration;
  - captions/visual package only if audio is supplied later;
- select voice preset when narration is generated;
- run quote/validation before spend;
- autosave locally until submission without sending private text unexpectedly.

Transcript jobs should produce generated audio when the chosen preset requires narration. The job manifest must record that the source was user-supplied text and should include a hash plus artifact metadata, not raw transcript text in public logs.

### 8.4 Tier and Limit UX

The UI must make limits understandable before upload or spend:

- show remaining free attempts when a wallet/session is eligible;
- show max input size, max transcript length, max output duration, max artifact package size, retention, and concurrency for the active tier;
- warn before upload if a file appears too large for the selected tier;
- show a side-by-side tier comparison when a job exceeds free or current paid limits;
- make upgrade/buy-credit actions contextual to the failed limit;
- show artifact retention countdowns on completed jobs;
- label free-tier outputs clearly as watermarked and short-lived.

Suggested free-tier copy:

```text
Free: 3 trial renders, up to 45 seconds, 100 MB artifact package, stored for 24 hours.
Outputs include a cast.e3d.ai watermark.
```

Suggested paid-tier copy with holder discount:

```text
Starter: render up to 10 minutes, download up to 1 GB per job.
Hold E3D for 20% off every job.
```

### 8.5 Payments and "Get E3D"

When credits are insufficient the UI must not leave the user stranded:

- show exact E3D/wE3D needed and supported chains;
- show treasury/token addresses from the quote response;
- show the E3D holder discount (20% off) as a reason to acquire and hold E3D rather than use another payment method;
- provide a prominent **Get E3D** button linking to `https://e3d.ai/token`;
- do not submit render jobs until credits are available.

The "Get E3D" path must be verified end-to-end before Phase 3. It is a Phase 2 acceptance criterion.

### 8.6 Visual and Interaction Quality

The hosted product should feel modern and trustworthy:

- use a restrained creator-tool layout with dense controls, clear sections, and immediate feedback;
- use tabs, segmented controls, sliders, toggles, and icon buttons where they make the workflow faster;
- provide drag-and-drop upload with progress, cancel, retry, and validation states;
- keep quote, balance, tier, and submit state visible without forcing users through separate pages;
- show render progress as meaningful stages: validating, transcribing, scripting, selecting visuals, rendering, packaging, complete;
- show user-safe logs as concise events, with full logs operator-only;
- provide polished empty states using the sample job, not generic explanatory text;
- ensure mobile works for checking jobs, buying credits, pasting transcript, and downloading artifacts, even if large uploads are better on desktop.

### 8.7 Job Detail, Artifacts, and Revisions

The completed job view should help users improve outputs without restarting.

Required:

- video preview where browser-supported;
- artifact list with type, size, expiration, checksum, and download action;
- IPFS archive panel showing pin status, `ipfs://` URIs, gateway URLs, and archive manifest;
- NFT provenance panel showing mint status, contract, token ID, and token URI when minted;
- manifest viewer with a user-friendly summary and raw JSON copy option;
- one-click revision actions for supported revision types:
  - regenerate thumbnail;
  - regenerate metadata/social copy;
  - change subtitle style;
  - toggle/regenerate end card;
  - regenerate B-roll for a short;
  - change generated narration voice for transcript jobs;
- clear credit cost before each revision;
- parent/child job history so revisions are traceable;
- publishing panel that is disabled until explicit credentials/options are present.

IPFS/NFT UX rules:

- IPFS archive is opt-in and must explain that archived artifacts may be durable and externally accessible depending on gateway/provider settings;
- NFT mint is opt-in and separate from IPFS archive;
- NFT mint requires explicit confirmation and must show the metadata that will become public before minting;
- private transcript text should never be shown as included in public NFT metadata; use hashes and summaries instead;
- if a user selects publish after local retention expires, show that Cast may temporarily rehydrate the MP4 from IPFS into worker storage for upload.

### 8.8 Agent Mode UX

Agent Mode should be a first-class panel, not buried documentation. It serves double duty: it makes the agent path discoverable for developers, and it demonstrates that Cast is API-native.

Required:

- show curl commands for capabilities, quote, submit, webhook, poll, artifact list, download, and revision using the current selected options;
- show matching `e3d-agent cast ...` commands;
- expose the OpenAPI link;
- expose `llms.txt`;
- expose `.well-known/agent-capabilities.json`;
- expose the capabilities endpoint;
- explain credit-key auth and delegated-wallet purchase safety briefly;
- include dry-run examples and expected JSON response snippets;
- show holder discount as part of the example (`holderDiscountApplied: true`);
- make limit errors and 402 payment errors easy for agents to parse and recover from.

Wallet behavior:

- browser wallet connection for address discovery and transaction signing;
- never ask the user to paste a private key;
- after purchase, register the transaction and store only the product credit key client-side as a bearer credential.

---

## 9. `e3d-agent` Enhancements

Cast must be a first-class product in `e3d-agent` — not an optional extension. A working end-to-end agent render is required before launch.

### 9.1 Client

Create:

```text
src/cast/cast-client.ts
```

Responsibilities:

- fetch capabilities;
- fetch OpenAPI/agent discovery metadata when useful;
- quote jobs;
- submit jobs;
- submit jobs with optional webhook URL;
- poll jobs;
- list artifacts;
- download artifacts;
- archive completed jobs to IPFS;
- mint archived jobs as NFTs with explicit delegated-wallet safeguards;
- create revision jobs;
- handle 402/credit exhaustion with actionable errors including `upgradePath` and `getE3DUrl`.

### 9.2 Payments

Generalize existing payment helpers so `maps` is not hardcoded in the core purchase path.

New commands:

```bash
e3d-agent cast credits
e3d-agent cast buy-credits --amount 1000 --payment-method base-we3d
e3d-agent cast quote --input ./episode.m4a --preset youtube
e3d-agent cast render --input ./episode.m4a --preset youtube --wait --download ./output
e3d-agent cast render --transcript ./script.txt --preset transcript_short --wait --download ./output
e3d-agent cast render --transcript ./script.txt --preset transcript_short --webhook https://agent.example.com/hooks/cast
e3d-agent cast archive --job cast_job_...
e3d-agent cast mint-nft --job cast_job_... --send --yes
e3d-agent cast status --job cast_job_...
e3d-agent cast artifacts --job cast_job_... --download ./output
e3d-agent cast revise --job cast_job_... --type subtitle_style --subtitle-style bold_mobile --wait --download ./output
```

Headless delegated-wallet purchase must require:

```text
AGENT_WALLET_PRIVATE_KEY
E3D_AGENT_ALLOW_DELEGATED_TRANSACTIONS=true
--send
--yes
```

Save returned credit key as:

```text
E3D_CAST_CREDIT_KEY=e3d_cast_pay_...
```

### 9.3 Examples and Docs

Add:

```text
examples/08-cast-render.ts
examples/09-cast-headless-publish.ts
examples/10-cast-webhook.ts
examples/11-cast-revise.ts
examples/12-cast-ipfs-archive.ts
examples/13-cast-mint-nft.ts
docs/cast.md
openapi/e3d-cast.yaml
```

Example 08 should render and download. Example 09 may publish only when explicit publishing credentials and flags are present.
Example 10 should receive or simulate a webhook. Example 11 should create a revision job from a completed parent job.
Example 12 should archive a completed job to IPFS. Example 13 should mint only with explicit delegated-wallet transaction flags.

The examples should be clean enough to paste into a blog post or README. They are marketing as much as documentation.

---

## 10. Deployment Requirements

### 10.1 DNS and Nginx

Host:

```text
cast.e3d.ai
```

Implementation should add an Nginx site or server block that:

- serves the UI;
- proxies `/api/cast/*` and `/api/payments/*` to the Spacepacket server;
- supports large uploads with configured body limits;
- uses HTTPS.

### 10.2 PM2

Add PM2 processes as needed:

```text
cast-ui       optional UI server if not static
cast-worker   render worker
```

Do not replace existing `signal-short` scheduling unless explicitly needed.

### 10.3 Environment Variables

Required or expected:

```text
CAST_PUBLIC_BASE_URL=https://cast.e3d.ai
CAST_STORAGE_DIR=/var/lib/e3d-pod2vid
CAST_FREE_ATTEMPTS=3
CAST_FREE_MAX_ARTIFACT_MB=100
CAST_FREE_RETENTION_HOURS=24
CAST_MAX_UPLOAD_MB=500
CAST_MAX_DURATION_SECONDS=7200
CAST_MAX_TRANSCRIPT_CHARS=20000
CAST_HOLDER_DISCOUNT_RATE=0.20
CAST_BURN_RATE=0.05
CAST_GET_E3D_URL=https://e3d.ai/token
CAST_IPFS_ARCHIVE_ENABLED=true
CAST_NFT_MINT_ENABLED=true
CAST_IPFS_LOCAL_RETENTION_HOURS=24
E3D_CAST_INTERNAL_SERVICE_KEY=...

ASSEMBLYAI_API_KEY=...
OPENAI_API_KEY=...
PEXELS_API_KEY=...
FFMPEG_PATH=ffmpeg
PINATA_API_KEY=...
PINATA_SECRET_API_KEY=...
E3D_NFT_MANAGER_ADDRESS=...
```

Optional publishing:

```text
YT_PRIVACY=private|unlisted|public
DISCORD_BOT_TOKEN=...
TELEGRAM_BOT_TOKEN=...
X_ACCESS_TOKEN=...
MOLTBOOK_API_KEY=...
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
```

---

## 11. Security and Safety

Required:

- product credit keys are accepted only as bearer credentials or `X-Payment-Key`;
- spend operations use `E3D_CAST_INTERNAL_SERVICE_KEY`;
- all file paths are resolved under `CAST_STORAGE_DIR`;
- reject path traversal;
- validate MIME type and extension;
- enforce upload size and duration limits before spend;
- enforce transcript length, free-attempt, artifact-size, retention, and concurrency limits by tier;
- sanitize job logs before returning them to users;
- use idempotency keys for paid job submission;
- do not expose API provider keys to the browser;
- do not expose Pinata/IPFS provider keys to the browser;
- do not archive private uploads/transcripts to IPFS without explicit opt-in;
- do not mint NFT metadata containing raw private transcript text;
- do not default to public publishing;
- delegated-wallet transactions in `e3d-agent` must retain explicit warnings and opt-in checks.

Recommended:

- simple per-wallet or per-credit-key rate limiting;
- periodic cleanup of failed/old uploads;
- operator-only access to full worker logs;
- malware/content moderation checks before public publishing.

---

## 12. Implementation Phases

### Phase 1: Product Registry and Payment Plumbing

Repos:

```text
/home/ubuntu/spacepacket/server
```

Tasks:

- add `cast` to `productRegistry.js` with holder discount rate and burn rate fields;
- ensure generated credit keys use `e3d_cast_pay_`;
- add tests for quote, purchase, balance, route cost, and unsupported routes;
- implement holder discount logic in quote response;
- implement burn tracking fields in spend records;
- confirm `/api/payments/products` lists Cast.

Acceptance:

- `POST /api/payments/credits/quote` with `product=cast` returns payment options including holder discount and burn amount;
- `POST /api/payments/credits/purchase` can issue a `cast` credit key in tests;
- `GET /api/payments/credits/balance?product=cast` works with service-token auth and credit-key auth;
- existing Maps payment tests still pass.

### Phase 2: Cast API, Job Queue, and "Get E3D" Path

Repo:

```text
/home/ubuntu/spacepacket/server
```

**v1 tasks:**

- add Cast route module in Spacepacket;
- implement health/capabilities/job quote/job submit/status/artifact endpoints;
- implement OpenAPI, `llms.txt`, and `.well-known/agent-capabilities.json` routes;
- implement webhook URL validation, delivery, retry, and fallback polling behavior;
- implement revision and publish endpoint scaffolding (all revision types are routed; v1 worker only executes thumbnail, metadata, subtitle style);
- implement IPFS archive endpoint using E3D core storage infrastructure (`uploadToIPFS.js` or wrapper);
- implement `mint-nft` endpoint scaffolded to return HTTP 501 with a `v1.1` message;
- set `nftMintAvailable: false` in capabilities response;
- implement transcript input validation and transcript job submission;
- expose tier/limit metadata through capabilities and quote responses;
- expose holder discount and burn amount in capabilities and quote;
- implement job persistence;
- implement idempotent credit spend on paid job submission;
- verify and document the "Get E3D" URL (`https://e3d.ai/token`) end-to-end;
- add tests for auth, idempotency, failed validation, insufficient credits, tier limits, transcript limits, and artifact path safety.

Acceptance:

- invalid upload/source requests fail before spend;
- oversized transcript jobs fail before spend with machine-readable limit errors;
- insufficient credits return HTTP 402 with `upgradePath` and `getE3DUrl` in body;
- duplicate `Idempotency-Key` does not double-spend;
- completed test jobs expose artifacts without arbitrary file read risk;
- capabilities endpoint is self-describing without external documentation and shows `nftMintAvailable: false`;
- OpenAPI, `llms.txt`, and agent-capabilities endpoints are reachable;
- webhook dry-run delivery can be tested locally and failed delivery does not break polling;
- revision jobs preserve parent-child relationship and quote before spend;
- IPFS archive endpoint validates consent, job ownership/auth, and artifact availability;
- `mint-nft` endpoint returns 501 with a clear v1.1 message;
- "Get E3D" URL is confirmed live and documented.

### Phase 3: Cast Worker Wrapper and Job Manifest

Repo:

```text
/home/ubuntu/e3d-pod2vid
```

**v1 tasks:**

- define the worker-facing job manifest format (JSON schema that Phase 2 API writes and the worker reads);
- add a job runner wrapper around existing scripts;
- add dry-run mode that validates inputs and writes a fake artifact manifest;
- support transcript-driven jobs by generating or accepting narration input according to preset;
- support 6 caption/style templates and platform metadata fields in the manifest;
- support end card toggle and watermark-by-tier from brand kit options;
- support revision job modes for thumbnail, metadata/social copy, and subtitle style;
- support IPFS archive manifests with local artifact IDs, CIDs, gateway URLs, checksums, and local retention timestamps;
- support rehydrating archived MP4 artifacts from IPFS/gateway into temp storage for later publishing when local retention has expired;
- add structured progress/status output;
- ensure output paths are deterministic under `CAST_STORAGE_DIR`;
- document required API keys for each preset.

**v1.1 tasks (deferred — do not implement in Phase 3):**

- revision modes for end card regen, B-roll regen, and voice regen;
- brand kit logo upload and primary color rendering;
- 4 visual style presets beyond default;
- output variant generation (up to 3 candidate cuts).

Acceptance:

- dry-run job completes locally without external API calls;
- real render path still supports the existing `pod2vid.py` behavior;
- thumbnail, metadata, and subtitle style revisions complete against a completed dry-run job;
- IPFS archive manifests are written with checksums and local retention timestamps;
- rehydration from IPFS completes when a local MP4 is unavailable;
- worker failure records a clear error code and user-safe message;
- no outputs are written into the git repo by default.

### Phase 4: Hosted UI and Worker Daemon

Repo:

```text
/home/ubuntu/e3d-pod2vid-service
```

Create this repo if it does not exist. It is a new repository — do not add these files to `/home/ubuntu/e3d-pod2vid`.

**v1 tasks:**

Worker daemon (new in `e3d-pod2vid-service`):

- implement a PM2 worker process that polls the job queue from Spacepacket and dispatches jobs;
- shell out to `/home/ubuntu/e3d-pod2vid/bin/pod2vid-job.py <manifest-path>` for each job;
- read structured stdout/manifest output and update job status via the Spacepacket API;
- handle worker errors, timeouts, and unexpected exits cleanly;
- write a `cast-worker` PM2 app entry in `ecosystem.config.js`.

UI (new in `e3d-pod2vid-service`):

- implement the workspace UI;
- implement Upload, Source URL, Transcript, and Sample input modes;
- implement public sample gallery (at least 3 real outputs) and preview frame;
- implement 6 caption/style template selector and preview;
- implement brand kit: end card toggle and watermark display by tier;
- implement tier/limit comparison and remaining free-attempt display;
- implement wallet connection;
- implement holder discount display in quote panel;
- implement quote/purchase/balance/job submission/status/artifact flows;
- implement "Get E3D" button linking to `CAST_GET_E3D_URL`;
- implement "Made with Cast" end card toggle and rebate display;
- implement completed-job artifact viewer with revision actions for thumbnail, metadata, and subtitle style;
- implement IPFS archive panel with consent flow, `ipfs://` URIs, gateway URLs, and archive manifest;
- add agent-mode examples in the UI;
- configure build output for Nginx/static hosting or a Node UI server.

**v1.1 tasks (deferred — do not implement in Phase 4, add to `e3d-pod2vid-service` in Phase 7):**

- NFT provenance panel and mint confirmation flow;
- revision actions for end card, B-roll, and voice;
- brand kit logo upload and primary color controls;
- 4 visual style preset selector;
- output variant selection panel.

Acceptance:

- user can connect wallet and see Cast credit balance and holder discount status;
- user can inspect at least 3 public sample outputs before submitting a job;
- user can preview aspect ratio, caption style, watermark/end card state, and metadata before paid submission;
- user can paste a transcript, see length/limit feedback, quote it (with discount applied), and submit an eligible job;
- new user can run a limited free/sample render without exceeding free-tier caps;
- user can get a quote and register a purchase transaction;
- user can submit a paid dry-run job and see completion;
- user can run quoted thumbnail, metadata, and subtitle style revisions against a completed dry-run job;
- user can archive a completed eligible dry-run job to IPFS and see returned IPFS/gateway URLs;
- UI shows `nftMintAvailable: false` state and does not expose a broken mint flow;
- UI blocks render submission when no credit key/balance is available and shows "Get E3D" path;
- UI blocks or explains jobs that exceed tier artifact/input limits;
- responsive layout works on desktop and mobile.

### Phase 5: `e3d-agent` Cast Support

Repo:

```text
/home/ubuntu/e3d-agent
```

**v1 tasks:**

- add `CastClient`;
- generalize buy-credit logic beyond hardcoded `maps`;
- add `cast` CLI group;
- store and read `E3D_CAST_CREDIT_KEY`;
- add webhook command (`--webhook` flag on render);
- add revision command (`revise`) for thumbnail, metadata, and subtitle style;
- add IPFS archive command (`archive`);
- add examples 08–12 and docs;
- add OpenAPI file;
- add tests for command parsing, quote/purchase product selection, and job client behavior.

**v1.1 tasks (deferred — do not implement in Phase 5):**

- `mint-nft` command and example 13;
- revision commands for end card, B-roll, and voice.

Acceptance:

- `e3d-agent cast buy-credits --amount 1000` quotes `product=cast` and shows holder discount;
- `e3d-agent cast render --dry-run --wait` completes against a local test server/mock;
- `e3d-agent cast archive --job cast_job_...` returns IPFS URIs and archive manifest;
- `e3d-agent cast revise --job cast_job_... --type subtitle_style` completes against a local test server/mock;
- Maps commands continue to work;
- delegated transaction safety checks remain intact;
- examples 08–12 are clean enough to appear in a public README without edits.

### Phase 6: Deployment

Repo:

```text
/home/ubuntu/e3d-pod2vid-service
```

Tasks:

- add deployment documentation;
- add PM2 process definitions;
- add Nginx config notes or script;
- verify HTTPS, proxying, upload limits, and health checks;
- run smoke tests against the deployed domain;
- verify "Get E3D" link from production UI.

Acceptance:

- `https://cast.e3d.ai` loads the UI;
- `https://cast.e3d.ai/api/cast/health` returns healthy;
- a dry-run paid job can be submitted end to end;
- rollback instructions are documented;
- "Get E3D" path works from the production domain.

### Phase 7: v1.1 API — NFT Mint

Repo:

```text
/home/ubuntu/spacepacket/server
```

Do not begin Phases 7–10 until Phase 6 is deployed and v1 is live. Resolve open questions 11 and 12 (NFT mint fee and contract choice) before writing any code in this phase.

**Tasks:**

- update `mint-nft` endpoint from HTTP 501 to full implementation;
- implement ERC-721 metadata construction (no raw transcript text in metadata);
- integrate `E3DNFTManager` for on-chain minting;
- require explicit `confirm: true` in request body for browser callers;
- set `nftMintAvailable: true` in capabilities response;
- add tests for mint auth, metadata content rules, and duplicate mint prevention.

**Acceptance:**

- `POST /api/cast/jobs/:jobId/mint-nft` returns a mint receipt with contract and token ID;
- NFT metadata does not include raw transcript text;
- duplicate mint requests for the same job are rejected or idempotent;
- capabilities response shows `nftMintAvailable: true`;
- existing v1 tests still pass.

### Phase 8: v1.1 Pipeline — Revisions, Styles, Variants

Repo:

```text
/home/ubuntu/e3d-pod2vid
```

**Tasks:**

- implement revision modes for end card regen, B-roll regen, and voice regen in the job runner;
- implement brand kit: logo upload rendering and primary color application in worker output;
- implement 4 visual style presets (editorial, tech, finance, cinematic) for B-roll selection;
- implement output variant generation (up to 3 candidate cuts) for short presets;
- document required API keys for new presets and revision modes.

**Acceptance:**

- revision modes for end card, B-roll, and voice complete against a completed parent job;
- logo upload is stored safely under `CAST_STORAGE_DIR` and rendered into output without arbitrary file read risk;
- visual style presets produce visually distinct B-roll selections;
- output variant jobs produce up to 3 candidate MP4s with a shared parent manifest;
- existing v1 render tests still pass.

### Phase 9: v1.1 Service — NFT UI, Brand Kit, Visual Styles

Repo:

```text
/home/ubuntu/e3d-pod2vid-service
```

**Tasks:**

- implement NFT provenance panel in the Job Detail view with consent flow and public metadata preview before minting;
- implement revision actions for end card, B-roll, and voice in the Job Detail view;
- implement brand kit controls: logo upload and primary color picker;
- implement 4 visual style preset selector;
- implement output variant selection panel for short presets.

**Acceptance:**

- NFT mint flow requires explicit confirmation and shows the metadata that will become public before minting;
- end card, B-roll, and voice revision actions are available on eligible completed jobs;
- logo upload is accepted in the UI and passed to the job options without exposing the file path;
- visual style presets are selectable before submission and reflected in the quote;
- output variant panel shows up to 3 candidate cuts when the job produces them;
- existing v1 UI acceptance criteria still pass.

### Phase 10: v1.1 Agent — NFT Mint Command

Repo:

```text
/home/ubuntu/e3d-agent
```

**Tasks:**

- add `e3d-agent cast mint-nft` command;
- require `--send` and `--yes` flags and delegated-wallet opt-in for headless mint;
- add example 13 (`examples/13-cast-mint-nft.ts`);
- add revision commands for end card, B-roll, and voice to the `revise` subcommand.

**Acceptance:**

- `e3d-agent cast mint-nft --job cast_job_... --send --yes` completes against a test/local contract;
- mint command is rejected without `--send --yes` and explicit delegated-wallet configuration;
- example 13 is clean enough to appear in a public README without edits;
- existing v1 agent tests still pass.

---

## 13. Test Plan

Spacepacket:

```bash
cd /home/ubuntu/spacepacket/server
npm test
```

Cast:

```bash
cd /home/ubuntu/e3d-pod2vid
python3 -m py_compile pod2vid.py tts_replace.py make_short.py signal_short.py
npm test
```

`npm test` may need to be added if no test script exists.

Agent:

```bash
cd /home/ubuntu/e3d-agent
npm test
npm run check
```

Manual smoke:

```bash
curl -f https://cast.e3d.ai/api/cast/health
curl -f https://cast.e3d.ai/api/payments/products
curl -f https://cast.e3d.ai/api/cast/capabilities
curl -f https://cast.e3d.ai/openapi/e3d-cast.yaml
curl -f https://cast.e3d.ai/llms.txt
curl -f https://cast.e3d.ai/.well-known/agent-capabilities.json
```

End-to-end:

- buy or mock Cast credits and verify holder discount is applied;
- run a free/sample render and verify free-attempt accounting and watermark;
- verify public sample outputs exist for transcript, audio, and agent-generated inputs;
- submit a transcript job and verify character limits;
- submit a dry-run job;
- verify one credit spend record including burn amount;
- verify job status reaches `succeeded`;
- verify artifact manifest download includes checksums, byte sizes, content types, and expiration timestamps;
- verify webhook delivery for a dry-run job and fallback polling when webhook delivery fails;
- verify a quoted revision job preserves parent-child relationship and does not require re-upload;
- verify IPFS archive returns `ipfs://` URIs, gateway URLs, checksums, and archive manifest;
- verify `mint-nft` endpoint returns 501 with a v1.1 message (full mint tested in Phase 7);
- verify later publishing can rehydrate from IPFS when the local MP4 is unavailable;
- verify oversized artifacts are rejected or marked failed before unsafe storage/download behavior;
- verify duplicate submission does not double-spend;
- verify "Get E3D" link resolves from both UI and agent 402 error response.

---

## 14. Open Questions

1. Should Cast use the existing Maps treasury addresses for v1, or should it receive a product-specific treasury?
2. What should the first public credit prices be for full video, short video, TTS replacement, and publishing?
3. What is the v1 IPFS provider policy: public Pinata/IPFS, private gateway, or mixed by tier?
4. Should public UI support direct wallet token transfer, or start with quote/register transaction flow plus wallet-provider send?
5. Should publishing to YouTube/social be offered in the hosted UI, agent-only, or operator-only in v1?
6. Which transcript-to-video voices and visual styles should be offered in v1?
7. What is the E3D holder qualification threshold for the 20% discount — any balance, a minimum hold, or time-weighted?
8. Should the 5% burn go to a dead address immediately or accumulate for a periodic burn event?
9. Should the "Made with Cast" rebate require a verified publish URL, or be self-reported?
10. Should IPFS archive be available on Starter, Pro only, or all paid tiers?

The following questions are **v1.1 blockers** and must be resolved before Phase 7 begins. They do not block v1 launch.

11. What is the exact NFT mint fee and should it be charged in E3D credits, wallet transaction cost, or both?
12. Should NFT minting use the existing `E3DNFTManager` for v1.1 or introduce a product-specific Cast collection?

---

## 15. Definition of Done

The feature is done when:

- `cast.e3d.ai` is reachable over HTTPS;
- users can connect a wallet, acquire/use Cast credits (with holder discount), submit a job, and retrieve output artifacts;
- users can create a job from upload, source URL, transcript text, or sample content;
- the free tier is limited by attempts, input size, transcript length, artifact size, duration, retention, and concurrency, and outputs carry a watermark;
- the "Get E3D" path works from the UI and from agent 402 error responses;
- agents can do the same through `e3d-agent` commands without a browser after onboarding;
- agents can discover inputs, presets, artifact schemas, tiers, pricing, holder discount rate, and burn rate through `GET /api/cast/capabilities`;
- agents can discover usage through OpenAPI, `llms.txt`, and `.well-known/agent-capabilities.json`;
- agents can use either webhook callbacks or polling for job completion;
- users and agents can run quoted revision jobs (thumbnail, metadata, subtitle style) against completed parent jobs;
- users can opt into IPFS archive and receive content-addressed artifact references without replacing local render storage;
- `mint-nft` endpoint exists and returns 501 with a clear v1.1 message (full NFT mint ships in Phase 7);
- Cast credits are issued, balanced, and spent through shared E3D Product Payments with holder discount and burn tracking;
- the service can run a dry-run job fully automatically;
- a real render job can run with configured external API keys;
- tests cover payment, idempotency, auth, worker failure, artifact safety, holder discount, and burn accounting;
- docs and agent examples are clean enough to share publicly without edits;
- the primary metric (E3D Token volume consumed per week) can be queried from spend records.

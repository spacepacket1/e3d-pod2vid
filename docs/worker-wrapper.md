# Pod2Vid Worker Wrapper

Phase 3 adds a deterministic worker entrypoint at `bin/pod2vid-job.py` that reads a single job manifest, writes all artifacts under `POD2VID_STORAGE_DIR`, and emits structured JSON status lines on stdout.

## Usage

```bash
python3 bin/pod2vid-job.py /path/to/job-manifest.json
```

Default storage is `/tmp/e3d-pod2vid` when `POD2VID_STORAGE_DIR` is not set.

## Supported presets

| Preset | Input | Output shape | Required API keys |
|---|---|---|---|
| `youtube` | audio upload or resolved URL file | 16:9 MP4 + SRT | `ASSEMBLYAI_API_KEY`, `OPENAI_API_KEY`, `PEXELS_API_KEY` |
| `short` | audio upload or resolved URL file | 9:16 MP4 + SRT | `ASSEMBLYAI_API_KEY`, `OPENAI_API_KEY`, `PEXELS_API_KEY` |
| `tts_video` | transcript or narration input | 16:9 MP4 + SRT | `OPENAI_API_KEY`, `PEXELS_API_KEY` |
| `transcript_video` | transcript or narration input | 16:9 MP4 + SRT | `OPENAI_API_KEY`, `PEXELS_API_KEY` |
| `transcript_short` | transcript or narration input | 9:16 MP4 + SRT | `OPENAI_API_KEY`, `PEXELS_API_KEY` |

Notes:

- `dryRun: true` skips all external API calls and fake-renders a complete artifact set locally.
- Transcript jobs may provide `input.narrationPath` and `input.diarizationPath`; otherwise the worker synthesizes narration with OpenAI TTS.
- Free-tier jobs watermark by default unless `brandKit.watermarkMode` overrides the tier rule.

## Caption and style templates

Supported manifest values for `options.subtitleStyle`:

- `clean_podcast`
- `bold_mobile`
- `finance_signal`
- `developer_demo`
- `news_brief`
- `minimal_subtitles`

`default` is accepted as an alias for `clean_podcast`.

## Revisions

Supported `revision.type` values in Phase 3:

- `thumbnail`
- `metadata`
- `subtitle_style`

Revision jobs are child jobs and must set `parentJobId`.

## IPFS archive and rehydration

- When `options.archiveToIpfs` or `archive.enabled` is true, the worker writes `archive-manifest.json` with local artifact IDs, checksums, CIDs, gateway URLs, and `localRetentionExpiresAt`.
- Archive entries may supply `archive.ipfs.artifacts.<artifactId>.sourcePath`, `ipfsUri`, `cid`, and `gatewayUrl`.
- If a later revision needs the parent MP4 and the local file has expired, the worker attempts to restore it from the archive manifest into `tmp/rehydrated-video.mp4`.

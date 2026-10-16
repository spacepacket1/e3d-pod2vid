# Unified Pod2Vid CLI Entrypoint

## Overview

Add a single executable `pod2vid` command that dispatches the repository’s existing render, Short, signal, upload, and announcement scripts through consistent subcommands. The implementation is a thin Python orchestration layer; existing backend scripts remain independently usable and retain ownership of media generation and external API behavior.

## Goals

- Provide `pod2vid run`, `pod2vid short`, `pod2vid signal`, and `pod2vid announce` subcommands.
- Support a one-command `pod2vid run <audio> --publish` workflow that renders, uploads to YouTube, and announces the resulting URL.
- Provide consistent `--dry-run` and `--json` controls.
- Support `--output-dir` for commands whose existing backends accept an output path.
- Preserve argument boundaries and propagate backend failures with useful diagnostics.
- Add isolated tests that never invoke media tools, networks, or external APIs.

## Non-Goals

- Rewriting or consolidating logic inside `pod2vid.py`, `make_short.py`, `signal_short.py`, `yt_upload.js`, or `announce.js`.
- Changing the hosted worker, job schema, authentication scripts, credentials, or token formats.
- Adding an installable Python package, Node dependency, shell completion, interactive prompts, or configuration files.
- Generating episode metadata, replacing voices, scheduling posts, or changing platform-specific publishing behavior.
- Removing or deprecating any existing script-level command.

## Existing Files

- `pod2vid.py` renders a long-form video from an audio input and optional output path.
- `make_short.py` renders its built-in vertical Short to an optional output path.
- `signal_short.py` supports `--dry-run` and `--force`, with its own fixed output locations.
- `yt_upload.js` accepts a video path, title, and optional description and reports the uploaded URL on an `Uploaded: https://www.youtube.com/watch?v=...` line.
- `announce.js` accepts a YouTube URL and optional custom message.
- `README.md` documents each backend as a separate command.
- `tests/` contains Python tests runnable through the configured repository verification command.

## Shared Constraints

- Keep the complete implementation within four changed files and 600 changed lines.
- Do not modify any existing rendering, publishing, authentication, worker, schema, dependency-lock, or protected file.
- Use only the Python standard library and the repository’s existing Node runtime.
- Build subprocess arguments as lists and never use `shell=True`.
- Resolve backend script paths relative to the CLI module so the command works when invoked outside the repository directory.
- Preserve paths and messages containing spaces as single subprocess arguments.
- Keep existing direct commands fully functional.
- Tests must replace subprocess execution with mocks or injected fakes and must not require credentials, ffmpeg, Node, media files, or network access.
- Never print secrets, environment values, or token-file contents.
- A failed step must prevent every dependent later step from running and must result in a nonzero CLI exit status.
- JSON mode must write exactly one valid JSON document to stdout; human-readable backend output may continue to use stdout and stderr when JSON mode is not selected.

## Phase 1 - Implement and Test the Unified Dispatcher
<!-- runner:model=codex:gpt-5.4-mini -->
<!-- pilot:touches=pod2vid -->
<!-- pilot:touches=pod2vid_cli.py -->
<!-- pilot:touches=tests/test_pod2vid_cli.py -->
<!-- runner:read=pod2vid.py -->
<!-- runner:read=make_short.py -->
<!-- runner:read=signal_short.py -->
<!-- runner:read=yt_upload.js -->
<!-- runner:read=announce.js -->
<!-- runner:verify=python3 -m pytest tests/ -->

### Requirements

- Add an executable top-level `pod2vid` Python launcher that imports and exits through `pod2vid_cli.main()`. Keep the launcher minimal so command behavior remains testable through the module.
- Add `pod2vid_cli.py` with an `argparse`-based interface and these subcommands:

  - `pod2vid run AUDIO`
    - Default output: `output/<audio-stem>.mp4`.
    - `--output-dir DIR` changes the directory while retaining `<audio-stem>.mp4`.
    - `--publish` runs the renderer, then `yt_upload.js`, then `announce.js`.
    - `--title TITLE` controls the YouTube title; default to the audio filename stem with hyphens and underscores converted to spaces.
    - `--description TEXT` supplies the optional YouTube description.
    - `--message TEXT` supplies announcement copy; when absent, invoke `announce.js` with only the uploaded URL so its existing default is retained.
    - Reject `--title`, `--description`, and `--message` unless `--publish` is present.

  - `pod2vid short`
    - Default output: `output/pod2vid-short.mp4`.
    - `--output-dir DIR` changes the directory while retaining `pod2vid-short.mp4`.
    - Dispatch to `make_short.py` with the resolved output path.

  - `pod2vid signal`
    - Accept `--force`.
    - Dispatch to `signal_short.py`, forwarding `--force` when selected.

  - `pod2vid announce URL [MESSAGE]`
    - Dispatch to `announce.js`, preserving the optional message as one argument.

- Support `--dry-run` on every subcommand:

  - For `run`, `short`, and `announce`, print or return the complete ordered execution plan without starting any subprocess.
  - For `signal`, preserve the existing useful semantics by executing `signal_short.py --dry-run`; also forward `--force` when requested.
  - A dry-run `run --publish` plan must include render, upload, and announce steps, with the announce step identifying that its URL comes from the upload result rather than fabricating a URL.

- Support `--json` on every subcommand:

  - Emit one JSON object containing `command`, `ok`, `dryRun`, and an ordered `steps` array.
  - Each completed step must include its stable name, argument vector, and return code.
  - A failed step must include captured stderr or a concise error string.
  - Successful `run` and `short` results must identify the planned output path.
  - A successful published `run` must include the parsed `videoUrl`.
  - Dry-run step entries must be marked as planned and must not claim execution occurred.

- Execute Python backends with the current Python interpreter and JavaScript backends with `node`.
- Run subprocesses from the repository directory while leaving the caller’s current directory unchanged.
- In human-readable mode, relay captured backend stdout and stderr in step order.
- Parse the YouTube URL only from the uploader’s documented `Uploaded:` line. If upload exits successfully without that line, treat the upload as failed and do not announce.
- Return the first failing backend’s nonzero status when available; otherwise return a stable nonzero wrapper error status.
- Handle `KeyboardInterrupt` without a traceback and return a conventional interrupted status.
- Add `tests/test_pod2vid_cli.py` covering:

  - Parser help and rejection of unknown subcommands or invalid publish-only options.
  - Exact renderer, Short, signal, uploader, and announcer argument vectors.
  - Default and custom output directories, including paths containing spaces.
  - Dry-run behavior and the special forwarded signal dry run.
  - JSON output validity and required fields.
  - Human-readable output forwarding.
  - Successful render/upload/announce ordering and URL extraction.
  - Default versus explicit title, description, and announcement message behavior.
  - Short-circuiting after render or upload failure.
  - Successful upload output that lacks an `Uploaded:` URL.
  - Exit-code propagation and interrupt handling.
  - Launcher existence and executable intent without invoking its backends.

### Acceptance Criteria

- `./pod2vid --help` lists all four subcommands.
- `./pod2vid run episode.m4a --dry-run` plans `pod2vid.py episode.m4a output/episode.mp4` without executing it.
- `./pod2vid short --output-dir "demo output" --dry-run --json` emits one valid JSON document whose output is `demo output/pod2vid-short.mp4`.
- `./pod2vid signal --dry-run --force` invokes `signal_short.py` with both backend flags.
- `./pod2vid announce URL "custom message" --dry-run` preserves the message as one argument and starts no subprocess.
- `./pod2vid run episode.m4a --publish` executes render, upload, and announce in that order and passes the uploader’s reported URL to the announcer.
- No announcement occurs when rendering fails, uploading fails, or the uploader does not report a parseable `Uploaded:` URL.
- Unit tests exercise all dispatch and orchestration behavior without performing external work.
- `python -m pytest tests/` passes.

## Phase 2 - Document the Happy Path and Compatibility
<!-- runner:model=codex:gpt-5.4-mini -->
<!-- pilot:touches=README.md -->
<!-- runner:read=pod2vid_cli.py -->
<!-- runner:verify=python3 -m pytest tests/ -->

### Requirements

- Update `README.md` with a concise unified CLI section near Quick Start.
- Document executable usage for:

  - Rendering an episode.
  - Rendering into a custom output directory.
  - Rendering, uploading, and announcing with `--publish`.
  - Generating the built-in Short.
  - Generating a signal Short with `--dry-run` and `--force`.
  - Announcing an existing YouTube URL.
  - Previewing commands with `--dry-run`.
  - Receiving machine-readable results with `--json`.

- Clearly explain that `signal --dry-run` retains `signal_short.py` semantics: it may fetch signals and generate copy but skips render and publication. Explain that dry runs for the other subcommands are execution-plan-only.
- Document the default output filenames and the title derived by `run --publish` when `--title` is omitted.
- State that the existing individual Python and Node commands remain supported for advanced or script-specific use.
- Keep existing detailed workflow and credential documentation; avoid duplicating credential tables or changing setup instructions unrelated to the dispatcher.
- Ensure every documented command matches the implemented parser exactly.

### Acceptance Criteria

- A new user can identify one command for render-only and one command for render-plus-publish without consulting individual backend sections.
- The documentation accurately describes `--output-dir`, `--dry-run`, `--json`, `--publish`, and signal dry-run behavior.
- Existing backend documentation remains present and is framed as the advanced/direct interface.
- No protected path or backend implementation is changed in this phase.
- `python -m pytest tests/` passes.

#!/usr/bin/env python3
"""Unified pod2vid command-line dispatcher."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable or "python3"
NODE = "node"
WRAPPER_ERROR = 1
INTERRUPTED = 130


def backend_path(name: str) -> str:
    return str(REPO_ROOT / name)


def default_title(audio: str) -> str:
    return Path(audio).stem.replace("-", " ").replace("_", " ")


def output_for(audio: str, output_dir: str | None) -> str:
    target_dir = Path(output_dir) if output_dir else Path("output")
    return str(target_dir / f"{Path(audio).stem}.mp4")


def short_output(output_dir: str | None) -> str:
    target_dir = Path(output_dir) if output_dir else Path("output")
    return str(target_dir / "pod2vid-short.mp4")


def uploaded_url(stdout: str) -> str | None:
    pattern = re.compile(r"^Uploaded:\s+(https://www\.youtube\.com/watch\?v=\S+)\s*$")
    for line in stdout.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    return None


@dataclass
class StepResult:
    name: str
    argv: list[str]
    planned: bool = False
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    output_path: str | None = None
    video_url: str | None = None
    url_source: str | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "argv": self.argv,
            "planned": self.planned,
            "returnCode": self.return_code,
        }
        if self.stdout:
            payload["stdout"] = self.stdout
        if self.stderr:
            payload["stderr"] = self.stderr
        if self.error:
            payload["error"] = self.error
        if self.output_path:
            payload["outputPath"] = self.output_path
        if self.video_url:
            payload["videoUrl"] = self.video_url
        if self.url_source:
            payload["urlSource"] = self.url_source
        return payload


def run_subprocess(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def emit_human_step(step: StepResult) -> None:
    print(f"[{step.name}] {' '.join(step.argv)}")
    if step.stdout:
        sys.stdout.write(step.stdout)
        if not step.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if step.stderr:
        sys.stderr.write(step.stderr)
        if not step.stderr.endswith("\n"):
            sys.stderr.write("\n")


def emit_plan(steps: list[StepResult]) -> None:
    print("Planned execution:")
    for step in steps:
        if step.url_source:
            print(f"[plan] {step.name}: {' '.join(step.argv)} ({step.url_source})")
        elif step.output_path:
            print(f"[plan] {step.name}: {' '.join(step.argv)} -> {step.output_path}")
        else:
            print(f"[plan] {step.name}: {' '.join(step.argv)}")


def run_step(name: str, argv: list[str]) -> StepResult:
    try:
        completed = run_subprocess(argv)
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        return StepResult(name=name, argv=argv, stderr=str(exc), error=str(exc))
    return StepResult(
        name=name,
        argv=argv,
        return_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def render_step(audio: str, output_path: str) -> StepResult:
    argv = [PYTHON, backend_path("pod2vid.py"), audio, output_path]
    step = StepResult(name="render", argv=argv, output_path=output_path)
    return step


def short_step(output_path: str) -> StepResult:
    argv = [PYTHON, backend_path("make_short.py"), output_path]
    return StepResult(name="short", argv=argv, output_path=output_path)


def signal_step(force: bool, dry_run: bool) -> StepResult:
    argv = [PYTHON, backend_path("signal_short.py")]
    if dry_run:
        argv.append("--dry-run")
    if force:
        argv.append("--force")
    return StepResult(name="signal", argv=argv)


def announce_step(url: str, message: str | None) -> StepResult:
    argv = [NODE, backend_path("announce.js"), url]
    if message is not None:
        argv.append(message)
    return StepResult(name="announce", argv=argv)


def upload_step(video_path: str, title: str, description: str | None) -> StepResult:
    argv = [NODE, backend_path("yt_upload.js"), video_path, title]
    if description is not None:
        argv.append(description)
    return StepResult(name="upload", argv=argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pod2vid")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_flags(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--dry-run", action="store_true")
        subparser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser("run", help="Render an audio file")
    run_parser.add_argument("audio")
    run_parser.add_argument("--output-dir")
    run_parser.add_argument("--publish", action="store_true")
    run_parser.add_argument("--title")
    run_parser.add_argument("--description")
    run_parser.add_argument("--message")
    add_common_flags(run_parser)

    short_parser = subparsers.add_parser("short", help="Render the built-in Short")
    short_parser.add_argument("--output-dir")
    add_common_flags(short_parser)

    signal_parser = subparsers.add_parser("signal", help="Render the signal Short")
    signal_parser.add_argument("--force", action="store_true")
    add_common_flags(signal_parser)

    announce_parser = subparsers.add_parser("announce", help="Announce an existing URL")
    announce_parser.add_argument("url")
    announce_parser.add_argument("message", nargs="?")
    add_common_flags(announce_parser)
    return parser


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.command == "run" and not args.publish:
        if args.title is not None or args.description is not None or args.message is not None:
            parser.error("--title, --description, and --message require --publish")


def dry_run_payload(command: str, steps: list[StepResult], output_path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "ok": True,
        "dryRun": True,
        "steps": [replace(step, planned=True, return_code=None).to_json() for step in steps],
    }
    if output_path:
        payload["outputPath"] = output_path
    return payload


def json_payload(command: str, ok: bool, dry_run: bool, steps: list[StepResult], output_path: str | None = None, video_url: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "ok": ok,
        "dryRun": dry_run,
        "steps": [step.to_json() for step in steps],
    }
    if output_path:
        payload["outputPath"] = output_path
    if video_url:
        payload["videoUrl"] = video_url
    return payload


def execute_run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[int, dict[str, Any] | None]:
    output_path = output_for(args.audio, args.output_dir)
    planned = [render_step(args.audio, output_path)]

    if args.publish:
        planned.append(upload_step(output_path, args.title or default_title(args.audio), args.description))
        announce_message = args.message
        announce_placeholder = announce_step("<video-url-from-upload>", announce_message)
        announce_placeholder.url_source = "upload result"
        planned.append(announce_placeholder)

    if args.dry_run:
        if not args.json:
            emit_plan(planned)
        return 0, dry_run_payload("run", planned, output_path)

    render = run_step("render", planned[0].argv)
    if not args.json:
        emit_human_step(render)
    if render.return_code != 0:
        return render.return_code or WRAPPER_ERROR, json_payload("run", False, False, [render], output_path=output_path)

    steps: list[StepResult] = [render]
    video_url: str | None = None

    if args.publish:
        upload = run_step("upload", planned[1].argv)
        steps.append(upload)
        if not args.json:
            emit_human_step(upload)
        if upload.return_code != 0:
            return upload.return_code or WRAPPER_ERROR, json_payload("run", False, False, steps, output_path=output_path)

        video_url = uploaded_url(upload.stdout)
        if not video_url:
            if not args.json:
                sys.stderr.write("upload completed without a parseable Uploaded: URL\n")
            failure = StepResult(
                name="upload",
                argv=planned[1].argv,
                return_code=upload.return_code,
                stdout=upload.stdout,
                stderr=upload.stderr,
                error="upload completed without a parseable Uploaded: URL",
            )
            return WRAPPER_ERROR, json_payload("run", False, False, [render, failure], output_path=output_path)

        announce = run_step("announce", [NODE, backend_path("announce.js"), video_url] + ([args.message] if args.message is not None else []))
        steps.append(announce)
        if not args.json:
            emit_human_step(announce)
        if announce.return_code != 0:
            return announce.return_code or WRAPPER_ERROR, json_payload("run", False, False, steps, output_path=output_path, video_url=video_url)

        payload = json_payload("run", True, False, steps, output_path=output_path, video_url=video_url)
        return 0, payload

    payload = json_payload("run", True, False, steps, output_path=output_path)
    return 0, payload


def execute_short(args: argparse.Namespace) -> tuple[int, dict[str, Any] | None]:
    output_path = short_output(args.output_dir)
    step = short_step(output_path)
    if args.dry_run:
        if not args.json:
            emit_plan([step])
        return 0, dry_run_payload("short", [step], output_path)
    executed = run_step(step.name, step.argv)
    if not args.json:
        emit_human_step(executed)
    ok = executed.return_code == 0
    payload = json_payload("short", ok, False, [executed], output_path=output_path)
    return (0 if ok else executed.return_code or WRAPPER_ERROR), payload


def execute_signal(args: argparse.Namespace) -> tuple[int, dict[str, Any] | None]:
    step = signal_step(args.force, args.dry_run)
    executed = run_step(step.name, step.argv)
    if not args.json:
        emit_human_step(executed)
    ok = executed.return_code == 0
    payload = json_payload("signal", ok, args.dry_run, [executed])
    return (0 if ok else executed.return_code or WRAPPER_ERROR), payload


def execute_announce(args: argparse.Namespace) -> tuple[int, dict[str, Any] | None]:
    step = announce_step(args.url, args.message)
    if args.dry_run:
        if not args.json:
            emit_plan([step])
        return 0, dry_run_payload("announce", [step])
    executed = run_step(step.name, step.argv)
    if not args.json:
        emit_human_step(executed)
    ok = executed.return_code == 0
    payload = json_payload("announce", ok, False, [executed])
    return (0 if ok else executed.return_code or WRAPPER_ERROR), payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        validate_args(args, parser)

        if args.command == "run":
            code, payload = execute_run(args, parser)
        elif args.command == "short":
            code, payload = execute_short(args)
        elif args.command == "signal":
            code, payload = execute_signal(args)
        elif args.command == "announce":
            code, payload = execute_announce(args)
        else:  # pragma: no cover - argparse enforces
            parser.error(f"unknown command: {args.command}")

        if args.json and payload is not None:
            print(json.dumps(payload))
        return code
    except KeyboardInterrupt:
        return INTERRUPTED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Worker wrapper for hosted Pod2Vid jobs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


SCHEMA_VERSION = "1.0"
DEFAULT_STORAGE_DIR = Path(tempfile.gettempdir()) / "e3d-pod2vid"
STYLE_TEMPLATES = {
    "default": "clean_podcast",
    "clean_podcast": "clean_podcast",
    "bold_mobile": "bold_mobile",
    "finance_signal": "finance_signal",
    "developer_demo": "developer_demo",
    "news_brief": "news_brief",
    "minimal_subtitles": "minimal_subtitles",
}
PRESETS = {
    "youtube": {
        "kind": "audio",
        "aspect": "16:9",
        "video_size": (1920, 1080),
        "required_keys": ["ASSEMBLYAI_API_KEY", "OPENAI_API_KEY", "PEXELS_API_KEY"],
    },
    "short": {
        "kind": "audio",
        "aspect": "9:16",
        "video_size": (1080, 1920),
        "required_keys": ["ASSEMBLYAI_API_KEY", "OPENAI_API_KEY", "PEXELS_API_KEY"],
    },
    "tts_video": {
        "kind": "transcript",
        "aspect": "16:9",
        "video_size": (1920, 1080),
        "required_keys": ["OPENAI_API_KEY", "PEXELS_API_KEY"],
    },
    "transcript_video": {
        "kind": "transcript",
        "aspect": "16:9",
        "video_size": (1920, 1080),
        "required_keys": ["OPENAI_API_KEY", "PEXELS_API_KEY"],
    },
    "transcript_short": {
        "kind": "transcript",
        "aspect": "9:16",
        "video_size": (1080, 1920),
        "required_keys": ["OPENAI_API_KEY", "PEXELS_API_KEY"],
    },
}
REVISION_TYPES = {"thumbnail", "metadata", "subtitle_style"}
SAFE_ERROR_MESSAGES = {
    "ERR_MANIFEST_VALIDATION": "The job manifest is invalid.",
    "ERR_ENV_MISSING": "The worker is missing required API keys or binaries.",
    "ERR_INPUT_MISSING": "The job input could not be resolved.",
    "ERR_PARENT_JOB_MISSING": "The requested parent job is unavailable.",
    "ERR_REHYDRATE_FAILED": "Archived media could not be restored.",
    "ERR_RENDER_FAILED": "The video render failed.",
    "ERR_REVISION_FAILED": "The requested revision failed.",
}


class WorkerError(RuntimeError):
    def __init__(self, code: str, detail: str, safe_message: str | None = None):
        self.code = code
        self.safe_message = safe_message or SAFE_ERROR_MESSAGES.get(code, "The worker job failed.")
        super().__init__(detail)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit(event: str, **payload: Any) -> None:
    message = {"event": event, "timestamp": utc_now(), **payload}
    print(json.dumps(message, sort_keys=True), flush=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_label_png(path: Path, title: str, subtitle: str, size: tuple[int, int] = (1280, 720)) -> None:
    ensure_parent(path)
    width, height = size
    image = Image.new("RGB", size, "#101820")
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (14, height)], fill="#00C2FF")
    title_font = load_font(58)
    sub_font = load_font(28)
    draw.text((60, 180), title, font=title_font, fill="#FFFFFF")
    wrapped = textwrap.wrap(subtitle, width=42)[:4]
    for index, line in enumerate(wrapped):
        draw.text((60, 290 + index * 40), line, font=sub_font, fill="#8FDBFF")
    image.save(path)


def write_text_file(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content)


def retention_expires_at(manifest: dict[str, Any]) -> str:
    if manifest.get("retention", {}).get("expiresAt"):
        return manifest["retention"]["expiresAt"]
    hours = manifest.get("retentionHours")
    if hours is None:
        hours = manifest.get("retention", {}).get("hours", 24)
    expiry = datetime.now(timezone.utc) + timedelta(hours=int(hours))
    return expiry.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def storage_root(manifest: dict[str, Any]) -> Path:
    explicit = manifest.get("storage", {}).get("rootDir") or os.environ.get("POD2VID_STORAGE_DIR")
    return Path(explicit or DEFAULT_STORAGE_DIR).resolve()


def job_root(manifest: dict[str, Any]) -> Path:
    return storage_root(manifest) / "jobs" / manifest.get("jobId", "invalid-job")


def job_paths(manifest: dict[str, Any]) -> dict[str, Path]:
    root = job_root(manifest)
    return {
        "root": root,
        "artifacts": root / "artifacts",
        "work": root / "work",
        "temp": root / "tmp",
        "manifest": root / "job-manifest.json",
        "result": root / "result.json",
        "artifact_manifest": root / "artifact-manifest.json",
        "archive_manifest": root / "archive-manifest.json",
        "rehydrated": root / "tmp" / "rehydrated-video.mp4",
    }


@dataclass
class ArtifactRecord:
    artifact_id: str
    type: str
    content_type: str
    path: Path
    expires_at: str
    source: str = "local"
    ipfs_uri: str | None = None
    gateway_url: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "artifactId": self.artifact_id,
            "type": self.type,
            "contentType": self.content_type,
            "path": str(self.path),
            "bytes": self.path.stat().st_size,
            "sha256": sha256_file(self.path),
            "expiresAt": self.expires_at,
            "source": self.source,
        }
        if self.ipfs_uri:
            payload["ipfsUri"] = self.ipfs_uri
        if self.gateway_url:
            payload["gatewayUrl"] = self.gateway_url
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


def preset_config(preset: str) -> dict[str, Any]:
    config = PRESETS.get(preset)
    if not config:
        raise WorkerError("ERR_MANIFEST_VALIDATION", f"Unsupported preset: {preset}")
    return config


def normalize_style(style: str | None) -> str:
    return STYLE_TEMPLATES.get(style or "default", "")


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = ["kind", "version", "jobId", "mode", "preset", "tier", "options"]
    missing = [field for field in required if field not in manifest]
    if missing:
        raise WorkerError("ERR_MANIFEST_VALIDATION", f"Missing fields: {', '.join(missing)}")
    if manifest["kind"] != "cast_job":
        raise WorkerError("ERR_MANIFEST_VALIDATION", f"Unsupported kind: {manifest['kind']}")
    if str(manifest["version"]) != SCHEMA_VERSION:
        raise WorkerError("ERR_MANIFEST_VALIDATION", f"Unsupported version: {manifest['version']}")
    if manifest["mode"] not in {"render", "revision"}:
        raise WorkerError("ERR_MANIFEST_VALIDATION", f"Unsupported mode: {manifest['mode']}")
    preset_config(manifest["preset"])
    style = normalize_style(manifest["options"].get("subtitleStyle"))
    if not style:
        raise WorkerError("ERR_MANIFEST_VALIDATION", "Unsupported subtitle style template")
    if manifest["mode"] == "render":
        input_payload = manifest.get("input") or {}
        if input_payload.get("kind") not in {"upload", "url", "transcript"}:
            raise WorkerError("ERR_MANIFEST_VALIDATION", "Render jobs require input.kind")
        if input_payload["kind"] == "transcript" and not input_payload.get("text"):
            raise WorkerError("ERR_MANIFEST_VALIDATION", "Transcript jobs require input.text")
    else:
        revision = manifest.get("revision") or {}
        if revision.get("type") not in REVISION_TYPES:
            raise WorkerError("ERR_MANIFEST_VALIDATION", "Unsupported revision type")
        if not manifest.get("parentJobId"):
            raise WorkerError("ERR_MANIFEST_VALIDATION", "Revision jobs require parentJobId")


def resolve_required_env(manifest: dict[str, Any]) -> list[str]:
    if manifest.get("dryRun"):
        return []
    if manifest.get("mode") == "revision":
        return []
    preset = preset_config(manifest["preset"])
    needed = list(preset["required_keys"])
    if manifest.get("mode") == "render" and manifest.get("input", {}).get("kind") in {"upload", "url"}:
        if "ASSEMBLYAI_API_KEY" not in needed:
            needed.append("ASSEMBLYAI_API_KEY")
    return needed


def validate_environment(manifest: dict[str, Any]) -> None:
    missing = [key for key in resolve_required_env(manifest) if not os.environ.get(key)]
    if missing:
        raise WorkerError("ERR_ENV_MISSING", f"Missing environment variables: {', '.join(missing)}")
    ffmpeg = shutil.which(os.environ.get("FFMPEG_PATH", "ffmpeg"))
    ffprobe = shutil.which(os.environ.get("FFPROBE_PATH", "ffprobe"))
    if not manifest.get("dryRun") and (not ffmpeg or not ffprobe):
        raise WorkerError("ERR_ENV_MISSING", "ffmpeg and ffprobe are required")


def copy_manifest_into_job(manifest: dict[str, Any], paths: dict[str, Path]) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["artifacts"].mkdir(parents=True, exist_ok=True)
    paths["work"].mkdir(parents=True, exist_ok=True)
    paths["temp"].mkdir(parents=True, exist_ok=True)
    write_json(paths["manifest"], manifest)


def create_metadata_payload(manifest: dict[str, Any], title: str | None = None) -> dict[str, Any]:
    input_payload = manifest.get("input") or {}
    requested = manifest.get("platformMetadata") or {}
    base_title = title or requested.get("title") or manifest.get("title") or f"Pod2Vid {manifest['jobId']}"
    transcript = input_payload.get("text", "")
    summary = " ".join(transcript.split())[:180] if transcript else f"Generated from {input_payload.get('kind', 'audio')} input."
    tags = requested.get("tags") or ["pod2vid", manifest["preset"], manifest["tier"]]
    return {
        "title": base_title,
        "description": requested.get("description") or summary,
        "tags": tags,
        "chapters": requested.get("chapters") or [],
        "platforms": requested.get("platforms") or ["youtube"],
        "subtitleStyle": normalize_style(manifest["options"].get("subtitleStyle")),
        "brandEndCard": bool((manifest.get("brandKit") or {}).get("endCard", manifest["options"].get("brandEndCard", True))),
        "watermarkEnabled": watermark_enabled(manifest),
    }


def create_social_copy_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    title = metadata["title"]
    description = metadata["description"]
    return {
        "youtube": {"title": title, "description": description, "tags": metadata["tags"]},
        "x": f"{title}\n\n{description[:180]}",
        "linkedin": f"{title}\n\n{description}",
        "telegram": title,
    }


def watermark_enabled(manifest: dict[str, Any]) -> bool:
    brand_kit = manifest.get("brandKit") or {}
    mode = brand_kit.get("watermarkMode", "tier_default")
    if mode == "force_on":
        return True
    if mode == "force_off":
        return False
    return str(manifest.get("tier", "")).lower() == "free"


def build_artifact(
    manifest: dict[str, Any],
    artifact_id: str,
    path: Path,
    type_name: str,
    content_type: str,
    *,
    source: str = "local",
    ipfs_uri: str | None = None,
    gateway_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ArtifactRecord(
        artifact_id=artifact_id,
        type=type_name,
        content_type=content_type,
        path=path,
        expires_at=retention_expires_at(manifest),
        source=source,
        ipfs_uri=ipfs_uri,
        gateway_url=gateway_url,
        metadata=metadata,
    ).to_dict()


def write_fake_video(path: Path, label: str) -> None:
    ensure_parent(path)
    path.write_bytes(f"FAKE-MP4:{label}\n".encode())


def write_fake_srt(path: Path, text: str) -> None:
    lines = [
        "1",
        "00:00:00,000 --> 00:00:04,000",
        text[:160] or "Pod2Vid dry-run output.",
        "",
    ]
    write_text_file(path, "\n".join(lines))


def alias_cid(value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()[:32]
    return f"bafy{digest}"


def archive_targets(manifest: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    provided = (((manifest.get("archive") or {}).get("ipfs") or {}).get("artifacts")) or {}
    gateway_base = ((manifest.get("archive") or {}).get("ipfs") or {}).get("gatewayBaseUrl", "https://gateway.example.invalid/ipfs").rstrip("/")
    targets: dict[str, dict[str, str]] = {}
    for artifact in artifacts:
        artifact_id = artifact["artifactId"]
        entry = provided.get(artifact_id) or {}
        cid = entry.get("cid") or alias_cid(f"{manifest['jobId']}:{artifact_id}:{artifact['sha256']}")
        ipfs_uri = entry.get("ipfsUri") or f"ipfs://{cid}"
        gateway_url = entry.get("gatewayUrl") or f"{gateway_base}/{cid}"
        targets[artifact_id] = {"cid": cid, "ipfsUri": ipfs_uri, "gatewayUrl": gateway_url}
    return targets


def write_archive_manifest(manifest: dict[str, Any], paths: dict[str, Path], artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    archive_enabled = bool(manifest["options"].get("archiveToIpfs") or (manifest.get("archive") or {}).get("enabled"))
    if not archive_enabled:
        return None
    targets = archive_targets(manifest, [a for a in artifacts if a["artifactId"] in {"video", "thumbnail", "captions", "metadata", "social_copy", "job_manifest"}])
    provided = (((manifest.get("archive") or {}).get("ipfs") or {}).get("artifacts")) or {}
    payload = {
        "kind": "pod2vid_archive",
        "jobId": manifest["jobId"],
        "createdAt": utc_now(),
        "localRetentionExpiresAt": retention_expires_at(manifest),
        "artifacts": [
            {
                "artifactId": artifact["artifactId"],
                "type": artifact["type"],
                "contentType": artifact["contentType"],
                "bytes": artifact["bytes"],
                "sha256": artifact["sha256"],
                "cid": targets[artifact["artifactId"]]["cid"],
                "ipfsUri": targets[artifact["artifactId"]]["ipfsUri"],
                "gatewayUrl": targets[artifact["artifactId"]]["gatewayUrl"],
                "sourcePath": (provided.get(artifact["artifactId"]) or {}).get("sourcePath"),
            }
            for artifact in artifacts
            if artifact["artifactId"] in targets
        ],
        "ipfs": {artifact_id: details["ipfsUri"] for artifact_id, details in targets.items()},
        "gatewayUrls": {artifact_id: details["gatewayUrl"] for artifact_id, details in targets.items()},
    }
    write_json(paths["archive_manifest"], payload)
    return payload


def render_transcript_audio(manifest: dict[str, Any], paths: dict[str, Path]) -> tuple[Path, Path]:
    transcript = manifest["input"]["text"]
    narration_path = paths["artifacts"] / "narration.mp3"
    diarization_path = paths["artifacts"] / "narration-diarization.json"
    provided_narration = manifest["input"].get("narrationPath")
    provided_diarization = manifest["input"].get("diarizationPath")
    if provided_narration:
        source = Path(provided_narration).resolve()
        if not source.exists():
            raise WorkerError("ERR_INPUT_MISSING", f"Narration input not found: {source}")
        shutil.copy2(source, narration_path)
        if provided_diarization:
            diar_source = Path(provided_diarization).resolve()
            if diar_source.exists():
                shutil.copy2(diar_source, diarization_path)
        if diarization_path.exists():
            return narration_path, diarization_path
    voice = manifest["options"].get("voicePreset", "alloy")
    ffprobe = os.environ.get("FFPROBE_PATH", "ffprobe")
    ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    segments = parse_transcript_segments(transcript)
    if not segments:
        raise WorkerError("ERR_INPUT_MISSING", "Transcript text produced no narration segments")
    tts_dir = paths["work"] / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    silence_path = tts_dir / "silence.mp3"
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.35", "-c:a", "libmp3lame", "-b:a", "64k", str(silence_path)],
        check=True,
    )
    rendered_segments: list[tuple[dict[str, str], Path]] = []
    for index, segment in enumerate(segments):
        out_path = tts_dir / f"segment-{index:03d}.mp3"
        synthesize_tts(segment["text"], voice, out_path, openai_key)
        rendered_segments.append((segment, out_path))
    concat_list = tts_dir / "concat.txt"
    with concat_list.open("w") as handle:
        for _, clip in rendered_segments:
            handle.write(f"file '{clip}'\n")
            handle.write(f"file '{silence_path}'\n")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(narration_path)], check=True)
    cursor = 0
    utterances = []
    for segment, clip in rendered_segments:
        probe = subprocess.run([ffprobe, "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)], capture_output=True, text=True, check=True)
        duration_ms = int(float(probe.stdout.strip()) * 1000)
        utterances.append({"speaker": segment["speaker"], "text": segment["text"], "start": cursor, "end": cursor + duration_ms})
        cursor += duration_ms + 350
    write_json(diarization_path, {"utterances": utterances})
    return narration_path, diarization_path


def synthesize_tts(text: str, voice: str, out_path: Path, openai_key: str) -> None:
    payload = json.dumps({"model": "tts-1-hd", "input": text, "voice": voice, "response_format": "mp3"}).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=payload,
        headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response, out_path.open("wb") as handle:
        handle.write(response.read())


def parse_transcript_segments(text: str) -> list[dict[str, str]]:
    segments = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            speaker_label, content = line.split(":", 1)
            speaker = "A" if speaker_label.lower().startswith(("speaker 1", "host", "a")) else "B"
            segments.append({"speaker": speaker, "text": content.strip()})
        else:
            segments.append({"speaker": "A", "text": line})
    return segments


def resolve_audio_input(manifest: dict[str, Any], paths: dict[str, Path]) -> tuple[Path, Path | None]:
    input_payload = manifest["input"]
    if input_payload["kind"] == "transcript":
        return render_transcript_audio(manifest, paths)
    local_path = input_payload.get("resolvedPath") or input_payload.get("path")
    if not local_path:
        raise WorkerError("ERR_INPUT_MISSING", "Audio jobs require input.path or input.resolvedPath")
    source_path = Path(local_path).resolve()
    if not source_path.exists():
        raise WorkerError("ERR_INPUT_MISSING", f"Input file not found: {source_path}")
    target_name = source_path.name
    target_path = paths["work"] / target_name
    shutil.copy2(source_path, target_path)
    diarization_path = None
    provided_diar = input_payload.get("diarizationPath")
    if provided_diar:
        diar_source = Path(provided_diar).resolve()
        diarization_path = paths["work"] / f"{target_path.stem}-diarization.json"
        shutil.copy2(diar_source, diarization_path)
    return target_path, diarization_path


def run_subprocess(command: list[str], *, env: dict[str, str]) -> None:
    emit("job.progress", phase="subprocess", detail=" ".join(command))
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise WorkerError("ERR_RENDER_FAILED", result.stderr.strip() or result.stdout.strip() or "subprocess failed")


def apply_branding(manifest: dict[str, Any], video_path: Path, paths: dict[str, Path]) -> Path:
    ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
    end_card_enabled = bool((manifest.get("brandKit") or {}).get("endCard", manifest["options"].get("brandEndCard", True)))
    watermark = watermark_enabled(manifest)
    if not end_card_enabled and not watermark:
        return video_path
    branded = paths["artifacts"] / "video.mp4"
    if end_card_enabled:
        end_card = paths["work"] / "end-card.png"
        render_label_png(end_card, "Made with Pod2Vid", manifest.get("brandKit", {}).get("tagline", "pod2vid.e3d.ai"), size=(1280, 720))
        list_file = paths["work"] / "brand-concat.txt"
        end_card_clip = paths["work"] / "end-card.mp4"
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", str(end_card), "-t", "2.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(end_card_clip)], check=True)
        source_for_concat = paths["work"] / "watermarked.mp4" if watermark else video_path
        if watermark:
            overlay_watermark(manifest, video_path, source_for_concat)
        with list_file.open("w") as handle:
            handle.write(f"file '{source_for_concat}'\n")
            handle.write(f"file '{end_card_clip}'\n")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(branded)], check=True)
        return branded
    overlay_watermark(manifest, video_path, branded)
    return branded


def overlay_watermark(manifest: dict[str, Any], source: Path, destination: Path) -> None:
    ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
    label = (manifest.get("brandKit") or {}).get("watermarkText") or "pod2vid.e3d.ai"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            f"drawtext=text='{label}':fontcolor=white@0.7:fontsize=28:x=w-tw-24:y=h-th-24:box=1:boxcolor=black@0.25",
            "-codec:a",
            "copy",
            str(destination),
        ],
        check=True,
    )


def render_thumbnail(manifest: dict[str, Any], paths: dict[str, Path], title: str) -> Path:
    thumbnail_path = paths["artifacts"] / "thumbnail.png"
    command = [sys.executable, str((Path(__file__).resolve().parent / "make_thumbnail.py")), title, str(thumbnail_path)]
    run_subprocess(command, env=os.environ.copy())
    return thumbnail_path


def render_job(manifest: dict[str, Any], paths: dict[str, Path]) -> list[dict[str, Any]]:
    emit("job.progress", phase="render", detail="Preparing input")
    audio_path, diarization_path = resolve_audio_input(manifest, paths)
    config = preset_config(manifest["preset"])
    env = os.environ.copy()
    env["VIDEO_WIDTH"] = str(config["video_size"][0])
    env["VIDEO_HEIGHT"] = str(config["video_size"][1])
    output_path = paths["work"] / "pipeline-output.mp4"
    if diarization_path:
        shutil.copy2(diarization_path, output_path.parent / f"{audio_path.stem}-diarization.json")
    emit("job.progress", phase="render", detail="Running pod2vid.py")
    run_subprocess([sys.executable, str((Path(__file__).resolve().parent / "pod2vid.py")), str(audio_path), str(output_path)], env=env)
    branded_video = apply_branding(manifest, output_path, paths)
    if branded_video != paths["artifacts"] / "video.mp4":
        shutil.copy2(branded_video, paths["artifacts"] / "video.mp4")
    captions_src = output_path.with_suffix(".srt")
    captions_dst = paths["artifacts"] / "captions.srt"
    shutil.copy2(captions_src, captions_dst)
    artifacts = [
        build_artifact(manifest, "video", paths["artifacts"] / "video.mp4", "mp4", "video/mp4"),
        build_artifact(manifest, "captions", captions_dst, "srt", "application/x-subrip"),
    ]
    transcript_text = manifest.get("input", {}).get("text")
    if transcript_text:
        transcript_path = paths["artifacts"] / "source-transcript.txt"
        write_text_file(transcript_path, transcript_text)
        artifacts.append(build_artifact(manifest, "source_transcript", transcript_path, "transcript", "text/plain"))
    metadata = create_metadata_payload(manifest)
    metadata_path = paths["artifacts"] / "metadata.json"
    social_copy_path = paths["artifacts"] / "social-copy.json"
    write_json(metadata_path, metadata)
    write_json(social_copy_path, create_social_copy_payload(metadata))
    artifacts.append(build_artifact(manifest, "metadata", metadata_path, "metadata", "application/json"))
    artifacts.append(build_artifact(manifest, "social_copy", social_copy_path, "social_copy", "application/json"))
    if manifest["options"].get("generateThumbnail"):
        title = metadata["title"]
        thumb_path = render_thumbnail(manifest, paths, title)
        artifacts.append(build_artifact(manifest, "thumbnail", thumb_path, "thumbnail", "image/png"))
    return artifacts


def dry_run_job(manifest: dict[str, Any], paths: dict[str, Path]) -> list[dict[str, Any]]:
    emit("job.progress", phase="dry-run", detail="Writing fake artifacts")
    video_path = paths["artifacts"] / "video.mp4"
    captions_path = paths["artifacts"] / "captions.srt"
    write_fake_video(video_path, manifest["jobId"])
    write_fake_srt(captions_path, manifest.get("input", {}).get("text", "Pod2Vid dry-run"))
    metadata = create_metadata_payload(manifest)
    metadata_path = paths["artifacts"] / "metadata.json"
    social_copy_path = paths["artifacts"] / "social-copy.json"
    write_json(metadata_path, metadata)
    write_json(social_copy_path, create_social_copy_payload(metadata))
    preview_path = paths["artifacts"] / "subtitle-preview.png"
    render_label_png(preview_path, metadata["title"], f"Style: {normalize_style(manifest['options'].get('subtitleStyle'))}")
    artifacts = [
        build_artifact(manifest, "video", video_path, "mp4", "video/mp4"),
        build_artifact(manifest, "captions", captions_path, "srt", "application/x-subrip"),
        build_artifact(manifest, "metadata", metadata_path, "metadata", "application/json"),
        build_artifact(manifest, "social_copy", social_copy_path, "social_copy", "application/json"),
        build_artifact(manifest, "subtitle_preview", preview_path, "preview", "image/png"),
    ]
    if manifest.get("input", {}).get("kind") == "transcript":
        transcript_path = paths["artifacts"] / "source-transcript.txt"
        write_text_file(transcript_path, manifest["input"]["text"])
        artifacts.append(build_artifact(manifest, "source_transcript", transcript_path, "transcript", "text/plain"))
    if manifest["options"].get("generateThumbnail"):
        thumbnail_path = paths["artifacts"] / "thumbnail.png"
        render_label_png(thumbnail_path, metadata["title"], "Dry-run thumbnail")
        artifacts.append(build_artifact(manifest, "thumbnail", thumbnail_path, "thumbnail", "image/png"))
    return artifacts


def load_parent_artifacts(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path]]:
    parent_paths = job_paths({"jobId": manifest["parentJobId"], "storage": manifest.get("storage", {})})
    if not parent_paths["result"].exists() or not parent_paths["artifact_manifest"].exists():
        raise WorkerError("ERR_PARENT_JOB_MISSING", f"Parent job not found: {manifest['parentJobId']}")
    return read_json(parent_paths["result"]), read_json(parent_paths["artifact_manifest"])["artifacts"], parent_paths


def artifact_by_id(artifacts: list[dict[str, Any]], artifact_id: str) -> dict[str, Any] | None:
    for artifact in artifacts:
        if artifact["artifactId"] == artifact_id:
            return artifact
    return None


def rehydrate_video(manifest: dict[str, Any], parent_paths: dict[str, Path], parent_artifacts: list[dict[str, Any]], destination: Path) -> Path:
    archive_manifest_path = parent_paths["archive_manifest"]
    if not archive_manifest_path.exists():
        raise WorkerError("ERR_REHYDRATE_FAILED", f"No archive manifest found for {manifest['parentJobId']}")
    archive_manifest = read_json(archive_manifest_path)
    video_entry = next((entry for entry in archive_manifest.get("artifacts", []) if entry.get("artifactId") == "video"), None)
    if not video_entry:
        raise WorkerError("ERR_REHYDRATE_FAILED", "Archive manifest does not include a video artifact")
    sources = [
        video_entry.get("sourcePath"),
        video_entry.get("gatewayUrl"),
        video_entry.get("ipfsUri"),
    ]
    for source in sources:
        if not source:
            continue
        try:
            if source.startswith("file://"):
                shutil.copy2(Path(source[7:]), destination)
            elif source.startswith("http://") or source.startswith("https://"):
                ensure_parent(destination)
                with urllib.request.urlopen(source, timeout=30) as response, destination.open("wb") as handle:
                    shutil.copyfileobj(response, handle)
            elif Path(source).exists():
                shutil.copy2(Path(source), destination)
            if destination.exists():
                return destination
        except Exception:
            continue
    parent_video = artifact_by_id(parent_artifacts, "video")
    if parent_video and Path(parent_video["path"]).exists():
        shutil.copy2(parent_video["path"], destination)
        return destination
    raise WorkerError("ERR_REHYDRATE_FAILED", f"Unable to rehydrate archived video for {manifest['parentJobId']}")


def resolve_parent_video(manifest: dict[str, Any], parent_paths: dict[str, Path], parent_artifacts: list[dict[str, Any]], current_paths: dict[str, Path]) -> Path:
    parent_video = artifact_by_id(parent_artifacts, "video")
    if not parent_video:
        raise WorkerError("ERR_PARENT_JOB_MISSING", "Parent job does not include a video artifact")
    video_path = Path(parent_video["path"])
    if video_path.exists():
        return video_path
    emit("job.progress", phase="rehydrate", detail="Restoring archived video")
    return rehydrate_video(manifest, parent_paths, parent_artifacts, current_paths["rehydrated"])


def revision_job(manifest: dict[str, Any], paths: dict[str, Path]) -> list[dict[str, Any]]:
    parent_result, parent_artifacts, parent_paths = load_parent_artifacts(manifest)
    parent_manifest = read_json(parent_paths["manifest"])
    revision_type = manifest["revision"]["type"]
    base_title = (artifact_by_id(parent_artifacts, "metadata") and read_json(Path(artifact_by_id(parent_artifacts, "metadata")["path"])).get("title")) or f"Pod2Vid {manifest['parentJobId']}"
    artifacts: list[dict[str, Any]] = []
    if revision_type == "thumbnail":
        title = manifest["revision"].get("title") or base_title
        thumbnail_path = paths["artifacts"] / "thumbnail.png"
        if manifest.get("dryRun"):
            render_label_png(thumbnail_path, title, "Revised thumbnail")
        else:
            render_thumbnail(manifest, paths, title)
        artifacts.append(build_artifact(manifest, "thumbnail", thumbnail_path, "thumbnail", "image/png"))
    elif revision_type == "metadata":
        metadata = create_metadata_payload(manifest, title=manifest["revision"].get("title") or base_title)
        metadata["description"] = manifest["revision"].get("description") or metadata["description"]
        metadata["parentJobId"] = manifest["parentJobId"]
        metadata_path = paths["artifacts"] / "metadata.json"
        social_copy_path = paths["artifacts"] / "social-copy.json"
        write_json(metadata_path, metadata)
        write_json(social_copy_path, create_social_copy_payload(metadata))
        artifacts.append(build_artifact(manifest, "metadata", metadata_path, "metadata", "application/json"))
        artifacts.append(build_artifact(manifest, "social_copy", social_copy_path, "social_copy", "application/json"))
    elif revision_type == "subtitle_style":
        source_video = resolve_parent_video(manifest, parent_paths, parent_artifacts, paths)
        video_out = paths["artifacts"] / "video.mp4"
        shutil.copy2(source_video, video_out)
        captions_src = artifact_by_id(parent_artifacts, "captions")
        captions_dst = paths["artifacts"] / "captions.srt"
        if captions_src and Path(captions_src["path"]).exists():
            shutil.copy2(Path(captions_src["path"]), captions_dst)
        else:
            write_fake_srt(captions_dst, "Subtitle style revision")
        preview_path = paths["artifacts"] / "subtitle-preview.png"
        style = normalize_style(manifest["options"].get("subtitleStyle") or manifest["revision"].get("subtitleStyle"))
        render_label_png(preview_path, "Subtitle Style Revision", f"{style} for {parent_result['jobId']}")
        style_manifest_path = paths["artifacts"] / "subtitle-style.json"
        write_json(style_manifest_path, {"parentJobId": manifest["parentJobId"], "subtitleStyle": style})
        source_type = "rehydrated" if source_video == paths["rehydrated"] else "local"
        artifacts.append(build_artifact(manifest, "video", video_out, "mp4", "video/mp4", source=source_type))
        artifacts.append(build_artifact(manifest, "captions", captions_dst, "srt", "application/x-subrip"))
        artifacts.append(build_artifact(manifest, "subtitle_preview", preview_path, "preview", "image/png"))
        artifacts.append(build_artifact(manifest, "subtitle_style", style_manifest_path, "subtitle_style", "application/json"))
    else:
        raise WorkerError("ERR_REVISION_FAILED", f"Unsupported revision type: {revision_type}")
    child_manifest = dict(parent_manifest)
    child_manifest.update({
        "jobId": manifest["jobId"],
        "parentJobId": manifest["parentJobId"],
        "mode": "revision",
        "revision": manifest["revision"],
        "options": manifest["options"],
    })
    write_json(paths["artifacts"] / "revision-context.json", child_manifest)
    artifacts.append(build_artifact(manifest, "revision_context", paths["artifacts"] / "revision-context.json", "manifest", "application/json"))
    return artifacts


def write_artifact_manifest(manifest: dict[str, Any], paths: dict[str, Path], artifacts: list[dict[str, Any]], archive_manifest: dict[str, Any] | None) -> dict[str, Any]:
    payload = {
        "kind": "pod2vid_artifact_manifest",
        "version": SCHEMA_VERSION,
        "jobId": manifest["jobId"],
        "createdAt": utc_now(),
        "localRetentionExpiresAt": retention_expires_at(manifest),
        "artifacts": artifacts,
    }
    if archive_manifest:
        payload["archiveManifestPath"] = str(paths["archive_manifest"])
        payload["archiveGatewayUrls"] = archive_manifest["gatewayUrls"]
    write_json(paths["artifact_manifest"], payload)
    return payload


def finalize_success(manifest: dict[str, Any], paths: dict[str, Path], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = list(artifacts)
    artifacts.append(build_artifact(manifest, "job_manifest", paths["manifest"], "manifest", "application/json"))
    archive_manifest = write_archive_manifest(manifest, paths, artifacts)
    artifact_manifest = write_artifact_manifest(manifest, paths, artifacts, archive_manifest)
    result = {
        "jobId": manifest["jobId"],
        "parentJobId": manifest.get("parentJobId"),
        "status": "succeeded",
        "mode": manifest["mode"],
        "preset": manifest["preset"],
        "dryRun": bool(manifest.get("dryRun")),
        "artifactManifestPath": str(paths["artifact_manifest"]),
        "archiveManifestPath": str(paths["archive_manifest"]) if archive_manifest else None,
        "artifacts": [artifact["artifactId"] for artifact in artifacts],
        "errorCode": None,
        "errorMessage": None,
        "startedAt": manifest.get("_startedAt"),
        "finishedAt": utc_now(),
    }
    write_json(paths["result"], result)
    emit("job.completed", jobId=manifest["jobId"], status="succeeded", artifacts=result["artifacts"])
    return artifact_manifest


def finalize_failure(manifest: dict[str, Any], paths: dict[str, Path], error: WorkerError) -> None:
    result = {
        "jobId": manifest.get("jobId"),
        "parentJobId": manifest.get("parentJobId"),
        "status": "failed",
        "mode": manifest.get("mode"),
        "preset": manifest.get("preset"),
        "dryRun": bool(manifest.get("dryRun")),
        "artifactManifestPath": str(paths["artifact_manifest"]),
        "archiveManifestPath": None,
        "artifacts": [],
        "errorCode": error.code,
        "errorMessage": error.safe_message,
        "errorDetail": str(error),
        "startedAt": manifest.get("_startedAt"),
        "finishedAt": utc_now(),
    }
    write_json(paths["result"], result)
    emit("job.completed", jobId=manifest.get("jobId"), status="failed", errorCode=error.code, errorMessage=error.safe_message)


def run_job_manifest(manifest_path: str) -> dict[str, Any]:
    manifest = read_json(Path(manifest_path))
    paths = job_paths(manifest)
    try:
        validate_manifest(manifest)
        validate_environment(manifest)
        manifest["_startedAt"] = utc_now()
        copy_manifest_into_job(manifest, paths)
        emit("job.started", jobId=manifest["jobId"], mode=manifest["mode"], preset=manifest["preset"], dryRun=bool(manifest.get("dryRun")))
        if manifest["mode"] == "render":
            artifacts = dry_run_job(manifest, paths) if manifest.get("dryRun") else render_job(manifest, paths)
        else:
            artifacts = revision_job(manifest, paths)
        return finalize_success(manifest, paths, artifacts)
    except WorkerError as error:
        finalize_failure(manifest, paths, error)
        raise
    except Exception as error:  # pragma: no cover - defensive wrapper
        wrapped = WorkerError("ERR_RENDER_FAILED", str(error))
        finalize_failure(manifest, paths, wrapped)
        raise wrapped

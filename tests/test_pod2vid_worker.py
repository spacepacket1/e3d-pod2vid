import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pod2vid_worker import (
    SCHEMA_VERSION,
    WorkerError,
    extract_transcript_title,
    parse_transcript_segments,
    resolve_required_env,
    resolve_speaker_voice,
    run_job_manifest,
    validate_manifest,
)


class Pod2VidWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.storage_dir = Path(self.temp_dir.name) / "storage"
        os.environ["POD2VID_STORAGE_DIR"] = str(self.storage_dir)

    def write_manifest(self, payload):
        path = Path(self.temp_dir.name) / f"{payload['jobId']}.json"
        path.write_text(json.dumps(payload))
        return path

    def base_manifest(self, job_id="pod2vid_job_test"):
        return {
            "kind": "cast_job",
            "version": SCHEMA_VERSION,
            "jobId": job_id,
            "mode": "render",
            "preset": "transcript_short",
            "tier": "starter",
            "retentionHours": 6,
            "dryRun": True,
            "input": {
                "kind": "transcript",
                "text": "Host: Hello world.\nGuest: We are testing the worker.",
            },
            "options": {
                "subtitleStyle": "bold_mobile",
                "generateThumbnail": True,
                "brandEndCard": True,
                "archiveToIpfs": False,
            },
            "brandKit": {
                "endCard": True,
                "watermarkMode": "tier_default",
            },
            "platformMetadata": {
                "platforms": ["youtube", "x"],
            },
        }

    def read_result(self, job_id):
        return json.loads((self.storage_dir / "jobs" / job_id / "result.json").read_text())

    def read_artifact_manifest(self, job_id):
        return json.loads((self.storage_dir / "jobs" / job_id / "artifact-manifest.json").read_text())

    def test_resolve_speaker_voice_defaults_differ_by_role(self):
        self.assertEqual(resolve_speaker_voice({}, "A"), "onyx")
        self.assertEqual(resolve_speaker_voice({}, "B"), "shimmer")

    def test_resolve_speaker_voice_honors_requested_gender_and_stays_distinct(self):
        options = {"voices": {"host": "female", "guest": "female"}}
        host_voice = resolve_speaker_voice(options, "A")
        guest_voice = resolve_speaker_voice(options, "B")
        self.assertEqual(host_voice, "nova")
        self.assertEqual(guest_voice, "shimmer")
        self.assertNotEqual(host_voice, guest_voice)

    def test_resolve_speaker_voice_ignores_invalid_gender(self):
        self.assertEqual(resolve_speaker_voice({"voices": {"host": "robot"}}, "A"), "onyx")

    def test_title_line_is_extracted_and_excluded_from_spoken_segments(self):
        text = "Title: My Show\nHost: Welcome.\nGuest: Thanks for having me."
        self.assertEqual(extract_transcript_title(text), "My Show")
        segments = parse_transcript_segments(text)
        self.assertEqual(segments, [
            {"speaker": "A", "text": "Welcome."},
            {"speaker": "B", "text": "Thanks for having me."},
        ])

    def test_missing_title_line_extracts_none(self):
        self.assertIsNone(extract_transcript_title("Host: Welcome.\nGuest: Thanks."))
        self.assertIsNone(extract_transcript_title("Title:   \nHost: Welcome."))

    def test_dry_run_render_writes_deterministic_artifacts(self):
        manifest = self.base_manifest()
        run_job_manifest(str(self.write_manifest(manifest)))

        result = self.read_result(manifest["jobId"])
        artifact_manifest = self.read_artifact_manifest(manifest["jobId"])

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["dryRun"], True)
        self.assertIn("video", result["artifacts"])
        self.assertEqual(artifact_manifest["jobId"], manifest["jobId"])
        self.assertTrue((self.storage_dir / "jobs" / manifest["jobId"] / "artifacts" / "video.mp4").exists())
        self.assertTrue((self.storage_dir / "jobs" / manifest["jobId"] / "artifacts" / "thumbnail.png").exists())
        self.assertEqual(artifact_manifest["localRetentionExpiresAt"][-1], "Z")

    def test_revision_modes_complete_against_dry_run_parent(self):
        parent = self.base_manifest(job_id="pod2vid_job_parent")
        run_job_manifest(str(self.write_manifest(parent)))

        for revision_type in ("thumbnail", "metadata", "subtitle_style"):
            child_id = f"pod2vid_job_{revision_type}"
            child = {
                "kind": "cast_job",
                "version": SCHEMA_VERSION,
                "jobId": child_id,
                "parentJobId": parent["jobId"],
                "mode": "revision",
                "preset": parent["preset"],
                "tier": parent["tier"],
                "retentionHours": 6,
                "dryRun": True,
                "options": {
                    "subtitleStyle": "news_brief",
                    "generateThumbnail": True,
                    "brandEndCard": True,
                    "archiveToIpfs": False,
                },
                "revision": {
                    "type": revision_type,
                    "subtitleStyle": "news_brief",
                    "title": f"Revised {revision_type}",
                },
            }
            run_job_manifest(str(self.write_manifest(child)))
            result = self.read_result(child_id)
            self.assertEqual(result["status"], "succeeded")

        subtitle_artifacts = self.read_artifact_manifest("pod2vid_job_subtitle_style")["artifacts"]
        artifact_ids = {artifact["artifactId"] for artifact in subtitle_artifacts}
        self.assertIn("video", artifact_ids)
        self.assertIn("subtitle_style", artifact_ids)

    def test_archive_manifest_and_rehydration_work_when_local_video_is_missing(self):
        video_source = Path(self.temp_dir.name) / "archived-source.mp4"
        video_source.write_bytes(b"archived video bytes")
        parent = self.base_manifest(job_id="pod2vid_job_archive_parent")
        parent["options"]["archiveToIpfs"] = True
        parent["archive"] = {
            "enabled": True,
            "ipfs": {
                "gatewayBaseUrl": "https://gateway.example.test/ipfs",
                "artifacts": {
                    "video": {
                        "sourcePath": str(video_source),
                        "cid": "bafyvideoarchive",
                        "ipfsUri": "ipfs://bafyvideoarchive",
                        "gatewayUrl": "file://" + str(video_source),
                    }
                },
            },
        }
        run_job_manifest(str(self.write_manifest(parent)))
        local_video = self.storage_dir / "jobs" / parent["jobId"] / "artifacts" / "video.mp4"
        local_video.unlink()

        child = {
            "kind": "cast_job",
            "version": SCHEMA_VERSION,
            "jobId": "pod2vid_job_rehydrate_child",
            "parentJobId": parent["jobId"],
            "mode": "revision",
            "preset": parent["preset"],
            "tier": parent["tier"],
            "retentionHours": 6,
            "dryRun": True,
            "options": {
                "subtitleStyle": "developer_demo",
                "generateThumbnail": False,
                "brandEndCard": True,
                "archiveToIpfs": False,
            },
            "revision": {
                "type": "subtitle_style",
                "subtitleStyle": "developer_demo",
            },
        }
        run_job_manifest(str(self.write_manifest(child)))
        rehydrated = self.storage_dir / "jobs" / child["jobId"] / "tmp" / "rehydrated-video.mp4"
        self.assertTrue(rehydrated.exists())
        self.assertEqual(rehydrated.read_bytes(), b"archived video bytes")

    def test_real_render_path_routes_through_pod2vid_script(self):
        audio_path = Path(self.temp_dir.name) / "input.mp3"
        audio_path.write_bytes(b"audio")
        manifest = self.base_manifest(job_id="pod2vid_job_real")
        manifest["dryRun"] = False
        manifest["preset"] = "youtube"
        manifest["input"] = {"kind": "upload", "path": str(audio_path)}
        manifest["options"]["archiveToIpfs"] = False

        with mock.patch("pod2vid_worker.validate_environment"), mock.patch("pod2vid_worker.run_subprocess") as run_subprocess, mock.patch("pod2vid_worker.apply_branding") as apply_branding:
            def fake_render_thumbnail(*args, **kwargs):
                thumb = self.storage_dir / "jobs" / manifest["jobId"] / "artifacts" / "thumbnail.png"
                thumb.parent.mkdir(parents=True, exist_ok=True)
                thumb.write_bytes(b"png")
                return thumb

            output_dir = self.storage_dir / "jobs" / manifest["jobId"] / "work"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "pipeline-output.mp4").write_bytes(b"video")
            (output_dir / "pipeline-output.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n")
            apply_branding.side_effect = lambda m, source, paths: source

            with mock.patch("pod2vid_worker.render_thumbnail", side_effect=fake_render_thumbnail):
                run_job_manifest(str(self.write_manifest(manifest)))

        first_command = run_subprocess.call_args_list[0].kwargs["env"]
        self.assertEqual(first_command["VIDEO_WIDTH"], "1920")
        self.assertEqual(first_command["VIDEO_HEIGHT"], "1080")
        command = run_subprocess.call_args_list[0].args[0]
        self.assertIn("pod2vid.py", command[1])
        self.assertEqual(command[2], str(output_dir / "input.mp3"))

    def test_transcript_with_title_line_prepends_title_card(self):
        manifest = self.base_manifest(job_id="pod2vid_job_title_card")
        manifest["dryRun"] = False
        manifest["preset"] = "transcript_short"
        manifest["input"] = {"kind": "transcript", "text": "Title: My Show\nHost: Welcome.\nGuest: Thanks."}
        manifest["options"]["archiveToIpfs"] = False

        output_dir = self.storage_dir / "jobs" / manifest["jobId"] / "work"
        output_dir.mkdir(parents=True, exist_ok=True)
        pipeline_output = output_dir / "pipeline-output.mp4"
        pipeline_output.write_bytes(b"video")
        (output_dir / "pipeline-output.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n")

        with mock.patch("pod2vid_worker.validate_environment"), \
             mock.patch("pod2vid_worker.resolve_audio_input", return_value=(Path("/tmp/audio.mp3"), None)), \
             mock.patch("pod2vid_worker.run_subprocess"), \
             mock.patch("pod2vid_worker.apply_branding", side_effect=lambda m, source, paths: source) as apply_branding, \
             mock.patch("pod2vid_worker.prepend_title_card", return_value=pipeline_output) as prepend_title_card, \
             mock.patch("pod2vid_worker.render_thumbnail") as render_thumbnail:
            render_thumbnail.side_effect = lambda *a, **k: pipeline_output
            run_job_manifest(str(self.write_manifest(manifest)))

        prepend_title_card.assert_called_once()
        self.assertEqual(prepend_title_card.call_args.args[0], "My Show")
        # apply_branding must receive whatever prepend_title_card returned, not
        # the raw pipeline output -- otherwise the title card would be silently
        # dropped from the final video.
        apply_branding.assert_called_once()
        self.assertEqual(apply_branding.call_args.args[1], pipeline_output)

    def test_transcript_without_title_line_skips_title_card(self):
        manifest = self.base_manifest(job_id="pod2vid_job_no_title_card")
        manifest["dryRun"] = False
        manifest["preset"] = "transcript_short"
        manifest["input"] = {"kind": "transcript", "text": "Host: Welcome.\nGuest: Thanks."}
        manifest["options"]["archiveToIpfs"] = False

        output_dir = self.storage_dir / "jobs" / manifest["jobId"] / "work"
        output_dir.mkdir(parents=True, exist_ok=True)
        pipeline_output = output_dir / "pipeline-output.mp4"
        pipeline_output.write_bytes(b"video")
        (output_dir / "pipeline-output.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n")

        with mock.patch("pod2vid_worker.validate_environment"), \
             mock.patch("pod2vid_worker.resolve_audio_input", return_value=(Path("/tmp/audio.mp3"), None)), \
             mock.patch("pod2vid_worker.run_subprocess"), \
             mock.patch("pod2vid_worker.apply_branding", side_effect=lambda m, source, paths: source), \
             mock.patch("pod2vid_worker.prepend_title_card") as prepend_title_card, \
             mock.patch("pod2vid_worker.render_thumbnail") as render_thumbnail:
            render_thumbnail.side_effect = lambda *a, **k: pipeline_output
            run_job_manifest(str(self.write_manifest(manifest)))

        prepend_title_card.assert_not_called()

    def test_validate_manifest_accepts_cast_job_kind(self):
        # The Node-side worker (e3d-cast) emits "kind": "cast_job" following
        # the pod2vid -> cast product rename. Must not raise.
        validate_manifest(self.base_manifest())

    def test_validate_manifest_rejects_pre_rename_kind(self):
        # Regression test for the actual production incident: this validator
        # used to require "kind": "pod2vid_job", while the Node-side worker
        # had already been renamed to emit "cast_job" -- every real job was
        # rejected here before doing any work, silently, for every user,
        # until this mismatch was found. Guards against the rename being
        # silently reverted (or re-drifting) in either direction.
        manifest = self.base_manifest()
        manifest["kind"] = "pod2vid_job"
        with self.assertRaises(WorkerError) as ctx:
            validate_manifest(manifest)
        self.assertEqual(ctx.exception.code, "ERR_MANIFEST_VALIDATION")

    def test_validate_manifest_rejects_unknown_kind(self):
        manifest = self.base_manifest()
        manifest["kind"] = "something_else"
        with self.assertRaises(WorkerError) as ctx:
            validate_manifest(manifest)
        self.assertEqual(ctx.exception.code, "ERR_MANIFEST_VALIDATION")

    def test_validate_manifest_rejects_unknown_transcription_engine(self):
        manifest = self.base_manifest()
        manifest["options"]["transcriptionEngine"] = "deepgram"
        with self.assertRaises(WorkerError) as ctx:
            validate_manifest(manifest)
        self.assertEqual(ctx.exception.code, "ERR_MANIFEST_VALIDATION")

    def test_resolve_required_env_skips_assemblyai_for_local_engine(self):
        manifest = self.base_manifest()
        manifest["dryRun"] = False
        manifest["preset"] = "youtube"
        manifest["input"] = {"kind": "upload", "path": "/tmp/input.mp3"}

        self.assertIn("ASSEMBLYAI_API_KEY", resolve_required_env(manifest))

        manifest["options"]["transcriptionEngine"] = "local"
        needed = resolve_required_env(manifest)
        self.assertNotIn("ASSEMBLYAI_API_KEY", needed)
        self.assertIn("OPENAI_API_KEY", needed)
        self.assertIn("PEXELS_API_KEY", needed)

    def test_real_render_with_local_engine_skips_assemblyai_and_writes_diarization(self):
        audio_path = Path(self.temp_dir.name) / "input.mp3"
        audio_path.write_bytes(b"audio")
        manifest = self.base_manifest(job_id="pod2vid_job_local_engine")
        manifest["dryRun"] = False
        manifest["preset"] = "youtube"
        manifest["input"] = {"kind": "upload", "path": str(audio_path)}
        manifest["options"]["archiveToIpfs"] = False
        manifest["options"]["transcriptionEngine"] = "local"

        fake_utterances = {"utterances": [{"speaker": "A", "text": "Hello.", "start": 0, "end": 1200}]}

        with mock.patch("pod2vid_worker.validate_environment"), \
                mock.patch("pod2vid_worker.transcribe_local", return_value=fake_utterances) as transcribe_local, \
                mock.patch("pod2vid_worker.run_subprocess") as run_subprocess, \
                mock.patch("pod2vid_worker.apply_branding") as apply_branding:
            def fake_render_thumbnail(*args, **kwargs):
                thumb = self.storage_dir / "jobs" / manifest["jobId"] / "artifacts" / "thumbnail.png"
                thumb.parent.mkdir(parents=True, exist_ok=True)
                thumb.write_bytes(b"png")
                return thumb

            output_dir = self.storage_dir / "jobs" / manifest["jobId"] / "work"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "pipeline-output.mp4").write_bytes(b"video")
            (output_dir / "pipeline-output.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n")
            apply_branding.side_effect = lambda m, source, paths: source

            with mock.patch("pod2vid_worker.render_thumbnail", side_effect=fake_render_thumbnail):
                run_job_manifest(str(self.write_manifest(manifest)))

        transcribe_local.assert_called_once()
        diarization_cache = output_dir / "input-diarization.json"
        self.assertTrue(diarization_cache.exists())
        self.assertEqual(json.loads(diarization_cache.read_text()), fake_utterances)


if __name__ == "__main__":
    unittest.main()

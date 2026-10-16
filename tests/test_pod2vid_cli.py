import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import pod2vid_cli


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Pod2VidCliTests(unittest.TestCase):
    def run_cli(self, argv, run_result=None, side_effect=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch("pod2vid_cli.subprocess.run") as run_mock:
            if side_effect is not None:
                run_mock.side_effect = side_effect
            elif run_result is not None:
                run_mock.return_value = run_result
            else:
                run_mock.return_value = FakeCompleted(0, "", "")
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = pod2vid_cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue(), run_mock

    def test_help_and_parser_rejections(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--help"])
        self.assertEqual(ctx.exception.code, 0)

        help_text = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(help_text):
                pod2vid_cli.main(["--help"])
        self.assertIn("run", help_text.getvalue())
        self.assertIn("short", help_text.getvalue())
        self.assertIn("signal", help_text.getvalue())
        self.assertIn("announce", help_text.getvalue())

        with self.assertRaises(SystemExit) as ctx:
            pod2vid_cli.main(["bogus"])
        self.assertEqual(ctx.exception.code, 2)

        with self.assertRaises(SystemExit) as ctx:
            pod2vid_cli.main(["run", "episode.m4a", "--title", "x"])
        self.assertEqual(ctx.exception.code, 2)

    def test_run_publish_uses_expected_argument_vectors(self):
        upload_stdout = "Uploading...\nUploaded: https://www.youtube.com/watch?v=abc123\n"
        code, _, _, run_mock = self.run_cli(
            ["run", "episode.m4a", "--publish", "--message", "custom message"],
            side_effect=[
                FakeCompleted(0, "render out\n", ""),
                FakeCompleted(0, upload_stdout, ""),
                FakeCompleted(0, "announce out\n", ""),
            ],
        )
        self.assertEqual(code, 0)
        self.assertEqual(run_mock.call_args_list[0].args[0], [
            sys.executable,
            str(Path(pod2vid_cli.REPO_ROOT) / "pod2vid.py"),
            "episode.m4a",
            "output/episode.mp4",
        ])
        self.assertEqual(run_mock.call_args_list[1].args[0], [
            "node",
            str(Path(pod2vid_cli.REPO_ROOT) / "yt_upload.js"),
            "output/episode.mp4",
            "episode",
        ])
        self.assertEqual(run_mock.call_args_list[2].args[0], [
            "node",
            str(Path(pod2vid_cli.REPO_ROOT) / "announce.js"),
            "https://www.youtube.com/watch?v=abc123",
            "custom message",
        ])

    def test_default_and_custom_output_directories_and_title_description(self):
        code, _, _, run_mock = self.run_cli([
                "run",
                "my-audio_file.m4a",
                "--publish",
                "--output-dir",
                "demo output",
                "--title",
                "Custom Title",
                "--description",
                "Long description",
            ], side_effect=[
                FakeCompleted(0, "", ""),
                FakeCompleted(0, "Uploaded: https://www.youtube.com/watch?v=abc123\n", ""),
                FakeCompleted(0, "", ""),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(run_mock.call_args_list[0].args[0][3], "demo output/my-audio_file.mp4")
        self.assertEqual(run_mock.call_args_list[1].args[0][-2:], ["Custom Title", "Long description"])

        _, _, _, run_mock = self.run_cli(
            ["run", "my-audio_file.m4a", "--publish"],
            side_effect=[
                FakeCompleted(0, "", ""),
                FakeCompleted(0, "Uploaded: https://www.youtube.com/watch?v=abc123\n", ""),
                FakeCompleted(0, "", ""),
            ],
        )
        self.assertEqual(run_mock.call_args_list[1].args[0][-1], "my audio file")

    def test_dry_run_plan_and_signal_forwarding(self):
        code, out, err, run_mock = self.run_cli(["run", "episode.m4a", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertFalse(run_mock.called)
        self.assertIn("pod2vid.py", out)
        self.assertIn("output/episode.mp4", out)
        self.assertEqual(err, "")

        code, out, _, run_mock = self.run_cli(["short", "--output-dir", "demo output", "--dry-run", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(run_mock.called)
        payload = json.loads(out)
        self.assertEqual(payload["outputPath"], "demo output/pod2vid-short.mp4")
        self.assertTrue(payload["dryRun"])
        self.assertTrue(payload["steps"][0]["planned"])

        code, _, _, run_mock = self.run_cli(["signal", "--dry-run", "--force"])
        self.assertEqual(code, 0)
        self.assertEqual(run_mock.call_args_list[0].args[0], [
            sys.executable,
            str(Path(pod2vid_cli.REPO_ROOT) / "signal_short.py"),
            "--dry-run",
            "--force",
        ])

    def test_json_human_output_and_outputs(self):
        code, out, _, _ = self.run_cli(["short", "--dry-run", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["command"], "short")
        self.assertIn("steps", payload)
        self.assertEqual(payload["outputPath"], "output/pod2vid-short.mp4")

        code, out, err, _ = self.run_cli(["short"], run_result=FakeCompleted(0, "stdout\n", "stderr\n"))
        self.assertEqual(code, 0)
        self.assertIn("stdout", out)
        self.assertIn("stderr", err)

    def test_run_publish_orders_and_short_circuits(self):
        code, _, _, run_mock = self.run_cli(
            ["run", "episode.m4a", "--publish"],
            side_effect=[FakeCompleted(1, "render failed\n", "render err\n")],
        )
        self.assertEqual(code, 1)
        self.assertEqual(len(run_mock.call_args_list), 1)

        code, _, _, run_mock = self.run_cli(
            ["run", "episode.m4a", "--publish"],
            side_effect=[
                FakeCompleted(0, "", ""),
                FakeCompleted(0, "uploaded but no url\n", ""),
            ],
        )
        self.assertEqual(code, 1)
        self.assertEqual(len(run_mock.call_args_list), 2)

    def test_run_publish_does_not_announce_without_uploaded_url(self):
        code, _, _, run_mock = self.run_cli(
            ["run", "episode.m4a", "--publish"],
            side_effect=[
                FakeCompleted(0, "", ""),
                FakeCompleted(0, "done\n", ""),
            ],
        )
        self.assertEqual(code, 1)
        self.assertEqual(len(run_mock.call_args_list), 2)

    def test_exit_code_propagation_and_interrupt_handling(self):
        code, _, _, _ = self.run_cli(["short"], run_result=FakeCompleted(7, "", ""))
        self.assertEqual(code, 7)

        code, out, err, _ = self.run_cli(["short"], side_effect=KeyboardInterrupt)
        self.assertEqual(code, 130)
        self.assertEqual(out, "")
        self.assertEqual(err, "")

    def test_announce_and_launcher(self):
        code, _, _, run_mock = self.run_cli(["announce", "URL", "custom message", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertFalse(run_mock.called)

        launcher = Path(pod2vid_cli.REPO_ROOT) / "pod2vid"
        self.assertTrue(launcher.exists())
        self.assertTrue(os.access(launcher, os.X_OK))
        self.assertTrue(launcher.read_text().startswith("#!/usr/bin/env python3"))


if __name__ == "__main__":
    unittest.main()

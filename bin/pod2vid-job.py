#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pod2vid_worker import WorkerError, run_job_manifest  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 bin/pod2vid-job.py <manifest.json>", file=sys.stderr)
        return 1
    try:
        run_job_manifest(sys.argv[1])
        return 0
    except WorkerError:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

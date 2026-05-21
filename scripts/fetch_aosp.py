#!/usr/bin/env python3
"""Initialize and sync the AOSP source tree.

Runs inside the build container. Idempotent: re-running just brings
the tree up to date for the configured branch.

Reads from the environment (set by the Makefile):
  AOSP_BRANCH      required, e.g. "android-15.0.0_r1"
  JOBS             optional, defaults to os.cpu_count()
  AOSP_DIR         optional, defaults to /workspace/aosp
  MANIFEST_URL     optional, defaults to upstream android.googlesource.com
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f">>> {msg}", flush=True)


def main() -> int:
    branch = os.environ.get("AOSP_BRANCH")
    if not branch:
        sys.exit("error: AOSP_BRANCH must be set")

    jobs = os.environ.get("JOBS") or str(os.cpu_count() or 4)
    aosp_dir = Path(os.environ.get("AOSP_DIR", "/workspace/aosp"))
    manifest_url = os.environ.get(
        "MANIFEST_URL",
        "https://android.googlesource.com/platform/manifest",
    )
    local_manifest_src = Path("/workspace/manifests/build-tools.xml")

    aosp_dir.mkdir(parents=True, exist_ok=True)

    if not (aosp_dir / ".repo").is_dir():
        log(f"repo init ({branch})")
        # --partial-clone / --clone-filter=blob:none: blobs on demand
        # --depth=1                                 : shallow clones
        # --no-tags                                 : skip release tags
        # --current-branch                          : only this branch
        subprocess.run(
            [
                "repo", "init",
                "--partial-clone",
                "--clone-filter=blob:none",
                "--depth=1",
                "--no-tags",
                "--current-branch",
                "-u", manifest_url,
                "-b", branch,
            ],
            cwd=aosp_dir,
            check=True,
        )

    local_manifests = aosp_dir / ".repo" / "local_manifests"
    local_manifests.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local_manifest_src, local_manifests / "build-tools.xml")

    # android.googlesource.com aggressively rate-limits cloud IPs (we
    # saw HTTP 429 / RESOURCE_EXHAUSTED with -j8 from Hetzner DE).
    # Throttle the network side hard while still letting checkout
    # parallelize across CPU cores.
    network_jobs = min(int(os.environ.get("SYNC_NETWORK_JOBS", "2")), int(jobs))
    log(f"repo sync (network j{network_jobs}, checkout j{jobs}, retries 5)")
    subprocess.run(
        [
            "repo", "sync",
            "--current-branch",
            "--no-tags",
            "--optimized-fetch",
            "--prune",
            "--force-sync",
            "--retry-fetches=5",
            f"--jobs-network={network_jobs}",
            f"--jobs-checkout={jobs}",
        ],
        cwd=aosp_dir,
        check=True,
    )

    size = subprocess.check_output(
        ["du", "-sh", str(aosp_dir)], text=True
    ).split()[0]
    log(f"sync complete: {size} on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

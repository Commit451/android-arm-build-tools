#!/usr/bin/env python3
"""Package the built binaries into a .tar.xz, with a MANIFEST.txt
so it's clear what's inside and which AOSP rev produced it.

Reads from the environment:
  TARGET             required, e.g. linux-arm64
  AOSP_BRANCH        required, recorded in the manifest
  BUILD_TOOLS_LABEL  optional, defaults to "unknown"
  OUT_DIR            optional, defaults to /workspace/out/$TARGET
  DIST_DIR           optional, defaults to /workspace/out/dist
"""

import datetime
import os
import platform
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f">>> {msg}", flush=True)


def main() -> int:
    target = os.environ.get("TARGET")
    if not target:
        sys.exit("error: TARGET must be set (e.g. linux-arm64)")
    branch = os.environ.get("AOSP_BRANCH")
    if not branch:
        sys.exit("error: AOSP_BRANCH must be set")
    label = os.environ.get("BUILD_TOOLS_LABEL", "unknown")

    out_dir = Path(os.environ.get("OUT_DIR", f"/workspace/out/{target}"))
    dist_dir = Path(os.environ.get("DIST_DIR", "/workspace/out/dist"))
    dist_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%Y%m%d")
    base = f"android-build-tools-{label}-{target}-{stamp}"

    manifest = (
        "android-arm-build-tools artifact\n"
        f"target           : {target}\n"
        f"build-tools tag  : {label}\n"
        f"aosp branch      : {branch}\n"
        f"built (UTC)      : {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"host             : {platform.system()} {platform.release()} {platform.machine()}\n"
    )
    (out_dir / "MANIFEST.txt").write_text(manifest)

    archive = dist_dir / f"{base}.tar.xz"
    archive.unlink(missing_ok=True)
    subprocess.run(
        [
            "tar", "-cJf", str(archive),
            "--exclude=*.tar.*",
            "--exclude=*.zip",
            ".",
        ],
        cwd=out_dir,
        check=True,
    )

    size = subprocess.check_output(
        ["du", "-h", str(archive)], text=True
    ).split()[0]
    log(f"packaged: {archive} ({size})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

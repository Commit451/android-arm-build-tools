#!/usr/bin/env python3
"""Build the configured Soong targets for linux-arm64 hosts.

Runs inside the linux-arm64 build container.

Reads from the environment:
  SOONG_TARGETS    required, space-separated module names
  JOBS             optional, defaults to os.cpu_count()
  AOSP_DIR         optional, defaults to /workspace/aosp
  OUT_DIR          optional, defaults to /workspace/out/linux-arm64
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f">>> {msg}", flush=True)


def find_host_bin_dir(aosp_dir: Path, targets: list[str]) -> Path:
    """Soong's host output directory name varies by branch
    (linux-arm64, linux_glibc-arm64, sometimes linux-x86 on legacy
    branches). Locate it by looking for any out/host/*/bin that has
    at least one of our targets.
    """
    for candidate in sorted((aosp_dir / "out" / "host").glob("*/bin")):
        for tool in targets:
            exe = candidate / tool
            if exe.is_file() and os.access(exe, os.X_OK):
                return candidate
    raise FileNotFoundError(
        f"none of {targets} found under {aosp_dir}/out/host/*/bin"
    )


def main() -> int:
    targets_str = os.environ.get("SOONG_TARGETS")
    if not targets_str:
        sys.exit("error: SOONG_TARGETS must be set")
    targets = targets_str.split()

    jobs = os.environ.get("JOBS") or str(os.cpu_count() or 4)
    aosp_dir = Path(os.environ.get("AOSP_DIR", "/workspace/aosp"))
    out_dir = Path(os.environ.get("OUT_DIR", "/workspace/out/linux-arm64"))

    # AOSP's envsetup.sh defines bash functions (lunch, m) so the
    # build chain has to run in bash, not invoked piece by piece.
    # aosp_arm64-eng is a benign device target; host-only builds
    # ignore device target specifics.
    soong_cmd = (
        "set -e\n"
        "source build/envsetup.sh\n"
        "lunch aosp_arm64-eng\n"
        f"m -j{jobs} {' '.join(targets)}\n"
    )
    log(f"building host tools: {' '.join(targets)}")
    subprocess.run(["bash", "-c", soong_cmd], cwd=aosp_dir, check=True)

    out_dir.mkdir(parents=True, exist_ok=True)

    log("locating host output directory")
    try:
        host_bin_dir = find_host_bin_dir(aosp_dir, targets)
    except FileNotFoundError as e:
        print(f"!! {e}", file=sys.stderr)
        print("   directories that exist:", file=sys.stderr)
        for d in sorted((aosp_dir / "out" / "host").glob("*")):
            print(f"     {d}", file=sys.stderr)
        return 1

    log(f"collecting from {host_bin_dir}")
    for tool in targets:
        src = host_bin_dir / tool
        if src.is_file() and os.access(src, os.X_OK):
            shutil.copy2(src, out_dir / tool)
            print(f"  copied {tool}")
        else:
            print(f"  !! {tool} not found at {src}")

    lib_dir = host_bin_dir.parent / "lib64"
    if not lib_dir.is_dir():
        lib_dir = host_bin_dir.parent / "lib"
    if lib_dir.is_dir():
        dest = out_dir / lib_dir.name
        dest.mkdir(exist_ok=True)
        for so in lib_dir.glob("lib*.so"):
            shutil.copy2(so, dest / so.name)

    log(f"done. Artifacts in {out_dir}:")
    for entry in sorted(out_dir.iterdir()):
        print(f"  {entry.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

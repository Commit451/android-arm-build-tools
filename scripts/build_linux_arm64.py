#!/usr/bin/env python3
"""Cross-compile aapt2 (and eventually other build-tools) for
linux-glibc-arm64 using CMake + the gcc-aarch64-linux-gnu toolchain.

Two-phase build:
  1. Host-side protoc — Soong's .proto files need protoc to run during
     CMake configure, and the target-arch protoc can't run on the
     build host (when host != arm64). So we build protoc separately
     for the host first, then pass its path into the main build.
  2. Target cross-compile — configures the root CMakeLists with our
     aarch64 toolchain file and ninja-builds the aapt2 target.

Reads from the environment:
  TARGETS          optional, space-separated tool names (default: aapt2)
  JOBS             optional, defaults to os.cpu_count()
  WORKSPACE        optional, defaults to /workspace
  OUT_DIR          optional, defaults to /workspace/out/linux-arm64
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"\n>>> {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> None:
    subprocess.run(cmd, check=True, **kwargs)


def build_host_protoc(workspace: Path, jobs: str) -> Path:
    """Build protoc with the host compiler (whatever the container's
    default gcc is). Returns the absolute path to the protoc binary.
    """
    src = workspace / "src" / "protobuf"
    if not src.is_dir():
        sys.exit(f"error: {src} does not exist; did fetch_sources.py run?")
    build_dir = workspace / "build" / "host-protoc"
    build_dir.mkdir(parents=True, exist_ok=True)

    log(f"configure host protoc in {build_dir}")
    run(
        [
            "cmake",
            "-S", str(src),
            "-B", str(build_dir),
            "-G", "Ninja",
            "-Dprotobuf_BUILD_TESTS=OFF",
            "-Dprotobuf_BUILD_EXAMPLES=OFF",
            "-DABSL_PROPAGATE_CXX_STD=ON",
            "-DCMAKE_BUILD_TYPE=Release",
        ],
    )
    log("build host protoc")
    run(["cmake", "--build", str(build_dir), "-j", jobs, "--target", "protoc"])

    candidates = list(build_dir.glob("**/protoc")) + list(build_dir.glob("**/protoc-*"))
    candidates = [c for c in candidates if c.is_file() and os.access(c, os.X_OK)]
    if not candidates:
        sys.exit(f"error: no protoc executable found under {build_dir}")
    return candidates[0]


def build_target(workspace: Path, protoc: Path, targets: list[str], jobs: str) -> Path:
    """Cross-compile the configured targets. Returns the bin dir
    where artifacts land."""
    toolchain = workspace / "cmake" / "toolchain-aarch64-linux-gnu.cmake"
    if not toolchain.is_file():
        sys.exit(f"error: toolchain file missing at {toolchain}")
    build_dir = workspace / "build" / "linux-arm64"
    build_dir.mkdir(parents=True, exist_ok=True)

    log(f"configure target build in {build_dir}")
    run(
        [
            "cmake",
            "-S", str(workspace),
            "-B", str(build_dir),
            "-G", "Ninja",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            f"-DPROTOC_PATH={protoc}",
            "-DCMAKE_BUILD_TYPE=Release",
        ],
    )

    log(f"build targets: {' '.join(targets)}")
    # `-- -k 0` passes --keep-going to the underlying ninja: keep
    # compiling other TUs after a failure so one CI run surfaces every
    # broken file at once, not just the first. We still exit non-zero
    # if any target failed, so this doesn't hide errors — it just
    # batches them.
    run([
        "cmake", "--build", str(build_dir), "-j", jobs,
        "--target", *targets, "--", "-k", "0",
    ])

    return build_dir / "bin"


def main() -> int:
    targets_str = os.environ.get("TARGETS", "aapt2")
    targets = targets_str.split()

    jobs = os.environ.get("JOBS") or str(os.cpu_count() or 4)
    workspace = Path(os.environ.get("WORKSPACE", "/workspace"))
    out_dir = Path(os.environ.get("OUT_DIR", "/workspace/out/linux-arm64"))

    log(f"workspace: {workspace}")
    log(f"targets:   {' '.join(targets)}")
    log(f"jobs:      {jobs}")

    protoc = build_host_protoc(workspace, jobs)
    log(f"host protoc: {protoc}")

    bin_dir = build_target(workspace, protoc, targets, jobs)

    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"collecting artifacts from {bin_dir}")
    for entry in bin_dir.rglob("*"):
        if entry.is_file() and os.access(entry, os.X_OK):
            tool = entry.name
            if tool in targets:
                shutil.copy2(entry, out_dir / tool)
                print(f"  copied {tool}")

    log(f"done. Artifacts in {out_dir}:")
    for entry in sorted(out_dir.iterdir()):
        print(f"  {entry.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

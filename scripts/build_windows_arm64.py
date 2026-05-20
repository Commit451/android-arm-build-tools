#!/usr/bin/env python3
"""Cross-compile the configured Soong targets for windows-arm64.

Runs inside the windows-arm64 build container, which has llvm-mingw
available at /opt/llvm-mingw.

Experimental: AOSP's stock host toolchain assumes x86_64-w64-mingw32.
We point Soong at aarch64-w64-mingw32 via env vars and apply any
patches in patches/*.patch that retarget the mingw triple. Expect
to land more patches in patches/ for targets that don't build cleanly.

Reads from the environment:
  SOONG_TARGETS    required, space-separated module names
  JOBS             optional
  AOSP_DIR         optional, defaults to /workspace/aosp
  OUT_DIR          optional, defaults to /workspace/out/windows-arm64
  PATCH_DIR        optional, defaults to /workspace/patches
  MINGW_TRIPLE     optional, defaults to aarch64-w64-mingw32
  MINGW_PREFIX     optional, defaults to /opt/llvm-mingw
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f">>> {msg}", flush=True)


def apply_patches(aosp_dir: Path, patch_dir: Path) -> None:
    """Apply patches/*.patch. Each patch must have a `# Project: <path>`
    header naming the AOSP-relative directory it applies to. Idempotent:
    a `git apply --check` decides whether the patch is already in place.
    """
    if not patch_dir.is_dir():
        return
    patches = sorted(patch_dir.glob("*.patch"))
    if not patches:
        return
    log(f"applying patches from {patch_dir}")
    for p in patches:
        project = None
        for line in p.read_text().splitlines():
            if line.startswith("# Project:"):
                project = line[len("# Project:"):].strip()
                break
        if not project:
            print(f"  !! {p.name} missing '# Project: <path>' header, skipping")
            continue
        proj_dir = aosp_dir / project
        check = subprocess.run(
            ["git", "apply", "--check", str(p)],
            cwd=proj_dir,
            capture_output=True,
        )
        if check.returncode == 0:
            subprocess.run(
                ["git", "apply", str(p)], cwd=proj_dir, check=True
            )
            print(f"  applied {p.name} to {project}")
        else:
            print(f"  {p.name} already applied or not applicable to {project}")


def find_windows_bin_dir(aosp_dir: Path) -> Path | None:
    canonical = aosp_dir / "out" / "host" / "windows-arm64" / "bin"
    if canonical.is_dir():
        return canonical
    for d in (aosp_dir / "out" / "host").glob("windows*"):
        bin_dir = d / "bin"
        if bin_dir.is_dir():
            return bin_dir
    return None


def main() -> int:
    targets_str = os.environ.get("SOONG_TARGETS")
    if not targets_str:
        sys.exit("error: SOONG_TARGETS must be set")
    targets = targets_str.split()

    jobs = os.environ.get("JOBS") or str(os.cpu_count() or 4)
    aosp_dir = Path(os.environ.get("AOSP_DIR", "/workspace/aosp"))
    out_dir = Path(os.environ.get("OUT_DIR", "/workspace/out/windows-arm64"))
    patch_dir = Path(os.environ.get("PATCH_DIR", "/workspace/patches"))
    mingw_triple = os.environ.get("MINGW_TRIPLE", "aarch64-w64-mingw32")
    mingw_prefix = os.environ.get("MINGW_PREFIX", "/opt/llvm-mingw")

    apply_patches(aosp_dir, patch_dir)

    env = os.environ.copy()
    env["ANDROID_MINGW_PREFIX"] = mingw_prefix
    env["ANDROID_MINGW_TRIPLE"] = mingw_triple
    env["PATH"] = f"{mingw_prefix}/bin:{env.get('PATH', '')}"

    # HOST_CROSS_OS=windows + HOST_CROSS_ARCH=arm64 ask Soong to emit
    # windows-arm64 variants of each module in addition to the native
    # host build. Cross outputs get .exe suffixes.
    soong_cmd = (
        "set -e\n"
        "source build/envsetup.sh\n"
        "lunch aosp_arm64-eng\n"
        f"m -j{jobs} HOST_CROSS_OS=windows HOST_CROSS_ARCH=arm64 "
        f"{' '.join(targets)}\n"
    )
    log(f"cross-building for {mingw_triple}: {' '.join(targets)}")
    subprocess.run(
        ["bash", "-c", soong_cmd], cwd=aosp_dir, env=env, check=True
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    win_bin_dir = find_windows_bin_dir(aosp_dir)
    if win_bin_dir is None:
        print("!! could not locate windows host output directory", file=sys.stderr)
        return 1

    log(f"collecting from {win_bin_dir}")
    for tool in targets:
        for candidate_name in (f"{tool}.exe", tool):
            src = win_bin_dir / candidate_name
            if src.is_file():
                shutil.copy2(src, out_dir / candidate_name)
                print(f"  copied {candidate_name}")
                break

    # llvm-mingw uses UCRT; ship whatever DLLs the tools depend on
    # alongside, so the result is drop-in into an SDK directory.
    for dll in win_bin_dir.glob("*.dll"):
        shutil.copy2(dll, out_dir / dll.name)

    log(f"done. Artifacts in {out_dir}:")
    for entry in sorted(out_dir.iterdir()):
        print(f"  {entry.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

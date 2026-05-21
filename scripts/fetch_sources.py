#!/usr/bin/env python3
"""Clone the AOSP project repos listed in repos.json at a given tag.

We only need a few dozen specific project repos for the CMake-based
build (~5 GB on disk), not the entire AOSP manifest (~125 GB).

Reads from the environment:
  AOSP_BRANCH      required, a tag or branch name (e.g. platform-tools-35.0.2)
  SRC_DIR          optional, defaults to /workspace/src
  REPOS_JSON       optional, defaults to /workspace/repos.json
  JOBS             optional, parallel clone jobs (default min(cpu, 4))
"""

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def log(msg: str) -> None:
    print(f">>> {msg}", flush=True)


def clone_one(repo: dict, branch: str, src_dir: Path) -> tuple[str, bool, str]:
    """Clone one repo. Returns (path, ok, message).

    Existing checkouts are re-used only if their tip matches `branch`.
    Otherwise the directory is removed and re-cloned — we never want
    to silently build from a stale source tree (e.g. an
    aarbt-* CI cache restored from a different AOSP_BRANCH).
    """
    rel_path = repo["path"]
    # Project repos.json paths are relative to project root; strip the
    # leading "src/" so we can place them under whatever SRC_DIR is.
    if rel_path.startswith("src/"):
        rel_path = rel_path[len("src/"):]
    dest = src_dir / rel_path
    if dest.is_dir() and (dest / ".git").exists():
        # Resolve the requested branch (a tag, here) to a commit SHA in
        # the existing checkout, then compare against HEAD.
        want = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/{branch}^{{commit}}"],
            cwd=dest, capture_output=True, text=True,
        )
        have = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=dest, capture_output=True, text=True,
        )
        if want.returncode == 0 and have.returncode == 0 \
                and want.stdout.strip() == have.stdout.strip():
            return (str(dest), True, "already cloned (ref matches)")
        # Mismatch (or the requested tag isn't even in this clone) —
        # wipe and re-clone below.
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "git", "clone",
                "-c", "advice.detachedHead=false",
                "--depth", "1",
                "--branch", branch,
                repo["url"],
                str(dest),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return (str(dest), True, "cloned")
    except subprocess.CalledProcessError as e:
        return (str(dest), False, e.stderr.strip().split("\n")[-1])


def install_shims(src_dir: Path, patch_dir: Path) -> None:
    """Drop AOSP-generated source files into the cloned tree that
    libincfs and libbuildversion expect to find there. Upstream AOSP
    generates these at build time (sysprop_library, version stamping);
    for our out-of-tree CMake setup we ship pre-generated copies in
    patches/misc/ and copy them into place.
    """
    misc = patch_dir / "misc"
    if not misc.is_dir():
        return

    drops: list[tuple[str, str]] = [
        # (source filename under patches/misc, dest path under src_dir)
        ("IncrementalProperties.sysprop.h",
         "incremental_delivery/sysprop/include/IncrementalProperties.sysprop.h"),
        ("IncrementalProperties.sysprop.cpp",
         "incremental_delivery/sysprop/IncrementalProperties.sysprop.cpp"),
        ("platform_tools_version.h",
         "soong/cc/libbuildversion/include/platform_tools_version.h"),
    ]
    log("installing pre-generated source shims")
    for filename, rel_dest in drops:
        srcfile = misc / filename
        dest = src_dir / rel_dest
        if not srcfile.is_file():
            print(f"  !! missing source: {srcfile}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(srcfile, dest)
        print(f"  installed {filename} -> {rel_dest}")


def fix_aapt2_proto_paths(src_dir: Path) -> None:
    """aapt2's .proto files import sibling .proto files by their
    full AOSP path (e.g. `import "frameworks/base/tools/aapt2/Resources.proto"`).
    Our build runs protoc with --proto_path=src/base/tools/aapt2 only,
    so the full-path imports don't resolve. Rewrite them to bare
    filenames. Same fix lzhiyong applies via sed.
    """
    aapt2_dir = src_dir / "base" / "tools" / "aapt2"
    if not aapt2_dir.is_dir():
        return
    replacements = {
        "frameworks/base/tools/aapt2/Configuration.proto": "Configuration.proto",
        "frameworks/base/tools/aapt2/Resources.proto": "Resources.proto",
    }
    touched = []
    for proto in aapt2_dir.glob("*.proto"):
        text = proto.read_text()
        new = text
        for old, repl in replacements.items():
            new = new.replace(old, repl)
        if new != text:
            proto.write_text(new)
            touched.append(proto.name)
    if touched:
        log(f"rewrote proto import paths in: {', '.join(touched)}")


def apply_patches(src_dir: Path, patch_dir: Path) -> None:
    """Apply patches/*.patch to the cloned source trees. Each patch
    must have a `# Project: <path>` header naming the project under
    src/ that the patch applies to (e.g. `# Project: src/protobuf`).
    Idempotent — re-running is safe; already-applied patches are
    skipped via `git apply --check`.
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
            print(f"  !! {p.name} missing '# Project:' header, skipping")
            continue
        # Patch headers say `src/<repo>`; cloned trees live directly
        # under src_dir (which is /workspace/src by default).
        if project.startswith("src/"):
            project = project[len("src/"):]
        proj_dir = src_dir / project
        if not proj_dir.is_dir():
            print(f"  !! {p.name}: project dir not found: {proj_dir}")
            continue
        check = subprocess.run(
            ["git", "apply", "--check", "-p1", str(p)],
            cwd=proj_dir,
            capture_output=True,
        )
        if check.returncode == 0:
            subprocess.run(
                ["git", "apply", "-p1", str(p)], cwd=proj_dir, check=True
            )
            print(f"  applied {p.name} -> {project}")
        else:
            print(f"  skipped {p.name} (already applied or N/A for {project})")


def main() -> int:
    branch = os.environ.get("AOSP_BRANCH")
    if not branch:
        sys.exit("error: AOSP_BRANCH must be set (e.g. platform-tools-35.0.2)")

    src_dir = Path(os.environ.get("SRC_DIR", "/workspace/src"))
    repos_json = Path(os.environ.get("REPOS_JSON", "/workspace/repos.json"))
    patch_dir = Path(os.environ.get("PATCH_DIR", "/workspace/patches"))
    jobs = int(os.environ.get("JOBS") or min(os.cpu_count() or 4, 4))

    with repos_json.open() as f:
        repos = json.load(f)

    src_dir.mkdir(parents=True, exist_ok=True)
    log(f"cloning {len(repos)} repos at {branch} into {src_dir} ({jobs} parallel)")

    failures = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(clone_one, r, branch, src_dir): r for r in repos}
        for fut in as_completed(futures):
            dest, ok, msg = fut.result()
            marker = "ok " if ok else "FAIL"
            print(f"  [{marker}] {dest}: {msg}", flush=True)
            if not ok:
                failures.append((dest, msg))

    if failures:
        log(f"{len(failures)} clone(s) failed:")
        for dest, msg in failures:
            print(f"  {dest}: {msg}")
        return 1

    install_shims(src_dir, patch_dir)
    fix_aapt2_proto_paths(src_dir)
    apply_patches(src_dir, patch_dir)

    size = subprocess.check_output(
        ["du", "-sh", str(src_dir)], text=True
    ).split()[0]
    log(f"sources ready: {size} on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

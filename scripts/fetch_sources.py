#!/usr/bin/env python3
"""Clone the AOSP project repos listed in repos.json at a given tag.

Replaces the previous fetch_aosp.py which drove `repo init` + `repo
sync` against the whole AOSP manifest. We only need a few dozen
specific project repos for the CMake-based build, so cloning them
directly is faster and uses ~3-5 GB instead of ~125 GB.

Reads from the environment:
  AOSP_BRANCH      required, a tag or branch name (e.g. platform-tools-35.0.2)
  SRC_DIR          optional, defaults to /workspace/src
  REPOS_JSON       optional, defaults to /workspace/repos.json
  JOBS             optional, parallel clone jobs (default min(cpu, 4))
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def log(msg: str) -> None:
    print(f">>> {msg}", flush=True)


def clone_one(repo: dict, branch: str, src_dir: Path) -> tuple[str, bool, str]:
    """Clone one repo. Returns (path, ok, message)."""
    rel_path = repo["path"]
    # Project repos.json paths are relative to project root; strip the
    # leading "src/" so we can place them under whatever SRC_DIR is.
    if rel_path.startswith("src/"):
        rel_path = rel_path[len("src/"):]
    dest = src_dir / rel_path
    if dest.is_dir() and (dest / ".git").exists():
        return (str(dest), True, "already cloned")
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

    apply_patches(src_dir, patch_dir)

    size = subprocess.check_output(
        ["du", "-sh", str(src_dir)], text=True
    ).split()[0]
    log(f"sources ready: {size} on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

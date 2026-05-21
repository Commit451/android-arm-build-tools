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


def main() -> int:
    branch = os.environ.get("AOSP_BRANCH")
    if not branch:
        sys.exit("error: AOSP_BRANCH must be set (e.g. platform-tools-35.0.2)")

    src_dir = Path(os.environ.get("SRC_DIR", "/workspace/src"))
    repos_json = Path(os.environ.get("REPOS_JSON", "/workspace/repos.json"))
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

    size = subprocess.check_output(
        ["du", "-sh", str(src_dir)], text=True
    ).split()[0]
    log(f"sources ready: {size} on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

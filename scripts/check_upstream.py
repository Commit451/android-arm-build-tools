#!/usr/bin/env python3
"""Detect the latest platform-tools-* tag from upstream AOSP.

Queries android.googlesource.com directly (the canonical source).
Prints a JSON blob to stdout describing the latest tag plus the
tag we're currently pinned to in config.env, and writes the same
fields to $GITHUB_OUTPUT if running inside GitHub Actions.

Exits 0 either way — "new tag available" is communicated via the
`new` field, not the exit code. That keeps shell error-handling
simple in the workflow.
"""

import json
import os
import re
import sys
import urllib.request

TAGS_URL = "https://android.googlesource.com/platform/build/+refs/tags/?format=JSON"
TAG_RE = re.compile(r"^platform-tools-(\d+)\.(\d+)\.(\d+)$")


def fetch_tags() -> list[str]:
    """Fetch the tag list and return raw tag names."""
    req = urllib.request.Request(TAGS_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
    # googlesource prefixes responses with )]}' to prevent JSON
    # hijacking; strip it before parsing.
    if body.startswith(")]}'"):
        body = body[body.index("\n") + 1:]
    data = json.loads(body)
    return list(data.keys())


def latest_platform_tools(tags: list[str]) -> str | None:
    """Pick the platform-tools-* tag with the highest semver."""
    versioned = []
    for t in tags:
        m = TAG_RE.match(t)
        if m:
            versioned.append((tuple(int(x) for x in m.groups()), t))
    if not versioned:
        return None
    versioned.sort()
    return versioned[-1][1]


def current_from_config(config_path: str) -> str | None:
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AOSP_BRANCH="):
                return line.split("=", 1)[1].strip()
    return None


def main() -> int:
    config = os.environ.get("CONFIG_ENV", "config.env")

    latest = latest_platform_tools(fetch_tags())
    current = current_from_config(config)
    is_new = bool(latest and current and latest != current)

    result = {
        "latest": latest,
        "current": current,
        "new": is_new,
    }
    print(json.dumps(result, indent=2))

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"latest={latest or ''}\n")
            f.write(f"current={current or ''}\n")
            f.write(f"new={'true' if is_new else 'false'}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Detect the latest build-tools version we can both build and ship.

A version is shippable only if it satisfies BOTH:

  1. sdkmanager actually distributes a `build-tools;X.Y.Z` package for
     it (the user's drop-in target dir comes from sdkmanager — if
     sdkmanager doesn't have the version, the install script has
     nowhere to write to).
  2. AOSP tags a corresponding `platform-tools-X.Y.Z` in its source
     tree (we build from source — no tag, no source to build).

The intersection is smaller than either set alone. As of writing,
sdkmanager ships through 37.0.0 but AOSP's source tags stop at
35.0.2, so the latest shippable version is the highest AOSP tag
that also appears in sdkmanager's catalog (35.0.1, since AOSP's
35.0.2 isn't packaged by sdkmanager).

Prints a JSON blob to stdout and writes `latest`, `current`, `new`
to $GITHUB_OUTPUT when running under GitHub Actions. Exits 0 either
way; freshness is reported via the `new` field.
"""

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

SDKMANAGER_REPO_URL = "https://dl.google.com/android/repository/repository2-3.xml"
AOSP_TAGS_URL = "https://android.googlesource.com/platform/build/+refs/tags/?format=JSON"

# Stable versions only — skip rc / preview tags from either source.
SDK_PKG_RE = re.compile(r"^build-tools;(\d+)\.(\d+)\.(\d+)$")
AOSP_TAG_RE = re.compile(r"^platform-tools-(\d+)\.(\d+)\.(\d+)$")


def _fetch(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={"Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def sdkmanager_versions() -> set[tuple[int, int, int]]:
    """Stable build-tools versions sdkmanager publishes."""
    body = _fetch(SDKMANAGER_REPO_URL, accept="application/xml")
    root = ET.fromstring(body)
    out: set[tuple[int, int, int]] = set()
    # Schema uses unprefixed `path` on `remotePackage` elements.
    for pkg in root.iter("remotePackage"):
        path = pkg.attrib.get("path", "")
        m = SDK_PKG_RE.match(path)
        if m:
            out.add(tuple(int(x) for x in m.groups()))
    return out


def aosp_tag_versions() -> set[tuple[int, int, int]]:
    """Stable platform-tools-* tags from upstream AOSP build repo."""
    body = _fetch(AOSP_TAGS_URL, accept="application/json").decode("utf-8")
    # googlesource prefixes responses with )]}' to prevent JSON
    # hijacking; strip it before parsing.
    if body.startswith(")]}'"):
        body = body[body.index("\n") + 1:]
    data = json.loads(body)
    out: set[tuple[int, int, int]] = set()
    for tag in data.keys():
        m = AOSP_TAG_RE.match(tag)
        if m:
            out.add(tuple(int(x) for x in m.groups()))
    return out


def latest_shippable() -> str | None:
    """Highest version that both sdkmanager ships and AOSP tags."""
    common = sdkmanager_versions() & aosp_tag_versions()
    if not common:
        return None
    v = max(common)
    return f"platform-tools-{v[0]}.{v[1]}.{v[2]}"


def current_from_config(config_path: str) -> str | None:
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AOSP_BRANCH="):
                return line.split("=", 1)[1].strip()
    return None


def main() -> int:
    config = os.environ.get("CONFIG_ENV", "config.env")

    latest = latest_shippable()
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

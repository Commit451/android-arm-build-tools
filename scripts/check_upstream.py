#!/usr/bin/env python3
"""Resolve sdkmanager build-tools versions to AOSP source refs we can build.

For every `build-tools;X.Y.Z` sdkmanager publishes, we want to know
which AOSP tag (or branch) to clone for the build. The mapping is
non-trivial because AOSP has used two different tag schemes:

  - `platform-tools-X.Y.Z` — legacy, used through 35.0.2.
  - `android-NN.0.0_rN` — current scheme, where NN is the Android
    major and rN counts release snapshots (r1 = GA, r3 ~= QPR1,
    r4 ~= QPR2 etc.). Build-tools `X.Y.Z` rolls forward inside an
    Android-NN line at irregular cadence.

Resolution is three tiers, tried in order for each sdkmanager version:

  1. KNOWN_MAPPINGS — explicit, hand-verified table below. Wins
     unconditionally. Add entries here as we test a new version.
  2. Legacy `platform-tools-X.Y.Z` AOSP tag.
  3. Heuristic: pick the highest `android-(X-20).0.0_rN` tag, on the
     assumption that build-tools X.0.0 corresponds to Android major X
     (which has been true since the renaming).

If none of the three resolve, the version is `no-source` — Google has
published the binary but AOSP hasn't tagged the source yet. We track
it but can't build it until the matching android-NN.0.0_rN appears.

Output (stdout): JSON manifest of all sdkmanager versions and their
resolutions. Output to $GITHUB_OUTPUT (when set): the legacy
`latest`/`current`/`new` fields plus `next_build` (the highest
shippable version, used by the workflow to decide what to build).
Exits 0 either way.
"""

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

SDKMANAGER_REPO_URL = "https://dl.google.com/android/repository/repository2-3.xml"
AOSP_TAGS_URL = "https://android.googlesource.com/platform/build/+refs/tags/?format=JSON"

SDK_PKG_RE = re.compile(r"^build-tools;(\d+)\.(\d+)\.(\d+)$")
LEGACY_TAG_RE = re.compile(r"^platform-tools-(\d+)\.(\d+)\.(\d+)$")
ANDROID_TAG_RE = re.compile(r"^android-(\d+)\.0\.0_r(\d+)$")


# --- explicit mappings -----------------------------------------------------
# sdkmanager (major, minor, micro) -> AOSP source ref.
# Populated as we verify each version's source point empirically.
# An entry overrides both the legacy and heuristic resolvers.
KNOWN_MAPPINGS: dict[tuple[int, int, int], str] = {
    # build-tools 36.x lines up with Android 16 (NN = X + 20):
    (36, 0, 0): "android-16.0.0_r1",  # Android 16 GA — verified local + CI
    (36, 1, 0): "android-16.0.0_r3",  # Android 16 QPR1 — verified local + CI
    # build-tools 37.x -> Android 17 (same NN = X + 20 rule):
    (37, 0, 0): "android-17.0.0_r1",  # Android 17 GA — verified local (Pi) + CI
}


def _fetch(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={"Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def sdkmanager_versions() -> set[tuple[int, int, int]]:
    body = _fetch(SDKMANAGER_REPO_URL, accept="application/xml")
    root = ET.fromstring(body)
    out: set[tuple[int, int, int]] = set()
    for pkg in root.iter("remotePackage"):
        m = SDK_PKG_RE.match(pkg.attrib.get("path", ""))
        if m:
            out.add(tuple(int(x) for x in m.groups()))
    return out


def aosp_tags() -> set[str]:
    """All tags on platform/build — caller filters."""
    body = _fetch(AOSP_TAGS_URL, accept="application/json").decode("utf-8")
    if body.startswith(")]}'"):
        body = body[body.index("\n") + 1:]
    return set(json.loads(body).keys())


def _latest_android_rN(major: int, tags: set[str]) -> str | None:
    """Highest android-MAJOR.0.0_rN tag (by N), or None."""
    candidates = []
    for t in tags:
        m = ANDROID_TAG_RE.match(t)
        if m and int(m.group(1)) == major:
            candidates.append((int(m.group(2)), t))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def resolve(version: tuple[int, int, int], tags: set[str]) -> tuple[str | None, str]:
    """(source_ref, status) for one sdkmanager version. status ∈
    {mapped, legacy, heuristic, no-source}."""
    if version in KNOWN_MAPPINGS:
        return KNOWN_MAPPINGS[version], "mapped"
    legacy = f"platform-tools-{version[0]}.{version[1]}.{version[2]}"
    if legacy in tags:
        return legacy, "legacy"
    # Heuristic: build-tools major X -> Android major (X - 20). Only
    # applies once we've left the platform-tools-* naming convention
    # (i.e. version >= 36).
    if version[0] >= 36:
        android_major = version[0] - 20
        ref = _latest_android_rN(android_major, tags)
        if ref:
            return ref, "heuristic"
    return None, "no-source"


def current_from_config(config_path: str) -> str | None:
    try:
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("AOSP_BRANCH="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


def main() -> int:
    config = os.environ.get("CONFIG_ENV", "config.env")
    sdk_vs = sdkmanager_versions()
    tags = aosp_tags()

    resolved = []
    for v in sorted(sdk_vs):
        source, status = resolve(v, tags)
        resolved.append({
            "sdk": f"{v[0]}.{v[1]}.{v[2]}",
            "source": source,
            "status": status,
        })

    # The "next thing to build" = highest version with a usable source.
    # The workflow checks against existing releases and decides.
    buildable = [r for r in resolved if r["source"]]
    next_build = max(buildable, key=lambda r: tuple(int(x) for x in r["sdk"].split("."))) \
        if buildable else None

    # Legacy fields for back-compat with the workflow.
    latest = f"platform-tools-{next_build['sdk']}" if next_build else None
    current = current_from_config(config)
    is_new = bool(latest and current and latest != current)

    result = {
        "next_build": next_build,
        "versions": resolved,
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
            if next_build:
                f.write(f"next_sdk={next_build['sdk']}\n")
                f.write(f"next_source={next_build['source']}\n")
                f.write(f"next_status={next_build['status']}\n")
                f.write(f"next_tag=platform-tools-{next_build['sdk']}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

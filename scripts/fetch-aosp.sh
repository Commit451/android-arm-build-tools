#!/usr/bin/env bash
# Initialize and sync the AOSP source tree.
#
# Runs inside the build container. Idempotent: re-running just brings
# the tree up to date for the configured branch.

set -euo pipefail

: "${AOSP_BRANCH:?must be set}"
: "${JOBS:=$(nproc)}"

AOSP_DIR=${AOSP_DIR:-/workspace/aosp}
MANIFEST_URL=${MANIFEST_URL:-https://android.googlesource.com/platform/manifest}

mkdir -p "$AOSP_DIR"
cd "$AOSP_DIR"

if [[ ! -d .repo ]]; then
    echo ">>> repo init ($AOSP_BRANCH)"
    # --partial-clone        : fetch blobs on demand instead of upfront
    # --clone-filter=blob:none : same, classic spelling
    # --depth=1              : shallow clone each project
    # --no-tags              : skip the gigabytes of release tags
    # --current-branch       : only this branch's history
    repo init \
        --partial-clone \
        --clone-filter=blob:none \
        --depth=1 \
        --no-tags \
        --current-branch \
        -u "$MANIFEST_URL" \
        -b "$AOSP_BRANCH"
fi

# Drop in our local manifest (currently a no-op stub, see manifests/).
mkdir -p .repo/local_manifests
cp -f /workspace/manifests/build-tools.xml .repo/local_manifests/build-tools.xml

echo ">>> repo sync -j${JOBS}"
repo sync \
    --current-branch \
    --no-tags \
    --optimized-fetch \
    --prune \
    --force-sync \
    -j"${JOBS}"

echo ">>> sync complete: $(du -sh "$AOSP_DIR" | cut -f1) on disk"

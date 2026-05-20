#!/usr/bin/env bash
# Build the configured Soong targets for linux-arm64 hosts.
#
# Runs inside the linux-arm64 build container.

set -euo pipefail

: "${SOONG_TARGETS:?must be set, e.g. \"aapt2 zipalign aidl\"}"
: "${JOBS:=$(nproc)}"

AOSP_DIR=${AOSP_DIR:-/workspace/aosp}
OUT_DIR=${OUT_DIR:-/workspace/out/linux-arm64}

cd "$AOSP_DIR"

# Source the AOSP build environment. envsetup.sh defines `lunch`, `m`,
# and the helpers Soong needs.
# shellcheck disable=SC1091
source build/envsetup.sh

# `lunch` picks a target product + variant. For host tools we don't
# really care which device target we pick — Soong cross-builds host
# binaries regardless. aosp_arm64-eng is a safe minimal choice.
lunch aosp_arm64-eng

echo ">>> building host tools for linux_glibc-arm64: $SOONG_TARGETS"

# `m` builds named modules. Force the host arch to arm64 so we get
# native aarch64 binaries even if Soong's default host detection
# misfires.
#
# HOST_CROSS_OS/ARCH are unset for the native-host case (we want
# linux_glibc-arm64 == default host on this container).
m -j"${JOBS}" ${SOONG_TARGETS}

mkdir -p "$OUT_DIR"

# Soong's host output directory name varies by branch and host
# detection: linux-arm64, linux_glibc-arm64, linux-x86 (legacy), etc.
# Locate it by looking for any 'bin' dir under out/host/ that has at
# least one of our targets.
echo ">>> locating host output directory"
HOST_BIN_DIR=""
for candidate in "${AOSP_DIR}"/out/host/*/bin; do
    [[ -d "$candidate" ]] || continue
    for tool in $SOONG_TARGETS; do
        if [[ -x "$candidate/$tool" ]]; then
            HOST_BIN_DIR="$candidate"
            break 2
        fi
    done
done

if [[ -z "$HOST_BIN_DIR" ]]; then
    echo "!!! none of [$SOONG_TARGETS] found under ${AOSP_DIR}/out/host/*/bin" >&2
    echo "    directories that exist:" >&2
    find "${AOSP_DIR}/out/host" -maxdepth 2 -type d 2>/dev/null | sed 's/^/      /' >&2 || true
    exit 1
fi

HOST_LIB_DIR="${HOST_BIN_DIR%/bin}/lib64"
[[ -d "$HOST_LIB_DIR" ]] || HOST_LIB_DIR="${HOST_BIN_DIR%/bin}/lib"

echo ">>> collecting from $HOST_BIN_DIR"
for tool in $SOONG_TARGETS; do
    src="$HOST_BIN_DIR/$tool"
    if [[ -x "$src" ]]; then
        cp -v "$src" "$OUT_DIR/"
    else
        echo "!!! $tool not found at $src (may not be a standalone binary in this branch)"
    fi
done

# Some tools dlopen shared libs from lib/lib64; copy those alongside
# so the binaries are relocatable into an SDK build-tools directory.
if [[ -d "$HOST_LIB_DIR" ]]; then
    mkdir -p "$OUT_DIR/$(basename "$HOST_LIB_DIR")"
    cp -v "$HOST_LIB_DIR"/lib*.so "$OUT_DIR/$(basename "$HOST_LIB_DIR")/" 2>/dev/null || true
fi

echo ">>> done. Artifacts in $OUT_DIR:"
ls -la "$OUT_DIR"

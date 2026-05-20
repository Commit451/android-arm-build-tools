#!/usr/bin/env bash
# Cross-compile the configured Soong targets for windows-arm64.
#
# Runs inside the windows-arm64 build container, which has llvm-mingw
# available at /opt/llvm-mingw.
#
# Experimental: AOSP's stock host toolchain assumes x86_64-w64-mingw32.
# We patch Soong's mingw config to use aarch64-w64-mingw32 from
# llvm-mingw. Expect to land additional source patches in patches/
# for targets that don't build cleanly.

set -euo pipefail

: "${SOONG_TARGETS:?must be set}"
: "${JOBS:=$(nproc)}"
: "${MINGW_TRIPLE:=aarch64-w64-mingw32}"
: "${MINGW_PREFIX:=/opt/llvm-mingw}"

AOSP_DIR=${AOSP_DIR:-/workspace/aosp}
OUT_DIR=${OUT_DIR:-/workspace/out/windows-arm64}
PATCH_DIR=${PATCH_DIR:-/workspace/patches}

cd "$AOSP_DIR"

# Apply any patches that retarget mingw paths/triples. Patches are
# applied with `git apply` per-project; idempotent via --check first.
if [[ -d "$PATCH_DIR" ]] && compgen -G "$PATCH_DIR/*.patch" >/dev/null; then
    echo ">>> applying patches from $PATCH_DIR"
    for p in "$PATCH_DIR"/*.patch; do
        # Patches are expected to be in `git format-patch` form with a
        # leading `Subject: [project]` line we use to route them.
        project=$(grep -m1 '^# Project:' "$p" | sed 's/^# Project: //')
        if [[ -z "$project" ]]; then
            echo "!!! $p missing '# Project: <path>' header, skipping"
            continue
        fi
        (
            cd "$AOSP_DIR/$project"
            if git apply --check "$p" 2>/dev/null; then
                git apply "$p"
                echo "    applied $p to $project"
            else
                echo "    $p already applied or not applicable to $project"
            fi
        )
    done
fi

# Point Soong at llvm-mingw. The variable names below are read by
# soong/cc/config/x86_windows_host.go and friends; for branches where
# those variable names differ, this is the first place to look when
# the build can't find the cross-compiler.
export ANDROID_MINGW_PREFIX="${MINGW_PREFIX}"
export ANDROID_MINGW_TRIPLE="${MINGW_TRIPLE}"
export PATH="${MINGW_PREFIX}/bin:${PATH}"

# shellcheck disable=SC1091
source build/envsetup.sh
lunch aosp_arm64-eng

echo ">>> cross-building for ${MINGW_TRIPLE}: $SOONG_TARGETS"
# HOST_CROSS_OS=windows HOST_CROSS_ARCH=arm64 tells Soong to emit
# windows-arm64 variants of each named module in addition to the
# native host build. The cross variants get a .exe suffix.
m -j"${JOBS}" \
    HOST_CROSS_OS=windows \
    HOST_CROSS_ARCH=arm64 \
    $(for t in $SOONG_TARGETS; do echo "$t"; done)

mkdir -p "$OUT_DIR"

WIN_BIN_DIR="${AOSP_DIR}/out/host/windows-arm64/bin"
if [[ ! -d "$WIN_BIN_DIR" ]]; then
    # Some branches put cross outputs under a different name.
    WIN_BIN_DIR=$(find "${AOSP_DIR}/out/host" -maxdepth 2 -type d -name 'windows*' | head -n1)
fi

if [[ -z "${WIN_BIN_DIR:-}" || ! -d "$WIN_BIN_DIR" ]]; then
    echo "!!! could not locate windows host output directory" >&2
    exit 1
fi

echo ">>> collecting from $WIN_BIN_DIR"
for tool in $SOONG_TARGETS; do
    for candidate in "$WIN_BIN_DIR/${tool}.exe" "$WIN_BIN_DIR/${tool}"; do
        if [[ -f "$candidate" ]]; then
            cp -v "$candidate" "$OUT_DIR/"
            break
        fi
    done
done

# llvm-mingw uses UCRT and statically links libc++; copy any DLLs the
# tools depend on so the result is drop-in into an SDK directory.
for dll in "$WIN_BIN_DIR"/*.dll; do
    [[ -f "$dll" ]] && cp -v "$dll" "$OUT_DIR/"
done

echo ">>> done. Artifacts in $OUT_DIR:"
ls -la "$OUT_DIR"

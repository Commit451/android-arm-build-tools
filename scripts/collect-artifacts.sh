#!/usr/bin/env bash
# Package the built binaries into a tarball/zip per target, with a
# manifest so it's clear what's inside and what AOSP rev produced it.

set -euo pipefail

: "${TARGET:?must be set (linux-arm64 or windows-arm64)}"
: "${AOSP_BRANCH:?must be set}"
: "${BUILD_TOOLS_LABEL:=unknown}"

OUT_DIR=${OUT_DIR:-/workspace/out/${TARGET}}
DIST_DIR=${DIST_DIR:-/workspace/out/dist}

mkdir -p "$DIST_DIR"
cd "$OUT_DIR"

stamp=$(date -u +%Y%m%d)
base="android-build-tools-${BUILD_TOOLS_LABEL}-${TARGET}-${stamp}"

cat > MANIFEST.txt <<EOF
android-arm-buildtools artifact
target           : ${TARGET}
build-tools tag  : ${BUILD_TOOLS_LABEL}
aosp branch      : ${AOSP_BRANCH}
built (UTC)      : $(date -u +"%Y-%m-%dT%H:%M:%SZ")
host             : $(uname -srm)
EOF

if [[ "$TARGET" == windows-* ]]; then
    archive="${DIST_DIR}/${base}.zip"
    rm -f "$archive"
    zip -r "$archive" . -x '*.tar.*' '*.zip'
else
    archive="${DIST_DIR}/${base}.tar.xz"
    rm -f "$archive"
    tar -cJf "$archive" --exclude='*.tar.*' --exclude='*.zip' .
fi

echo ">>> packaged: $archive ($(du -h "$archive" | cut -f1))"

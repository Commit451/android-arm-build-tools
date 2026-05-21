#!/usr/bin/env bash
# install android-arm-buildtools binaries into your Android SDK.
# See https://github.com/Commit451/android-arm-buildtools
#
# Replaces the linux-x86_64 native binaries (aapt2, aidl, zipalign,
# split-select) that sdkmanager installed with aarch64-glibc builds,
# so AGP/Gradle can run on arm64 Linux machines.

set -euo pipefail

REPO="Commit451/android-arm-buildtools"
SDK=""
BT_VERSION="auto"

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

  --sdk PATH       Path to your Android SDK (default: \$ANDROID_HOME,
                   \$ANDROID_SDK_ROOT, or ~/Android/Sdk).
  --version X.Y.Z  build-tools version (default: latest GitHub Release).
                   The matching build-tools must already be installed
                   via sdkmanager — this script only replaces the four
                   native binaries.
  -h, --help       this message.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --sdk)     SDK="$2"; shift 2 ;;
        --version) BT_VERSION="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# --- platform sanity checks --------------------------------------------
if [ "$(uname -s)" != "Linux" ]; then
    echo "error: targets Linux, you're on $(uname -s)" >&2
    exit 1
fi
case "$(uname -m)" in
    aarch64|arm64) ;;
    *)
        echo "error: these binaries are aarch64; your machine reports $(uname -m)." >&2
        echo "       Google's sdkmanager already provides x86_64 — you don't need this project." >&2
        exit 1
        ;;
esac

# --- resolve SDK path --------------------------------------------------
if [ -z "$SDK" ]; then
    SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
fi
if [ ! -d "$SDK" ]; then
    echo "error: Android SDK not found at $SDK" >&2
    echo "       set \$ANDROID_HOME or pass --sdk PATH." >&2
    exit 1
fi

# --- resolve version ---------------------------------------------------
if [ "$BT_VERSION" = "auto" ]; then
    LATEST_TAG=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
        | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' \
        | head -n1)
    if [ -z "$LATEST_TAG" ]; then
        echo "error: couldn't query the latest release from GitHub." >&2
        echo "       pass --version X.Y.Z explicitly." >&2
        exit 1
    fi
    BT_VERSION=${LATEST_TAG#platform-tools-}
    echo "latest release: $LATEST_TAG"
fi

DEST="$SDK/build-tools/$BT_VERSION"
if [ ! -d "$DEST" ]; then
    echo "error: $DEST does not exist." >&2
    echo "       install the matching build-tools first:" >&2
    echo "         sdkmanager \"build-tools;$BT_VERSION\"" >&2
    exit 1
fi

TAG="platform-tools-$BT_VERSION"
BASE="https://github.com/$REPO/releases/download/$TAG"

echo "installing $TAG (aarch64-linux-gnu) into $DEST"
for tool in aapt2 aidl zipalign split-select; do
    printf "  %-13s ... " "$tool"
    curl -fsSL "$BASE/$tool" -o "$DEST/$tool.tmp"
    chmod +x "$DEST/$tool.tmp"
    mv "$DEST/$tool.tmp" "$DEST/$tool"
    echo "ok"
done

echo
"$DEST/aapt2" version | head -n1 || true
echo "done. \`./gradlew :app:assembleDebug\` should now run."

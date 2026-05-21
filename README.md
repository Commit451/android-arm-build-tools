# android-arm-buildtools

Drop-in `aapt2`, `aidl`, `zipalign`, and `split-select` binaries for
**Linux on ARM64** — the four Android SDK build-tools that
Gradle/AGP actually invokes during a normal app build.

Google's `sdkmanager` only ships these for `linux-x86_64`. On a
Raspberry Pi, Asahi Linux machine, ARM Chromebook, Ampere server,
or native-arm64 WSL, AGP fails with `exec format error` until you
swap in arm64 builds. This project ships those, automatically
rebuilt for each new upstream AOSP `platform-tools-*` release.

## Install

You already need the matching build-tools installed via
`sdkmanager` first (the Java parts — apksigner, dx, etc. — come
from there; we only replace the four native binaries).

```sh
sdkmanager "build-tools;35.0.2"
```

Then run the installer:

```sh
curl -fsSL https://raw.githubusercontent.com/Commit451/android-arm-buildtools/main/install.sh | bash
```

That picks up the latest Release, detects your SDK via
`$ANDROID_HOME` / `$ANDROID_SDK_ROOT` / `~/Android/Sdk`, and drops
the binaries into `$SDK/build-tools/<version>/`.

To pin a specific version, or use a non-default SDK path:

```sh
curl -fsSL https://raw.githubusercontent.com/Commit451/android-arm-buildtools/main/install.sh -o install.sh
chmod +x install.sh
./install.sh --version 35.0.2 --sdk /opt/android-sdk
```

The script refuses to run on non-aarch64 hosts and on hosts that
don't already have the matching `build-tools/<version>/` directory.

## Verify

After install, this should work in any AGP project without
"exec format error":

```sh
./gradlew :app:assembleDebug
```

Or smoke-test the binary directly:

```sh
$ANDROID_HOME/build-tools/35.0.2/aapt2 version
# Android Asset Packaging Tool (aapt) 2.X-...
```

## Releases

All builds are on the [Releases tab](https://github.com/Commit451/android-arm-buildtools/releases).
A GitHub Actions workflow polls AOSP daily for new
`platform-tools-*` tags and publishes a fresh build for each one.

If you'd rather grab a single binary directly, each Release has
`aapt2`, `aidl`, `zipalign`, `split-select`, a combined `.tar.xz`,
and `SHA256SUMS` attached.

## Building from source / contributing

See [`DEV.md`](DEV.md).

## License

MIT. See [`LICENSE`](LICENSE).

\\ ゜o゜)ノ

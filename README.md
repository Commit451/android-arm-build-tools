# android-arm-build-tools

Drop-in `aapt2`, `aidl`, `zipalign`, and `split-select` binaries for
**Linux on ARM64** — the four Android SDK build-tools that
Gradle/AGP actually invokes during a normal app build.

Google's `sdkmanager` only ships these for `linux-x86_64`. On a
Raspberry Pi, Asahi Linux machine, ARM Chromebook, Ampere server,
or native-arm64 WSL, AGP fails with `exec format error` until you
swap in arm64 builds. This project ships those, automatically
rebuilt as upstream AOSP publishes new build-tools source tags.

## Install

You already need the matching build-tools installed via
`sdkmanager` first (the Java parts — apksigner, dx, etc. — come
from there; we only replace the four native binaries).

```sh
sdkmanager "build-tools;36.1.0"
```

Then run the installer:

```sh
curl -fsSL https://raw.githubusercontent.com/Commit451/android-arm-build-tools/main/install.sh | bash
```

That picks up the latest Release, detects your SDK via
`$ANDROID_HOME` / `$ANDROID_SDK_ROOT` / `~/Android/Sdk`, and drops
the binaries into `$SDK/build-tools/<version>/`.

To pin a specific version, or use a non-default SDK path:

```sh
curl -fsSL https://raw.githubusercontent.com/Commit451/android-arm-build-tools/main/install.sh -o install.sh
chmod +x install.sh
./install.sh --version 36.0.0 --sdk /opt/android-sdk
```

Available versions are listed on the [Releases tab](https://github.com/Commit451/android-arm-build-tools/releases).
The script refuses to run on non-aarch64 hosts and on hosts that
don't already have the matching `build-tools/<version>/` directory.

### AGP 9.x: also point aapt2 at the arm64 binary

Android Gradle Plugin 9.x stopped using the SDK's `aapt2` and
instead pulls its own from Maven
(`com.android.tools.build:aapt2:<agp-version>:linux`), which is
x86_64-only. The drop-in above is still needed by other steps,
but on AGP 9+ you also have to tell Gradle to use the arm64
binary directly. Add this to your project's `gradle.properties`
(or `~/.gradle/gradle.properties` to apply globally):

```properties
android.aapt2FromMavenOverride=/home/you/Android/Sdk/build-tools/36.1.0/aapt2
```

Use the full path to the `aapt2` that this project's installer
just wrote. Restart the Gradle daemon (`./gradlew --stop`) after
changing the property so it picks up the new binary.

If you're on AGP 8.x or older you can skip this step — those
versions still shell out to `$SDK/build-tools/<v>/aapt2`.

## Verify

After install, this should work in any AGP project without
"exec format error":

```sh
./gradlew :app:assembleDebug
```

Or smoke-test the binary directly:

```sh
$ANDROID_HOME/build-tools/36.1.0/aapt2 version
# Android Asset Packaging Tool (aapt) 2.X-...
```

## Compatibility

Binaries are built on Debian 12 (Bookworm) — glibc 2.36, GCC 12 —
so they need glibc 2.36+ and GLIBCXX_3.4.30+ at runtime. Distros
that work out of the box:

- Raspberry Pi OS Bookworm (glibc 2.36) ✅
- Debian 12+ ✅
- Ubuntu 22.04+ ✅ (glibc 2.35 — close enough; libstdc++ matches)
- Fedora 38+ / Asahi Linux ✅
- Anything newer than the above ✅

If you're on something older, [build from source](DEV.md) against
your distro's libc.

## Available versions

We ship the versions where AOSP has tagged public source we can
build from. As of writing:

- `36.1.0` — Android 16 QPR1, built from `android-16.0.0_r3`
- `36.0.0` — Android 16 GA, built from `android-16.0.0_r1`
- `35.0.1` — Android 15, built from `platform-tools-35.0.1`

AGP doesn't require build-tools to match `compileSdk`, so any of
the above paired with e.g. `compileSdk 36` works fine.

### What about 37.0.0 / 36.2.0 / future versions?

sdkmanager sometimes publishes a build-tools version before AOSP
tags the corresponding source publicly. 37.0.0 is the current
example: Google ships the binary but the underlying source hasn't
appeared in any public AOSP branch we can build from. When that
changes, our daily workflow auto-detects the new tag and publishes
a matching arm64 build (no action needed on this end). See
[`DEV.md`](DEV.md) for the resolver design.

## Releases

All builds are on the [Releases tab](https://github.com/Commit451/android-arm-build-tools/releases).
A GitHub Actions workflow runs daily, resolves each sdkmanager
build-tools version to an AOSP source ref (legacy `platform-tools-*`
tag or the newer `android-NN.0.0_rN` scheme), and publishes a
fresh release when something new shows up.

If you'd rather grab a single binary directly, each Release has
`aapt2`, `aidl`, `zipalign`, `split-select`, a combined `.tar.xz`,
and `SHA256SUMS` attached.

## Building from source / contributing

See [`DEV.md`](DEV.md).

## License

MIT. See [`LICENSE`](LICENSE).

\\ ゜o゜)ノ

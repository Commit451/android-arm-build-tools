# android-arm-buildtools

Build the Android SDK `build-tools` native binaries (aapt, aapt2,
aidl, zipalign, dexdump, split-select) for architectures Google
does not ship: **Linux ARM64 (aarch64)** and **Windows ARM64**.

This is what unblocks compiling and packaging Android apps on:

- Linux on ARM (Raspberry Pi, Ampere/Graviton servers, Asahi Linux,
  ARM-native WSL, Pinebook, etc.)
- Windows on ARM (Surface Pro X / Surface Pro 9 5G / WoA dev kits)

Google ships `darwin-arm64` binaries in build-tools 34.0.0+, so
Apple Silicon Macs are already covered upstream and are not a
target here.

## Status — read this first

| Target          | Status                                                                |
| --------------- | --------------------------------------------------------------------- |
| `linux-arm64`   | **Not currently functional.** Needs a refactor to cross-build from x86_64 — see below. |
| `windows-arm64` | Experimental, untested. Same refactor will apply.                     |

Earlier versions of this README claimed `linux-arm64` was the
"primary path" built natively in an ARM64 container. A cloud-side
test on 2026-05-20 against AOSP `android-15.0.0_r1` proved this
wrong: AOSP's `prebuilts/` directory contains only `linux-x86`
variants of the toolchain Soong needs to bootstrap itself (Go,
clang, build-tools). There is no `prebuilts/go/linux-arm64/`. Soong
fails immediately on an ARM64 host with:

```
prebuilts/go/linux-x86/bin/go: cannot execute binary file:
Exec format error
```

### Path forward

The fix is to **cross-build from an x86_64 host** instead of
building natively on an arm64 host. Soong supports this via
`HOST_CROSS_OS=linux HOST_CROSS_ARCH=arm64` (the same mechanism
the windows-arm64 path uses for that target). Outputs land in
`out/host/linux_glibc-arm64/bin/` and run on arm64 Linux.

Concretely, the Dockerfile would change from `arm64v8/ubuntu:22.04`
to `ubuntu:22.04` (x86_64), the build container itself runs
natively on any x86_64 host or under Apple Silicon's Rosetta, and
the Makefile passes the cross-host flags to `m`. None of this is
in place yet — the current `linux-arm64.Dockerfile` and
`build_linux_arm64.py` assume the now-disproven native-arm64
approach.

### Other test findings worth knowing

- **Disk: ~125 GB on disk for AOSP source alone**, not the 15-30 GB
  this README originally claimed. That was the size of the shallow
  git history; the working tree (actual source files) is much
  bigger. Plan on ~200 GB free for source + Soong out/.
- **`android.googlesource.com` rate-limits cloud IPs aggressively.**
  `repo sync -j8` from a Hetzner cloud server trips HTTP 429 within
  minutes. `scripts/fetch_aosp.py` is now throttled to
  `--jobs-network=2 --retry-fetches=5`.
- The first build attempt from scratch surfaced unrelated bugs in
  the project (Makefile `SHELL` syntax, ARM-incompatible apt
  packages, root-vs-builder bind-mount permissions) — these are
  fixed in the commit history but unrelated to the larger
  cross-build refactor.

## How it works (one paragraph)

Everything runs in Docker. `docker buildx` builds an
`arm64v8/ubuntu:22.04` image with AOSP's build dependencies plus
the `repo` tool. The container clones AOSP source at the
configured tag, then runs Soong (`source build/envsetup.sh && m
aapt2 …`) to produce host binaries. The `windows-arm64` image
layers `llvm-mingw` on top and exports `HOST_CROSS_OS=windows
HOST_CROSS_ARCH=arm64` so Soong cross-compiles `.exe`s alongside
the native build.

## Prerequisites

- **Docker** with `buildx` (Docker Desktop 4.x+, or Docker Engine
  20.10+ with the buildx plugin).
- **Disk: ~200 GB free.** Approximate breakdown (revised after a
  real run — original estimate was wrong by 4-5×):
  - AOSP source working tree: ~125-150 GB in `aosp/`
  - Soong build intermediates: ~30-50 GB in `aosp/out/`
  - ccache (persisted across runs): up to ~5 GB in `.ccache/`
  - Built artifacts: a few hundred MB in `out/`
- **RAM:** 16 GB minimum, 32 GB recommended.
- **Host arch:**
  - **Apple Silicon Mac**: works natively, Docker Desktop handles
    arm64 containers without any setup.
  - **Linux ARM64 host**: works natively.
  - **Linux x86_64 host**: works under QEMU emulation; expect
    **3-10x slowdown** on the compile step. Run `make binfmt`
    once to register the emulator with the kernel.
  - **Windows x86_64 host**: works under WSL2 + Docker Desktop
    with binfmt; similar slowdown as Linux x86_64.

If you don't have an ARM64 box at all and don't want to wait for
QEMU emulation, see [Building in the cloud](#building-in-the-cloud)
below.

## First-run walkthrough

**Budget ~1-2 hours of mostly-unattended wall time on a fast
machine.** Subsequent runs are minutes.

The full pipeline runs in three phases. You can invoke them
separately while learning the tool, or run them all at once with
`make linux-arm64`.

### 1. Build the Docker image (~5-10 min)

```sh
make image-linux-arm64
```

This produces an `arm64v8/ubuntu:22.04` image with AOSP deps + the
`repo` tool. Done once; cached across runs.

### 2. Sync the AOSP source (~10-30 min, network-bound)

```sh
make fetch
```

Clones the AOSP tree at `$AOSP_BRANCH` (default
`android-15.0.0_r1`) into `./aosp/` using `repo` with
`--partial-clone --depth=1 --no-tags`. About 15-30 GB on disk.

### 3. Build the binaries (~30-90 min native, multiples of that under emulation)

```sh
make linux-arm64
```

Runs Soong inside the container. You'll see these phases scroll by
in order — knowing what to expect helps tell "working" from "hung":

| Output you'll see                | Phase                                | Typical time |
| -------------------------------- | ------------------------------------ | ------------ |
| `bootstrapping build environment` | Soong compiles its own build system  | 2-5 min      |
| `Reading product config`         | Soong parses every `Android.bp`      | 2-5 min      |
| `[N/M] <action>`                 | Ninja runs the actual compilation    | 20-80 min    |
| `>>> collecting from …`          | Our script copies binaries to `out/` | seconds      |
| `>>> packaged: …`                | `collect_artifacts.py` makes tarball | seconds      |

Or skip the phase-by-phase approach and just:

```sh
make linux-arm64
```

`linux-arm64` depends on `fetch` which depends on
`image-linux-arm64`, so one command does the whole pipeline.

## What you'll get

Default Soong targets (override via `SOONG_TARGETS` in
`config.env`):

```
aapt aapt2 aidl dexdump split-select zipalign
```

Output layout:

```
out/linux-arm64/
    aapt
    aapt2
    aidl
    dexdump
    split-select
    zipalign
    lib64/                          # shared libs the binaries dlopen

out/dist/
    android-build-tools-35.0.0-linux-arm64-YYYYMMDD.tar.xz
```

## Verifying the build

After `make linux-arm64` succeeds, confirm the binaries actually
run on the target arch:

```sh
# Type check
file ./out/linux-arm64/aapt2
# expected: ELF 64-bit LSB ... ARM aarch64 ...

# Runs?
./out/linux-arm64/aapt2 version
# expected: Android Asset Packaging Tool (aapt) 2:...

./out/linux-arm64/zipalign 2>&1 | head -1
# expected: Zip alignment utility
```

If you're on a non-ARM host, run them inside the build container
(which is ARM64 Linux):

```sh
make shell-linux-arm64
# inside the container:
out/linux-arm64/aapt2 version
```

## Installing into your Android SDK

```sh
SDK=~/Android/Sdk
BT=35.0.0
cp -v out/linux-arm64/* "$SDK/build-tools/$BT/"
chmod +x "$SDK/build-tools/$BT/"{aapt,aapt2,aidl,zipalign,dexdump,split-select}
```

On Windows ARM64, copy `out/windows-arm64/*.exe` into the
equivalent `build-tools\<version>\` directory of your SDK.

Confirm AGP/Gradle picks them up: run `./gradlew :app:assembleDebug`
on any app project and watch for `aapt2 daemon started` without
"exec format error" or "cannot execute binary file".

## Configuration

Knobs live in `config.env`. Override on the `make` command line:

```sh
# Build against an older AOSP tag.
make linux-arm64 AOSP_BRANCH=android-14.0.0_r1

# Build only aapt2 (much faster).
make linux-arm64 SOONG_TARGETS=aapt2

# Cap parallelism (default = container nproc).
make linux-arm64 JOBS=4
```

| Variable             | Default                                              | Meaning                                |
| -------------------- | ---------------------------------------------------- | -------------------------------------- |
| `AOSP_BRANCH`        | `android-15.0.0_r1`                                  | AOSP tag/branch to build from.         |
| `BUILD_TOOLS_LABEL`  | `35.0.0`                                             | Metadata for artifact filenames.       |
| `SOONG_TARGETS`      | `aapt aapt2 aidl dexdump split-select zipalign`      | Soong module names to build.           |
| `JOBS`               | `nproc`                                              | Parallel build jobs.                   |
| `CCACHE_DIR`         | `./.ccache`                                          | ccache location; persisted across runs. |
| `LLVM_MINGW_VERSION` | `20240619`                                           | llvm-mingw release for Windows ARM64.  |

## Building in the cloud

If you don't have an ARM64 box, or want a "click button, get
binaries" pipeline:

### GitHub Actions

GitHub provides native `ubuntu-24.04-arm` runners — free for
public repos, paid for private. Standard ARM runners only have
~14 GB disk, which is too small for an AOSP checkout. Use the
larger SKU (`ubuntu-24.04-arm-16-core`, ~150 GB disk).

Drop something like this in `.github/workflows/build.yml`:

```yaml
name: build-linux-arm64
on: [workflow_dispatch]
jobs:
  build:
    runs-on: ubuntu-24.04-arm-16-core
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache@v4
        with:
          path: |
            aosp
            .ccache
          key: aosp-${{ hashFiles('config.env') }}
      - run: make linux-arm64
      - uses: actions/upload-artifact@v4
        with:
          name: linux-arm64
          path: out/linux-arm64/
```

The `actions/cache` step is critical — it persists the AOSP tree
and ccache between runs, so only the first invocation pays the
full sync + build cost. After that, runs are minutes.

### Hetzner Cloud

`CAX41` (16 vCPU Ampere, 32 GB RAM) is ~€0.04/hr ≈ $0.045/hr.
Best $/perf for serious iteration. Provision once, ssh in,
`git clone` this repo, `make linux-arm64`, keep the source tree on
disk for fast incremental rebuilds. First build runs in 20-40 min;
a typical iteration cycle costs ~$1-2 of compute.

### Oracle Cloud Free Tier

Ampere A1 (4 vCPU / 24 GB RAM) is perpetually free. Slower than
CAX41 (4 cores vs 16) so first build is 60-90 min, but if you
keep it always-on, $0 forever. Caveat: free-tier availability
varies by region; sometimes you can't provision one.

### AWS / GCP / Azure

Graviton (AWS), Axion/Tau T2A (GCP), Cobalt 100 (Azure) all work
fine. No compelling reason to pick over Hetzner unless you're
already there or need integration with other resources.

## Troubleshooting

**`exec format error` when starting the container.**
You're on an x86_64 host without binfmt registered. Run `make
binfmt` once (requires `--privileged`), or use Docker Desktop
which sets this up automatically.

**`repo init` hangs or 403s.**
`android.googlesource.com` rate-limits aggressively when running
from cloud IPs. Retry, or set `MANIFEST_URL` in
`scripts/fetch_aosp.py` to a GitHub mirror like
`https://github.com/aosp-mirror/platform_manifest`.

**`No space left on device` mid-build.**
Soong's `out/` intermediates are large. Either free disk, or
build fewer targets at once with `SOONG_TARGETS=aapt2`.

**Soong errors with `no rule to make target X`.**
The module name in `SOONG_TARGETS` doesn't exist in your AOSP
branch. Look it up:
```sh
make shell-linux-arm64
grep -rn 'name: "X"' aosp/ | head
```

**Build is mysteriously slow even after the first run.**
ccache probably isn't persisting. Check `.ccache/` exists on the
host and is bind-mounted into the container. Inside the container:
```sh
ccache -s
```
should show non-zero `cache hit (direct)` after a rebuild. If
zero, the bind mount isn't working — check `make -n linux-arm64`
output for the `-v` flag pointing at `.ccache`.

**`aapt2 version` segfaults or "GLIBC_X.Y not found" on the host.**
You built against a newer glibc than your host ships. Either
build against an older `AOSP_BRANCH` (older AOSP = older glibc
baseline) or update your host glibc.

**Windows ARM64 build fails with "unknown target aarch64-w64-mingw32".**
Soong's mingw config still points at x86_64. This is the
experimental part. Look at `aosp/build/soong/cc/config/x86_windows_host.go`
(filename varies by branch) and add a patch to `patches/` that
swaps the triple. The build script applies anything matching
`patches/*.patch` with a `# Project:` header.

## When things really break

If `make linux-arm64` exits non-zero and the error isn't actionable:

1. Re-run with full output captured:
   ```sh
   make linux-arm64 2>&1 | tee build.log
   ```
2. The interesting lines are usually the last 50 of `build.log`
   plus any `FAILED:` lines from Soong/Ninja above them.
3. To poke at build state interactively, drop into the container
   and reproduce by hand:
   ```sh
   make shell-linux-arm64
   # inside:
   cd aosp
   source build/envsetup.sh
   lunch aosp_arm64-eng
   m -j4 aapt2     # or whichever target was failing
   ```
4. If filing an issue, please include: AOSP branch, host arch
   (`uname -srm` on the host), the last 50 lines of `build.log`,
   and whether `make distclean && make linux-arm64` changes
   anything.

## Project layout

```
.
├── Makefile                       # entry point — `make help` lists targets
├── config.env                     # version pins, knobs
├── docker/
│   ├── linux-arm64.Dockerfile
│   └── windows-arm64.Dockerfile
├── manifests/
│   └── build-tools.xml            # local repo manifest stub
├── scripts/
│   ├── fetch_aosp.py
│   ├── build_linux_arm64.py
│   ├── build_windows_arm64.py
│   └── collect_artifacts.py
├── patches/                       # source patches applied before build
├── aosp/                          # repo sync target (gitignored)
└── out/                           # built binaries land here (gitignored)
```

## Why not just download prebuilts?

For Linux ARM64, no official prebuilts exist — Google ships only
`linux-x86_64`. Community alternatives (`lzhiyong/android-sdk-tools`,
Termux packages) target **Android** (bionic libc), not Linux
desktop (glibc), so they won't run on a Raspberry Pi or Asahi
Linux — only on a phone in Termux.

For Windows ARM64, nothing prebuilt is published anywhere I know of.

## References

- AOSP source: <https://source.android.com/>
- Soong build system: <https://source.android.com/docs/setup/build>
- `llvm-mingw` (Windows ARM64 toolchain): <https://github.com/mstorsjo/llvm-mingw>
- AOSP mirror on GitHub: <https://github.com/aosp-mirror>

## License

android-arm-buildtools is available under the MIT license. See the LICENSE file for more info.

\ ゜o゜)ノ
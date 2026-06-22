# DEV.md — building android-arm-build-tools from source

For people who want to rebuild the binaries themselves, hack on
the pipeline, add more tools, or debug a CI failure when AOSP
moves upstream and a patch goes stale. End users just need
[`README.md`](README.md).

## Why this project exists

Android SDK build-tools' native binaries only ship for `linux-x86_64`,
`darwin-x86_64`, and `darwin-arm64` (from build-tools 34.0.0+).
There is no `linux-aarch64` build, and AOSP doesn't have a clean
upstream path to produce one: there's no `prebuilts/go/linux-arm64`,
no `prebuilts/clang/host/linux-arm64`, and Soong's
`arm64_linux_host.go` targets bionic-on-Linux (not glibc).
[`MIGRATION.md`](MIGRATION.md) has the full archaeology.

This project bypasses Soong entirely. It clones ~40 specific AOSP
project repos, compiles them with `gcc-aarch64-linux-gnu` against
glibc via CMake, and ships the resulting binaries. The shape is
borrowed from [`lzhiyong/android-sdk-tools`](https://github.com/lzhiyong/android-sdk-tools)
(which targets bionic-on-Android via the NDK); we retarget the same
source set to glibc-on-Linux.

## Architecture

```
   repos.json
       │
       ▼
   scripts/fetch_sources.py
       │  git clone --depth=1 per repo at $AOSP_BRANCH
       │  + apply patches/*.patch
       │  + install patches/misc/ shim source files
       ▼
   src/                          ~5 GB
       │
       ▼
   scripts/build_linux_arm64.py
       │
       ├──► host protoc build      build/host-protoc/
       │     (cmake src/protobuf w/ system gcc)
       │
       └──► target cross-build     build/linux-arm64/
             (cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-aarch64-linux-gnu.cmake
                    -DPROTOC_PATH=...)
                │
                ├── third-party libs (abseil, fmtlib, pcre,
                │   libpng, expat, boringssl, protobuf,
                │   jsoncpp, zopfli, googletest)
                │
                ├── AOSP-internal libs (cmake/lib/*.cmake)
                │     libbase, liblog, libcutils, libutils,
                │     libandroidfw, libincfs, libselinux,
                │     libsepol, libziparchive, libbuildversion,
                │     libpackagelistparser, libprocessgroup
                │
                └── tools (cmake/build-tools/*.cmake)
                      aapt2, aidl, zipalign, split-select
       │
       ▼
   scripts/collect_artifacts.py
       │
       ▼
   out/linux-arm64/{aapt2,aidl,zipalign,split-select}
   out/dist/android-build-tools-X.Y.Z-linux-arm64-YYYYMMDD.tar.xz
```

A force-included compatibility header
(`cmake/shims/glibc_compat.h`) covers the bionic-vs-glibc gaps:
bare C11 atomic typedef names in C++ TUs, `__builtin_available`,
and `<cstring>` / `<memory>` / `<limits>` not pulled in transitively.

Specific in-source patches in `patches/` handle per-file issues
the shim can't cover (GNU strerror_r, `st_mtime` macro vs
designated initializers, incomplete random-access iterator,
GCC ICE workarounds, etc.).

## Build it yourself

### Prerequisites

- **Docker** (Docker Desktop 4.x+, or Docker Engine 20.10+).
- **Disk: ~15 GB free.** Breakdown: src/ ~5 GB, build/ ~5-10 GB.
- **RAM:** 8 GB minimum.
- **Host arch:** anything Docker supports. The build container's
  `gcc-aarch64-linux-gnu` cross-compiles regardless of host arch.
  - On arm64 hosts (Apple Silicon, Linux arm64): the cross-toolchain
    is effectively native.
  - On x86_64 hosts: the build container runs natively as x86_64,
    cross-compiling to arm64 — no QEMU emulation involved.

### Run it

```sh
make linux-arm64
```

That's the whole pipeline: image build → source fetch → host
protoc → target cross-build → artifact collection. First run is
~10-20 min; subsequent runs are minutes thanks to ccache + cached
sources.

```sh
make help               # list all targets
make image-linux-arm64  # just build the docker image
make fetch              # just clone sources
make shell-linux-arm64  # drop into the build container for debugging
make clean              # rm -rf out/ build/
make distclean          # also rm src/, ccache, and the docker image
```

### Configuration

Knobs in `config.env`, overridable on the make command line:

| Variable            | Default                                       | Meaning                            |
| ------------------- | --------------------------------------------- | ---------------------------------- |
| `AOSP_BRANCH`       | `android-16.0.0_r3`                           | git tag/branch cloned for every repo (local-dev default; CI overrides) |
| `BUILD_TOOLS_LABEL` | `36.1.0`                                      | metadata for artifact filenames    |
| `TARGETS`           | `aapt2 aidl zipalign split-select`            | which binaries to build            |
| `JOBS`              | container `nproc`                             | parallel build jobs                |
| `CCACHE_DIR`        | `./.ccache`                                   | persisted across runs              |

```sh
make linux-arm64 AOSP_BRANCH=android-16.0.0_r1 BUILD_TOOLS_LABEL=36.0.0 JOBS=2
```

## CI / upstream tracker

`.github/workflows/upstream-watch.yml` runs daily at 08:00 UTC.
`scripts/check_upstream.py` resolves every `build-tools;X.Y.Z`
sdkmanager publishes to a build-from source ref via three tiers,
tried in order:

  1. **`KNOWN_MAPPINGS`** — an explicit, hand-verified table at the
     top of the script. Wins unconditionally. Add an entry after
     verifying a new version's source point.
  2. **Legacy `platform-tools-X.Y.Z`** AOSP tag — works for the
     pre-rename versions (through 35.0.2).
  3. **Heuristic `android-(X-20).0.0_rN`** — for `X >= 36`, take the
     highest `_rN` of the matching Android major. Latest revision
     wins (`_r4` over `_r3` etc.).

If none resolve, the version is `no-source` — sdkmanager has it
but no buildable AOSP ref exists yet. We track it in the script
output but don't try to build until a source ref is available.

The workflow's cron path reads the resolver's `next_*` outputs
(next_tag / next_source / next_sdk) and dispatches a build against
those. If a release already exists for `next_tag`, the workflow
skips — keeping cron idle until something new appears upstream.

Manual dispatch with `force_tag` overrides everything; use it for
backfill or to rebuild a specific version (see Releases tab).

You can manually dispatch the workflow at any time from the
[Actions tab](https://github.com/Commit451/android-arm-build-tools/actions/workflows/upstream-watch.yml).
The optional `force_tag` input skips detection and builds a
specific tag — useful for re-running after fixing a broken patch.

If a new upstream tag breaks the build (AOSP source moved in a
way our patches don't anticipate), the workflow fails loud and
emails the repo admins. The fix is usually:

1. Local: `make linux-arm64 AOSP_BRANCH=<new tag>`
2. See what breaks, update the relevant file in `patches/` or
   `cmake/shims/glibc_compat.h`
3. Push, re-dispatch the workflow

## Adding more tools

`aapt`, `dexdump`, and the rest are intentionally out of scope —
AGP doesn't invoke them in a normal app build, and `dexdump` in
particular drags in `src/art/` which is the most bionic-tangled
subtree of AOSP. If you want them anyway:

1. Add to `TARGETS` in `config.env`.
2. Include the relevant fragment in `cmake/build-tools/CMakeLists.txt`
   (`aapt.cmake` is already vendored — `dexdump.cmake` was
   deleted but recoverable from git history).
3. Build and iterate on whatever breaks — see the existing
   `patches/` for the pattern.

## Project layout

```
.
├── README.md                          # end-user install instructions
├── DEV.md                             # this file
├── MIGRATION.md                       # historical: Soong → CMake pivot
├── LICENSE                            # MIT
├── install.sh                         # user-facing install script
│
├── Makefile                           # `make help`
├── config.env                         # version pins, knobs
│
├── docker/
│   └── linux-arm64.Dockerfile         # ubuntu:24.04 + cross-toolchain
│
├── repos.json                         # AOSP source repos to clone
│
├── scripts/
│   ├── fetch_sources.py               # clone repos.json + apply patches
│   ├── build_linux_arm64.py           # cmake/ninja driver
│   ├── collect_artifacts.py           # tar artifacts into out/dist
│   └── check_upstream.py              # CI: detect new AOSP tags
│
├── cmake/
│   ├── toolchain-aarch64-linux-gnu.cmake
│   ├── shims/glibc_compat.h           # force-included, bionic→glibc shim
│   ├── stubs/atrace_stub.cpp          # no-op libcutils atrace_* impls
│   ├── lib/                           # AOSP-internal static libs
│   └── build-tools/                   # per-binary CMakeLists
│
├── patches/                           # source patches applied at fetch time
│   ├── *.patch                        # each has a `# Project:` header
│   └── misc/                          # pre-generated source shims
│
├── .github/workflows/
│   └── upstream-watch.yml             # daily AOSP poll + auto-release
│
├── src/                               # cloned AOSP repos (gitignored)
├── build/                             # CMake build dirs (gitignored)
└── out/                               # built binaries (gitignored)
```

## Troubleshooting

**`PermissionError: [Errno 13]` creating `/workspace/src`.**
Bind-mount permission mismatch — the container runs as `builder`
(uid 1000) but the host workspace is owned by your user. Run
`chown -R 1000:1000 .` on the project directory, or run inside CI
where the workflow does this automatically.

**Build fails part-way through, error in a file you haven't touched.**
Almost always a bionic-vs-glibc gap that hasn't been shimmed.
Look at `cmake/shims/glibc_compat.h` and the existing
`patches/*.patch` for the pattern, then add a new patch or extend
the shim.

**`No space left on device` mid-build.**
The `out/`, `build/`, and `src/` dirs together can hit 15 GB. If
you're on a constrained box, run with `JOBS=1` (lower peak
intermediate sizes) or move src/build off the constrained volume.

**Out of memory during compile.**
protobuf and aapt2 under `-O3` are the canaries. Cap `JOBS`
(e.g. `make linux-arm64 JOBS=2` on an 8 GB box). 8 GB RAM is the
documented floor.

**Workflow fails on a new AOSP tag.**
AOSP source moved in a way an existing patch doesn't anticipate.
`git apply --check` will refuse and the build won't get to compile.
Refresh the patch context lines locally, push, re-dispatch.

## References

- AOSP source: <https://source.android.com/>
- AOSP mirror on GitHub: <https://github.com/aosp-mirror>
- lzhiyong/android-sdk-tools (the bionic-targeted predecessor):
  <https://github.com/lzhiyong/android-sdk-tools>

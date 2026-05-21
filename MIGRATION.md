# Migration: Soong → CMake + glibc cross-toolchain

## Why

The current implementation tries to drive AOSP's Soong build system in
an `arm64v8/ubuntu:22.04` container, expecting it to bootstrap natively
on an aarch64 Linux host. A 2026-05-20 cloud test proved this doesn't
work: AOSP `android-15.0.0_r1` ships only `linux-x86` prebuilts of its
toolchain (Go, clang, build-tools), and the one host target Soong has
for arm64 Linux (`arm64_linux_host.go`) is **bionic-arm64**, not
**glibc-arm64**. The end goal — a `aapt2` you can drop into a Raspberry
Pi / Asahi / Ampere server's Android SDK — requires glibc.

There is no first-class path inside AOSP to produce a glibc-arm64
build of these tools. We need to leave Soong behind.

## The approach we're adopting

Borrow the shape of [`lzhiyong/android-sdk-tools`](https://github.com/lzhiyong/android-sdk-tools)
— that project also bypasses Soong, but it targets bionic-on-Android
via the Android NDK. We do the same shape but retarget to **glibc on
Linux** via `aarch64-linux-gnu-gcc` from Ubuntu's
`gcc-aarch64-linux-gnu` package.

### High-level shape

| Phase    | Current (Soong)                                       | New (CMake)                                                |
| -------- | ----------------------------------------------------- | ---------------------------------------------------------- |
| Fetch    | `repo init` + `repo sync` of the whole AOSP manifest (~125 GB) | `git clone --depth=1` of ~40 specific AOSP project repos (~3-5 GB) |
| Build env | `arm64v8/ubuntu:22.04` (arm64 host, broken)         | `ubuntu:24.04` (any arch) + `gcc-aarch64-linux-gnu`        |
| Build    | `lunch aosp_arm64-eng && m aapt2` via Soong/Make    | `cmake -B build && ninja -C build aapt2`                   |
| Output   | `out/host/linux_glibc-arm64/bin/aapt2` (doesn't exist) | `build/aapt2` — glibc-arm64 ELF, drop-in for AOSP SDK     |

### Why this works where the old approach didn't

- `gcc-aarch64-linux-gnu` is a normal Debian/Ubuntu package; it's a
  glibc cross-toolchain for aarch64 Linux, supported for years. No
  AOSP-side host config gymnastics.
- CMake handles cross-compilation natively via toolchain files. No
  Soong, no Kati, no Ninja-via-Go-bootstrap.
- The C/C++ source code for `aapt2` and friends is the same regardless
  of target glibc arch — once it builds for glibc-x86_64 (AOSP's host
  build path), it generally builds for glibc-arm64 with just a
  compiler swap.
- We don't need to fetch all of AOSP because we explicitly enumerate
  the source repos each tool needs.

## What this migration touches

**Removed:**
- `scripts/build_linux_arm64.py` — was a Soong invoker; rewritten
- `scripts/fetch_aosp.py` — was `repo`-based; replaced by per-repo cloning
- `docker/linux-arm64.Dockerfile` — was arm64v8 native build; replaced by x86-or-any with cross-toolchain
- `manifests/build-tools.xml` — local manifest stub for `repo`; no longer used

**Added:**
- `repos.json` — list of AOSP project repos to clone (path + url)
- `cmake/toolchain-aarch64-linux-gnu.cmake` — CMake toolchain file pinning the cross-compiler
- `cmake/aapt2/CMakeLists.txt` (and similar for other tools) — vendored / adapted from lzhiyong
- `scripts/fetch_sources.py` — replaces `fetch_aosp.py`; clones what's listed in `repos.json`

**Kept (largely unchanged):**
- `Makefile` — surface API stays the same (`make linux-arm64`, `make clean`); the targets just delegate to new scripts
- `scripts/collect_artifacts.py` — packaging is target-independent
- `patches/` directory and the patch-application loop pattern — we'll just add new patches
- The GitHub repo, the LICENSE, the overall README structure
- `windows-arm64` path stays as-is for now (already experimental; can be
  rewritten the same way later with `aarch64-w64-mingw32` from llvm-mingw)

## Open questions / known risks

1. **Will lzhiyong's CMakeLists compile against glibc with just a
   toolchain swap?** The source has bionic-isms (Android log macros,
   `<sys/system_properties.h>`, `__system_property_get`, etc.) that
   they shim out via `patches/misc/`. For glibc target, those shims
   are mostly still right (they stub things out to no-ops, which is
   fine on either libc), but we may hit ones they didn't need to
   address because NDK provided them.

2. **Library dependency graph.** `aapt2` depends transitively on
   libbase, libutils, libcutils, libziparchive, libpng, libexpat,
   libprotobuf, libandroidfw, more. Each needs its own CMakeLists,
   and each has its own bionic-isms. lzhiyong did this work for
   their target; we're piggybacking on it.

3. **Host bootstraps.** Protoc has to run during the build to
   generate C++ from `.proto` files. lzhiyong builds a host protoc
   first, then cross-builds the target. We need the same pattern.

4. **Maintenance.** lzhiyong's project pinned at platform-tools-35.0.2.
   We may pin similarly; bumping to a newer AOSP tag will likely need
   patch updates.

5. **Scope.** This migration starts with `aapt2` only. Other binaries
   (`aapt`, `aidl`, `zipalign`, `dexdump`, `split-select`) follow once
   the first one is working.

## Migration steps (in order)

1. **Write this file.** (You're reading it.)
2. **Replace the Dockerfile** with a glibc cross-build environment.
   Verify `aarch64-linux-gnu-gcc --version` works inside it.
3. **Write `fetch_sources.py`** + `repos.json`. Start with lzhiyong's
   list as a baseline; trim later if we find unused repos.
4. **Add the CMake toolchain file** pinning the cross-compiler.
5. **Vendor lzhiyong's `aapt2` CMakeLists** and any patches needed
   for the deps it pulls in. Re-target NDK paths → glibc cross.
6. **Update the Makefile** to drive cmake/ninja instead of make/Soong.
7. **Build `aapt2`.** Iterate on patches until it links.
8. **Verify the binary** runs on an arm64 Linux machine
   (cax31 in Hetzner, or any arm64 host with glibc).
9. **Repeat for the other tools** in `SOONG_TARGETS`. Rename that
   variable to `CMAKE_TARGETS` or similar while we're at it.
10. **Update README** to describe the new approach honestly.
11. **Decide on windows-arm64**: leave as Soong-experimental, or
    pivot to the same CMake + llvm-mingw pattern. Defer until after
    linux-arm64 ships.

## Not in scope

- A full rewrite of the windows-arm64 path. The current Soong-based
  windows-arm64 Dockerfile and script stay; we just know they
  inherit the same issues and will need their own pivot later.
- Producing a `.deb` or other distro-packaging. We ship raw
  binaries; distro packaging is a downstream concern.
- Caching / CDN of pre-built artifacts. Each user builds for
  themselves for now.

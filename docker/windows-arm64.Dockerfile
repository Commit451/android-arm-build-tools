# Cross-compile environment for Windows ARM64 targets.
#
# Reuses the Linux ARM64 build environment and layers on llvm-mingw,
# which is currently the only mingw-w64 toolchain that targets ARM64
# Windows (binutils' mingw-w64 is x86-only).
#
# This image is experimental. AOSP's host toolchain is wired for
# x86_64-w64-mingw32; we patch Soong configs at build time to point at
# aarch64-w64-mingw32. Expect rough edges and likely source patches.

ARG BASE_IMAGE=android-arm-buildtools-linux-arm64:latest
FROM ${BASE_IMAGE}

USER root

ARG LLVM_MINGW_VERSION=20240619

# llvm-mingw publishes ubuntu-22.04 aarch64 host packages with all
# four cross targets (i686, x86_64, armv7, aarch64) bundled. We grab
# the aarch64-host build; if you're on x86_64-host emulation, swap to
# the x86_64 variant for speed.
RUN set -eux; \
    arch="$(uname -m)"; \
    case "$arch" in \
        aarch64) pkg="llvm-mingw-${LLVM_MINGW_VERSION}-ucrt-ubuntu-22.04-aarch64.tar.xz" ;; \
        x86_64)  pkg="llvm-mingw-${LLVM_MINGW_VERSION}-ucrt-ubuntu-22.04-x86_64.tar.xz" ;; \
        *) echo "Unsupported host arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/llvm-mingw.tar.xz \
        "https://github.com/mstorsjo/llvm-mingw/releases/download/${LLVM_MINGW_VERSION}/${pkg}"; \
    mkdir -p /opt/llvm-mingw; \
    tar -xJf /tmp/llvm-mingw.tar.xz -C /opt/llvm-mingw --strip-components=1; \
    rm /tmp/llvm-mingw.tar.xz

ENV PATH=/opt/llvm-mingw/bin:${PATH} \
    MINGW_TRIPLE=aarch64-w64-mingw32 \
    MINGW_PREFIX=/opt/llvm-mingw

# Sanity-check the toolchain at build time so a broken image fails
# here rather than 30 minutes into a Soong build.
RUN aarch64-w64-mingw32-clang --version \
    && aarch64-w64-mingw32-clang++ --version

USER builder
WORKDIR /workspace

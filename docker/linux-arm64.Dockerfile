# Build environment for cross-compiling Android SDK build-tools to
# linux-glibc-arm64.
#
# Works on x86_64 and arm64 hosts. CMake configures the build as a
# cross-compile to aarch64-linux-gnu; on x86_64 hosts that runs through
# the gcc-aarch64-linux-gnu package, on arm64 hosts it runs natively
# (the system gcc IS aarch64-linux-gnu-gcc).
#
# This is a deliberate departure from the previous Soong-based pipeline
# — see MIGRATION.md for the why.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        bison \
        build-essential \
        ca-certificates \
        ccache \
        cmake \
        curl \
        file \
        flex \
        git \
        gnupg \
        gperf \
        gcc-aarch64-linux-gnu \
        g++-aarch64-linux-gnu \
        libssl-dev \
        ninja-build \
        pkg-config \
        protobuf-compiler \
        python3 \
        python-is-python3 \
        sudo \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

# Non-root user so workspace bind-mounts stay manageable. Same UID/GID
# the previous Dockerfile used so anyone with a chowned workspace from
# the earlier setup doesn't need to re-chown.
ARG USERNAME=builder
ARG USER_UID=1000
ARG USER_GID=1000
# Ubuntu 24.04's base image ships with a default `ubuntu` user at
# uid 1000; remove it so we can claim the uid for `builder`.
RUN if id -u 1000 >/dev/null 2>&1; then userdel -r "$(id -un 1000)" 2>/dev/null || true; fi \
    && if getent group 1000 >/dev/null 2>&1; then groupdel "$(getent group 1000 | cut -d: -f1)" 2>/dev/null || true; fi \
    && groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME}

USER ${USERNAME}
RUN git config --global user.name "AOSP Builder" \
    && git config --global user.email "builder@android-arm-buildtools.local"

ENV USE_CCACHE=1 \
    CCACHE_DIR=/workspace/.ccache

WORKDIR /workspace

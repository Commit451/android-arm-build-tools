# Build environment for native Linux ARM64 AOSP builds.
#
# Built with: docker buildx build --platform=linux/arm64 ...
# On x86_64 hosts this runs under QEMU emulation (slow but functional);
# on aarch64 hosts it runs natively.
#
# AOSP gained official aarch64 Linux host support around Android 14;
# older branches will not build here without cross-compilation
# scaffolding that this Dockerfile does not provide.

FROM arm64v8/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Packages here come from AOSP's "Establishing a Build Environment"
# doc plus a few that recent branches' lunch/m steps complain about.
RUN apt-get update && apt-get install -y --no-install-recommends \
        bc \
        bison \
        build-essential \
        ca-certificates \
        ccache \
        cmake \
        curl \
        file \
        flex \
        fontconfig \
        git \
        git-lfs \
        gnupg \
        gperf \
        imagemagick \
        libelf-dev \
        libffi-dev \
        libgl1-mesa-dev \
        liblz4-tool \
        libncurses5 \
        libsdl1.2-dev \
        libssl-dev \
        libxml2 \
        libxml2-utils \
        lzop \
        ninja-build \
        openjdk-17-jdk \
        openssh-client \
        pkg-config \
        procps \
        python-is-python3 \
        python3 \
        python3-pip \
        rsync \
        schedtool \
        sudo \
        unzip \
        x11proto-core-dev \
        xsltproc \
        zip \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# `repo` is the AOSP source manager. Install the launcher; the version
# inside the tree is upgraded by `repo` itself on first use.
RUN curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo \
        -o /usr/local/bin/repo \
    && chmod +x /usr/local/bin/repo

# AOSP refuses to build as root. Create a non-root user with sudo so
# the build runs as a regular user but we can still install things if
# needed during iteration.
ARG USERNAME=builder
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME}

# Git identity is required by `repo init` even though we're not committing.
USER ${USERNAME}
RUN git config --global user.name "AOSP Builder" \
    && git config --global user.email "builder@android-arm-buildtools.local" \
    && git config --global color.ui false \
    && git config --global init.defaultBranch main

# AOSP build system reads this to decide how much parallelism it gets.
ENV USE_CCACHE=1 \
    CCACHE_EXEC=/usr/bin/ccache \
    CCACHE_DIR=/workspace/.ccache

WORKDIR /workspace

# android-arm-buildtools — top-level orchestration.
#
# All real work happens inside Docker. This Makefile builds the
# container images, runs the AOSP sync inside them, runs the per-target
# build script, and packages the result.

SHELL := /usr/bin/env bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

# ---- knobs ------------------------------------------------------------
include config.env
export

# Resolve project dir to an absolute path; bind-mounted into containers.
PROJECT_DIR := $(abspath .)

# Image names.
IMG_LINUX_ARM64   := android-arm-buildtools-linux-arm64:latest
IMG_WINDOWS_ARM64 := android-arm-buildtools-windows-arm64:latest

# Common docker-run flags. Build steps run non-interactively so they
# work under CI; shell-* targets layer `-it` on top for a real terminal.
DOCKER_RUN_ARGS := \
	--rm \
	-v $(PROJECT_DIR):/workspace \
	-w /workspace \
	-e AOSP_BRANCH=$(AOSP_BRANCH) \
	-e BUILD_TOOLS_LABEL=$(BUILD_TOOLS_LABEL) \
	-e SOONG_TARGETS="$(SOONG_TARGETS)" \
	-e JOBS=$(JOBS)

DOCKER_RUN_INTERACTIVE := $(DOCKER_RUN_ARGS) -it

# ---- public targets ---------------------------------------------------
.PHONY: all linux-arm64 windows-arm64 fetch clean distclean \
        image-linux-arm64 image-windows-arm64 \
        shell-linux-arm64 shell-windows-arm64 \
        binfmt help

help:
	@cat <<-'EOF'
	  android-arm-buildtools
	  ----------------------
	  make linux-arm64       build everything for Linux ARM64
	  make windows-arm64     cross-build for Windows ARM64 (experimental)
	  make all               both of the above
	  make fetch             just sync AOSP source
	  make clean             remove out/
	  make distclean         remove out/, aosp/, ccache, and images
	  make shell-linux-arm64 drop into a shell in the linux-arm64 image
	  make binfmt            (Linux hosts) register QEMU for foreign-arch images
	EOF

all: linux-arm64 windows-arm64

# One-time binfmt setup so x86_64 Linux hosts can run arm64 containers.
# Docker Desktop does this automatically; bare docker engine doesn't.
binfmt:
	docker run --privileged --rm tonistiigi/binfmt --install arm64

# ---- images -----------------------------------------------------------
image-linux-arm64:
	docker buildx build \
		--platform=linux/arm64 \
		--load \
		-t $(IMG_LINUX_ARM64) \
		-f docker/linux-arm64.Dockerfile \
		docker/

image-windows-arm64: image-linux-arm64
	docker buildx build \
		--platform=linux/arm64 \
		--load \
		--build-arg BASE_IMAGE=$(IMG_LINUX_ARM64) \
		--build-arg LLVM_MINGW_VERSION=$(LLVM_MINGW_VERSION) \
		-t $(IMG_WINDOWS_ARM64) \
		-f docker/windows-arm64.Dockerfile \
		docker/

# ---- workflow ---------------------------------------------------------
fetch: image-linux-arm64
	docker run $(DOCKER_RUN_ARGS) \
		$(IMG_LINUX_ARM64) \
		python3 scripts/fetch_aosp.py

linux-arm64: fetch
	docker run $(DOCKER_RUN_ARGS) \
		$(IMG_LINUX_ARM64) \
		bash -c 'python3 scripts/build_linux_arm64.py && TARGET=linux-arm64 python3 scripts/collect_artifacts.py'

windows-arm64: fetch image-windows-arm64
	docker run $(DOCKER_RUN_ARGS) \
		$(IMG_WINDOWS_ARM64) \
		bash -c 'python3 scripts/build_windows_arm64.py && TARGET=windows-arm64 python3 scripts/collect_artifacts.py'

# ---- shells (for iteration / debugging) -------------------------------
shell-linux-arm64: image-linux-arm64
	docker run $(DOCKER_RUN_INTERACTIVE) $(IMG_LINUX_ARM64) bash

shell-windows-arm64: image-windows-arm64
	docker run $(DOCKER_RUN_INTERACTIVE) $(IMG_WINDOWS_ARM64) bash

# ---- cleanup ----------------------------------------------------------
clean:
	rm -rf out/

distclean: clean
	rm -rf aosp/ .ccache/
	-docker image rm $(IMG_LINUX_ARM64) $(IMG_WINDOWS_ARM64) 2>/dev/null

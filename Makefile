# android-arm-buildtools — top-level orchestration.
#
# All real work happens inside Docker. This Makefile builds the
# container image, clones the AOSP project repos listed in
# repos.json, drives a CMake cross-build, and packages the result.
#
# See MIGRATION.md for the architecture switch from Soong to CMake.

SHELL := /bin/bash
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
	-e TARGETS="$(TARGETS)" \
	-e JOBS=$(JOBS)

DOCKER_RUN_INTERACTIVE := $(DOCKER_RUN_ARGS) -it

# ---- public targets ---------------------------------------------------
.PHONY: all linux-arm64 windows-arm64 fetch clean distclean \
        image-linux-arm64 image-windows-arm64 \
        shell-linux-arm64 shell-windows-arm64 \
        help

help:
	@cat <<-'EOF'
	  android-arm-buildtools
	  ----------------------
	  make linux-arm64       cross-build TARGETS for linux-glibc-arm64
	  make windows-arm64     (still Soong-based, broken — see MIGRATION.md)
	  make fetch             clone AOSP project repos into src/
	  make clean             remove out/ and build/
	  make distclean         clean + remove src/, ccache, and docker images
	  make shell-linux-arm64 drop into a shell in the build image
	  make help              this message

	  Configure via config.env or VAR=value on the command line, e.g.:
	    make linux-arm64 TARGETS=aapt2 AOSP_BRANCH=platform-tools-35.0.2
	EOF

all: linux-arm64

# ---- images -----------------------------------------------------------
# Multi-arch: build for the host's native platform. CMake handles the
# cross-compile to aarch64 internally via the toolchain file.
image-linux-arm64:
	docker build \
		-t $(IMG_LINUX_ARM64) \
		-f docker/linux-arm64.Dockerfile \
		docker/

image-windows-arm64: image-linux-arm64
	docker buildx build \
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
		python3 scripts/fetch_sources.py

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
	rm -rf out/ build/

distclean: clean
	rm -rf src/ .ccache/
	-docker image rm $(IMG_LINUX_ARM64) $(IMG_WINDOWS_ARM64) 2>/dev/null

# Root CMakeLists for android-arm-buildtools.
#
# Builds Android SDK build-tools native binaries (starting with aapt2)
# for linux-glibc-arm64, using a cross-toolchain (or natively if the
# host arch already matches).
#
# Pass cmake/toolchain-aarch64-linux-gnu.cmake via -DCMAKE_TOOLCHAIN_FILE.
# Pass -DPROTOC_PATH=/path/to/host-protoc with a host-architecture
# protoc binary; the cross-compiled protoc cannot run on the build host.
#
# Structure adapted from lzhiyong/android-sdk-tools; we keep their
# per-tool .cmake files but trim third-party deps to the subset aapt2
# needs and retarget the toolchain from NDK/Android to glibc/Linux.

cmake_minimum_required(VERSION 3.18)
project(android-arm-buildtools)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
enable_language(ASM)

# Position-independent code is required for several of the AOSP libs;
# matches lzhiyong's setup. fcolor-diagnostics is clang-only; only set
# it if the compiler accepts it.
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag(-fcolor-diagnostics HAVE_FCOLOR_DIAGNOSTICS)
if(HAVE_FCOLOR_DIAGNOSTICS)
    add_compile_options(-fcolor-diagnostics)
endif()
add_compile_options(-fPIC -Wno-attributes)

# Force-included compat header — see cmake/shims/glibc_compat.h.
# Provides stubs for Clang/bionic-only constructs (e.g.
# __builtin_available) so AOSP source compiles under GCC + glibc.
add_compile_options(-include ${PROJECT_SOURCE_DIR}/cmake/shims/glibc_compat.h)

# Make off_t / lseek 64-bit on 32-bit platforms (and harmless on 64-bit).
add_compile_definitions(_FILE_OFFSET_BITS=64)

# Marker version recorded in libbuildversion (see patches/misc).
set(TOOLS_VERSION 35.0.1)

# Where fetch_sources.py drops the cloned AOSP project repos.
set(SRC ${PROJECT_SOURCE_DIR}/src)

# ---- protoc handling -------------------------------------------------
# Target-side protobuf is built from src/protobuf below; but the
# protoc compiler we use to generate C++ from .proto files has to run
# on the BUILD host, so it has to be a separately-built host binary.
# Caller passes -DPROTOC_PATH=...
set(PROTOC_COMPILER)
if(DEFINED PROTOC_PATH)
    set(PROTOC_COMPILER ${PROTOC_PATH})
    if(NOT EXISTS ${PROTOC_COMPILER})
        message(FATAL_ERROR "PROTOC_PATH=${PROTOC_COMPILER} does not exist")
    endif()
    message(STATUS "Using host protoc: ${PROTOC_COMPILER}")
else()
    message(WARNING "PROTOC_PATH not set; aapt2 proto sources will not regenerate")
endif()

# ---- third-party libraries -------------------------------------------
# Subset of lzhiyong's list, trimmed to what aapt2 actually needs.
# Each subdir is a cloned AOSP project repo with its own CMakeLists.
set(ABSL_PROPAGATE_CXX_STD ON CACHE BOOL "" FORCE)
set(protobuf_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(protobuf_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

add_subdirectory(${SRC}/abseil-cpp EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/fmtlib EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/pcre EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/libpng EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/expat/expat EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/boringssl EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/protobuf EXCLUDE_FROM_ALL)
# Additional third-party libs needed by the non-aapt2 tools:
#   - jsoncpp: aapt + split-select
#   - zopfli:  zipalign
#   - googletest: aidl links gmock
add_subdirectory(${SRC}/jsoncpp EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/zopfli EXCLUDE_FROM_ALL)
add_subdirectory(${SRC}/googletest EXCLUDE_FROM_ALL)
# protobuf's config.h is wired into its include path via
# patches/protobuf-include-config.patch, applied at fetch time.

# ---- AOSP internal libraries + tools ---------------------------------
add_subdirectory(cmake/lib)
add_subdirectory(cmake/build-tools)

# CMake toolchain file for cross-compiling to linux-glibc-arm64.
#
# Pass to cmake with:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-aarch64-linux-gnu.cmake ...
#
# On x86_64 hosts, this uses the gcc-aarch64-linux-gnu apt package.
# On arm64 hosts, the system gcc IS aarch64-linux-gnu-gcc (it's the
# same binary, just a different name); the build is effectively
# native, but we keep the cross-compile structure so the same CMake
# invocation works on both host architectures.

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

# Allow override (e.g. CC=/path/to/clang) via env vars, but default to
# the standard gnu-cross binaries from Ubuntu/Debian.
if(NOT DEFINED CMAKE_C_COMPILER)
    set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
endif()
if(NOT DEFINED CMAKE_CXX_COMPILER)
    set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
endif()
if(NOT DEFINED CMAKE_ASM_COMPILER)
    set(CMAKE_ASM_COMPILER aarch64-linux-gnu-gcc)
endif()
if(NOT DEFINED CMAKE_AR)
    set(CMAKE_AR aarch64-linux-gnu-ar)
endif()
if(NOT DEFINED CMAKE_RANLIB)
    set(CMAKE_RANLIB aarch64-linux-gnu-ranlib)
endif()
if(NOT DEFINED CMAKE_STRIP)
    set(CMAKE_STRIP aarch64-linux-gnu-strip)
endif()

# Library/include search paths.
#
# - On x86_64 hosts with the cross-toolchain installed, aarch64 libs
#   and headers live under /usr/aarch64-linux-gnu/.
# - On arm64 hosts (where this build is effectively native), the
#   same libs live under /usr/ via the multiarch /usr/lib/aarch64-linux-gnu/
#   layout.
# Cover both with FIND_ROOT_PATH; BOTH mode lets CMake fall back to
# normal search if the rooted paths come up empty.
set(CMAKE_FIND_ROOT_PATH
    /usr/aarch64-linux-gnu
    /usr/lib/aarch64-linux-gnu
    /
)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)

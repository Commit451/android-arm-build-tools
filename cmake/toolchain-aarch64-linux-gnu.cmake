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

# Look for libraries / headers in the cross sysroot under
# /usr/aarch64-linux-gnu/, not in the host's /usr/.
set(CMAKE_FIND_ROOT_PATH /usr/aarch64-linux-gnu)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# pkg-config: don't use host's .pc files when cross-compiling.
set(ENV{PKG_CONFIG_DIR} "")
set(ENV{PKG_CONFIG_LIBDIR} "/usr/aarch64-linux-gnu/lib/pkgconfig:/usr/aarch64-linux-gnu/share/pkgconfig")
set(ENV{PKG_CONFIG_SYSROOT_DIR} "/")

// Force-included into every translation unit (see CMakeLists.txt:
// add_compile_options(-include .../glibc_compat.h)). Provides drop-in
// stubs for Clang/bionic-only constructs used by AOSP source so the
// same source compiles cleanly with GCC + glibc.

#pragma once

#ifndef __clang__
// __builtin_available(android X, *) is Clang's API-availability check.
// AOSP's libbase/logging.cpp and friends use it to gate code paths on
// the Android platform API level. On glibc Linux there is no Android
// API level, so make every such guard succeed unconditionally.
#define __builtin_available(...) (true)
#endif

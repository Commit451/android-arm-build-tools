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

#ifdef __cplusplus
// AOSP source uses the bare C11 atomic typedef names (atomic_int,
// atomic_bool, ...) in headers that get included by both C and C++
// translation units. GCC's <stdatomic.h> only defines those names
// when compiling as C; in C++ mode you have to go through <atomic>
// and the std:: namespace. Bring the std:: names into global scope
// so the AOSP headers parse cleanly in C++ TUs.
#include <atomic>
using std::atomic_int;
using std::atomic_uint;
using std::atomic_bool;
using std::atomic_long;
using std::atomic_ulong;
using std::atomic_llong;
using std::atomic_ullong;
using std::atomic_short;
using std::atomic_ushort;
using std::atomic_char;
using std::atomic_schar;
using std::atomic_uchar;
using std::atomic_size_t;
using std::atomic_ptrdiff_t;
using std::atomic_intptr_t;
using std::atomic_uintptr_t;
#endif // __cplusplus

#endif // !__clang__

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
// AOSP source also routinely calls bare strlen/strncmp/memcpy
// from C++ TUs without including <cstring>; bionic's transitive
// includes provide the declarations, glibc's don't.
#include <cstring>
// numeric_limits<T> referenced without <limits> in libandroidfw.
#include <limits>
// std::unique_ptr referenced without <memory> in libincfs/path.h
// (and likely more AOSP shared headers).
#include <memory>
// Typedefs.
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
// Sized atomic typedefs (also from <stdatomic.h>).
using std::atomic_int_least8_t;
using std::atomic_int_least16_t;
using std::atomic_int_least32_t;
using std::atomic_int_least64_t;
using std::atomic_uint_least8_t;
using std::atomic_uint_least16_t;
using std::atomic_uint_least32_t;
using std::atomic_uint_least64_t;
using std::atomic_int_fast8_t;
using std::atomic_int_fast16_t;
using std::atomic_int_fast32_t;
using std::atomic_int_fast64_t;
using std::atomic_uint_fast8_t;
using std::atomic_uint_fast16_t;
using std::atomic_uint_fast32_t;
using std::atomic_uint_fast64_t;
// memory_order enum + values.
using std::memory_order;
using std::memory_order_relaxed;
using std::memory_order_consume;
using std::memory_order_acquire;
using std::memory_order_release;
using std::memory_order_acq_rel;
using std::memory_order_seq_cst;
// Free-function atomic operations from <stdatomic.h>.
using std::atomic_init;
using std::atomic_load;
using std::atomic_load_explicit;
using std::atomic_store;
using std::atomic_store_explicit;
using std::atomic_exchange;
using std::atomic_exchange_explicit;
using std::atomic_compare_exchange_strong;
using std::atomic_compare_exchange_weak;
using std::atomic_compare_exchange_strong_explicit;
using std::atomic_compare_exchange_weak_explicit;
using std::atomic_fetch_add;
using std::atomic_fetch_sub;
using std::atomic_fetch_and;
using std::atomic_fetch_or;
using std::atomic_fetch_xor;
using std::atomic_fetch_add_explicit;
using std::atomic_fetch_sub_explicit;
using std::atomic_fetch_and_explicit;
using std::atomic_fetch_or_explicit;
using std::atomic_fetch_xor_explicit;
using std::atomic_thread_fence;
using std::atomic_signal_fence;
#endif // __cplusplus

#endif // !__clang__

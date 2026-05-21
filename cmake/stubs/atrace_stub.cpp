// No-op implementations of the libcutils atrace_* API used by
// libandroidfw's ScopedTrace. aapt2 doesn't actually need Android
// tracing; we just have to satisfy the linker.
//
// The real implementation lives in
// src/core/libcutils/trace-dev.cpp which we dropped from the
// libcutils sources because it pulls in Android-specific kernel
// tracefs paths and ALOG macros.

#include <stdint.h>

extern "C" {

uint64_t atrace_get_enabled_tags(void) {
    return 0;
}

void atrace_begin_body(const char* /*name*/) {}

void atrace_end_body(void) {}

void atrace_async_begin_body(const char* /*name*/, int32_t /*cookie*/) {}

void atrace_async_end_body(const char* /*name*/, int32_t /*cookie*/) {}

void atrace_async_for_track_begin_body(const char* /*track_name*/,
                                       const char* /*name*/,
                                       int32_t /*cookie*/) {}

void atrace_async_for_track_end_body(const char* /*track_name*/,
                                     int32_t /*cookie*/) {}

void atrace_instant_body(const char* /*name*/) {}

void atrace_instant_for_track_body(const char* /*track_name*/,
                                   const char* /*name*/) {}

void atrace_int_body(const char* /*name*/, int32_t /*value*/) {}

void atrace_int64_body(const char* /*name*/, int64_t /*value*/) {}

}  // extern "C"

#
# Copyright © 2022 Github Lzhiyong
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

add_library(libcutils STATIC
    ${SRC}/core/libcutils/android_get_control_file.cpp
    ${SRC}/core/libcutils/canned_fs_config.cpp
    ${SRC}/core/libcutils/config_utils.cpp
    ${SRC}/core/libcutils/fs.cpp
    ${SRC}/core/libcutils/fs_config.cpp
    ${SRC}/core/libcutils/hashmap.cpp
    ${SRC}/core/libcutils/iosched_policy.cpp
    ${SRC}/core/libcutils/load_file.cpp
    ${SRC}/core/libcutils/multiuser.cpp
    ${SRC}/core/libcutils/native_handle.cpp
    ${SRC}/core/libcutils/properties.cpp
    ${SRC}/core/libcutils/record_stream.cpp
    ${SRC}/core/libcutils/socket_inaddr_any_server_unix.cpp
    ${SRC}/core/libcutils/socket_local_client_unix.cpp
    ${SRC}/core/libcutils/socket_local_server_unix.cpp
    ${SRC}/core/libcutils/socket_network_client_unix.cpp
    ${SRC}/core/libcutils/sockets_unix.cpp
    ${SRC}/core/libcutils/sockets.cpp
    ${SRC}/core/libcutils/str_parms.cpp
    ${SRC}/core/libcutils/strlcpy.c
    # No-op stubs for the atrace_* API since we dropped trace-dev.cpp;
    # libandroidfw's ScopedTrace needs these to link.
    ${PROJECT_SOURCE_DIR}/cmake/stubs/atrace_stub.cpp
    # The following are Android-only (linux/ashmem.h, kernel uevent
    # device, qtaguid traffic-accounting, Android reboot semantics)
    # and don't compile against glibc + a stock Linux kernel header
    # set. aapt2 doesn't reference them; if a later link surfaces a
    # missing symbol we'll bring back specific files.
    #   android_reboot.cpp
    #   ashmem-dev.cpp
    #   klog.cpp
    #   partition_utils.cpp
    #   qtaguid.cpp
    #   trace-dev.cpp
    #   uevent.cpp
    )

target_compile_definitions(libcutils PRIVATE 
    -D_GNU_SOURCE
    )

target_include_directories(libcutils PRIVATE
    ${SRC}/core/libutils/include
    ${SRC}/core/libcutils/include
    ${SRC}/logging/liblog/include 
    ${SRC}/libbase/include
    )
    

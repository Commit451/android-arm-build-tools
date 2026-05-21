# Internal AOSP libraries used by aapt2 (and the other build-tools
# binaries when we add them). Each lib*.cmake compiles its sources
# straight out of the corresponding cloned AOSP repo under ${SRC}.
#
# Adapted from lzhiyong/android-sdk-tools — trimmed to the subset
# aapt2 transitively links. When we add more binaries (aapt, aidl,
# zipalign, dexdump, split-select), add the libs they need here too.

include(libbase.cmake)
include(liblog.cmake)
include(libcutils.cmake)
include(libutils.cmake)
include(libandroidfw.cmake)
include(libincfs.cmake)
include(libselinux.cmake)
include(libsepol.cmake)
include(libziparchive.cmake)
include(libbuildversion.cmake)
include(libpackagelistparser.cmake)
include(libprocessgroup.cmake)

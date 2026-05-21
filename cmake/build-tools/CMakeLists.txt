# Per-binary CMakeLists for the build-tools. MVP scope is aapt2 only;
# the other .cmake files (aapt, aidl, zipalign, etc.) will get added
# in subsequent iterations once aapt2 builds cleanly.

project(build-tools)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME})

include(aapt2.cmake)

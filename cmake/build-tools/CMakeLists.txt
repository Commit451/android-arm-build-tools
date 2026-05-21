# Per-binary CMakeLists for the build-tools. Each .cmake declares
# an executable + its source list + transitive link deps.

project(build-tools)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME})

include(aapt2.cmake)
include(aapt.cmake)
include(aidl.cmake)
include(zipalign.cmake)
include(dexdump.cmake)
include(split-select.cmake)

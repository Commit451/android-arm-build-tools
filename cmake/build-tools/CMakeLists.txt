# Per-binary CMakeLists for the build-tools. Each .cmake declares
# an executable + its source list + transitive link deps.

project(build-tools)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME})

include(aapt2.cmake)
# aapt.cmake stays included because it defines the `libaapt` static
# library that split-select links against; the `aapt` executable
# target it also defines just doesn't get built unless aapt is in
# TARGETS (ninja --target driven).
include(aapt.cmake)
include(aidl.cmake)
include(zipalign.cmake)
include(split-select.cmake)
# dexdump dropped: it's a debug-only tool (never invoked by AGP)
# and pulls in src/art/ which has a much larger bionic surface.

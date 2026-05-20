# patches/

Per-project patches applied to the AOSP source tree before the build.

Each patch must include a header comment naming the project it applies
to, relative to the AOSP root:

```
# Project: build/soong
From: ...
Subject: [...]
...
```

`scripts/build-windows-arm64.sh` reads `# Project:` and runs
`git apply` inside that subdirectory.

Patches are applied idempotently — re-running the build is safe.

Most patches here exist because AOSP's host build system assumes
`x86_64-w64-mingw32` for Windows targets and needs nudging to use
`aarch64-w64-mingw32` from llvm-mingw. As AOSP gains upstream
Windows-on-ARM support, patches in this directory should shrink
or disappear.

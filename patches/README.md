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

`scripts/fetch_sources.py` reads `# Project:` and runs `git apply -p1`
inside that subdirectory after cloning, before the build runs.

Patches are applied idempotently — re-running is safe; already-applied
ones are skipped via `git apply --check`.

Most patches here exist because AOSP source assumes bionic + Clang +
the NDK toolchain. Each patch addresses one place where that
assumption breaks under GCC + glibc.

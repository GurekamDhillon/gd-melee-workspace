# Aurora GD motion perf + arena-guard v2

Incremental patch on top of aurora-gd-motion-v1 (already in the checkout), produced with
`git -C melee diff -- extern/aurora` after the perf lane; apply with
`git -C melee apply --directory=... ` is NOT needed on this tree (already applied). Check consistency:
`git -C melee apply --reverse --check _build/patches/aurora-gd-motion-perf-v2.patch`.
Contents: capture reads host-side sources instead of the write-combined frame arenas, content-addressed
shared blobs, per-recording push reuse (Blob::slot), no variant-uniform arena push, profiler timings
(motion::take_timing), pool stats, uniform-arena MaxUniformSize reserve in arena_fits (fixes the
finish() append abort, 0xC0000409), draw drop after overflow, test hook test_fill_uniform_arena.
Rebuild Aurora (build_aurora_melee.bat) then tools/port/build.sh.

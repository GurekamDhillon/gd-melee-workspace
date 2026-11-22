# Codex packet: make the native test suite green on integration (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Worktrees ALREADY EXIST; edit ONLY there:
- game `E:\Projects\Melee Workspace\worktrees\nativefix` (branch `agent/nativefix`, from game integration `6170b5b2d`);
  build root `E:\Projects\Melee Workspace\_build\agents\nativefix`
- workspace `E:\Projects\Melee Workspace\worktrees\ws-nativefix` (branch `ws/nativefix`), for `tools/port/native_test.sh`
No git writes (the coordinator commits). You MAY run `bash tools/port/build.sh --native-test <name>` and the full
native sweep (`tools/port/native_test.sh`), the headless suite (`run.sh --test`) and builds. No windowed runs.

## Why

These 8 registered native test cases fail on integration (identical before and after unrelated lanes, so they are
pre-existing drift), which makes every lane's "no new failures" check noisier:

```
slippi-fixture 1    slippi-rb 1    script-policy 1    arena-spawn 1
view-canvas 1    profiler-core 1    mex-items-query 127    atlas-mods-door 1
```

(`mex-items-query`: `Assertion failed: gw_Mex_ItemRangeAvailable(4608,64)` at `pc/tests/mex_items_query_test.c:46`;
exit 127 also suggests a missing tool/library in one case.)

## Do, per case

Find WHY it fails: the test is stale against intended product changes (update the test to the current, correct
behaviour, citing the commit that changed it), the test harness/link list is missing a source or symbol (fix the build
recipe in `native_test.sh` or the test's sources), an environment dependency (a missing tool: make the test find it or
skip with an explicit message that names what is missing, never silently), or a REAL product bug (do NOT paper over it:
fix the product code if it is small and clearly wrong; otherwise leave the test failing and explain). Never weaken an
assertion just to pass; never delete a test.

## Deliver

Report `E:\Projects\Melee Workspace\_build\tmp\codex-native-cleanup-report.md`: per case: cause (with file:line and
evidence), what you changed (test vs harness vs product), and its result; the full native sweep before/after (pass
counts); the headless suite result; proposed commit messages per worktree. Any product-code change listed separately
and prominently.

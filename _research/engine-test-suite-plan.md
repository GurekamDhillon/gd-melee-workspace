# In-engine unit test suite — plan

## 1. Why this exists

Every claim verified in this project so far has been one of three things: **compiles**, **links**,
or **boots without a fatal assert**. None of them proves behaviour. That gap is now the dominant
risk: there are 128 m-ex patches in flight that are "compile-clean" and entirely unvalidated, and
a broken verification check (a grep pattern that could never match) already produced one false
all-clear in this project.

The tests must run **in-engine** — linking the real `gw_`-prefixed game objects and executing in
real guest memory — because the code under test *is* the engine. A mocked x86 build would be
little-endian and semantics-free, i.e. it would test a different program than the one that ships.

## 2. Where it hooks into the real boot sequence

`pc/platform/main.c` (`main()`) currently runs, in order:

1. `gw_install_crash_handler()`
2. `gw_find_iso(argc, argv)` — requires a disc image
3. Target Test mod scan
4. `aurora_initialize(...)` — **window + GPU**
5. `AuroraSetViewportPolicy(...)`
6. `gw_apply_fixups()` — rewrites pointers inside game globals
7. `gw_mem_init()` — reserves MEM1/ARAM
8. `gw_gx_init_render_modes()`
9. `gw_frame_init()` — frame driver
10. `gw_start_watchdog()`
11. `gw_main()` — the game's own main loop

The test path branches **after step 7 and before step 8**, and skips step 4 entirely:

```
--test  ->  gw_apply_fixups(); gw_mem_init();
            gw_test_init();            // tier-dependent bring-up
            rc = gw_test_run_all();
            gw_test_report();
            return rc;                 // 0 = all passed
```

Skipping Aurora is what makes this fast and CI-able: no window, no D3D12, no vsync. Tests that
genuinely need rendering stay in the existing launch-and-grep harness (§6, T3).

Test code lives behind `#if defined(TARGET_PC) && defined(MELEE_TESTS)`, so the matching non-PC
build can never see it — the same byte-identity rule the rest of the port follows.

## 3. Tiers — what is actually testable

Be honest about this up front; over-promising here is how test suites die.

| Tier | Needs | Examples |
|---|---|---|
| **T0 pure** | nothing but `gw_mem_init` | endian helpers (`gw_r32`/`gw_w32`/`gw_rf32`) round-trip; `tt_parse_ckind` name→kind; mode-classification truth tables |
| **T1 guest-memory** | MEM1 + fixups | struct layout/size assertions; `ftMapping_list` external→internal char ID mapping; table counts (`icons`, `mnStageSel_803F06D0`, `LBHEAP_HEAP_COUNT`) |
| **T2 HSD-lite** | HSD init + a heap | JObj/DObj construction, `HSD_POBJ` display-list handling |
| **T3 game integration** | ISO, scene load, GObjs | stage load, fighter spawn, damage/knockback |

**T0 + T1 are the sweet spot** and cover most of the debt we actually have. T2 needs HSD bring-up
that may itself require assets. T3 is not a unit test — it stays the scripted-launch harness.

## 4. Design decisions

### 4.1 Same binary, `--test` flag — not a second executable
The link is driven by a hand-maintained 1005-line response file
(`_build/melee_link_objects.rsp`) plus a 990-line manifest (`_build/masstest/files.txt`). A second
target means maintaining a second copy of both. Reusing the one binary avoids that entirely. Test
cases compile through the existing `pipe_wsl.sh` pipeline into `out/`, so they link like any TU.

### 4.2 Registration: generated, not magic
MSVC has no `__start_`/`__stop_` section symbols, and C static-initialiser lists are unreliable.
So a small generator scans `melee/pc/tests/*.c` for a registration macro and emits a
`gw_test_registry.c`. This matches the project's existing Python-driven, manifest-based pipeline
rather than introducing runtime cleverness.

### 4.3 Isolation: snapshot/restore MEM1
Reset game state between tests by snapshotting MEM1 (24 MB `memcpy`, ~ms) and restoring it after
each test, then re-running `gw_apply_fixups()`. Strong isolation, cheap.

**Caveat to respect:** platform-side statics (in `gw_runtime.c` et al.) are *not* in MEM1 and will
not be restored. Tests must not depend on platform state they don't set up themselves.

### 4.4 Failure containment: a crashing test is a FAIL, not a dead run
- Crashes: SEH (`__try`/`__except`) around each test via `gw_test_run_one`.
- Hangs: per-test timeout driven by the existing watchdog.
- `gw_panic`/`HSD_ASSERT` must be redirectable in test mode so an assert is captured as a failure
  instead of aborting the process.

### 4.5 Determinism
Seed the RNG per test; disable frame pacing (not initialised in test mode); freeze the frame
counter. A test that passes once and fails once is worse than no test.

### 4.6 Output: TAP-shaped, plus a greppable summary
```
ok 1 - endian_f32_roundtrip
not ok 2 - ftmapping_specials_identity
  expected 26, got 25
TESTS: pass=1 fail=1 total=2
```
The `TESTS:` line is what a harness greps for; it echoes how verification already works in this
project, and gives a real exit code for CI.

## 5. Immediate tests — written against today's actual debt

These are chosen because they validate work already landed or in flight:

| Test | Guards |
|---|---|
| `ftmapping_specials_identity` | the char-ID refactor (must be identity under vanilla counts) |
| `heap_table_shape` | `LBHEAP_HEAP_COUNT`, terminator value, `heap_array` size, **names-table length matches** (the sixth site that almost shipped broken) |
| `css_icon_count` | `icons[]` size vs `SELKIND_COUNT + 1` |
| `sss_stage_count` | `mnStageSel_803F06D0[]` size vs `NUM_STAGES + 1` |
| `scene_table_bounds` | `gm_GetAllGameModes`/`Scenes` counts match their tables |
| `is1pmode_truth_table` | the C-stick gate: all 13 1P modes true, VS modes false |
| `endian_helpers_roundtrip` | `gw_r32`/`gw_w32`/`gw_rf32` symmetry |

Every one of these is a property that today is only checked by *reading the diff*.

## 6. Build + run integration

- Tests: `melee/pc/tests/*.c` → add to `files.txt` **and** `melee_link_objects.rsp` (both are
  hand-maintained — this is known friction; a generator for these is worth doing at the same time).
- Framework: `pc/platform/gw_test.c` + `gw_test.h` (runner, registry, isolation, capture).
- Harness: `_build/run_tests.bat` → `melee-pc.exe --test --iso <iso>`, parse `TESTS:`, exit
  non-zero on failure.

## 7. Risks

| Risk | Mitigation |
|---|---|
| HSD bring-up (T2) may need assets | keep T2 optional; T0/T1 must not depend on it |
| MEM1 snapshot hides leaks through platform statics | document; assert platform state explicitly per test |
| Test code shipping in release | `MELEE_TESTS` define; strip in release builds |
| Suite drifts from reality | each ported behaviour adds a test **in the same change**, not later |
| `--test` path diverging from the real boot path | keep the branch tight — same `gw_apply_fixups`/`gw_mem_init` sequence |

## 8. Phased rollout

1. **Phase 1** — `--test` flag, runner, registry generator, T0/T1, TAP output, exit code. This is
   the smallest genuinely useful suite, and enough to start paying down debt.
2. **Phase 2** — MEM1 snapshot isolation, SEH containment, per-test timeout, panic capture.
3. **Phase 3** — HSD bring-up for T2.
4. **Phase 4** — backfill tests for every already-ported behaviour (the 4 landed + the 128 in
   flight), then make "adds a test" a condition of merging a port.

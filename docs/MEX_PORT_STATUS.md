# m-ex port + test suite — status

Consolidated state of the m-ex porting effort and the in-engine test suite. Companion to
`_research/mex-content-expansion.md`, `_research/mex-tier-c-hooks.md`,
`_research/engine-test-suite-plan.md`, and `_research/mex-port-triage.md`.

## 1. How much is actually ported

| | Count |
|---|---:|
| m-ex `.asm` patches total | 1,169 |
| Resolvable to a decomp function | 1,130 (96.7%) |
| **Ported so far** | **4** |

Ported: `no_title_demo`, `no_special_messages`, `no_trophy_messages`, plus the Persistent Heap
Expansion family.

**Do not describe scaffolding as porting.** Three refactors — char-ID count indirection, CSS/SSS
table sizing, scene table bounds — make future work data-driven but port **zero** m-ex behaviour.
They are groundwork.

## 2. Findings that changed the plan

- **Two directive spellings.** m-ex uses `#To be inserted @ <hex>` (991 files) *and*
  `#To be inserted at <hex>` (178). Matching only `at` hides 85% of the corpus. Both are handled by
  `tools/mex_port/resolve_patches.py`.
- **`MxDb.dat` is not a patch index.** It is an HSD DAT (`mexDebug` root) of
  `{u32 start; u32 end; char* name}` — a retail-DOL symbol table for crash stack traces.
- **Tier C is reachable after all.** m-ex's `Fighter On*` hooks are not arbitrary code injection:
  each replaces one `addi` computing a per-character callback table base, and the decomp already
  calls `ftData_<X>[fp->kind]`. So they are **table-slot overrides**, not PPC execution. See
  `_research/mex-tier-c-hooks.md`.

## 3. In-engine test suite

```
melee-pc.exe --test --iso <GAME01 iso>      # runs headless, exits with the failure count
```

- Runner: `pc/platform/gw_test.{h,c}`; tests: `pc/platform/gw_tests_core.c` (platform) and
  `pc/tests/mex_tests.c` (game-side, compiled through the game pipeline).
- **Game-side bridge:** gwtool prefixes game symbols, so game code calling `TestRegister`/`TestFail`
  references `gw_TestRegister`/`gw_TestFail`; those bridges live in `gw_test.c`. Game-side registry
  is `MexTestRegisterAll` -> `gw_MexTestRegisterAll`.
- **15 tests**, exit 0. Two configurations must both be run:
  - `_build/run_tests.bat` — default; asserts features are **off**
  - `_build/run_tests_mex.bat` — `MELEE_MEX` set; asserts the **enabling** path works
  The two flag tests partition these configurations, because the flag list is read once and cached.

Guarantees, each **demonstrated failing on purpose** before being trusted:

| Guarantee | Proof |
|---|---|
| MEM1 snapshot/restore isolation | fixups re-run observable after every test |
| `gw_panic` capture | probe -> `not ok`, suite continued, exit 1 |
| SEH crash containment | null-deref probe -> caught, suite continued |
| Per-test timeout | infinite-loop probe -> `TESTS: TIMEOUT in "..."`, exit 2 |

`heap_table_shape` was also falsified by breaking the heap terminator (7 -> 6) and watching it
report `not ok`.

## 4. Verification tooling

- **`tools/mex_port/verify_changed.sh`** — compiles every changed game TU. Use the **text** signal:
  `pipe_wsl.sh` prints `CC_FAIL`/`GW_FAIL`, and its failure handlers used to `exit 0` (fixed).
- **`tools/mex_port/lint_ports.py`** — enforces the porting conventions on every `Mex_Enabled` site:
  a `#if defined(TARGET_PC)` earlier in the file, an attribution comment citing the m-ex URL within
  20 lines, and **globally unique feature names** (two files sharing a flag would couple unrelated
  behaviours).
- Both were falsified against planted bad input before being relied on.

## 5. The methodology hazard (read this first)

Four separate checks in this effort reported success unconditionally:

| Check | Why it always passed |
|---|---|
| `grep 'assertion failed'` | real text is `assertion "X" failed` |
| `pipe_wsl.sh` return code | script `exit 0`s on failure |
| a timeout probe | break condition was reachable |
| a NULL flag test | loop body never ran with an empty feature list |

Three were written by the same author. **Treat any green result as untrusted until the check has
been shown able to fail.** The test runner prints an explicit `TESTS: pass=N fail=M` line, and
probes are removed after use.

## 6. Open problems

### MELEE_TRAINING direct launch (blocked)

`MELEE_TRAINING=<ckind>` boots into Training Mode but dies at
`assertion "memp_kouho" failed in src/melee/lb/lbmemory.c on line 154` within ~4 frames
(`retrace=4`, `prim=0` — nothing renders).

**Diagnosis (after six refuted hypotheses, all resolved by measurement rather than reasoning):**

- The assert is a **capacity failure**, not a data-structure problem: the request is
  `0x133740` (~1.26 MB) against ~422 KB free. The free-list walk could never succeed. Every
  cache-seeding attempt targeted things that were never the cause.
- ARAM is **healthy** (~9.8 MB free) through the whole training handler — measured either side of
  `gm_80189CDC`. The ~9.4 MB drain happens **after** the handler returns, in the `GS_TRAINING`
  scene load.
- **Port-side ARAM reservation is ruled out**: the port allocates the full 16 MB and the AX shim
  only reads from it.

So the scene load needs ~9.4 MB + 1.26 MB ≈ 10.7 MB against ~9.8 MB available — roughly 0.9 MB
short. Four attempts at seeding cache fields and a fifth at adding the CSS state's own
`gm_801B06B0` call all produced an identical assert.

**Next step:** instrument the `GS_TRAINING` scene load (not `gmtrainingmode.c`) to find what
consumes the ~9.4 MB. Full measurements and the frame-resolution recipe are in `docs/HANDOFF.md`.
A failure-path diagnostic in `lbMemory_80014FC8` logs the request size and arena bounds.

**Do not attempt a code change here before measuring** — every code-first attempt failed; every
measurement succeeded.

### 128-patch batch

Workers were dispatched by category (`Additional`+`gameplay`, `qol`) with disjoint file ownership,
because m-ex patches cluster hard on shared functions (`mnCharSel_CursorThink` takes 26).

**First attempt failed silently:** four workers ran ~25 min, produced **zero files**, then all
stopped within two minutes of each other (a common-cause termination, not four separate failures).
Their transcripts showed heavy planning and no writes, and no completion notification ever arrived.
Lesson recorded in HANDOFF: *absence of a completion notification is not evidence of progress* —
check session timestamps, and require work to be written incrementally so a dying worker still
leaves value.

**Second attempt succeeded**, with one change: workers were told to **save each edit as they made
it** rather than batching. Both delivered.

| | |
|---|---|
| qol | 58m 9s |
| Additional + gameplay | 1h 26m 4s |
| changed src TUs | 18 -> 36 |
| `Mex_Enabled` flags | ~4 -> 42 |

Verification (run against the files, not their result tables):

```
verify_changed.sh:  33 files, 0 failures  [TARGET_PC]
                    33 files, 0 failures  [non-TARGET_PC]
lint_ports.py:      43 call sites, 0 violations
link:               MELEE_PC_LINK_OK
tests:              15/15 exit 0  (flags off)
                    15/15 exit 0  (MELEE_MEX on)
runtime:            22 flags enabled, ~66s Training Mode, 0 FATAL, renders
```

**Caveat that still stands:** this proves the ports *compile, link and run*. It does **not** prove
each reimplemented behavior matches m-ex semantics — that needs per-flag play testing. 15 tests are
not load-bearing for 42 flags.

### Flag inventory

Authoritative list of strings accepted by `MELEE_MEX` / `mods/mex.txt`. 49 unique names across 50
call sites (`rotate_camera_dpad_down` is used at two sites in one file — same feature, allowed;
the lint only forbids *cross-file* reuse). A typo here fails silently, with no error.

| Flag | Source file |
|---|---|
| `default_4_stocks` | `gm/gmmain_lib.c` |
| `default_8_minutes` | `gm/gmmain_lib.c` |
| `default_no_items` | `gm/gmmain_lib.c` |
| `default_stock_mode` | `gm/gmmain_lib.c` |
| `default_tournament_stages` | `gm/gmmain_lib.c` |
| `disable_fod_reflection` | `ft/ftdrawcommon.c` |
| `enable_c_stick_1p` | `gm/gmvs.c` |
| `fill_trophy_save_data` | `gm/gmmain_lib.c` |
| `have_99_trophies` | `ty/toy.c` |
| `hide_nametag_invisible` | `if/ifnametag.c` |
| `keep_ko_stars` | `gm/gmvsmelee.c` |
| `ko_stars_on_exit` | `gm/gmvs.c` |
| `limit_costume_id` | `gm/gmvs.c` |
| `neutral_respawn` | `gm/gm_1601.c` |
| `neutral_spawn` | `gm/gmvs.c` |
| `no_pending_messages` | `gm/gm_16F1.c` |
| `no_pending_messages_2` | `gm/gm_1736.c` |
| `no_special_messages` | `gm/gm_1736.c` |
| `no_title_demo` | `gm/gm_181A.c` |
| `no_trophy_messages` | `gm/gm_16F1.c` |
| `reduce_result_screen_lag` | `gm/gm_1798.c` |
| `rotate_camera_dpad_down` | `db/dbcamera.c` (2 sites) |
| `skip_memcard_prompt` | `gm/gm_1AED.c` |
| `skip_result_screen` | `gm/gmvsmelee.c` |
| `stage_music_5050` | `gr/ground.c` |
| `text_align_background` | `sysdolphin/baselib/hsd_3A76.c` |
| `text_alpha_tev` | `sysdolphin/baselib/hsd_3A76.c` |
| `text_copy_alpha` | `sysdolphin/baselib/hsd_3A76.c` |
| `ucf_dbooc_squatrv_fix` | `ft/kinds/ftCommon/ftCo_SquatRv.c` |
| `unlock_all_characters` | `gm/gm_1601.c` |
| `unlock_all_stages` | `gm/gm_1601.c` |
| `unlock_all_star` | `gm/gmmain_lib.c` |
| `unlock_all_trophies` | `ty/toy.c` |
| `unlock_individual_characters` | `gm/gm_1601.c` |
| `unlock_individual_stages` | `gm/gm_1601.c` |
| `unlock_random_stage_select` | `gm/gmmain_lib.c` |
| `unlock_score_display` | `gm/gmmain_lib.c` |
| `unlock_sound_test` | `gm/gmmain_lib.c` |
| `unlock_special_messages` | `gm/gmmain_lib.c` |
| `unlock_special_messages_2` | `gm/gmmain_lib.c` |
| `use_save_banner_1` | `lb/lbcardgame.c` |
| `xy_disables_start` | `sysdolphin/baselib/controller.c` |
| `disable_fod_in_doubles` | `mn/mncharsel.c` |
| `enable_c_stick_always_1p_camera` | `cm/camera.c` |
| `enable_c_stick_always_1p_camera2` | `cm/camera.c` |
| `enable_c_stick_always_cpu_debug` | `ft/fighter.c` |
| `enable_c_stick_always_interrupt1` | `ft/fighter.c` |
| `enable_c_stick_always_interrupt2` | `ft/fighter.c` |
| `enable_c_stick_always_spoof_debug_level` | `ft/fighter.c` |

### Previously deferred patches — now done

Seven patches were deferred because they land in files another worker owned. That rule is void once
all workers finish and there is a single writer, so they were completed (42 -> 49 flags):

`Disable FoD in Doubles` (`mn/mncharsel.c`), `1P Camera` + `1P Camera2` (`cm/camera.c`), and
`Enable CStick for CPU`, `PlayerThink_Interrupt1/2`, `Spoof Debug Level` (`ft/fighter.c`) — i.e. the
C-stick-always and FoD-doubles behaviors, which were missing from the first batch.

### Semantic audit (behavior, not just compilation)

`verify_changed.sh` proves the ports *compile, link and run*. It does not prove the reimplemented
behavior matches m-ex. These families were read against the original patches and confirmed faithful:

| Family | m-ex original | Port |
|---|---|---|
| `unlock_individual_stages` / `unlock_all_stages` / `unlock_individual_characters` / `unlock_all_characters` | `li r3,1` | `return true;` |
| `stage_music_5050` | `li r0,50` | 50% branch on `HSD_Randi(RANDI_MAX)` |
| `skip_result_screen` | `li r27,0` | `id0 = 0;` |
| `default_*` (5 flags) | byte-offset `.long` words | exact field writes, only the changed bytes |

Two silent-failure classes checked specifically, since both compile cleanly and pass every gate:
**dead helper** (`gmMainLib_MexApplyTournamentDefaults` is defined *and* called) and
**wiped-by-init** (the apply runs just before `memzero(gmMainLib_804D3EE0, 0x10A30)`, but the
defaults live at `0x803D4A48`, outside that range).

## 7. Housekeeping

- `_build/` is outside version control; `pipe_wsl.sh` was modified there (now exits non-zero and
  prints diagnostics instead of swallowing them). Review before relying on it.
- `melee/pc/` carries the test runner, tests, and the `--test` branch in `main.c`.
- Nothing is committed.

## 8. Session additions (2026-09-16)

- **Tier C hook surface** (see `HANDOFF.md` §2) — the `Fighter On*` families are re-expressed as a
  native per-`(event, kind)` override array with `gw_Mex_HookRegister` / `gw_Mex_PredicateRegister`
  and their dispatches. This is *not* part of the 49-flag family: the hooks do not use `Mex_Enabled`,
  so the inventory and the 50-call-site lint are unaffected.
- Tests are now **17/17** (adds `mex_onframe_hook_register_and_clear` and
  `mex_predicate_register_and_clear`).
- The baseline is now **committed** (root `d374ee3`, melee `54727c190`); the "Nothing is committed"
  note above is superseded.
- New blocker: `Akaneia.iso` boot OOMs when a save exists (`HANDOFF.md` §4).

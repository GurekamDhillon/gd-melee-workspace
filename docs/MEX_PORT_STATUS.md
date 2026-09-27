# m-ex port and test suite - status

**Current as of 2026-09-27**, source audit of game `4c676892a` and workspace `fc23753`.
This dated inventory supersedes the earlier 4-patch/15-test state in this file. Current task
priorities live in [NEXT-SESSION.md](NEXT-SESSION.md). No builds or tests were run for this audit.

## Implemented surfaces

| Surface | Source / scope |
|---|---|
| Feature flags | 49 literal `Mex_Enabled` names at 50 call sites; inventory below. These optional patch reimplementations are not a count of every supported m-ex behaviour |
| Fighter data | `ftdata.c`, `gw_mex_data`, `gw_mex_ftfunction_runtime`: table-driven fighter data and conditional per-kind overrides, clone-base fallback, interpreted PPC callbacks and native bridge |
| Slots and skeletons | `ft/forward.h`: 94 PC m-ex slots; `ftparts.h`: 255 parts and 0x20000-byte fighter animation buffers. Motion-table rewrite skips empty rows and bounds the archive; thrown-skeleton rows keep their kind |
| Stages and items | `gw_mex_grfunction` and item runtime: stage callback overrides and custom-item paths; disc/mod data still determines available content |
| Effects | m-ex fighter effect-bank dispatch remains; Geno additionally supplies native `.gfx.json` simulation/rendering and fighter/article bindings |
| Geno | `pc/geno/geno.h`: JSON version 5, additive v5.5 script/state/article features. This is an extension alongside m-ex, not an upstream patch count |
| PC palette models | `pobj.c` and Aurora implement the palette subclass; `gw_mods.c` recognises `engine.pobj_palette = 1` and refuses unsupported requirements |
| Launch and 1P | `gw_scene.c` supports explicit modes/players/stages; current code includes m-ex 1P table mapping and Classic IntroEasy's `Mtx44` correction. The old blanket Training-launch blocker is obsolete |

This list establishes code presence. It does not prove every disc, stage or fighter has passed a
current playthrough. Do not carry forward old OOMs, 15/17/70/185-test totals or stage failure lists
as current results without their matching build and run evidence.

## Test and verification commands

```bash
bash tools/port/run.sh --test mex-tests --iso "C:/path/game.iso"
bash tools/port/run.sh --test --realtime mex-tests-rt --iso "C:/path/game.iso"
```

Run with the intended `MELEE_MEX` configuration and mounted mods. The flag cache and feature
paths require separate enabled/disabled runs when a flag changes. `run.sh --test` requests turbo
by default, but headless tests have no paced frame loop; `--realtime` clears that request.

The runner is `pc/platform/gw_test.c`; registries include `gw_tests_core.c`, `pc/tests/mex_tests.c`,
Geno and script modules. Registration is not a passing result. Read the explicit
`TESTS: pass=N fail=M` summary, exit status and full sandbox log. Game-side `TestRegister` /
`TestFail` calls reach the native `gw_` bridges through gwtool's symbol prefixing.

`tools/mex_port/lint_ports.py` checks guards, attribution and feature-name ownership.
`verify_changed.sh` checks changed game TUs; `build.sh` additionally owns bridge regeneration,
fixpoint and the final EXE ABI audit. These checks do not establish per-feature semantic parity.
See [tools/port/README.md](../tools/port/README.md) for paths and timing switches.

## Flag inventory

Extracted from literal `Mex_Enabled("name")` calls in the current game tree. Source paths are
relative to the game checkout. Two uses of `rotate_camera_dpad_down` are in the same file.

| Flag | Source |
|---|---|
| `default_4_stocks` | `src/melee/gm/gmmain_lib.c` |
| `default_8_minutes` | `src/melee/gm/gmmain_lib.c` |
| `default_no_items` | `src/melee/gm/gmmain_lib.c` |
| `default_stock_mode` | `src/melee/gm/gmmain_lib.c` |
| `default_tournament_stages` | `src/melee/gm/gmmain_lib.c` |
| `disable_fod_in_doubles` | `src/melee/mn/mncharsel.c` |
| `disable_fod_reflection` | `src/melee/ft/ftdrawcommon.c` |
| `enable_c_stick_1p` | `src/melee/gm/gmvs.c` |
| `enable_c_stick_always_1p_camera` | `src/melee/cm/camera.c` |
| `enable_c_stick_always_1p_camera2` | `src/melee/cm/camera.c` |
| `enable_c_stick_always_cpu_debug` | `src/melee/ft/fighter.c` |
| `enable_c_stick_always_interrupt1` | `src/melee/ft/fighter.c` |
| `enable_c_stick_always_interrupt2` | `src/melee/ft/fighter.c` |
| `enable_c_stick_always_spoof_debug_level` | `src/melee/ft/fighter.c` |
| `fill_trophy_save_data` | `src/melee/gm/gmmain_lib.c` |
| `have_99_trophies` | `src/melee/ty/toy.c` |
| `hide_nametag_invisible` | `src/melee/if/ifnametag.c` |
| `keep_ko_stars` | `src/melee/gm/gmvsmelee.c` |
| `ko_stars_on_exit` | `src/melee/gm/gmvs.c` |
| `limit_costume_id` | `src/melee/gm/gmvs.c` |
| `neutral_respawn` | `src/melee/gm/gm_1601.c` |
| `neutral_spawn` | `src/melee/gm/gmvs.c` |
| `no_pending_messages` | `src/melee/gm/gm_16F1.c` |
| `no_pending_messages_2` | `src/melee/gm/gm_1736.c` |
| `no_special_messages` | `src/melee/gm/gm_1736.c` |
| `no_title_demo` | `src/melee/gm/gm_181A.c` |
| `no_trophy_messages` | `src/melee/gm/gm_16F1.c` |
| `reduce_result_screen_lag` | `src/melee/gm/gm_1798.c` |
| `rotate_camera_dpad_down` | `src/melee/db/dbcamera.c` |
| `skip_memcard_prompt` | `src/melee/gm/gmscmemcard.c` |
| `skip_result_screen` | `src/melee/gm/gmvsmelee.c` |
| `stage_music_5050` | `src/melee/gr/ground.c` |
| `text_align_background` | `src/sysdolphin/baselib/hsd_3A76.c` |
| `text_alpha_tev` | `src/sysdolphin/baselib/hsd_3A76.c` |
| `text_copy_alpha` | `src/sysdolphin/baselib/hsd_3A76.c` |
| `ucf_dbooc_squatrv_fix` | `src/melee/ft/kinds/ftCommon/ftCo_SquatRv.c` |
| `unlock_all_characters` | `src/melee/gm/gm_1601.c` |
| `unlock_all_stages` | `src/melee/gm/gm_1601.c` |
| `unlock_all_star` | `src/melee/gm/gmmain_lib.c` |
| `unlock_all_trophies` | `src/melee/ty/toy.c` |
| `unlock_individual_characters` | `src/melee/gm/gm_1601.c` |
| `unlock_individual_stages` | `src/melee/gm/gm_1601.c` |
| `unlock_random_stage_select` | `src/melee/gm/gmmain_lib.c` |
| `unlock_score_display` | `src/melee/gm/gmmain_lib.c` |
| `unlock_sound_test` | `src/melee/gm/gmmain_lib.c` |
| `unlock_special_messages` | `src/melee/gm/gmmain_lib.c` |
| `unlock_special_messages_2` | `src/melee/gm/gmmain_lib.c` |
| `use_save_banner_1` | `src/melee/lb/lbcardgame.c` |
| `xy_disables_start` | `src/sysdolphin/baselib/controller.c` |

## Limits and evidence rules

- A feature flag's presence does not prove its behaviour matches the original patch. Check the
  guarded implementation and the actual enabled path; table/hook/Geno support is a separate surface.
- Read m-ex as a specification and retain attribution; do not copy its implementation or assets.
  `resolve_patches.py` recognises both insertion-directive spellings. `MxDb.dat` is debug symbol
  data, not a patch inventory.
- Guest callback signatures and addresses must match the final linked EXE. Unsupported bridge
  signatures and unresolved lookups need individual audits, not an old aggregate gap count.
- Keep test isolation explicit: native statics can outlive restored MEM1. New caches need the
  appropriate invalidation; a green harness summary alone cannot rule out a stale artifact.
- The larger fighter heap and renderer buffers are implementation changes. Multi-fighter memory
  limits and four-Sora visual stability require a current Windows run.

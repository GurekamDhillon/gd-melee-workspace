# Integration ledger — 2026-10-01

Prepared on this Windows workspace (WSL session) from
`HANDOFF-GITHUB-INTEGRATION-2026-10-01.md`. That handoff recorded intent; this file records
what was actually done, what was deliberately not taken, and what could not be verified here.
Nothing was pushed, tagged or published.

## Result

| Repository | Integration branch | Merge commits |
| --- | --- | --- |
| Workspace (`origin-ws`) | `integration/2026-10-01/roguelite-100` | `0b2a548` (primary pair), `35319af` (Linux 0.1.8) |
| Workspace, graphics preflight | `integration/2026-10-01/graphics-preflight` | `d89875b` (recovered WIP), `00fb921` (missing CI test) |
| Game (`pub`) | `integration/2026-10-01/roguelite-100-game` | `e47950dd2` (primary pair), `21d001dea` (VK kit) |

Local work was preserved throughout: the 42 workspace and 50 game local-only commits are ancestors
of the integration branches, and the four modified `tools/slippi` files were never staged.

## The five game conflicts

All five were resolved by source review, never by `ours`/`theirs`.

`pc/gameworld/script_model.h`, `script_model.inc`, and four spots in `pc/gameworld/script_game.c`
turned on `area` versus `owner`. These are **two different concepts, not a rename**, and both are
live after the merge:

- `area` — an index into `script_stage.area[]`, the named-map-area table. Read by
  `script_largemap.inc`, which exists only on the local side.
- `owner` — a refcounted resource token, read by `ScriptGame_ModelRefOwned` via
  `script_stage.model_owner[]`.

Incoming had no `script_largemap.inc`, and the auto-merged `script_model.inc` assigns both
`candidate.area` and `candidate.owner`. Both fields were therefore kept on `ScriptMeshInstance`,
`ScriptStageLine` and `ScriptStageTarget`.

Three decisions needed judgement rather than concatenation:

1. **Enemy event codes collided.** Both sides emitted `what = 9` with incompatible payloads: local
   `on_enemy_removed` = (kind, handle, reason), incoming `on_enemy_hit` = (handle, from, damage).
   Lua on both sides consumes them — `gamemode_demo`, `boss_gamemode_bonus` and
   `pc/tests/gamemode_demo.lua` on one side, `roguelite/main.lua:1243` on the other — so neither
   could win. `on_enemy_hit` moved to `10`, the name table and the dispatcher bound (`> 9` → `> 10`)
   were updated to match. `on_enemy_removed` keeps `9`.
2. **`l_spawn_enemy` kind count.** Incoming hardcoded 6 enemy kinds; the merged table is 7
   (`SCRIPT_ENEMY_KINDS 7`, deliberately kept so Lua event indices are preserved). The symbolic
   bound was kept and incoming's ownership-capacity check added.
3. **`fly_phys` ordering.** Local `hold_step()` and incoming's fly-cursor pulse both touch
   `x914[].state` and `x195c_hitlag_frames`. The pulse now runs first so it reads the frame's real
   hitlag instead of one `hold_step` already zeroed, and `hold_step` stays last so a held hitbox
   re-arms capsules last.

Both enemy APIs were kept: local's tri-state terminal lifecycle (`script_enemy_terminal`,
`ScriptGame_EnemyStatus`) alongside incoming's accessor set (`script_enemy`, `EnemyAlive`,
`EnemyI/F/Contact`, `EnemyReceived`). The Lua registration table is the union of both sides;
`stage_bounds` was registered once on *each* side and had to be deduped to 149 unique entries.

## Workspace branches

The primary pair already contained the whole deepseek report trail under
`docs/handoff/2026-10-01/reports/deepseek-coordination/`, the contracts, and the 54-file
`tools/roguelite` suite. Verified byte-identical where checkable:
`integration-followup-5-report.md` and `integration-review-3.md` each match the snapshot copies
exactly.

| Branch | Disposition |
| --- | --- |
| `handoff/…/roguelite-100-integration` | merged, clean |
| `release/linux-0.1.8` | merged; 5 Linux-only commits, no Windows release metadata touched |
| `agent/linux-qt-launcher` | ancestor of the primary pair; nothing to import |
| `claude/hopeful-brahmagupta-js9imw` | already in local target |
| 13 × `handoff/…/deepseek-*` | superseded — same lane reports already integrated |
| `handoff/…/deepseek-stage-seams` | superseded — `docs/STAGE-FLOOR-SEAMS.md` documents the shipped `gd.stage_link` API; the snapshot's research report predates it |
| `handoff/…/linux-qt-launcher` | superseded — only `docs/scripting.md` differs |
| `handoff/…/model-test-campaign` | two review reports byte-identical to what landed; rest are lane artifacts for a foreign path layout |
| `handoff/…/gene-world-capacity` | rejected — `GENE-WORLD-CAPACITY-SEED.json` is a lane manifest; `menu/out_brand/out_brand/**` (39 files) duplicates the real `menu/out_brand/` tree |

`AGENTS.md` on `deepseek-gene-world` deserves a note: it is **not** project rules. It is a two-line
ephemeral lane scope note ("Own only `runtime_gene_world.lua`, `tools/roguelite/test_gene_world.py`
… Root reviews and lands"). It was rejected rather than placed at the repo root, where it would
mislead the next agent. The handoff's reference to "`AGENTS.md` rules" appears to mean the agent
configuration generally.

## Game branches

| Branch | Disposition |
| --- | --- |
| `handoff/…/roguelite-100-game` | merged, 5 conflicts reviewed |
| `handoff/…/vk-concepts-kit` | **imported** (`21d001dea`), 28 files of authored kit source. Its README states it is not exported and has never been built; do not claim in-game availability |
| `handoff/…/sol-native-owner-cleanup` | superseded — its `ScriptGame_StageReleaseDeadOwners` already arrived via the primary pair in `script_stage_owner.inc`. Its unique files are lane artifacts: a patch, a report pointing at `/home/gd/melee_linux_test/…`, and **two committed ELF binaries**, which must never be imported |
| `handoff/…/linux`, `model-test-campaign`, `gene-world-capacity`, 10 × `deepseek-*`, `archived-linux-compat` | superseded or already contained; no file absent from the merged baseline |
| `agent/linux`, `claude/hopeful-brahmagupta-js9imw`, `master`, `pc-port` | ancestors of the primary pair or already in the local target |

## Graphics preflight

The WIP in `worktrees/linux-graphics` had **no commits** and was invisible to WSL git: its `.git`
file records a Windows path, so `git worktree list` reports every worktree as `prunable` and git
refuses to operate them. The files were intact on disk and were snapshotted to
`/tmp/opencode/gdm-preserve/linux-graphics-wip-2026-10-01.tgz` before anything else. **Do not run
`git worktree prune` from WSL** — it would drop the registrations.

Landed on its own branch as `d89875b` (14 files), then the missing CI-referenced test as `00fb921`.

What was verified here for the first time — the helper had never been compiled:

- Builds clean as ELF32 i386 under `-Wall -Wextra -Werror`.
- Healthy driver: enumerates `llvmpipe (LLVM 19.1.7, 256 bits)`, API 1.4.305, creates a real
  Vulkan device with a graphics queue and swapchain, `usable: true`, exit 0.
- Missing loader (shadowed with a non-ELF `libvulkan.so.1`): reports
  "Cannot load libvulkan.so.1 in the 32-bit game environment.", exit 2.
- No usable driver (`VK_ICD_FILENAMES` at a nonexistent manifest): reports
  `vkCreateInstance failed (VkResult -9)`, exit 2.
- Wrong architecture (64-bit build): refuses with `bits: 64`, exit 2.
- `tools/port/test_graphics_probe.py` — the file `.github/workflows/launcher-qt.yml` referenced but
  which had never been written — now exists and passes 5/5, asserting the same contract
  `parseGraphicsReport()` uses.
- Qt launcher in WSL: both CTest targets pass (`launcher_core`, `launcher_graphics`, 2/2).
  `graphics.cpp` compiles clean.

Not verified: the `vkCreateDevice`-failure branch needs a driver that enumerates a device but
refuses device creation. No UI render or manual preflight flow was inspected. The Windows launcher
build is still blocked — the previous attempt failed in MSBuild with `MSB6001` (duplicated
case-insensitive environment keys), which needs a process-local child-environment fix, not a
global execution-policy change. GPU selection identifies vendor/device pairs, not individual PCI
addresses, and behaviour with inherited explicit ICD selections is unexamined. Direct CLI
`launch-melee` preflight is still launcher-only.

## The roguelite suite is not evidence on this machine

`python -m unittest discover -s tools/roguelite -p 'test_*.py'` runs **167 tests: 73 failures,
31 errors, 7 skipped, 56 passed.** This is a layout artifact, not a verdict on the merge.

The suite was written against a different machine's checkout. 89 of its files resolve
`melee/worktrees/linux/pc/scripts/examples/roguelite`, a lane that does not exist here; only
`certify_rooms.py` honours `GW_MELEE`, and pointing it at the real game repo moved the result only
from 34 errors to 31. There is also no Lua interpreter installed, and `test_gene_world.py`
explicitly refuses a mock ("Actual Lua interpreter required").

The 57 fully-green modules are exactly those needing neither the foreign checkout nor Lua:
installer and path-safety refusals, replay trace validation, report parsing, mesh formats. The
doc's step 6 anticipated this — "fix/configure actual-source test paths instead of accidentally
testing a different checkout" — and that fix has not been made. **Do not read 73/31 as a
regression, and do not read 56 as a pass.** Re-run on a machine with the lane layout or after the
paths are parameterised.

## Verification gaps beyond this session's reach

This session ran on WSL/Linux. The following are **not** done and must not be reported as done:

- No game build. The game builds only on Windows with the disc images.
- No bridge fixpoint and no EXE ABI audit.
- No headless game tests, no `run.sh` gameplay run, no controller or timing check.
- No on-screen verification of any changed menu, room, HUD or stage seam.
- Game-side C was **not** compiler-verified: the documented
  `clang --target=powerpc-unknown-eabi -fsyntax-only` needs clang, and only gcc is present here.
  The merge was verified structurally instead: zero conflict markers, comment- and string-aware
  brace/paren balance on all five files, no duplicate Lua registration keys, and every referenced
  handler resolving to an included `.inc`.

## Defects that remain open

The October 1 upstream review still stands and is **not** resolved by this integration:

1. An earned or exported gene cannot be discarded durably — save validation still requires the
   historical exported gene to exist in the collection.
2. Legacy Restore spends an item when native healing refuses; return/readback and rollback
   ownership are not handled truthfully.
3. V2 Restore persists contradictory inventory and campaign supply counts instead of one
   transaction.
4. Run history is appended after the durable finish save and can disappear on reload.

Also still open: bounded pagination and decline confirmation on pending-export menus; some
regression tests that bypass real menus or contain an always-true assertion; incomplete art
dependency reproducibility.

Feature milestones remain open too: room certification, controller traversal, enemy/boss controls,
effects and region integration, audio and camera. **Integration readiness is not 100/100 product
completion.**

## Recoverable state

- `/tmp/opencode/gdm-preserve/linux-graphics-wip-2026-10-01.tgz` — the graphics WIP as found.
- `/tmp/opencode/gdm-preserve/slippi-local-modified.patch` — the four local `tools/slippi` edits
  (131 insertions), still uncommitted in the working tree and deliberately not staged.
- `docs/HANDOFF-GITHUB-INTEGRATION-2026-10-01-branches.json` — the original fetch inventory.
- Nothing was pushed. Local `master` and `pc-port` were not advanced.

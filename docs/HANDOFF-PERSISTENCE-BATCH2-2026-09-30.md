# Handoff — persistence fixes and Batch 2 integration (2026-09-30)

Separate from `HANDOFF-ROGUELITE-2026-09-30.md`, `DEEPSEEK-NEXT-PASS.md` and
`DEEPSEEK-BULK-HANDOFF.md`. This one covers the persistence workstream and the
start of live v2 integration. Read `docs/PERSISTENCE-REVIEW-2026-09-30.md` too.

## Where things stand

Game checkout `melee/worktrees/linux`, recent commits:

```
c64741c28 roguelite: TBD3 save seam and progress migration
7fd8adc8d script: add gd.data_write_atomic with a native test
a709387bb roguelite: route service and TBD3 progress section
cb185a23b roguelite: reconcile upper-door recipe, real floor openings
f0ceccfc7 roguelite: finite pickups and codec key collisions
ecf824146 roguelite: preserve runtime modules
```

Workspace `gdm`: `7707966 roguelite: TBD3 save seam...`, `71f6a99 docs:
document gd.data_write_atomic`.

Uncommitted / owned by others (do not reset):
- `pc/platform/gw_script.c`: prior native work (~696 insertions vs HEAD) plus the
  committed `data_write_atomic`. The atomic helper is committed; the rest is
  pre-existing. Stage only your hunks, or coordinate.
- Frozen Sol modules: `adapter.lua`, `route.lua`, `progress.lua`, `rooms.lua`,
  `room_recipes.lua` (consume their APIs; do not edit).
- `route_map.lua` + `tools/roguelite/test_route_map.py` are committed and
  bundled in `prepare.py` (discovered-map view; accepts `reward:<room_id>`).

Verification that is known good:
```sh
cd /home/gd/melee_linux_test/gdm
python3 -m unittest discover -s tools/roguelite -p 'test_*.py'   # 37 named + module suites
env MELEE_MODS=0 MELEE_SCRIPTS=0 _build/agents/linux/melee --test \
  --iso "/home/gd/melee_linux_test/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
# 212/212 pass. Without MELEE_SCRIPTS=0 the three installed-script tests
# (script_pad_claim_gaps, script_pad_mask, script_lab_events) fail for
# environment reasons; root confirmed 33/33 script_ under the clean flags.
```

## Persistence review status

- P1 (temp collision) — DONE. Game commit `ba6cce4ee`. The temp is
  `dir/.atomic-<base>.tmp` (dot component unaddressable by the data-name
  grammar) with exclusive creation; handles both path separators; native test
  `script_data_write_atomic` now covers sibling `.tmp` survival and a
  failed-replace (target is a directory) that keeps sibling data. Native suite
  212/212 with `MELEE_MODS=0 MELEE_SCRIPTS=0`.
  - The `gs_data_path` snprintf length checks are implemented in the working
    tree but not committed, because that function differs in HEAD (backslash
    form) and is entangled with pre-existing uncommitted native work. Wire the
    checks when that work is committed; the atomic temp path length is checked.
- P2 (future-slot overwrite) — DONE. Game commit `35be19ff7` (main.lua) +
  regression in `test_runtime.py`: a valid generation plus a `TBD4` slot stays
  byte-identical across a save; loader classifies slots and wraps parsing in
  `pcall`.
- P3 (progress section / schema versions / migration in the loader) — OPEN,
  Batch 2 item 2.

### P1 detail (for reference) — atomic temp filename collides with a real data file
`l_data_write_atomic` uses `path + ".tmp"`. Script data names allow `.tmp`, so:
```lua
gd.data_write('x.tmp','keep'); gd.data_write_atomic('x','new')  -- destroys x.tmp
```
Fix: write the temporary as `dir/.atomic-<base>.tmp`. A path component starting
with `.` is unaddressable by the data-name grammar (`gs_data_path` rejects
leading `.` and `/.`), so it can never collide with or delete user data. Use
exclusive creation (`fopen(...,"wbx")`), and on open failure remove only that
unaddressable stale temp and retry once. Check `snprintf` results for
`gs_data_path` and the temp path; fail rather than truncate. Add native cases:
`x.tmp` preserved; a replace failure (target is a directory) keeps prior bytes;
keep the existing success/oversize/empty cases.

### P2 — an unsupported future A/B file is still overwritable
`main.lua` discards the `Checkpoint.decode` refusal reason and chooses the save
slot by parity. A valid older slot + an unsupported `TBD4` in the other slot:
the next save can overwrite the future file. Fix: classify each slot as
valid / legacy / unsupported-future / corrupt / empty (a reason containing
`preserved` with an envelope version > 3, or a `manifest schema` /
`progress version` refusal inside TBD3). Mark future slots protected; `save()`
must write the other slot and explain the restriction; if both are protected,
disable saving without touching either. Corrupt (non-future) slots stay
disposable as today. Add fixtures: valid gen 2 in A + `TBD4` in B -> gen 3 save
leaves B byte-identical; unknown manifest/progress version inside TBD3 behaves
the same; wrap the loader's `checkpoint()` in `pcall` so malformed nested data
is controlled refusal, never a thrown error.

### P3 — not yet done
`main.lua` does not yet pass a progress section to `Checkpoint.encode`, pass
expected schema versions to `Checkpoint.decode`, or call
`Legacy.migrate_progress` in its loader. Route creation is still
`Dungeon.generate`. Do not claim these live.

## Batch 2 — live v2 integration (in progress)

Immediate milestone: a real generated run entered through native TBD, with
certified physical rooms, branching/return traversal, safe save/resume. All
recipes are still `certified=false`, so `route:create` refuses and v1 remains the
live path; wire the plumbing with an explicit logged refusal/fallback.

Ordered bounded patches:
1. Instantiate `Topology`/`Adapter`/`Route` in `main.lua`; on new runs try
   `route:create`, log the refusal, and fall back to `Dungeon` v1. Add a
   `rogue_route` diagnostic. Keep v1 saves resumable with the frozen generator.
2. Save layer P3: write resolved manifest + schema-2 progress; pass expected
   versions to `Checkpoint.decode`; loader calls `Legacy.migrate_progress` and
   `Route:validate_save` inside `pcall`.
3. Replace `enter()` fixed floor/platform assembly with `Rooms.collision`
   (`floor_segments`, `platforms`, `lines`), slope `gd.stage_add_line`, and
   `Rooms.anchor`/`Rooms.arrival`; keep the incremental `preload_step` yields.
4. Per-socket doors: trigger from the source anchor, spawn at the destination
   socket's arrival; support top, bottom (downward-passage trigger), forks,
   merges, allowed returns and one-way drops. Preserve the recursive D-pad tree
   (Left/Right/Down choose; Up returns; Up taunts only at root).
5. Transactional `Route:travel`/`Route:collect`; mirror Core cleared/claimed/
   room/supplies/stocks; rollback both on failed load/save/reward/entry.
6. Manifest-driven encounters/rewards from resolved specs; only implemented
   mechanics; a disappeared actor is not a confirmed defeat.
7. Wire `route_map.build` into the discovered-map command/pause view (bundle it
   first). Note: `route_map` keys claims by catalogue reward id while
   `route.lua` records `'reward:'..room_id`; reconcile before relying on
   `reward_claimed`.

Do not edit the frozen Sol modules to make this work; consume their current
signatures (`Route:create/resume/travel/collect/validate_save`,
`Rooms.collision/anchor/arrival/preload_step`, `Adapter:manifest`).

## Batch 3 — native admission (after the above)

Build an isolated certification harness that inspects an uncertified recipe
without bypassing production admission; normal-speed controller clips per
admitted template (branch/merge/cross first), both merge entries, side/top
returns, one-way drops, movement profiles, seams, camera/blast bounds. Then
enter through the native TBD button and run distinct seeds through branching,
backtracking, locks, clear/reward/failure/victory and exact-route resume.
Human feel and unavailable hardware remain pending; do not self-certify.

## Reporting

Report changed files, what is actually live vs planned, exact commands/results,
evidence paths and limitations. Commit only owned files; preserve dirty work.
No release, no tag, no uncapped FPS experiment.

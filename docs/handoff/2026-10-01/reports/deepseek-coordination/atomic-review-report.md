Read-only review complete. Findings below are from the working tree at `melee/worktrees/linux` (HEAD `7fd8adc8d`), which another session has dirty; the atomic writer itself is identical between the commit and the working tree.

## Confirmed defects

**D1 — medium: the temp name can destroy a legitimate data file**
`l_data_write_atomic` builds `tmp = path + ".tmp"` (`gw_script.c:2540`), truncates it with `fopen(tmp,"wb")` (`:2541`) and `DeleteFileA(tmp)` (`:2550`, `:2554`). But `.tmp` is a legal suffix under `gs_data_path`'s own grammar (`.` allowed mid-name, `:2446-2456`), so `x.tmp` is a valid user file. `gd.data_write_atomic('x',...)` overwrites/removes the user's `x.tmp`; a prior `gd.data_write('x.tmp',...)` is silently destroyed.
Repro (console): `gd.data_write('x.tmp','keep')` → `gd.data_write_atomic('x','new')` → `gd.data_read('x.tmp')` returns nil.
Fix: make the temp name unrepresentable by the grammar (e.g. leading `.`, which `:2453` rejects at a name start), or refuse names matching the temp suffix, or open exclusively (`"wbx"`/`O_EXCL`). Regression: write `x.tmp`, atomic-write `x`, assert `x.tmp` unchanged.

**D2 — low: silent truncation can mis-target the temp/target**
`gs_data_path` formats the destination with `snprintf(out, cap, "%s/%s", dir, name)` and checks nothing (`:2465`); the writer then `snprintf(tmp, sizeof tmp, "%s.tmp", path)` (`:2540`). With a long `gs.data_dir` plus a 96-char name / 127-char id, both silently truncate; a truncated `tmp` can name a different file. Repro is install-path dependent. Fix: have `gs_data_path` reject names that overflow `cap`, and check the temp `snprintf` return.

**D3 — low: deterministic non-exclusive temp left behind / racy across processes**
The temp create (`:2541`) is non-exclusive and the name is fixed per target, and nothing removes a stale `x.tmp` after an interruption between `fopen` and `MoveFileExA` (`:2553`). Two processes writing the same target race on one temp. Fix: unique suffix + exclusive create; optionally sweep stale temps on load.

**D4 — caveat (not confirmed here): Windows replace is not atomic**
The doc comment (`:2522-2528`) correctly claims atomicity only for Linux `rename(2)`. `MoveFileExA(...,MOVEFILE_REPLACE_EXISTING)` (`:2553`, Linux shim `gw_compat_linux.c:512-518` maps to `rename`) is not guaranteed atomic on Windows and can fail on a sharing violation; failure keeps the old file, so behavior is safe, but the "never a partial file" claim only holds where rename is atomic. Worth stating explicitly.

## Missing test evidence (not defects)

`test_script_data_write_atomic` (`gw_script.c:9316-9350`) covers only success replace, an oversized refusal that returns before `fopen` (`:2537`), and an empty payload. It never drives a failed `fopen`/`fwrite`/`fflush`/`fclose` or a failed `MoveFileExA`, so Batch 1 items "short/failed write reports failure" and "failed replacement leaves old bytes intact" have no native evidence. The Python stub (`tools/roguelite/test_runtime.py:18,154-177`) covers a throwing write and a truncated newest slot, but its `data_write` is a stub, not the native helper. Also `CHECK_ATOMIC` detects success via `strstr(out,"true")` (`:9334`) — fine for the fixed strings used, but not a general proof.

## Batch 1 requirements still unimplemented in checkpoint/main

- **Req 1 (explicit migration):** `main.lua`'s `checkpoint()` (`main.lua:41-78`) parses TBD2/TBD1 inline and never calls `Legacy.migrate`/`migrate_progress`; `Legacy` is bundled (`prepare.py:34`) but unused. `DungeonV1` is not bundled (`prepare.py:34` bundles `dungeon` as `Dungeon`), as the checkpoint doc notes.
- **Req 3/4 (TBD3 progress + resolved manifest):** `save()` (`main.lua:79-109`) calls `Checkpoint.encode` with **no** `progress` field (`:97`), so schema-2 progress is never persisted (`decoded.progress` at `:57` is always nil). The manifest written is `Dungeon.generate(run.world_seed)` (`:88`), not a resolved v2 route manifest; `Route`, `Adapter`, `Topology`, `Progress` are not referenced by main.lua. Selected vs run fighter is kept distinct, but partner/transform rules are absent.
- **Req 6 (contain malformed nested data):** `checkpoint()` (`main.lua:45`) calls `Checkpoint.decode` without `pcall`; decode only pcalls `codec.decode` (`checkpoint.lua:80,90`) and calls `core.restore` unwrapped (`:70,74`), so a malformed profile/run section can throw instead of controlled refusal. Resource-history checks (earnable pickups/opened locks) remain open, as `SOL-RUNTIME-CHECKPOINT.md` states.

Requirement 2's sandbox path/name contract and 1 MB payload bound are implemented (`gs_data_path`, `:2537`), modulo D1/D2. Save migration is not complete.

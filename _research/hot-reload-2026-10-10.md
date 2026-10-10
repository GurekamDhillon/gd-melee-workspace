# Hot reload without a package rebuild (research, 2026-10-10)

Supersedes: nothing. Research only; no code was changed, nothing was built or run.
Evidence labels: **[read]** = a line of code/doc was read; **[agent]** = reported by a read-only
research agent, paths given but not re-opened by me; **[infer]** = reasoning, unconfirmed.
No timing in this note is measured. The "~72 s" splice preview figure was not found in any doc.

## Headline

1. The engine ALREADY has a live data hot reload for hitbox words (and attributes, parameters,
   same-layout overlays, the Lab script): `gd.hot_reload` / F8 in the Geno Lab. It rewinds,
   re-reads geno.json plus the overlay words files, re-applies to live fighters and REPLAYS the
   logged input on the new data. `melee/docs/geno.md:716-741` [read]; `melee/pc/platform/geno_registry.c:2025-2090`
   (`gw_Geno_Reload`), `melee/pc/geno/geno_game.c:849-855` (`GenoGame_LabReload`),
   `melee/pc/platform/gw_script.c:4611-4630` (`l_hot_reload`) [read].
2. The Workbench does not use it. "Rebuild + reload" = full Stage A/B/C package build, then
   `wb.reload`, which always fails by design and makes the launcher RESTART the engine process
   (`gw_script.c:7424-7431`, `engine_link.cpp:301-309, 476-480`) [agent].
3. So a hitbox-only fast path is mostly plumbing: assemble one `.genoasm` to `.words`, patch that
   overlay in the package, then call the existing hot reload. It is not a new engine feature.
4. Animation is the opposite: the bank/figatree is read once at start and nothing in the engine
   re-reads one clip. That is the big (C-side) item.

## R1. What "Rebuild + reload" runs

Path [agent unless noted]:
- Blender button `geno_wb.rebuild_reload`: `tools/blender/geno_workbench/operators.py:553`, label
  `props.py:195`; calls `Session.rebuild_reload()` `api.py:443-480`: MCP `rebuild`, then `reload`,
  then re-select row and frame.
- `rebuild` is a C++ launcher command, `tools/release/launcher/qt/workbench/commands_save.cpp:81-133`
  (30-minute timeout `:103`, no shell, cwd = git root). It runs the `rebuild` argv from the project
  `workbench.json`; goku-xv2: `python ports/goku-xv2/tools/build.py --fighter
  _build/goku-xv2/author-source/fighter.json` (`ports/goku-xv2/workbench.json:9-14`).
- `build.py main()` (`ports/goku-xv2/tools/build.py:424-460`):
  - Stage A `tools.geno.artist.pipeline.build()` (`pipeline.py:94-150`), always whole: [0/5] headless
    Blender glb export only if .glb older than .blend (`pipeline.py:46`); [1] validate; [2] mesh +
    plan.json + animation bank (`convert.write_bank`, `convert.py:208`; build dir deleted first
    `pipeline.py:106-107`); [3] `build_models` (fighterbuild once per costume); [4] assemble moves +
    geno.json + `tools.geno.check` subprocess; [5] install geno-lab and enabled.txt into mods/.
  - Stage B `apply()` (`build.py:235-420`): plan patch, bind placeholders, `script.assemble` per move
    (`:309`), window checks (`:315`), overlays, `write_fx` (`:187`), presentation art, Ki model
    (`build_ki :371`), lua/goku.lua, geno.json (`:383`), movemap, mod.json, reports.
  - Stage C: `audit_gameplay.audit(fit=True)` (`:442`), `ground_audit.py`, `tools.geno.check`,
    `tools.geno.report --frames` (`:447-457`).
- Likely slow [infer, unmeasured]: fighterbuild per costume, the Blender export when stale, the
  audit/report passes, and the full process restart + boot of the reload step.
- Package root `_build/goku-xv2/author-source/package/mods/goku-xv2/` (`workbench.json:15`):
  geno.json, mod.json, files/ (plan.json, GnGokuKi.dat, models, `Gn<Token>AJ.dat` bank,
  presentation), moves/*.words, lua/, plus the geno-lab companion mod.
- Hitbox-only change: `gameplay.json` is read raw, never compiled (`build.py:25, :237`). The hitbox
  numbers live in `ports/goku-xv2/moves/*.genoasm` (named by each move's `script`, `build.py:309-314`);
  the Workbench `edit_hitbox` edits the row's script file (`geno_data.cpp:279-292`,
  `commands_hitbox.cpp:72-77`), not gameplay.json (which is only change-checked, `:285`). A hitbox
  change therefore needs only: `moves/<name>.words`, the matching overlay entry in geno.json,
  and (nice-to-have) parity/loss reports. NOT: mesh, bank, models, glb export [infer from code;
  not run]. Hitbox scale comes from `art-report.json` (`build.py:240-242`), persisted across rebuilds.
  Note: if the owner edits `gameplay.json` fields (not the script) those flow in through Stage B
  only; check which fields feed overlays before promising a fast path for them.

## R2. How the engine consumes a define; what a reload touches

- Read at start: define registry parse `geno_define_registry.inc:20` (`plan`, `animation` file
  names); plan.json parse `:893-913`; bank file named by `fighter.animation`, returned by
  `gw_Geno_DefineString` `:537-541`. Docs: "read once at start" (`geno.md:22`; `pipeline.py:149`;
  artist README `:62`; goku-xv2 README "restart after every package rebuild").
- Hot-reload hook (offline only): `gd.hot_reload([sec])` steps (`geno.md:716-731`): rewind `sec`
  (default 2) -> `gw_Geno_Reload` (re-read every mounting mod's geno.json + the words files its
  overlays name into `gn_next`, compare layout, install, bump pool generation; returns 1 installed,
  0 layout changed, -1 parse failure keeps old data; `geno_registry.c:2025-2090`) ->
  `GenoGame_LabReload` (refill overlay pool, repoint subaction rows, rebuild state rows/params,
  recompute attributes via `ftCo_800D105C`) -> reload Lab script -> replay logged input.
- Reloads cleanly: attributes, jumps, special attributes, hooks, on_land, change-action checks,
  behaviour parameters, state next/land targets, landing/root-motion/counter params, SAME-LAYOUT
  subaction overlay words, the Lab script (`geno.md:733-735`).
- Does not: layout changes (profile set, state count/order/names/callbacks/anim rows/flags,
  article list, overlay list/order or script slot lengths/offsets) -> automatic match restart
  (`gd.lab_leave("restart")`, loading screen, same fighters/stage). Disc/file data (Pl*.dat,
  animations, models) need a new match. `on_init` hooks are not re-run (`geno.md:736-741`).
  Implication: lengthening a hitbox script beyond its slot is a layout change -> restart (still
  seconds, no rebuild). Same-length edits (changing numbers) replay in place.
- Staleness the engine itself guards: `geno_registry.c:2025-2060` states live fighters hold profile
  indices, subaction rows per overlay and copied callbacks, hence the layout rule.
- Rollback/netplay: `gd.hot_reload` calls `gs_require_offline`, which raises "offline-only (refused
  during a netplay/rollback session)" when rollback or netplay is enabled (`gw_script.c:889-895`,
  `:4622`). The online define handshake lists the bank and plan files two peers must agree on
  (`geno_define_online.inc:20-30`: content id `profile->id`, files[] = anim_file, plan_file). So a
  hot reload is a local-only authoring tool and cannot desync a netplay match; any mid-match swap
  online would have to be a negotiated define change [infer]. The pause-time cost: replay re-simulates
  `sec` seconds, fine.
- Other reload hooks checked: Lua `require`/`dofile` are banned in the sandbox (`gw_script.c:10499`
  `banned[]`), so there is no Lua require-reload; `wb.reload` is restart-only; no file watcher found.
  The `lab.lua` script is reloaded by hot reload (`lab.lua:703-705`, F8 at `:5867`, menu `:864-871`).
  Whether a mod's fighter-side lua (`lua/goku.lua`) is re-read by hot reload is not confirmed [infer: no].

## R3. Inventory of data that could load quickly (ranked for Goku re-picks/splices, hitboxes, Workbench)

| # | Data | Lives in | Consumed | Hot path | Size | Risk |
|---|---|---|---|---|---|---|
| 1 | Hitbox / hurtbox params, subaction events (same layout) | `moves/*.genoasm` -> `.words` -> overlay in geno.json | overlay pool -> subaction rows (`GenoGame_LabReload`) | Workbench: assemble one script, write one words file, call hot reload. Engine side exists | S | slot-length growth = restart; need a single-move assembler entry (build.py `bind`+`script.assemble`, `:93, :309`) |
| 2 | Attributes (weights, speeds, jump heights, fall speeds), landing lag, IASA/timers carried as state params | geno.json fighter/state params | `GenoGame_LabReload` recompute | Already works in F8; just edit geno.json and press F8 (or script it) | S (zero for hand edit) | Stage B rewrites geno.json, so hand edits get overwritten by the next build; edit the source, not the output |
| 3 | Lab script (`lab.lua`) and CLIPS/MOVES UI | `melee/pc/geno/mods/geno-lab/scripts/lab.lua` | reloaded by F8 | exists | 0 | none |
| 4 | Animation of one clip (the splice loop) | `Gn<Token>AJ.dat` bank | read once at start (R4) | needs engine primitive | L | see R4 |
| 5 | ground_modes.json, row-lengths, splice recipes / clip timing | `ports/goku-xv2/ground_modes.json`, `splices.json` | build-time in `xv2_to_artist.animations()` (`xv2_to_artist.py:711`), `splice.bake :346`, `retime :273` | they change the BAKED bank, so they are animation (row 4), not data. A fast path = re-bake one row only | M (with R4) | ground logic is applied after splice bake (`xv2_to_artist.py:562-591`); a one-row bake must run the same ground pass |
| 6 | fx / emitter params | `build.py write_fx :187`, `fx_build.py`, `fx_emitter_template.json` | written at Stage B into the package; runtime consumer not examined | probably a files/ or geno.json fragment; check whether geno.json `fx` is in the hot-reload re-read set | unknown (S-M) | not examined; confirm before promising |
| 7 | Toon/shadow tints, camera/stage params | not examined | | | ? | Not researched in this pass; first look in `plan.json` / presentation art and `gw_*` render settings. Owed |
| 8 | CLIPS library rows | `clip-library.json`, `ANIM-ROWS.json` from `xv2_to_artist.py`; CLIPS UI `lab.lua:5014-5420` | `gd.anim_rows` `gw_script.c:4330`, `gd.anim_preview` `gw_script.c:4352` / `script_game.c:2677` | metadata only is reloadable by F8 (script); the poses are the bank | S for labels | pose data = row 4 |

Notes:
- `build.py` already separates "gameplay reapply" (Stage B) from the art build (Stage A, persisted in
  `author-source`). I found no flag to run Stage B alone. A `--gameplay-only` (skip A, skip C audits)
  is the cheapest plumbing win and is likely seconds [infer: Stage B is Python + assembler].
- Anything the Workbench edits in `gameplay.json` that is NOT an overlay word (names, windows,
  parity metadata) does not need the engine at all.

## R4. What is already hot-reloadable today that the owner may not know about

- **F8 / `gd.hot_reload`** in the Geno Lab (STATES > Hot reload): live attributes/params/overlay
  words/Lab script, with automatic input replay. Includes the Lab console route
  `gd.hot_reload()` and the Lab macro path `lab.lua:2264` (reload at a marked frame, `A.from`).
- Layout change is handled by a quick match restart rather than a process restart, so even the
  "bad" case is a loading screen, not a package rebuild + engine boot.
- The Workbench engine link already has a headless engine mode and a TCP client
  (`tools/blender/geno_workbench/client.py`, `melee/pc/platform/gw_workbench.c`); the restart in
  `reload` is a choice (`engine_link.cpp`), not a limit of the protocol [agent; infer].
- `MELEE_LAB_MODE=clips` + `MELEE_LAB_CLIP=<row|name>` (`lab.lua:5148`, `ports/goku-xv2/tools/clips.ps1`)
  jumps straight into the CLIPS viewer on one clip.
- Not reloadable: Lua `require`/`dofile` (banned in the script sandbox), `on_init` hooks.

## R5. Animation as a first-class question (owner addition)

### How one clip gets to the engine [agent; paths read by the agent]
- **XV2 clip**: `ports/goku-xv2/tools/xv2_to_artist.py` (`main ~:901`). `animations(source, mesh,
  rows, splices)` (`:711`) samples IR clips on the BAC clock, applies retime (`frames`,
  `time_factor`) and the hover/anchor ground logic (`ground_modes.json` overrides). `emit_glb` writes
  `goku.glb`, `fighter.json`, `clip-library.json`, `ANIM-ROWS.json`. `--build` runs `build.py`.
- **Splice recipe**: `ports/goku-xv2/splices.json`; `tools/splice.py` (`bake :346`, `retime :273`,
  `mirror :208`, `apply_yaw :255`, `npz_clip :179`). Baked inside `animations()` before ground logic
  (`xv2_to_artist.py:562-591`). Recipe is preview-only unless `"wired": true`. `splice.py preview`
  does a reduced build (`--splice-only`, `GOKU_AUTHOR=splice-preview`) into
  `_build/goku-xv2/splice-preview/package/mods` with one library row `s<recipe>` (`splice_preview :593`).
- **Cross-port npz**: `tools/cross_port.py` (needs `GW_ISO_VANILLA`) -> `ports/ir/tools/retarget_melee_anim.py`
  -> `_build/goku-xv2/cross-port/<Row>/`; a segment names it `melee:<fighter>/<action>`; registry
  `tools/cross-port.json`.
- **Blender NLA**: `tools/blender/geno_workbench/nla_layout.py`, `nla.py` (`bake :709` calls
  `splice.bake :363`; `export_baked :766` runs artist `export_fighter.do_export`; `bake_and_export
  :842`); operator `operators_nla.py:135` `geno_wb.bake_export` writes ONLY a glb to
  `settings.nla_export_path`. "Save strips as recipe" writes `splices.authored.json`, never splices.json.
  Nothing after the glb triggers the package build (not verified in selftest/realcheck).
- **Packaging**: `convert.write_bank` (`tools/geno/artist/convert.py:208`) writes `Gn<Token>AJ.dat`,
  one figatree sub-archive per clip (`Ply<Token>_Share_ACTION_<Clip>_figatree`, rotation s16 1/4096 rad),
  installed into the mod `files/`; `geno.json fighter.animation` names it, `fighter.rows` lists
  unbound library rows (row 303+). Bank cap 256 clips (`GPL_MAX_CLIPS`), 576 for CLIPS (`geno.md:3100`).

### Engine side
- Bank is read once at game start (docs above). I did NOT locate the C function that reads
  `anim_file` into memory (searched the geno_define_*.inc, gw_script.c, script_game.c): where the
  bank is cached and which pointers reference it is unconfirmed. First task of any animation hot swap.
- No single-row reload, no per-clip override file, no mod reload that re-reads animation was found.
- LAB CLIPS reads the already-loaded bank: `gd.anim_rows(focus)` (`gw_script.c:4330`, skips rows
  bound to a Geno state), `gd.anim_preview(focus,row,frame,rate,face)` (`gw_script.c:4352`;
  `script_game.c:2677` `lab_preview_row[]`), pose-only when the fighter enters Wait (`geno.md:3105`).
  Console `lab clips ...` (`lab.lua:5403`).

### Cost: Blender NLA/splice edit to seeing it in seconds
Exists: NLA layout + bake + glb export; splice bake and a reduced single-recipe preview build;
CLIPS viewer with `MELEE_LAB_CLIP`; a Blender<->engine TCP link.
Missing (estimates, unmeasured):
1. Engine primitive to replace one bank row (re-read/patch the figatree, update every live
   fighter's animation pointer, keep gameplay hashes consistent). 2-4 days of C plus tests, after
   finding the load site. This is the only real blocker. Offline-only (like hot_reload) keeps it
   away from rollback.
2. Incremental encoder that writes just one clip (encoder at `ports/ir/tools/figatree.py`): ~0.5 day.
3. Workbench command `reload_clip(row, file)` + Blender hook after `bake_export`: ~1 day.
4. CLIPS auto-replay of the changed row: ~0.5 day.
Shortcut without engine change: rebuild only the preview bank and use `gd.lab_leave("restart")`
(match restart = loading screen). The restart re-reading a changed bank from disk is UNVERIFIED;
test first (1 day). Disc/file data "need a new match" (`geno.md:739`), so a restart is the
documented way to get new animations today.

## Top 5 recommendations (nothing implemented)

1. **Hitboxes: route the Workbench through the existing hot reload.** New `edit_hitbox` flow:
   assemble that move's genoasm -> words (reuse `build.py bind`/`script.assemble`), patch geno.json
   overlay/words in the package, then `gd.hot_reload` (F8 path) instead of rebuild + engine restart.
   Expect ~1-3 s for same-layout edits; layout growth falls back to a match restart. Size S-M.
   Verify first: (a) the headless Workbench engine can call `gd.hot_reload` (needs gameplay, offline);
   (b) the replay step is acceptable in the Workbench's frame-refetch flow.
2. **Add `build.py --gameplay-only`** (skip Stage A and the audits): shortens everything that is
   not animation or models (attributes, fx, move scripts, window checks) to Python-only seconds.
   Size S. Benefits non-Workbench edits too.
3. **Animation fast path, step 0: test "restart match re-reads the bank".** If yes, a splice/NLA edit
   becomes: bake -> `splice.py preview`-style single-row bank rebuild -> `lab_leave("restart")`, with
   CLIPS auto-playing the row via `MELEE_LAB_CLIP`. Size S (a test + a script). Gate for item 4.
4. **Animation true hot swap** (one-row bank patch + `reload_clip` workbench command + Blender
   hook after `bake_export`): the 'edit NLA, see it in seconds' goal. Size L (4-6 days incl. finding
   the load site). Do after 3 tells us what the restart path costs.
5. **Let Blender's `bake_export` finish the loop**: after writing the glb, call an incremental
   per-row `xv2_to_artist --splice-only` + bank encode (no whole-package rebuild, no models), which
   is also the prerequisite for 3 and 4. Size M.

## Decisions / owed
- Owed (nobody ran anything): all timings; whether hot_reload works in the headless Workbench
  engine; whether lengthening a hitbox script changes overlay slot length; location of the bank
  load in C; fx/tint/camera/stage consumers (R3 rows 6-7).
- Not examined: toon/shadow tints, camera/stage params (rows 7).

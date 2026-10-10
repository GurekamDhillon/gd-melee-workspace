# Goku XV2 v0.2 handoff — 2026-10-08

The schema-valid source IR and its Falcon parity bridge are ready. A playable
prototype using Goku's converted model and 61 clips has also run in GD's Melee.
This is a shallow adaptation with explicit losses and unfinished animation rows.

The user reviewed the first live version and found Goku too short. The rebuilt
version uses a 20-unit bind height: measured Wait-pose mesh height is 16.64857,
up from 11.654 (43% larger). Sockets, hurtboxes, fighter spheres, article spawn
offsets and the authored beam geometry were rebuilt/scaled together. Host
movement values remain labelled design values. Source IR values were unchanged.

Launch the persistent visible LAB in PowerShell:

```powershell
& 'E:\Projects\Melee Workspace\ports\goku-xv2\tools\play.ps1'
```

It uses a 1920×1080 window and render scale 3, the workspace's normal preview
settings. The model, scripts and animation bank come from
`E:\Projects\Melee Workspace\_build\goku-xv2\author-source\package\mods\goku-xv2`.
F11 / Alt+Enter toggles borderless fullscreen. Restart after package rebuilds.

## Completed gates and their limits

| Gate | Result | Evidence under `E:\Projects\Melee Workspace\` |
|---|---|---|
| Shared source IR validator | Exit 0; 35,424 IDs, 943 evidence entries | `_build\goku-xv2\ir-validation.log` |
| Independent source integrity | 1,499 files; 1,496 hashes; 36,130 JSON pointers; 6,994 BAC events; 28,359 BCM nodes; 139 parity rows; zero errors | `_build\goku-xv2\ir-integrity.log` |
| Focused test suite | 20 passed, including the local Falcon-disc test | `_build\goku-xv2\tests.log` |
| Artist validate | Exit 0; zero blockers, 12 warnings | `_build\goku-xv2\artist-validation.log` |
| Artist build, integrated gameplay wrapper | Exit 0; model comparison reported zero triangle/weight differences | `_build\goku-xv2\author-source\package\build\` |
| Geno check / report / schema freshness | Check: zero errors/warnings. All eight special bindings and required attack ownership recorded; `donor_free:true` is the tool's ownership result, not an animation-completeness claim | `...\package\build\geno-check.json`, `geno-report.json`; `python -m tools.geno.schema --check` |
| Offline script/pose/collision adapter | 182 active-frame sphere samples, 159 posed hurtbox samples; fourteen fitted capsules | `...\package\build\framedata-parity-check.json`, `hitbox-positions.json`, `hurtbox-coverage.json` |
| Contact sheets | 33 PNGs; red hit spheres and green hurt capsules drawn in Blender against the actual converted poses | `_build\goku-xv2\contact-sheets\index.json` |
| Native executable build | Exit 0; bridge ABI audit passed | `_build\goku-xv2\runtime-build.log` |
| Native special execution | Ten casts cover eight ground/air inputs plus three ground charge tiers; matching article spawns and zero fighter Lua faults | `_build\runs\goku-xv2-large-specials\melee-pc.log`, `GOKUCHECK PASS` |
| Native artist proof | Idle, walk, run, jump/double-jump, jab, shield input, grab and forward throw executed. Jab dealt 3%; grab captured; forward throw dealt 7%. This fixture runs the dash offstage and places the idle dummy offstage, so it is not a full combat acceptance suite | `_build\runs\goku-xv2-large-art\melee-pc.log`, `ARTPROOF DONE` |
| Visible preview | Model and animations rendered in the native game; user supplied size feedback and interacted with the revised fighter | `_build\runs\goku-xv2-preview\melee-pc.log` |

The shared `framedata_check.py` and `check_hitbox_positions.py` help was inspected.
Their original Ultimate-only CLI comparisons were **not run**, because they
require ACMD/install inputs absent from XV2. The port's parity adapter reuses
their native script/FigaTree/collider functions with real BAC and destination
data. It does not fabricate ACMD or certify XV2 collider equivalence.

## Remaining work and known faults

- **275 artist rows remain placeholders**, with eight aliases and seven
  no-animation rows; all 351 rows are listed in `ANIM-ROWS.json`. Source clip
  inventory contains the 93 Goku body clips. Several directional attack labels
  remain provisional. Other throws, ledges, damage and recovery art need authorship.
- Shader output is a provisional opaque diffuse atlas. Full DYT/toon rendering,
  source eye composition, facial skin deformation and hair/belt secondary motion
  are lost. Mesh topology remains dense (18,183 triangles). Source audio is absent.
- XV2 FPS has **not been measured**. Sampling uses the local exporter's 60-fps
  convention. Source runtime, BCM conditions and BAC time-scale fidelity are
  unverified; nothing in the source IR is marked observed.
- Source stats are absent. All 46 target importer attributes are design values
  with Falcon/reference-speed provenance. `calibrate_attrs.py` is specific to
  Ultimate and was not used to invent an XV2 conversion.
- Fitted hurtboxes cover 94.29% of rest mesh points and at least 88.48% of sampled
  poses. Those are measurements, not quality acceptance thresholds. Full moveset
  contact, both-facing behavior, shield interactions, landing cases, balance and
  rollback are **not comprehensively verified**.
- A LAB savestate taken before lazy article-model loading can restore away the
  model bytes while retaining a native cache entry. The first proof showed later
  articles with zero draw objects. Warming all three tiers before saving the
  baseline fixed the proof: every subsequent cast retained two joints/one draw
  object. This is a test-harness workaround; the engine cache/snapshot issue is
  not fixed. Normal fresh gameplay does not use this restore sequence.
- Closing the native game reports an existing `aurora_shutdown()` access
  violation (`0xC0000005`) caught by `melee/pc/platform/shim_vi.c:392`, followed by
  exit 0. The same fault appears in `_build/runs/np_host/melee-pc.log`, which
  explicitly loaded no mods. This explains the logged shutdown fault; no
  first-chance stack was captured, and the renderer issue is **not fixed**.

The source exporter and accepted v0.1 package remain read-only. No game bytes
were committed, no commits were created, and unrelated workspace files were
preserved. See [README.md](README.md) for exact paths and rebuild commands,
[PARITY.md](PARITY.md) for adaptation choices and
[ROLE-MAP.md](ROLE-MAP.md) for the single bone-role vocabulary mapping.

## 2026-10-08 polish pass

Shadow (engine fix, all base:none fighters), locomotion rows, move/hitbox review and engine cel
shading (`fighters[].toon`). Decisions: PARITY.md "Move review" and "Locomotion". Engine commits on
`worktrees/goku-polish` branch `agent/goku-polish`; the exe there (`_build/agents/goku-polish`)
is required for the shadow and toon. `gameplay.json` carries the `toon` block; `build.py` copies it
into geno.json. The workspace schema (`tools/geno/schema.py`, `geno.schema.json`) gained `toon` and
must land together with the engine branch.

## 2026-10-09 combo-lane fixes and grab/pad audit

- **Ki charge**: `M.kicharge_frame` loops the clip (`if ctx.self.anim_ended then ctx.loop() end`); `combo/tests/run_combo_ki.py` 5/5 (kicharge ki 0 -> 100).
- **Uair** (owner: retune): active f6-13 (was f7-11), spheres 6.0/4.8 design units (were 4.0/3.2); animation, damage, angle, KB unchanged. After the launcher short hop it now connects Fox, Falcon, Jigglypuff and Marth at 0/30/60/90% with no DI (it missed Marth at 0/30 and Puff at 30). Recorded in `gameplay.json` timing, `tools/attacks.py` and the FIDELITY.md uair row.
- **Self-chaining launcher aerials**: not reproducible in the current build (traces, 4 victims; routes taken end at `Launcher>Jump`). Engine reading: a light press needs `pressed_buttons & A`; a C-stick press is classed heavy (`geno_combo_smash`) and retail aerials read the stick separately, so the spec's C^ cannot feed `Uair>Nair`. `routes_prefix` removed from both specs and from `runner.lua`.
- **Throws never ended** (the owner's stuck grab): the throw scripts set `cmd_var idx=0`, which makes `ftCo_800DD724` freeze the thrower's animation at the release frame until the victim's thrown anim reaches it; a retail victim of a base-none thrower keeps its pose (engine commit 9e163eb50) so it never does (Goku stayed in Throw* 400+ frames). The four throw scripts no longer set it. `lua/grab_check.lua`: 26 cases x 4 victims PASS, both facings (throws 29/37 frames).
- **Pad takeover** (the "softlock" in the preview): geno-lab's `menu_close`/`menu_leave` and the CLIPS pose hold made `gd.input(port, 0, n)` for ports 1-6 outside a task, which claims the port until released. Fix on `agent/goku-labpad` (worktree `worktrees/goku-labpad`, commit 3f6c49c19): `pad_neutral()` + release in `on_frame`. Gate `lua/pad_check.lua` (fails on the old lab.lua with `P1 script release (owner 2)`, passes on the fixed one).
- Tools: `tools/run_lua_check.py <script> <TAG> [--vs ...]` runs a lua gate in turbo.
- Open: victims held/thrown by Goku keep a frozen pose (engine design in 9e163eb50); bair swap to Luigi's AttackAirB not started (needs a cross-skeleton retarget tool).

## 2026-10-09 cross-port bair (Melee Luigi AttackAirB)

Owner choice: no suitable XV2 back attack, so bair is Luigi's AttackAirB (animation + hitboxes). Tool: `ports/ir/tools/retarget_melee_anim.py` (workspace branch `ws/retarget-tool`; until it merges set `GOKU_RETARGET_DIR` to `worktrees/ws-retarget-tool/ports/ir/tools`). `python ports/goku-xv2/tools/cross_port.py` (needs GW_ISO_VANILLA) writes the clip to `_build/goku-xv2/cross-port/AttackAirB/`, `moves/bair.genoasm` and the bair block of `gameplay.json`; registry `tools/cross-port.json`; `xv2_to_artist.py` bakes it; `fidelity.py` reports status CROSS-PORT. `attacks.py` skips cross-port moves. Gate: `lua/bair_check.lua`. View: `tools/clips.ps1 AttackAirB`.

## 2026-10-09 punch-list pass (items 1, 3, 7, 8, 11, 12)

- **Ground blend (#1, #3)**: `xv2_to_artist.py` `ground_blend()`: anchored rows that start/end standing ramp the lowest point between the hover height and the floor anchor over 6 frames; exit poses ease into Wait; Squat/SquatWait/SquatRv are anchored (grounded). Gate `lua/ground_trace.lua`.
- **Landing sink (#7)**: cause = engine ECB is the bounding box of six joints (head, shoulders, knees, hip) and his folded flight-stance aerials lift them; `build.py` puts TopN in the hip slot of `ftdata.x44_ecb` (Goku only). Gate `lua/landing_check.lua` (40 landings, 0 sinking; was 28).
- **Emblem (#8)**: `mark` is a black-ink DDS-alpha decal; `material_tile` now composites it over the gi orange from its own UV window.
- **Bair reach (#11)**: bone-scale tracks carried (`cross_port.py scale_tracks`, `cross-port.json scale_gain` 0.33, fighter.json `clips.scale_bones`, artist `convert.py`/`model.py`/`validate.py` opt-in). Gate `lua/bair_reach.lua`.
- **Landing lag (#12)**: `tools/landing_lag_range.py` -> `_build/goku-xv2/landing-lag-range.md` (all of his aerials already inside the retail range).
- Re-pick shortlists: `_build/goku-xv2/repick-shortlists.md`.

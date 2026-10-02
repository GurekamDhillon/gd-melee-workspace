I'll start by exploring the worktree and reading the referenced docs.

Now I understand the environment. Let me set up a todo list and start building.

Now I'll create the game-side certification mod.

Now the main Python harness. This is the core deliverable.

Now the pure test suite.

Let me quiet the CLI tests' expected stderr noise.

I'll add a guard so the shared review app dir can't be modified by accident.

Delivered the isolated certification harness. No existing files were modified; native runs/installs/commits were not performed.

## Owned artifacts
- `tools/roguelite/certify_rooms.py` — CLI harness (inspect / plan / install / restore / run)
- `tools/roguelite/test_certify_rooms.py` — 45 pure tests (plans, parser, refusal, state, install safety)
- `melee/worktrees/linux/pc/scripts/examples/roguelite_certification/{main.lua,README.md}` — the isolated native probe (game checkout `linux3` only)

## What it does
- `inspect` resolves every template through `RoomRecipes.resolve` purely (no native process), reporting recipe version/`certified=false`/sockets/openings.
- `plan` builds per-template coverage: `branch_y` ascent/return/both forks, `rejoin_merge` both entries, `junction_cross` drop + safe arrival + alternate return + one-way check, `shortcut_door`; mobility profiles bowser/jigglypuff/falco/kirby. Status is `proposed-needs-native-validation`.
- The probe mod preloads the BF kit one model per tick, spawns the reviewed visuals, builds **segmented** floors/platforms/slopes (`Rooms` + `gd.stage_add_platform`/`stage_add_line`), isolates FD, labels teleports `fixture=true`, and records bounded per-frame traces. Teleports are never traversal evidence.
- Verdicts are always `pending-native-run` (no run) or `manual-review-required`; `certified` is never set. Logs are JSONL + a summary JSON with capture paths.

## Exact CLI
```sh
python3 tools/roguelite/certify_rooms.py inspect --json /tmp/cert-inspect.json
python3 tools/roguelite/certify_rooms.py plan
python3 tools/roguelite/certify_rooms.py install --app-dir <isolated-app-dir>
python3 tools/roguelite/certify_rooms.py restore --app-dir <isolated-app-dir>
python3 tools/roguelite/certify_rooms.py run --app-dir <isolated-app-dir> --port 51700 \
  --log <...>.jsonl --capture-dir <captures> --summary <...>.json
```

## Root prerequisites
- Native build with the current model/stage API (`gd.model_load/spawn/despawn/release`, `stage_add_platform`, `stage_add_line`, `stage_isolate`), launched at normal speed with `MELEE_CONSOLE_PORT` and the disc; `_build/agents/linux` exe must be rebuilt from the current game checkout.
- Install only into a dedicated app dir. `install` refuses the shared `_build/agents/linux` unless `--allow-shared`, backs up `enabled.txt` once, writes only the `roguelite_certification` mod, and never touches `scripts-data/roguelite_main` or the exe.
- `run` refuses `MELEE_TURBO`/`MELEE_FPS=u` (and an accelerated `gd.perf` rate), debug flight, a CPU port 1, already-certified recipes, and missing APIs (reported by name).

## Honest limitations
- No native traversal was run here; `run` requires root on a Windows/Linux host. The 82-test suite (`python3 -m unittest discover -s tools/roguelite -p 'test_*.py'`, 1 pre-existing skip) only validates plans, parsing, refusals, state/cleanup and install safety. Lua compiles under `lua5.4`; bundled mod compiles.
- Proposed controller probe programs are starting points, not proven traversals; seam/clearance/one-way outcomes are classified as candidates/`inconclusive`/`failed-*` and always flagged for human review.

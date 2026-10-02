I'll start by orienting myself in this isolated worktree and reading the relevant docs.

Now I have enough context. Let me set up my task plan and start implementing.

Now the test harness:

All 14 Lua tests pass. Now the contract document:

All 15 tests pass. Let me verify I only touched the assigned files and check for regressions.

Let me smoke-test the lexical bundling form (as `prepare.py` wraps modules) to catch any cross-module local assumptions.

Gate 6 enemy/boss controller work is implemented and tested. Report:

**Frozen files (new, owned; nothing else edited)**
- `melee/worktrees/linux/pc/scripts/examples/roguelite/encounter_behaviors.lua`
- `melee/worktrees/linux/pc/scripts/examples/roguelite/boss_behaviors.lua`
- `tools/roguelite/test_enemy_behaviors.py`
- `docs/ENEMY-BEHAVIOR-CONTRACT.md`

Confirmed via `git status`: `main.lua`, `prepare.py`, `core.lua`, `runtime_encounters.lua`, `technical_ai.lua`, `progress.lua`, catalogues and other tests are untouched (pre-existing dirty baseline preserved).

**API**
- `Behaviors.new(Core, {get_run,visible,actions,on_event}, opts)` → `:add/remove(id,reason)/tick(frame,obs)/states/counters(id?)/confirm(move_id,success)/release`.
- Pure boundary: `sanitize_obs` (drops hidden input/teleport), bounded per-target pose history for reaction delay, `delayed_pose`, monotonic-frame refusal, room-aware `avoid`/`recover`.
- Returns legal `move`/`recover`/`ability` requests; ability data read from real `Core.ability` (ready/reach/damage/action) — no invented engine API, no charge/teleport/invuln.
- 6 distinct archetypes (pressure/guard/zone/aerial/elite/boss) spanning custom+fighter; 12 authored compositions; simultaneous-tell arbiter; separated measured `opportunities/requests/successes`.
- Optional explicit `deps.actions = {available, submit}` for the concurrent gene_actions worker; success only from host `confirm`.
- `Boss.attach/resume/state`, 3 controllers (warden/glacier/tempest), phases with tell/attack-choice/vulnerability/recovery/positioning, `Boss.progress_addon` (versioned sibling record; `progress.lua` frozen) with validate/encode/decode, phase resume and duplicate-reward refusal.

**Results**
- `python3 -m unittest tools.roguelite.test_enemy_behaviors -v` → **15/15 OK** against the real Core/catalogues/Codec.
- Lexical-bundle smoke (IIFE wrapping, as `prepare.py` does) loads and validates both modules.
- Full `tools/roguelite` discovery: 129 run; the 4 errors are pre-existing missing generated art (`menu/out_effects_study`, `menu/out_roguelite`) in `test_certify_rooms`, `test_rooms`, `test_runtime` — unrelated to these files.

**Integration requirements**
1. Bundle `encounter_behaviors.lua` then `boss_behaviors.lua` in the root-owned `prepare.py` (after `enemy_genes`/`technical_ai`, before `main.lua`).
2. Provide the observation function from real engine reads and execute requests via `Core.activate` + `gd.enemy_strike`/`gd.enemy_hurt` or fighter input; report outcomes with `manager:confirm`.
3. Persist the boss addon (checkpoint sidecar / next schema) and gate boss rewards through `progress_claim_reward`.

**Unavailable here (pending root/native):** native enemy combat, rendered tell readability, Windows/Linux game, controller feel, AI tech-execution counts, human readability/boss feel. No 20XX/UnclePunch or external system reuse is claimed; only the existing native technical-assist interface was read.

# Can slippi-ai / Phillip pilot fighters in our port? Feasibility study, 2026-10-03

Read-only study. Nothing in the game or workspace was edited, built or launched. Scratch (clones, the
downloaded checkpoint, pickle dump) is in `_build/tmp/slippi-ai-research/` (git-ignored). No Python
package was installed anywhere. Tags: **VERIFIED** = read in a repo/doc/file (cited), **INFERRED** =
reasoned, not tested. Nothing here was run against the game.

Prior art in our tree: `_research/roguelite-ai-2026-09-30.md` audited slippi-ai at 275c0727 and copied no
code or weights; that stays true here (VERIFIED: that file, header and table row for Slippi-AI).

## 0. Short answer

- A usable trained agent **can be downloaded today**: slippi-ai's README links a 95.6 MB checkpoint
  ("medium-v2", 12 characters, 21 frames of delay) on Dropbox. No licence or terms accompany the
  weights, so it is for local testing only, never for our release. (Section 2.)
- The agent needs only a **small observation** (per player: percent, facing, x, y, action id,
  character, jumps left, shield, on-ground, invulnerable, stocks-free; stage id; up to 15 items) and
  returns a **GameCube pad** (stick 33x33 buckets, C-stick, trigger, 8 buttons). Our Lua API already
  exposes nearly all of it. (Sections 3, 4.)
- Recommended bridge: **a Python process that loads the checkpoint through slippi-ai's own agent API
  (no Dolphin, no libmelee) and talks to the port over the existing console socket, with a small Lua
  script in the port doing per-frame export and input queueing. Size S, no C changes.** (Section 4.)
- It would give us a real-ish opponent on normal stages for Melee characters. It would not navigate
  our custom levels, would not play Sora or Meta Knight as themselves, and does not drive menus.
  (Section 5.)

## 1. What the projects are

### slippi-ai ("Phillip II"), https://github.com/vladfi1/slippi-ai

- VERIFIED (README.md): successor to Phillip; "starts with behavioral cloning on slippi replays, which
  makes it a lot more like a human". Two stages: imitation learning from replays, then RL
  self-play refinement (README "Code Overview"; `slippi_ai/rl/run.py`, `train_two.py`).
- VERIFIED: active. Last commit 2026-09-23 ("[readme] Acknowledge Enzyme"); pushed 2026-10-03; 161
  stars (gh api). Python >= 3.12 (`setup.cfg` `python_requires = >=3.12`; README "Tested with python
  3.12 and 3.13"). Stack: JAX + Flax `nnx` is primary, TensorFlow stack legacy (ARCHITECTURE.md).
  `setup.cfg` pins `jax<=0.10.1`, `flax>=0.12`; extras `cuda12`/`cuda13`.
- **Observation** (VERIFIED `slippi_ai/types.py`, `slippi_db/parse_libmelee.py`, `jax/embed.py`):
  `Game` = `p0`, `p1` (the agent is always p0, so ports are remapped), `stage`, `randall`
  (Yoshi's), `fod_platforms`, `items` (15 slots). Per `Player`: `percent, facing, x, y, action
  (uint16), invulnerable, character, jumps_left, shield_strength, on_ground`, previous `controller`,
  and `nana` (Ice Climbers' partner). Embedding (`jax/embed.py:403-450`): action is a one-hot of
  size 0x18F (399) with CLAMP policy (a comment notes some Kirby copy states exceed it); character a
  one-hot of 0x21 (33); jumps_left one-hot of 7; xy scale 0.05; shield scale 0.01. The embedded
  per-step input is 2613 wide (first weight matrix `(2613, 768)` in the checkpoint, below).
  **Not used**: action frame, hitstun, hitlag, speeds (optional `with_speeds`, off in the
  checkpoint), ECB, stocks. (`action_frame`/`hitstun_frames_left` are commented out in `embed.py:432-436`.)
  **No stage geometry** except stage id, Fountain of Dreams platform heights and Randall.
- **Action space** (VERIFIED `controller_lib.py`, `jax/embed.py:546-576`, `jax/controller_heads.py`):
  buttons A B X Y Z L R D_UP (autoregressive order), main stick, C stick, one shoulder value. In the
  checkpoint `axis_spacing = 32`, so each stick axis is 33 buckets over [0,1] (about 5 raw units of the
  native +-80 range; `AXIS_SPACING = 160`), shoulder spacing 4. Heads are autoregressive
  (`controller_head: autoregressive`/`residual` in config).
- **Reaction time / delay** (VERIFIED `eval_lib.py:87-183`, `jax/policies.py:60-71`): the policy has a
  trained `delay` (frames). `DelayedAgent` pre-fills its output queue with `delay - console_delay`
  dummy controllers and pops one per frame, so the controller applied at frame t was computed from the
  observation at frame t - delay. The released checkpoint has `delay = 21` (read from the pickle's
  config). Phillip README quotes "18+ frames". **Consequence for a bridge: the agent has about 20
  frames of slack, so the link does not have to answer within one frame.** (INFERRED from that queue
  design; the code supports it, nothing was run.)
- **Run against Dolphin** (VERIFIED `slippi_ai/dolphin.py`, `envs.py`, libmelee): `Dolphin` wraps a
  `melee.Console`, launches a Slippi Dolphin AppImage/exe, connects to the Slippi spectator stream,
  creates `melee.Controller`s (named pipes), navigates menus with libmelee's menu helper, and each frame
  `Parser.get_game(gamestate)` converts to `Game`, the agent samples, `send_controller` writes
  press/tilt commands. Headless/fast mode needs a custom "ExiAI" Dolphin build
  (`use_exi_inputs`, `enable_ffw`; `dolphin.py:113-125`, libmelee `console.py:418-426`) from
  https://github.com/vladfi1/slippi-Ishiiruka (branch `exi-ai-rebase`).
- **Training pipeline** (VERIFIED README, `slippi_db/parse_local.py`): `.slp` archives -> parquet via
  `slippi_db/parse_local.py` -> `scripts/train.py` (imitation; "on a good GPU (e.g. a 3080Ti) ... a few
  days to a week") -> `rl/run.py` or `rl/train_two.py` (RL). Metrics to wandb.
- **Evaluation scripts** (VERIFIED): `scripts/eval_two.py` (play a model vs human or another model),
  `scripts/run_evaluator.py`, `scripts/netplay.py`, `scripts/twitchbot.py`.
- **A decomp-based simulator exists but is not public.** `slippi_ai/sim_env/` imports
  `melee_sim` ("melee-sim-light", README credits Enzyme); only Fox and Falco, six stages
  (`sim_env/env.py:42-53`). `pip index versions melee-sim` and `melee_sim` returned nothing and
  `github.com/Enzyme/melee-sim-light` is a 404. VERIFIED the module is imported and absent from
  `requirements.txt`/`setup.cfg`. It is useful to us as a **template**: its docstring describes "the
  direct bridge from native buffers to the slippi-ai Game/Controller structures", which is exactly
  the adapter we would write (`sim_env/env.py:1-18`).
- **Licence: MIT**, "Copyright (c) 2020 Vlad Firoiu" (`LICENSE`). MIT permits use, copying,
  modification, merging, publishing, distribution, sublicensing and sale, provided the copyright and
  permission notice are included in all copies or substantial portions. (VERIFIED, file head;
  `setup.cfg` classifier also says MIT.) The licence covers code, not the weights (Section 2).

### Phillip (original), https://github.com/vladfi1/phillip

- VERIFIED (Readme.md line 4): "This project is no longer active and is subject to bit-rot",
  points to slippi-ai. Last commit 2026-07-06 ("Remove git-lfs tracked agents, stop using git-lfs");
  one commit in the shallow history I fetched (INFERRED: repo history is longer; clone was --depth 1).
- Pure deep RL; `setup.py`: `tensorflow==2.13`, `pyzmq`, `python_requires='<3.12'`. State comes
  from Dolphin's MemoryWatcher at hard-coded RAM addresses (`state_manager.py`: `0x804C1FAC`,
  `0x80453080 + 0xE90*player_id`) plus a custom Dolphin; Windows needs a custom Dolphin zip
  (Readme step 1). "Training on Windows is not supported."
- Agents: about 82 MB of TF checkpoints are committed under `agents/` (Fox/Falco/Marth/Peach/Sheik
  on FD, a Falcon on BF, delay0/12 folders). The best human-like agents (`delay18/FalcoBF` etc.) are
  stubs (20 KB) in the repo and live in a Google Drive zip (link in Readme).
- **Licence: GPL-3.0** (`LICENSE`, "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007"): copyleft;
  a work that includes or links it must be distributed under GPL-3.0 with source. Our tree is GPL-2.0
  (root `LICENSE`; source files carry `SPDX GPL-2.0-or-later`, e.g. `gw_slippi_wire.h:1`), so
  Phillip code must never be merged into the port. INFERRED: running it as a separate process is fine.
- Verdict (INFERRED): obsolete. It reads RAM addresses that do not exist in our process, needs TF
  2.13 on Python < 3.12, and slippi-ai supersedes it. Do not use.

### libmelee, the interface library both depend on

- Two copies: https://github.com/altf4/libmelee (README: "ARCHIVE ... managed by xpilot now";
  version 0.41.1, last commit 2026-01-25) and the maintained fork https://github.com/vladfi1/libmelee
  (last commit 2026-07-29; `pyproject.toml`: `license = "LGPL-3.0-only"`, authors "AltF4,vladfi1";
  deps `pyenet-vladfi`, `py-ubjson`, `numpy`, `pywin32`). slippi-ai requires `melee>=0.47.1`
  (`setup.cfg`), i.e. the fork's line. VERIFIED.
- **Licence: LGPL-3.0** (`LICENSE.txt`, "GNU LESSER GENERAL PUBLIC LICENSE Version 3"): may be used
  by non-GPL programs if used as an unmodified separable library; modifications to the library must be
  released under LGPL-3.0, and users must be able to replace it. Also, its bundled `GALE01r2.ini` is a
  Slippi gecko-code file (see Credits).
- libmelee is **not needed** under the recommended bridge, except if we want to reuse its `Action`,
  `Character`, `Stage` enums (see Section 4).

## 2. Trained agents: what is actually downloadable

| Artifact | Where | Size | Scope | Terms |
|---|---|---|---|---|
| "medium-v2" | Dropbox link in slippi-ai README ("Playing the Bot") | **95,559,707 bytes (91.1 MiB)**, fetched by me into scratch as `medium-v2.bin` | 12 characters: fox, falco, marth, sheik, jigglypuff, cptfalcon, peach, yoshi, popo, luigi, pikachu, samus; one model, character chosen with `--p2.character`; any opponent; delay 21 | none stated anywhere I found |
| Full "released models" folder | second Dropbox folder in the README | not fetched (a folder; size not shown without the account page) | per-character/delay variants (INFERRED from `eval_lib.build_matchup_table(models_path, delay)`) | none stated |
| Tiny demo checkpoints | `slippi_ai/data/checkpoints/*` in the repo | 476 KB total | toy (tests) | MIT as repo contents (INFERRED) |
| Phillip agents | `phillip/agents/` (82 MB, TF) and Google Drive zip | 82 MB in repo; Drive zip size not checked | Fox/Falco/Marth/Peach/Sheik/Puff/Falcon | GPL-3.0 repo; Drive terms unknown |
| Hosted bot | Twitch channel x_pilot (README) | n/a | plays via Slippi netplay | public netplay only; not usable by us |

Disclosure: my first request for the Dropbox page URL (`dl=0`) was redirected and downloaded the whole
95.6 MB model rather than an HTML page. It stayed in scratch and I did not install or execute anything
from it. I inspected it safely: the file is a Python pickle (protocol 4); I listed its opcodes with
`pickletools.dis` (no execution) and loaded it with a **restricted unpickler that only allows numpy
and stubs everything else** (VERIFIED, run here). Findings:

- keys `state, config, name_map, step, rl_config`. `state['policy']` holds **23,887,032 float32
  parameters** (so about 95.5 MB). Network `tx_like`: 3 layers, hidden 768, ffw multiplier 2, LSTM
  recurrent layer, GELU (config `network.tx_like`). `policy.delay = 21`.
- Trained on "Dataset-3.18.0" (path in config); RL stage config shows a KL term toward a teacher
  `top12_d21_imitation_3x768_v5`; run name `top12_d21_rl_kl_5e-02`.
- **The policy is name-conditioned**: `name_map` is a table of real player tags (Zain, Amsa,
  Cody, Aklo, ... and "Master Player"); the RL config plays as "Master Player". (Credit/ethics note:
  the model is imitation of named real players.)
- The Dropbox link, the README text and every file I read contain **no licence for the weights**. The
  repo's MIT covers code. Our own earlier audit made the same point. Treat redistribution as **not
  granted** (INFERRED; ask the author).
- **Replay data**: README says most imitation data came from "anonymized ranked collections" supplied
  by Fizzi (link only inside the Slippi Discord) plus "the many players who have generously shared
  their replays". The dataset is **not published** and its terms are unknown. The number of replays is
  not stated in the repo. Training the full model is therefore not reproducible by us and not what we
  would do; compute order of magnitude is "days to a week on a 3080 Ti" for imitation alone (README),
  and the RL stage on top. (VERIFIED README; replay count unknown.)
- A model for **Sora or Meta Knight does not exist** and cannot be built from replays (there are none).

## 3. The interface a game must provide

### What libmelee reads from Dolphin

- Transport (VERIFIED libmelee `slippstream.py`, `console.py`): Slippi Dolphin runs a
  "Slippstream" server (default UDP/ENet 127.0.0.1:51441, `slippispectatorlocalport`); libmelee
  connects with `enet`, sends a JSON handshake, and receives **UBJSON "raw" Slippi events**:
  `PAYLOADS (0x35)`, `GAME_START (0x36)`, `PRE_FRAME (0x37)`, `POST_FRAME (0x38)`, `GAME_END`,
  `FRAME_START`, `FRAME_BOOKEND`, `ITEM_UPDATE`, `FOD_INFO`, `DL_INFO`, `PS_INFO`, `MENU_EVENT`
  (`console.py:989-1086`). One game state is produced per frame, at the console's 60 Hz (or fast
  forward). In EXI mode inputs/ffw go through the custom build.
- Fields in a libmelee `PlayerState` (VERIFIED `console.py:1233-1296`): position x/y, character,
  action id, `action_frame`, facing, percent, shield strength, stock, hitstun frames left, hitlag,
  on_ground (`!airborne byte`), jumps_left, invulnerable, five speeds (`speed_air_x_self`,
  `speed_ground_x_self`, `speed_y_self`, `speed_x_attack`, `speed_y_attack`), is_powershield, plus the
  controller state (sticks, trigger, button bits). `GameState`: frame, stage, players, projectiles,
  Stadium/FoD/Dreamland info. **slippi-ai uses only the subset in Section 1.**
- libmelee re-indexes animation frames to start at 1 and treats Sheik/Zelda as one character (README
  "Note About Consistency"); slippi-ai ignores action frames so the first is irrelevant to it.
- **Minimum Slippi version** slippi-ai demands: 3.18.0 (`dolphin.py:91`). Reason: field availability.

### What libmelee sends back

- Dolphin **named pipes** (Windows `\\.\pipe\slippibot<port>`; Linux `Pipes/slippibot<port>`), text
  lines `PRESS A`, `RELEASE A`, `SET MAIN x y`, `SET C x y`, `SET L v` with floats in [0,1] and 0.5 as
  neutral; flushed once per frame; Dolphin config `BlockingPipes = True` makes the game wait for input
  each frame (lock-step) (VERIFIED `controller.py:106-370`, `console.py:340-345`).
- slippi-ai sets 8 buttons, `main_stick(x,y)`, `c_stick(x,y)`, one L-shoulder value
  (`controller_lib.send_controller`). Quantisation: stick 5 raw units; shoulder spacing 4 of 140.
  Raw ranges: stick +-80, deadzone 23 (`controller_lib.py` constants). Not used: Start, D-pad L/R/D,
  analog R separately.

### Stage and character assumptions

- Stage id one-hot of 64 (`embed.py:494`), so any libmelee stage id < 64; the training data is mostly
  the six legal stages (the sim env lists FoD, Stadium, Yoshi's, Dream Land, Battlefield, FD,
  `sim_env/env.py:42-53`). Character one-hot 33 (0x21). INFERRED: unseen stage/character rows were
  never trained, so behaviour for ids outside the data is undefined, not an error.
- The model never receives stage geometry. This is structural, not statistical (VERIFIED `types.py`
  `Game`).

## 4. What our port exposes, and the bridge

### Our side (all VERIFIED unless tagged)

- `gd.player(port)` / `gd.players()` (`docs/scripting.md:172-200`; `gw_script.c:1137-1229`): port,
  char, kind, costume, cpu, x, y, vx, vy, percent, stocks, falls, facing (+-1), **action** (id),
  action_frame, anim_frame, airborne, hitlag, and LAB fields: `hitstun`, `in_hitstun`, `ecb`,
  `ecb_lock`, `jumps_used/max/left`, `walljumps_used`, `shield`, `shield_on`, `shield_x/y/r`,
  `ground_vel`, `intangible` timer and a body state (normal/invincible/intangible), animation names,
  active `hitboxes`.
- `gd.items()` (id, kind, owner_port, x, y, vx, vy, facing, frame_alive, state), `gd.hitboxes(port)`,
  `gd.match()` -> `{active, frame, stage, netplay}`, `gd.pad(port)`, `gd.frame()`.
- `gd.input(port, spec [,frames])` takes `{buttons=, x=, y=, cx=, cy=, l=, r=}`, sticks -127..127,
  triggers 0..255; it replaces every other source, counts **completed logic frames**, and the claim
  persists (neutral between holds) until released (`docs/scripting.md:315`, `gw_script_pad.c:14-28`).
- Hooks `on_frame_pre()` (start of each logic frame) and `on_frame()` (end) run in lock-step with
  game logic (`scripting.md:138-150`). Lua is sandboxed: **no network, no io** (`scripting.md:91-113`);
  files only via `gd.data_read/write` (1 MB each). Per call budget 2M instructions / 50 ms.
- The **console socket** (`MELEE_CONSOLE_PORT`, `gw_script.c:8316-8345`): loopback only, plain text,
  one line in, lines out then `>>> ok`/`>>> error`; up to 4 clients; "one command per client per
  rendered frame"; commands include `state`, `pause`, `resume`, `step [n]`, `input ...`, and any
  Lua expression (`= expr`), whose Lua environment persists between lines (`scripting.md:596-637`,
  `melee/pc/scripts/console.py`). So one command can both set inputs and return a serialized state.
- `MELEE_PAD_SCRIPT` (txt or Lua) and `MELEE_PAD_LIVE` (a file re-read each PADRead) exist
  (`gw_script_pad.c:1-30`) but are weaker than `gd.input`.
- **Slippi codes**: the port applies the same gameplay codes as Slippi (UCF 0.84 pad buffer,
  dashback, shield drop, etc.), chosen with `MELEE_SLIPPI_CODES=online|tournament|off`; default for
  live play is vanilla (`gw_replay.c:1362-1370`, `_research/slippi-gameplay-codes.md:20-57`; a
  few SDI/tumble variants are listed there as gaps). **This matters**: the agent learned on Slippi
  online replays that ran with UCF; set `MELEE_SLIPPI_CODES=online` for agent tests. VERIFIED that the
  switch exists; INFERRED that it makes the ruleset match what the agent saw.
- **Slippi work already in the tree** (`gw_replay.c`, `gw_slippi_*.c`, `tools/replay/slp.py`,
  `tools/slippi/*`, `docs/HANDOFF-2026-09-24-SLIPPI.md`): the port **reads** `.slp` files
  (`MELEE_SLP`), compares its state trace to them, and speaks the Slippi **netplay peer** packets
  (ENet pads/acks/selections, `gw_slippi_wire.h` pinned to Dolphin `SlippiNetplay.cpp`). It does
  **not** write `.slp` frames and does **not** serve the spectator/Slippstream protocol that libmelee
  consumes (grep for spectator/slippstream/libmelee across `melee/pc` and `_research` found nothing
  relevant; `_research/rollback-netcode.md:586` lists spectators as "later"). So option (a) would be
  new work.

### Field mapping (what the adapter must produce per frame)

| slippi-ai field | our source | note |
|---|---|---|
| percent, x, y | `gd.player` | floats |
| facing | `facing > 0` | |
| action | `action` | the internal action-state id; libmelee's `Action` enum is the same numbering (INFERRED; spot-check a few: standing, dash, jumpsquat, shield) |
| character | `char` | external id; INFERRED same as libmelee `Character` for the 25 vanilla fighters; m-ex/custom ids (>= 0x21) are out of range |
| jumps_left | `jumps_left` | |
| shield_strength | `shield` | check scale (libmelee 0-60) |
| on_ground | `not airborne` | libmelee uses a separate byte; near-equal |
| invulnerable | `intangible > 0` or body state != normal | INFERRED mapping, verify |
| nana | none for non-ICs (exists = false) | |
| stage | `gd.match().stage` | our stage kind id -> libmelee `Stage` id table needed (INFERRED: both are Melee's external stage ids; verify for FD) |
| items | `gd.items()` | map `kind` to libmelee projectile types; the model has a 0xEC item-type one-hot |
| prev controller | kept by the agent process | |
| frame index / reset | `gd.match().frame`, `on_match_start` | `needs_reset` at the first frame |

### Options

**(a) Emulate libmelee's world (Slippstream server + pipe reader).** Port side: write a Slippi event
encoder (Game Start payload, Pre/Post frame with the full post-frame layout, item events, frame
bookend, UBJSON handshake) as an ENet server (we already carry ENet for netplay), plus a named-pipe
reader for the `PRESS/SET` text; then fake or patch libmelee's `Console` (it also expects to launch
Dolphin, read its config, detect a Slippi version) and its menu helper. Latency about 1 frame.
Size **L**, and slippi-ai's menu logic and `melee.Console.run` assumptions would still need patching.
Benefit: unmodified agents, and replay/live-stream tooling for free. Not worth it now.

**(b) Thin adapter producing libmelee `GameState` objects.** A Python module builds
`melee.GameState/PlayerState` from our state and runs slippi-ai's `Parser` and
`send_controller`. Needs libmelee installed (LGPL, fine as a dependency). It buys nothing over (c)
because slippi-ai's agent API consumes `slippi_ai.types.Game`, not `GameState`. Size **M**.

**(c) Direct policy from a small Python process, no libmelee (recommended).** The process loads
the checkpoint via `slippi_ai.saving`/`eval_lib.build_delayed_agent` (VERIFIED these exist,
`eval_lib.py:440`), builds `Game` (a NamedTuple of numpy scalars, `types.py`) from our state,
calls `agent.step(game, needs_reset)` once per frame, decodes the controller and sends it back. This
mirrors `envs.Environment.current_state/step` (`envs.py:76-120`) and the closed-source sim adapter
(`sim_env/env.py`). Two transport variants:

- **c1 (S, zero C changes):** a Lua mod runs in the port: `on_frame()` appends a compact state
  record to a ring buffer; a console command (`= agent_pull(from_frame)`) returns the last N frames;
  another (`= agent_push({...})`) enqueues future pad samples that `on_frame_pre()` applies with
  `gd.input(port, spec, 1)`. Because the agent is delay-tolerant (about 20 frames of slack), the
  agent need not answer within one frame; it can poll every few frames. For reproducible tests,
  `pause` + `step k` gives lock-step: run k frames, pull k records, push k actions
  (INFERRED; the pieces are documented, the combination is untested). `MELEE_TURBO=1` needs
  `MELEE_PAD_SCRIPT`/`MELEE_LAB_BATCH`, which the carrier Lua script can satisfy, so lock-step
  turbo is plausible for fast tests. Console socket limits: one command per client per rendered
  frame, and Lua's 50 ms budget per call.
- **c2 (M, native):** a C-side per-frame agent socket (`MELEE_AGENT_PORT`) that writes a fixed binary
  state record at the frame boundary and blocks (with timeout) for one pad sample: true blocking
  input like Dolphin's `BlockingPipes`, microsecond-level latency, no 50 ms Lua cap. Needs
  changes in `gw_script.c`/`gw_script_pad.c`-adjacent code and a build+bridge fixpoint cycle.
  Worth doing only if c1's polling proves flaky.

Latency (INFERRED): loopback TCP is well under a millisecond; the binding constraints are
once-per-rendered-frame command intake (c1) and the model's per-step cost.

**Call-outs on mismatches that matter**

1. **Action ids and frame counts on ported/custom fighters.** The model embeds the action id only,
   no frame, so frame-count mismatches are invisible; but ids on m-ex/custom fighters (Sora,
   Meta Knight, Ultimate Kirby) are not Melee ids and `character` >= 33 is outside the one-hot.
   Action is clamped at 399 (CLAMP policy). The agent will still output a controller, but its
   timing logic is tuned to Melee's moves of that id. INFERRED.
2. **Custom stages, mazes, LAB.** No geometry input (VERIFIED), so unseen geometry cannot be reasoned
   about. LAB mode is a match like any other, but drills and savestates that rewrite state mid-match
   would look like teleports to a recurrent policy; call `needs_reset` after a load.
3. **Frame pacing.** The agent assumes exactly one step per game frame at 60 Hz with fixed delay.
   The port runs 60 Hz logic even when rendering is uncapped (`scripting.md:556-573`), good. Turbo
   or paused stepping is fine if the agent is stepped by frame count, not wall clock.
4. **Rollback/netplay.** Out of scope; `gd.input` is documented as local diagnostic input and not
   rollback state (`scripting.md:315`); turbo refuses netplay.
5. **Controller quantisation.** Our `gd.input` takes raw -127..127; slippi-ai's range is +-80. Use
   `raw = round((v-0.5)*160)`; check one dashback and one shield-drop to confirm the port's stick
   processing treats +-80 like hardware. Triggers: the model's L value 0..1 maps to 0..140 raw
   (`controller_lib.py`), pass that as `l` (our API takes 0..255).
6. **Sheik/Zelda & Ice Climbers.** libmelee special-cases both; our state has no Nana row, so IC
   would need a second subfighter read. Skip IC; use Fox/Falco/Marth/Sheik/Falcon/Puff.

## 5. What it would and would not be good for

**Good (INFERRED from design + checkpoint scope):**
- Being a real opponent on legal stages with vanilla characters: approach, spacing, combos,
  edge-guarding and recovery are exactly what imitation + RL on ranked replays covers. This is
  much better than "stand still / mash". At delay 21 the agent is beatable but sensible.
- Exercising a **ported character's moves** from the other side: Sora as the opponent of agent Fox is
  plausible (the agent sees an unfamiliar character id and clamped action ids), producing realistic
  pressure on Sora's hurtboxes, shield and recovery. The agent will not play Sora's own moves.
- Soak tests: long unattended Fox-vs-Fox or Fox-vs-X games on FD exercise physics, hitlag, items,
  stage transitions and crash paths much more than a script.
- Enemy fighters and bosses in missions: a deliverable only for Melee roster characters in
  arena-like stages. The mission design (`docs/PLAN-ENVOY-EDITOR-MISSIONS-2026-10-03.md`) would
  need difficulty knobs; the model has none besides delay and sampling temperature (INFERRED
  from agent options).

**Not good for:**
- **Traversing custom levels, mazes and vertical routes.** Out of distribution by construction:
  observations contain stage id and position only, no geometry or goal; the training objective is
  damage and stocks; there is no waypoint input (VERIFIED `types.py`, reward module). I found no
  evidence for or against generalisation to custom geometry (the sim env supports six legal stages
  only, `sim_env/env.py:42-53`), so the honest prior is "it will fight an empty room". Do not
  attempt.
- Driving menus: the agent never drives menus; libmelee's menu helper does, and our menus are
  ours. No.
- Pilot Sora or Meta Knight as themselves: no weights, no data (Section 2).
- Determinism: a sampled policy plus JAX nondeterminism means no exact repeatability unless seeded;
  a test must assert on outcomes with tolerances, not on exact frames.

**Traversal: own controller vs. reusing agent skills.** The agent is monolithic (an LSTM-transformer
over the whole state), not a library of skills; `techskill.py` is analysis, not control. There is no
interface to ask for "dash-dance to x" or "wavedash left", so its movement skills cannot sit under a
navigation layer without distillation. The better plan is the bot already in design: a small
closed-loop controller (waypoint in, stick/jump/dash out) written as state machines using our own
`gd.player` + `ecb` + floor queries, tuned on the actual action ids. Training a small traversal
policy in our engine is possible in principle (imitation from the controller's own demonstrations,
or RL) but the cap of **4 concurrent game instances** (memory rule) and the lack of a batched,
headless simulator make RL impractical; slippi-ai's own RL ran on thousands of sim lanes or a
fast-forward Dolphin farm. INFERRED; I did not measure our turbo throughput.

## 6. Cost and practicality on this machine

- Hardware (VERIFIED, `nvidia-smi`): **NVIDIA GeForce RTX 5070, 12,227 MiB**, driver 610.60, CUDA
  user mode 13.3. WSL2 (Debian 13, Python 3.13.5, 20 logical cores, 15 GB RAM visible) sees the GPU
  (`nvidia-smi -L` in WSL lists it; `/usr/lib/wsl/lib/libcuda.so` present). `venv` and `pip` exist in
  WSL. Windows Python is **3.11.9**, below slippi-ai's required 3.12 (VERIFIED `python --version`).
- Model cost (INFERRED from the verified parameter count): 23.9 M parameters, so roughly 50
  MFLOP per step. Pure compute is far below 1 ms even on CPU; the realistic floor is JAX dispatch
  and the autoregressive controller sampling (a dozen small sequential heads), probably 1 to 5 ms/step
  on CPU, below 1 ms on the GPU. I did not install JAX or time it; measure in stage 1. A 60 Hz budget
  is 16.7 ms, and the agent tolerates 20 frames of lag, so CPU inference is expected to be enough.
- Platform: JAX GPU wheels target Linux (`jax[cuda13]` extra in `setup.cfg`); Windows native is CPU
  only (INFERRED from JAX's published support; not verified here). So: **run the agent in WSL
  (GPU or CPU) in a venv inside the workspace, or on Windows with a separate Python >= 3.12 (CPU)**;
  the latter needs a Python install we have not done.
- Game <-> WSL link (INFERRED): the console socket binds 127.0.0.1 on Windows
  (`gw_script.c:8329-8345`), unreachable from WSL's default NAT network (WSL host gateway is
  172.21.48.1, seen via `ip route`; no `.wslconfig` is present, so mirrored networking is off). The
  reliable pattern: a stdlib-only relay on Windows (Python 3.11 is enough) connects to the game on
  127.0.0.1 and to the WSL agent through Windows-to-WSL localhost forwarding (on by default), or
  enable `networkingMode=mirrored` (a user-level change; not done).
- Memory/instance rules: agent adds no game instance; fits the cap of four melee-pc.

## 7. Staged recommendation

**Stage 0 (hours, no engine change): prove a pad round trip with a stand-in agent.**
Python relay + Lua mod (`on_frame` export ring, `agent_push` queue) with a scripted dummy policy
instead of the network; confirm that 120 frames of exported state arrive in order, that pushed inputs
land on the intended frame (`gd.pad` echo), under `pause`+`step` lock-step and at realtime.

**Stage 1 (the first experiment worth doing, 1-2 days):** Fox (agent, P1) vs a level-0 CPU Fox (P2),
Final Destination, in the LAB (never training mode), ACE disc, `MELEE_SLIPPI_CODES=online`,
`MELEE_VOLUME=3`, visible window.
- WSL venv under `_build/tmp/` (not system Python): `pip install -e ".[jax,tf]"` as in the
  README (or CPU-only JAX first), medium-v2 loaded with `eval_lib`'s loader, character `fox`.
- Agent process builds `Game` per frame from the field table, steps the delayed agent, pushes pad
  samples. Log-based pass criteria (no screenshots): agent exercised >= 15 distinct action ids
  including dash, jump, aerial attack and shield; dealt damage to P2 within 60 s; no `on_frame`
  budget errors; measured ms per agent step and queue depth recorded. Then hand GD a window to
  judge "does it play like a player" (memory: agents build, GD tests).
- Engine needs: nothing new if the field table above holds. Likely small Lua-only gaps to check:
  the stage id and character id tables, an `invulnerable` field mapping, `gd.items` kinds ->
  projectile types, and a `needs_reset` signal after savestate loads.

**Stage 2:** run the two-agent version (Fox vs Falco, both agents) for soak tests, then use it as the
opponent for Sora (id remapping experiment, log-only first). Decide c1 vs c2 from Stage 1 timing
evidence; build c2 only if polling jitters.

**Stage 3 (optional):** enemy-fighter hook for missions: a `gd.agent` kind so a mission can bind an
external agent process to an enemy port, with a difficulty ladder (delay override, temperature,
random input drop).

**Do NOT attempt:** (1) option (a), a full Slippstream/pipe emulation; (2) Phillip (obsolete,
GPL-3.0, TF 2.13, RAM-address based); (3) training slippi-ai from scratch (no data, days of GPU);
(4) using the agent for traversal/mazes/menus; (5) shipping or bundling the weights in a release;
(6) piloting Sora/MK as themselves with Fox weights and calling it parity; (7) playing the agent
online or on Slippi ranked (libmelee README: bots on Unranked will get accounts banned).

**Risks.** Licence: weights have no stated terms and the replay corpus is unpublished; Phillip is
GPL-3.0 and must stay out of our GPL-2.0 tree. No weights for our characters. Out-of-distribution
fighters/stages produce unpredictable but not crashing behaviour (INFERRED). Maintenance: slippi-ai
is moving fast (JAX pin `<=0.10.1` linked to an open JAX issue in `setup.cfg`; checkpoint "version 5"
format) so pin a commit; the author can change weights format. Our side: Lua budget 50 ms,
one console command per frame, and WSL/Windows networking friction. Training cost is zero if we
do not train.

## Credits

Everything below was read, run (restricted) or relied on while writing this note. We owe credit
to all of them; none of their code, weights or data is in our tree today.

| Project | Author / owner | Link | Licence | What we drew on |
|---|---|---|---|---|
| slippi-ai ("Phillip II") | Vlad Firoiu (vladfi1, "x_pilot") | https://github.com/vladfi1/slippi-ai | MIT, (c) 2020 Vlad Firoiu | architecture, observation/controller design, checkpoint structure, README claims |
| Phillip | Vlad Firoiu | https://github.com/vladfi1/phillip | GPL-3.0 | read only, to judge status |
| libmelee (maintained fork) | AltF4 and vladfi1 | https://github.com/vladfi1/libmelee | LGPL-3.0 (`pyproject.toml`) | Slippstream/pipe interface and field set |
| libmelee (original, archived) | AltF4 (Jordan Hemphill, per upstream) | https://github.com/altf4/libmelee | LGPL-3.0 (`LICENSE.txt`) | same, older version 0.41.1 |
| Project Slippi (Slippi Dolphin / Ishiiruka, slippi-ssbm-asm, replay format) | Fizzi and the Project Slippi team | https://github.com/project-slippi/Ishiiruka (GPL-2.0), https://github.com/project-slippi/slippi-ssbm-asm (GPL-3.0), https://slippi.gg | as listed | spectator protocol, replay format, gecko codes and replay corpus origin |
| ExiAI Slippi Ishiiruka / Dolphin forks | vladfi1 | https://github.com/vladfi1/slippi-Ishiiruka, https://github.com/vladfi1/dolphin | GPL-2.0 | headless/fast-forward build described by libmelee/slippi-ai |
| melee-sim-light (decomp-based simulator) | Enzyme (credited in slippi-ai README) | not public | unknown | only its adapter code in slippi-ai, as design template |
| "medium-v2" checkpoint and the models folder | Vlad Firoiu | Dropbox links in the slippi-ai README | **none stated** | 95.6 MB file inspected locally (structure, config, delay) |
| Replay dataset ("Dataset-3.18.0", anonymized ranked collections) | Fizzi / Project Slippi, and many players who shared replays | not published | none stated | not used; origin of the weights |
| pyenet-vladfi | vladfi1 (fork of pyenet) | https://github.com/vladfi1/pyenet | BSD-3-Clause | libmelee dependency |
| SmashBot | AltF4 | https://github.com/altf4/SmashBot | GPL-3.0 | only mentioned (prior note) |

Attribution each option would require of us if used:

- **Recommended (c1), using slippi-ai as an external, separately installed tool and the weights
  locally:** nothing is redistributed, so no licence obligation; still give credit by name in the
  test tool's README and our docs ("agent: slippi-ai by Vlad Firoiu, MIT; model medium-v2 by the same
  author, trained on Project Slippi replays"), link the repos, and tell the author before any public
  mention. If we ever vendor or copy slippi-ai code (even the `Game` field layout in a Python
  file), include the MIT copyright line and permission notice with it.
- **(b) with libmelee as a dependency:** list libmelee (LGPL-3.0, AltF4 and vladfi1) as a dependency
  with its licence text in the tool; do not modify and vendor it unless we publish the changes
  under LGPL-3.0.
- **(a) Slippstream/pipe emulation:** implementing a protocol compatible with Project Slippi's
  does not copy code, but we would be reading Slippi's GPL sources (Ishiiruka GPL-2.0,
  slippi-ssbm-asm GPL-3.0); follow our existing practice (reimplement, put an attribution comment
  naming the file and address, as in `_research/slippi-gameplay-codes.md`), credit Project Slippi, and
  keep any copied wire constants clearly attributed.
- **Phillip (not recommended):** GPL-3.0 code cannot be merged into our GPL-2.0 tree; if its weights
  or agents were ever used, credit Vlad Firoiu and the Phillip project and keep them out of
  releases.
- **Weights in any release or public repo:** do not, until the author grants written terms; if
  granted, ship the licence/permission text and credit the replay contributors as he specifies.
- **Replays:** we do not hold the dataset; if we ever record our own replays for training, credit and
  consent rules for those apply to us (no disc-derived data committed, per workspace rules).

## Open questions for the owner

1. Is local-only use of the downloaded weights acceptable, with no redistribution, until Vlad Firoiu
   states terms? May I (or you) ask him for explicit permission and for the list of released models?
2. Install a second Python (3.12+) on Windows, or keep the agent in WSL with a relay (needs no
   Windows install, optional `.wslconfig` mirrored networking)?
3. Which roster do you want agent opponents for first: vanilla fighters only, or also Sora/Meta Knight
   as the human-side target (remap experiment)?
4. Is the "traversal bot" to stay a hand-written controller (recommended), or do you want a separate
   learned traversal policy study (needs a batched headless mode we do not have)?
5. Mission enemies: acceptable to ship the agent only as a developer testing tool, not as a game
   feature, given the weight terms?

## Verification trail

- Clones: slippi-ai (HEAD 2026-09-23), phillip (2026-07-06), libmelee (altf4, 2026-01-25),
  libmelee-vladfi1 (2026-07-29), all `--depth 1` in `_build/tmp/slippi-ai-research/`.
- Checkpoint inspection: restricted unpickler, numpy only, other globals stubbed; parameter count
  23,887,032; `delay` 21; `axis_spacing` 32.
- Not done: no JAX/TF install, no timing, no run against the game, no libmelee install, no pipe test.

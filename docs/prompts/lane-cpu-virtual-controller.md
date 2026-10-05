# Lane packet: drive fighters through Melee's own CPU controller (2026-10-04)

For an engine lane that can build and run the game. One engine writer at a time. Read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/TERMINOLOGY.md`, `docs/scripting.md` (scripted input `gd.input`, `gd.cpu_mode`,
`gd.cpu_modes`, the idle-CPU default, `gd.wait_until`, the fly cursor), and the retail CPU code:
`melee/src/melee/ft/ftcmdscript.h` (the `CpuCmd_*` command set), `ft/ftcpuattack.c`, `ft/kinds/ftCommon/ftCo_0A01.c`
(the CPU's destination `fp->cpu.x54`, set near line 987), `ft/types.h` (the `fp->cpu` struct: lstick, cstick,
buttons, triggers), and `Fighter_procCpu` / where the CPU's virtual pad is consumed (`fighter.c` ~2211-2251).

## The owner's idea (verbatim, with their sketch)
"btw have we considered using fp->cpu.x54 and commmands like CpuCmd_LstickTowardDestination for testing to make things
easier rather than our input methods?"
Sketch: `CPUMoveTo(x, y)` -> a movement planner ("what inputs get me there fastest?") -> `fp->cpu.lstick / buttons /
triggers` -> the normal Melee engine. "fp->cpu.* = essentially a virtual GameCube controller"; `fp->cpu.x54` = the
vanilla CPU's destination; `Fighter_procCpu()` = the place to hook a planner; `mpIsland` = the existing representation
of floors and platforms; later, a short-horizon beam search / model-predictive planner ("an automated mini-TAS
generator"), "Start with MPC + beam search + Melee's existing platform topology + virtual controller injection."

## Why it matters here
Today tests drive fighters by injecting pad state (`gd.input`), which only works on a human-controlled slot ("scripted
input does not drive a CPU slot"), needs per-frame holds, and knows nothing about where the fighter is. Opponents in
tests are therefore either idle or the retail AI. And CPU opponents cannot perform technique (L-cancel, wavedash,
cancels), which the loot layer is about to reward. Melee already has a deterministic virtual controller per fighter
and a small command language for it, inside the simulation.

## Build, in phases; each ends built, suite green, and demonstrated in the game
**Phase 1: the virtual controller and the retail command language, exposed.**
- A third CPU mode beside the existing stand/fight: `script`. In it the retail AI does not write `fp->cpu.*`; a script
  does, at the same point in the frame (reuse the hook the idle-CPU work added: the place neutral input is written).
- `gd.cpu_pad(port, {x=,y=,cx=,cy=,l=,r=,buttons=...} [, frames])`: set the virtual pad directly (works on CPU slots,
  sub-fighters, and 1P opponents).
- `gd.cpu_script(port, {...})`: run a sequence of the retail commands by name (press/release, `set_lstick_x`,
  `wait`, `lstick_toward_destination`, `lstick_x_toward_destination`, `lstick_toward_fighter`, `wait_if_motion`, the
  clamped variants: map every `CpuCmd_*` that exists, document the unknown ones as unknown), executed by the retail
  interpreter so timing is the game's own; `gd.cpu_dest(port, x, y)` sets `fp->cpu.x54`; status and completion
  readable (`gd.cpu_script_done`), and `gd.wait_until` can wait on it.
- All of it inside the simulation: deterministic, covered by the LAB snapshot and rewind (prove 0 differing bytes with
  a script running), and usable under rollback in principle (state what would be needed for netplay: it is the same
  state the retail CPU already keeps).
- A small library of technique macros as command sequences, tuned per fighter from the fighter's own attributes (jump
  squat frames, air-dodge landing lag): short hop, full hop, dash, dash dance, wavedash, waveland, L-cancelled aerial,
  shield, perfect-shield attempt at a given frame, tech in a direction, jump-cancel grab. Each verified in the game by
  the skill/contact events where they exist.
**Phase 2: `gd.cpu_goto(port, x, y [, opts])` without search.** A rule-based mover over the stage's floor and platform
topology (`mpIsland`, the collision lines, ledges): walk or dash on the same floor, jump to a platform within the
fighter's measured jump reach, drop through, recover to the ledge; reports arrived / blocked / fell. Good enough to
position fighters in tests ("stand at the left edge of the top platform") and replace most uses of teleport-then-wait.
**Phase 3: the planner the owner sketched.** A short-horizon search over inputs (beam search / model-predictive: plan
30-60 frames, execute a few, re-plan) to reach a destination fast, including wavedashes and platform movement. Decide
and justify the forward model: the real simulation through the snapshot engine (exact, expensive: measure frames per
second of look-ahead available offline) versus a light kinematic model from the fighter's attributes with periodic
correction. Offline first. Report achievable speed and where it fails.
Tests in the suite pattern for phases 1 and 2; a catalogue demo ("cpu controller": a CPU Fox wavedashes across the
stage, L-cancels an aerial, and walks to a marked spot); docs. Update the lane-brief boilerplate in
`tools/port/README.md`: how a test positions and drives an opponent with these calls.
Report: file:line, the command table, the technique macros and their per-fighter timing source, the snapshot proof,
what phase you reached, and what the loot layer gains (CPU opponents that can earn technique-triggered statuses).

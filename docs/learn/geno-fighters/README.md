# Learn to make Geno fighters

A short course for people. It teaches you to change and extend a fighter in GD's Melee with
**Geno**, the port's own layer for fighter content, and to see every change in the LAB.

Written 2026-10-03 against the game source as it stands that day. Where this course and
`melee/docs/geno.md` disagree, the reference wins for facts and this course should be corrected.
Every packet ends with a Sources list so you can check a claim yourself.

## Who this is for

- You have modded Melee a little (a texture or a costume), or you are a programmer who is new
  to Melee modding.
- You want a new or changed fighter in this port, and you have not read the engine.
- You can edit a text file and run a command in a terminal. You do not need to write C or PowerPC.

## The short answer to "does Geno replace m-ex?"

Version 6 adds an offline native-definition path for the Geno engine; see [packet 11](11-defined-fighter.md). Packet [13](13-fighter-lua.md) (a stub, 2026-10-07) writes a move as a Lua callback with typed per-fighter state. Its game acceptance is still pending. The earlier attachment course below describes the tested path. m-ex gives a fighter a place in the game: a slot, its files, costumes, an icon on the character
select. Geno changes how a fighter plays: new action states, script logic, values, hooks, projectiles
and effects. Geno sits on top of m-ex and never edits it. Packet 0 gives the full answer, with a
table.

## What you need

| you need | why |
|---|---|
| A Windows PC and a legally obtained Melee NTSC 1.02 disc image of your own | the game runs only with your own disc. No disc data is in this repository or in this course |
| The game, either a release build or one you build from source (`SETUP.md`, `tools/port/README.md`) | to run the LAB. A release build ships the LAB mod |
| A text editor | `geno.json` and move scripts are plain text |
| Python 3 | to compute move-script words (packet 3) and run the frame-data diff (packet 7) |
| Optional: an ACE or Akaneia disc | needed only for packets that add a new fighter slot (packet 2 explains why) |

You will not see a game window in this course until packet 1. Packet 0 is reading.

## The course

| packet | title | you finish with | time | state |
|---|---|---|---|---|
| [0](00-what-m-ex-and-geno-are.md) | What m-ex and Geno are | the answer to "can Geno do what m-ex does", and a map of what you can and cannot make | 30 min | complete |
| [1](01-first-success.md) | Run a Geno fighter in the LAB | a Geno mod you wrote yourself, a changed number, seen in the LAB after a hot reload | 45 min | complete |
| [2](02-anatomy-of-a-fighter.md) | Anatomy of a fighter | a labelled map of one fighter's files, states and animations, read from the LAB | 45 min | complete |
| [3](03-your-first-new-move.md) | Your first new move | a new move on a button, with your own hitbox, tested frame by frame | 90 min | complete |
| [4](04-physics-and-feel.md) | Physics and feel | notes and a worked example outline | 60 min | outline |
| [5](05-projectiles-and-effects.md) | Projectiles and effects | an article definition outline | 60 min | outline |
| [6](06-attributes-animations-model.md) | Attributes, animations and the model | what is data you can edit, and what needs tools | 45 min | outline |
| [7](07-testing-and-debugging.md) | Testing and debugging | a checklist for the LAB tools, the frame-data diff and the log | 45 min | outline, with verified log lines |
| [8](08-packaging-and-sharing.md) | Packaging and sharing | a mod folder you can give to someone | 30 min | outline |
| [9](09-going-further.md) | Going further | pointers to the Ultimate-to-Melee pipeline and the fidelity rule | 30 min | outline |
| [10](10-known-gaps.md) | Known gaps | what is unverified, contradictory or missing | 15 min | complete |

"Complete" means every step is taken from the real code and documents and has a Sources list. It
does not mean the author ran the game: the course was written from the code. On 2026-10-03 a tester
then did packets 0 to 3 in the game, step by step, through the console, and the text was corrected
(each packet's status line says what was and was not checked; packets 4 to 9 were not run). What no
one has checked is anything that needs a person at the screen: key presses, how the LAB's panels
look. Packet 10 collects what is open. If a step fails for you, that is useful: please report which
packet and step.

## Glossary

Read this once, and come back when a word trips you.

**m-ex.** A community mod framework for Melee that lets a disc add fighters, stages, items and music
by editing data tables. This port reads m-ex data and runs it. Its tables live in one file,
`MxDt.dat`.

**Geno.** This port's own layer for fighter content. It is opt-in per fighter through a file called
`geno.json`. A fighter with no `geno.json` behaves exactly as before.

**Fighter kind.** The engine's number for a fighter. Retail fighters have fixed kinds. Added m-ex
fighters take the next free slot, so their number depends on which mods are enabled. Geno finds a
fighter by its file name (`PlKb.dat`) or a vanilla name (`kirby`), not by number.

**Clone base.** The existing fighter an added m-ex fighter copies its code from. A fighter whose
table row gives no code of its own runs its clone base's moves. Geno then changes what differs.

**Action state** (the engine also says **motion state**, **motion id**). One thing a fighter can be
doing: standing, a jab, a jump, a special move. The engine numbers them. Each has a row naming its
animation and the small functions that run it every frame.

**Subaction.** A row in the fighter's data file holding one animation and the script that goes with
it. An action state plays one subaction. The LAB shows the subaction number as `anim_id`, and
`geno.json` calls the same number `subaction`.

**ftcmd script** (a subaction's script). A list of 32-bit commands: wait N frames, make a hitbox,
play a sound, make an effect, mark the move as cancellable. Melee uses opcodes 0 to 58. Geno adds
opcode 59, an escape with sub-commands for variables, if/else and more.

**Hitbox.** A sphere that hurts. A move creates up to four at a time. **Hurtbox:** a capsule on the
body that can be hurt. **ECB** (environmental collision box): the diamond the fighter uses to touch
floors, walls and ledges.

**IASA** (interruptible as soon as). The frame from which a move can be cancelled into something
else. In a script it is a flag that turns on.

**KBG, BKB, WBK.** A hitbox's knockback numbers: growth (scales with the victim's damage), base
(always there) and weight-based, also called fixed knockback.

**Article.** A projectile or other thing a fighter throws. In Geno an article is a Melee item.

**Hook.** A named native function Geno can run. A script runs one with the escape's `CALL`
sub-command, and `geno.json` can bind a hook to a moment such as "every frame" or "on landing".

**Dispatch point.** One of those moments: `on_init`, `on_frame`, `on_action`, `on_land`, `on_hit`.

**Profile.** One fighter's entry in `geno.json`.

**Overlay.** A profile that attaches to an existing fighter and changes it. The only kind Geno
supports today. `define`, a brand-new fighter made by Geno alone, is reserved and skipped.

**LA and RA variables.** Script variables. LA (long-term) survive across action states. RA
(per-action) are cleared on each action change. Each is an int bank and a float bank.

**LAB.** The in-game mode for studying a fighter: hitboxes, frame stepping, rewind, a move browser
and more. Reached from SOLO > LAB.

**Rollback and determinism.** Online play re-runs recent frames. Anything Geno keeps must be game
state and must come out identical every time. That is why Geno has no host time or random numbers
of its own and why its variables are saved with savestates.

**Shim boundary.** The port compiles the game's C for PowerPC and retargets it, while the shims are
native code. A fighter author who writes only `geno.json`, scripts and data never meets this. It
matters only if you add a new native behaviour: game-side code calls the unprefixed name, and
scalars cross the boundary, never pointers. `melee/CLAUDE.md` has the rule.

## Rules this course follows

- Facts come from the code and the reference. If a command, field or key could not be found in the
  tree, it is not written here, and the packet says what is missing.
- No game data is shown. Numbers you read from the LAB stay on your machine. Never commit or share
  disc-derived files.
- Credit your sources (packet 8).

## Sources

- `melee/docs/geno.md` sections 1 to 3, 7, 14; `docs/mods-packaging.md`; `CREDITS.md`.
- `CLAUDE.md`, `melee/CLAUDE.md` (the shim boundary), `melee/pc/geno/CLAUDE.md` (the two halves).
- `README.md`, section "The Geno engine"; `SETUP.md`.

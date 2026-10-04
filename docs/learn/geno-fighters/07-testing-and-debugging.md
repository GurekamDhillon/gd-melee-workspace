# Packet 7: Testing and debugging (outline)

**Status: outline, with verified log lines and commands.** Nothing here was run by the author.

**Goal:** know which LAB tool answers which question, how to measure a move, and how to read the log
when a mod does nothing.

**Prerequisites:** packets 1 and 3.

## Which tool answers which question

| question | tool | where |
|---|---|---|
| Did Geno load my file? | the log: search `geno:` | `melee/pc/platform/geno_registry.c` |
| What state is the fighter in, and what animation? | `gd.player(1).motion_name`, `anim_id`, `anim_name`; INSPECT (`5`) info panel `I` | `melee/docs/geno.md` 14.3, 14.9 |
| Where are the hitboxes, hurtboxes and ECB? | HITBOXES (`2`): `B` boxes, `L` labels, `E` ECB, `D` data panel | 14.9 |
| When does a hitbox open and close? | FRAMES (`3`) timeline; `lab events [port]` | 14.7, 14.9 |
| What are a move's exact numbers, measured as it runs? | `lab card`, the move card (TRAINING `M`) | 14.12 |
| Frame data for every state | frame-data export (TOOLS, `lab export`), then diff | 14.11 |
| What changed between two versions of my files? | `lab fdiff`, or `python melee/pc/geno/tools/framedata_diff.py <A> <B>` | 14.11 |
| Where does a hit send the victim? | LAUNCH (`7`): knockback preview, DI, hitstun | 14.11 |
| Does my change make A and B differ over the same inputs? | A/B (`8`): `R` records A, `B` reloads and re-runs | 14.11 |
| Step forward and back | Space, Right, Left; the long rewind; `F5` / `F6` save and load a state | 14.9, 14.10 |
| Reload `geno.json` and replay the last seconds | `F8`, STATES > Hot reload | 14.10 |
| Does it survive rollback? | rollback visualiser (FRAMES `N`) and SyncTest | 14.11, 4 |

TRAINING (`9`) adds frame advantage, an input display and technique feedback (14.12). The LAB is
offline only.

## Measure a move

The export runs every common `Attack*` state, the eight input specials and every Geno state from a
neutral state, and writes startup, active windows, total length, IASA, landing lag, autocancel and
per-hitbox damage, angle, KBG, BKB, WBK, radius and bone (14.11).

Headless:

```
MELEE_SCENE="mode=lab;p1=kirby;stage=fd" MELEE_LAB_BATCH=v1 MELEE_LAB_BATCH_QUIT=1
```

(`MELEE_LAB_BATCH_PORT` picks the port and `MELEE_LAB_BATCH_VERBOSE` logs each state.) Run the
fighter alone: an opponent in range is hit and hitlag stretches the numbers (14.11). Output goes
to `scripts-data/geno-lab_lab/framedata/<fighter>/<version>/` as `moves.csv`, `hitboxes.csv` and
`framedata.json`. Change a number, export again under a new version, and run the diff. Its exit
status is 0 for no differences, 1 for differences, 2 for bad arguments (the tool's docstring).

**Caveat from the reference (14.12):** the static reading of a script (the FRAMES timeline, the move
browser, the export's autocancel and `total_script` fields) may be one frame high. The measured
numbers (`lab card`, the export's startup and active) agree with each other and with known Fox
values on the ACE disc, per the reference's table.

## Reading the log

The path is `melee-pc.log` in the run's folder (for a sandboxed run, `_build/runs/<name>/`,
`CLAUDE.md` fact 3). **Read the log of a failing run before deciding what failed**: the harness
under-reports. Lines that begin `geno:` come from Geno. These are the ones in the source, and
what they mean for an author:

| line (shape) | meaning and fix |
|---|---|
| `geno: <path> is not valid JSON (<why> near "...") - ignored` | a syntax error: the whole file is skipped |
| `geno: <path> has no "geno": <version> - ignored` | add the version field |
| `geno: <path> is Geno v<N>, this build is v<M> - reading what it knows` | the file is newer than the build: later keys are ignored |
| `geno: ... attach "<x>" names no fighter I know (use a vanilla name or a Pl*.dat)` | wrong `attach` |
| `geno: <mod>/<fighter> attaches to <file>, which this install does not have - inactive` | the m-ex fighter it attaches to is not mounted |
| `geno: ... entry has no "attach" - skipped` | `define` is not supported: `... "define" (new fighters) is not supported by Geno v<N> yet - entry skipped` |
| `geno: ... attribute "<name>" ... - ignored` | unknown or invalid attribute |
| `geno: ... <name> is not a parameter Geno knows - ignored` | a behaviour parameter typo |
| `geno: ... state <name>: behavior "<x>" is unknown` | typo in `behavior` |
| `geno: ... state <name>: bad "like"` / `bad "next"` / `bad "land"` | a target string that does not parse |
| `geno: ... <name> callback "<x>" is unknown - the behavior's is used` | a callback name typo, with a safe fallback |
| `geno: ... cannot open script file <path>` | the word file is missing |
| `geno: ... <file>: bad word "<text>" (or the script pool is full)` | a non-numeric word, or too many overlay words |
| `geno: ... a subactions entry needs "index" 0-1023 - ignored` | bad overlay index |
| `geno: ... too many subaction overlays - the rest are ignored` | past the overlay limit |
| `geno: ... more than 48 states - the rest are ignored` | `GENO_MAX_STATES` is 48 (`geno.h`) |
| `geno: ... more than 16 articles - the rest are ignored` | the article limit |
| `geno: ... article <name>: model file <f> not found (in a mod or on the disc)` | the article's model path |
| `geno: hot reload: layout changed (<why>)` | the LAB restarts the match |

The registry also logs `geno: fighter <name> (<Pl file>) -> kind <k>: id <hash>, ...` and
`geno: <n> geno.json file(s), <m> fighter entr(y/ies)` when it loads. A script that names a Geno
target the profile does not declare is skipped and logged, and a later matching check still fires
(15.3, 16.1). Geno's logs are rate-limited, because re-simulated frames would repeat them (section 4).

## Off the game

- `melee/pc/geno/tools/lab_stage_d_check.lua` runs the LAB's logic against a stub with any Lua 5.4.
  It checks the LAB, not your fighter.
- `luac -p <file>.lua` syntax-checks Lua scripts.
- `python melee/pc/geno/tools/scan_ftcmd_opcodes.py` counts the opcodes in a disc's scripts (the
  census that shows opcode 59 is unused by shipped fighters).
- The headless suite: `bash tools/port/run.sh --test <name> --iso <disc>`. Geno's tests are named
  `geno_*` in `melee/pc/geno/geno_tests.c`. This tests the engine, not your mod.

## Not available

- A **validator** for `geno.json` or a word file. The only checks are the engine's log lines.
- A **disassembler for your own overlay** other than the LAB's `lab events` and `gd.timeline`.
- Any guide to the per-state **diagnostic events** (`geno: ... event N` lines) beyond the numbers in
  the reference. The event numbers are listed in the sections that introduce each feature.

## Check yourself (for the full packet)

- A mod that does nothing and logs nothing: what are the three first things to check?
- Why do you run a fighter alone for the frame-data export?
- Which of the LAB's numbers might be one frame high?

## Sources

- `melee/docs/geno.md`: 4, 14.3, 14.7 to 14.12, 15.3, 16.1.
- `melee/pc/platform/geno_registry.c` (the `geno:` log formats), `melee/pc/geno/geno.h`
  (`GENO_MAX_STATES`).
- `melee/pc/geno/tools/framedata_diff.py`, `lab_stage_d_check.lua`, `scan_ftcmd_opcodes.py`.
- `melee/pc/geno/CLAUDE.md`; `CLAUDE.md` (facts 1 and 3); `tools/port/README.md`.

# Packet 1: Run a Geno fighter in the LAB

**Goal:** write the smallest possible Geno mod, load it, change one number, hot reload, and see the
change in the LAB.

**You will have at the end:** a mod folder called `tutorial-kirby` that you wrote, a log line proving
Geno loaded it, and a changed jump or fall you watched in the LAB.

**Prerequisites:** packet 0. The game running with your own Melee disc image, and the LAB mod
installed (step 1). Time: about 45 minutes.

**Status:** run in the game by a tester on 2026-10-03 (a source build, the vanilla disc, a
sandboxed run, driven through the console). Steps 2 to 7 worked as written except where this text
now says otherwise; the corrections are folded in. Not checked by a person at the screen: the `F8`
and `F5` keys, the `6` and `T` keys in step 7, and how anything looks on screen. The console and Lua
equivalents were used instead and are named below. A release build's folder layout was not checked.
Packet 10 lists what is still open.

## Why a number and not a hitbox

You may expect "change a move's damage" here. That cannot be done by editing the move in place,
because a move's original script is inside the fighter's data file, which is disc data. A Geno
overlay can put commands in front of the original script, or replace it whole, but it cannot edit a
number inside it (`melee/docs/geno.md` section 15.5: the `ORIG` sub-command "continues with the
original script from its start"). So the smallest honest first change is a fighter attribute.
Packet 3 writes a whole move script and changes its damage.

## Step 1: have the game and the LAB

Either way you need your own legally obtained Melee NTSC 1.02 disc image (the README's Download
section says the same; mod discs also work).

- **A release build.** The release package includes the LAB mod (`tools/release/build_release.ps1`
  copies `mods/geno-lab` into it). Unzip it and put your disc in as the README says.
- **From source.** Follow `SETUP.md`, then build with `bash tools/port/build.sh`. A sandboxed run
  looks for mods in `_build/mods` (`docs/mods-packaging.md` section 2.1). Copy the folder
  `melee/pc/geno/mods/geno-lab` into that `mods` folder.

Mods mount **at boot**: the game scans its mods folder when it starts. A mod you add later needs a
restart (hot reload in step 5 re-reads files of mods already mounted).

**Starting a source build with your own mods folder.** Point the game at the folder with
`MELEE_MODS_DIR` (a full path; the default `_build/mods` is empty) and skip the menus with
`MELEE_SCENE`. From the repository root, in Git Bash, with your disc path set in `.env`
(`GW_ISO_VANILLA`):

```
set -a && . ./.env && set +a
export MELEE_MODS_DIR="$(pwd -W)/my-mods"   # the folder that holds geno-lab and tutorial-kirby
export MELEE_CONSOLE_PORT=51821             # lets you drive the game from a second terminal
export MELEE_SCENE="mode=lab;p1=kirby;p2=fox/cpu0;stage=fd"
bash tools/port/run.sh --realtime my-first-run --iso "$GW_ISO_VANILLA"
```

Each run needs a new sandbox name (`my-first-run`, then `my-second-run`). The log is
`_build/runs/<name>/melee-pc.log`. From a second terminal,
`python melee/pc/scripts/console.py 51821 "= gd.attrs(1).gravity"` runs a console line in the
running game; typing the same line after pressing the backtick key in the game window does the
same. The checks below were made this way.

## Step 2: write the mod

Make a folder called `tutorial-kirby` inside the mods folder. The folder name is the mod's id
(`docs/mods-packaging.md` section 4). Put two files in it.

`mod.json`:

```json
{
  "id": "tutorial-kirby",
  "name": "Tutorial Kirby",
  "version": "0.1.0",
  "kind": "fighter",
  "description": "Packet 1 of the Geno course: a Geno overlay on Kirby.",
  "requires": [],
  "conflicts": []
}
```

`geno.json`, beside `mod.json`:

```json
{
  "geno": 5,
  "fighters": [
    {
      "attach": "kirby",
      "name": "Kirby (tutorial)",
      "jumps": { "max": 9 }
    }
  ]
}
```

What each part does (`melee/docs/geno.md` section 7):

| key | meaning |
|---|---|
| `"geno": 5` | the file format version. This build reads up to 5. A higher number loads what it knows and logs a warning |
| `"attach": "kirby"` | the existing fighter to change: a vanilla name (`kirby`, `marth`, `gnw`...) or a data file name (`PlKb.dat`) |
| `"name"` | shown in logs only |
| `"jumps": {"max": 9}` | nine jumps in total (the ground jump counts as one) |

In step 5 you will add `"attributes"`: any of the 40 fighter attributes by name, applied each time
the fighter spawns, before the game's own modifiers.

Do not copy `files/` folders or disc files into this mod. It needs none. This is an **overlay**: it
changes the Kirby the game already has, on this install. It is not a new fighter (packet 2 explains
the difference).

## Step 3: start the game and check the log

1. Start the game. Open **SOLO > LAB**. The LAB appears only when the `geno-lab` mod is mounted.
2. Pick Kirby for player 1, anything for player 2, any stage. (To skip the menus you can launch with
   `MELEE_SCENE="mode=lab;p1=kirby;p2=fox/cpu0;stage=fd"`, the scene grammar in `melee/docs/geno.md`
   section 14.8.)
3. Open the game's log (a sandboxed run keeps it as `melee-pc.log` in its run folder, `CLAUDE.md`
   fact 3; the release launcher opens logs for you). Search for `geno:`.

First the mount lines list both mods (`gw: mods:   tutorial-kirby           fighter 0.1.0    on`).
Then, seen in a real run, two `geno:` lines (the count line comes first):

```
geno: 1 geno.json file(s), 1 fighter entry
geno: fighter Kirby (tutorial) (PlKb.dat) -> kind 4: id <16 hex digits>, 0 attribute(s), max jumps 9, 0 air vy, hooks 0/0/0/0, 0 special attribute(s), 0 on_land, 0 subaction overlay(s), 0 Geno state(s), 0 behaviour parameter(s), 0 article(s), 0 on_hit hook(s)
```

Once a match starts, `geno: kind 4 player 0 attributes overridden: 0 field(s), max_jumps 9` follows.
The LAB also writes `geno: kind 4 player 0 on_hit: ...` lines whenever anything hits player 1;
ignore them. The fighter line is the proof the mod loaded.

In a LAB match started with `p2=fox/cpu0`, player 2 walks over and attacks Kirby: a level 0 CPU is
not a standing dummy. Type `= gd.cpu_mode(2,"stand")` in the console to make it stand still.
If you see `geno: ... is not valid JSON ... - ignored`, you have a typo (a missing comma is the
usual one). If you see `attach "..." names no fighter I know`, the `attach` name is wrong. If you
see nothing with `geno:`, the mod did not mount: check the folder name, `mod.json`, and
`enabled.txt` (if the mods folder has one, your id must be listed, `docs/mods-packaging.md`
section 4).

## Step 4: read a number from the game

The LAB is a match that never ends, so there is time to look.

1. Open the console with the backtick key (the one left of `1`; `docs/scripting.md`, Quick start).
2. Type `= gd.attrs(1).gravity` and press Enter. This prints player 1's current gravity.
   `gd.attrs(port)` returns all 40 named attribute fields (`melee/docs/geno.md` section 14.3).

Write the number down. It is Kirby's gravity on your install, straight from your disc, which is why
this course does not print it. Notice how small the numbers are. (The console answers with the bare
number, for example `0.08`. It is the number you double in step 5.)

## Step 5: see it, then change it

1. In the LAB, jump with Kirby and watch how fast he falls. Press `F5` to save a state first, so
   you can come back to the same spot (the keys are in `melee/docs/geno.md` section 14.9).
   To put a number on the fall without watching, jump and read `= gd.player(1).y` every frame
   (`= gd.pause()`, then `step 1` and the read, repeated). At the disc's gravity Kirby's full hop
   peaked at about 14.8 units and he landed 46 frames after the jump started.
2. Edit `geno.json`: add an `"attributes"` line to Kirby's entry, with `gravity` at about twice the
   number you wrote down, and save the file. For example, if you read `0.064`:

   ```json
   "attributes": { "gravity": 0.128 },
   "jumps": { "max": 9 }
   ```

   (`0.064` is only an illustration of the shape. Use twice your own number. Adding a profile key
   changes the profile, not the list of profiles, so the hot reload accepts it.)
3. Press `F8` (hot reload). The LAB rewinds about two seconds, re-reads every mounting mod's
   `geno.json`, re-applies the data to the live fighters, and replays your inputs on the new data
   (`melee/docs/geno.md` section 14.10). From the console the same reload is `lab reload`; it
   replays nothing unless you give it seconds (`lab reload 2`).
4. Jump again. Kirby falls faster. Check the number: `= gd.attrs(1).gravity`. The reload is applied
   a moment after the command returns, so a check typed in the same instant can still show the old
   number; wait a second and ask again.

The log shows what the reload did. Seen in a real run:

```
geno: hot reload: 1 profile(s) changed, overlay words unchanged
hot reload: geno.json: 1 entry changed, overlay words unchanged; 1 fighter(s) re-applied; Lab script reloaded; replaying 0.0 s
geno: kind 4 player 0 attributes overridden: 1 field(s), max_jumps 9
```

Measured with gravity doubled: the same full hop peaked at about 7.8 units and landed after 27
frames (before: 14.8 and 46), with no restart.

What reloads cleanly: attributes, jumps, special attributes, hooks, `on_land`, change-action checks,
Geno state rows and overlay words. What does not: a change to which fighters have profiles, what a
profile attaches to, the number of states, or the list of overlays. Those change the layout, so the
LAB restarts the match instead. File data (the model, animations) needs a new match. `on_init`
hooks do not run again. A `geno.json` that does not parse keeps the old data and says so.

## Step 6: change the jumps and see the log line

1. Set `"jumps": { "max": 9 }` to `{ "max": 9, "air_vy": [1.8, 1.55, 1.35, 1.2, 1.1] }`. These are
   the reference's own example impulses (`melee/docs/geno.md` section 7). If you kept the doubled
   gravity from step 5, take it out first: with it Kirby lands before a second air jump.
2. Press `F8`, then jump repeatedly in the air, about half a second apart (Kirby's air-jump
   animation does not accept the next jump sooner). The log shows a line per air jump:

```
geno: kind 4 player 0 air jump 1 of 8
geno: kind 4 player 0 air jump 2 of 8
```

What the tester saw: the impulses change (the first air jump rose faster, the fifth slower), and
Kirby chained **five** air jumps. A sixth air jump never happened although the log said max jumps 9,
and the line the reference promises for jumps past Melee's table
(`... (beyond Melee's multi-jump table)`, section 10) never appeared. So on Kirby `jumps.max`
above 6 does not give extra jumps in this build. That is open (packet 10); the `air_vy` change
itself works.

## Step 7: look at one move's script

You cannot edit it yet, but you should see one.

1. Press `6` for the MOVES mode (`melee/docs/geno.md` section 14.11). It lists every action state
   Kirby has. (Console: `lab moves Attack11` lists matching states with their motion id.)
2. Pick **Attack11** (the first jab, named as in the decompilation's motion list) with the up and
   down keys and press Enter. It plays from neutral. (Console: `lab play Attack11`.)
3. Press `T`. The timeline follows along the bottom: hitbox windows are coloured by hitbox id, and
   the right panel lists each window as `fN-M #id dmg% angle kbg bkb wbk radius`.
4. In the console, `lab events` prints the same script decoded, command by command, for the move
   that just played. Seen for the jab (shortened):

```
Attack11 (Attack11) 9 events, length 17, end
  f1   continuation
  f4   hitbox #0 b43 3% a361 g50 b8 w0 r3.12 normal
  f6   hitboxes_clear
  f17  iasa
```

A hitbox line reads `#id bBONE damage% aANGLE gGROWTH bBASE wWEIGHT rRADIUS element`: the first `b`
is the bone (joint) number, the second is base knockback. Write the bone number down; packet 3
needs it. It is not 2.

You have just read the ftcmd script of a move. In packet 3 you will write one.

## Check yourself

- Is there a `geno:` line for your fighter in the log, and does it say max jumps 9?
- Did `= gd.attrs(1).gravity` change after the hot reload?
- Did the log say `hot reload: 1 profile(s) changed`?
- Did the full hop get shorter when gravity doubled?
- Can you say why a hitbox's damage could not be changed here?

## Common mistakes

- **Editing the wrong copy.** A running game reads the mods folder it was started with. A sandboxed
  run copies the exe, not the mods, but check the log's mount line (`gw: mods: <folder> - 2 mod(s)`)
  to see which folder was used.
- **Forgetting the restart** after adding the mod for the first time.
- **A trailing comma** in the JSON. The reader is strict and ignores the whole file.
- **Expecting `F8` to do everything.** Layout changes restart the match; model and animation changes
  need a new match.
- **Using a wrong attribute name.** An unknown name is logged as ignored: `attribute "<name>" ... -
  ignored`. Use the names `gd.attrs(1)` prints.
- **Expecting a new fighter.** This changes Kirby on your install. Other fighters stay as they were.

## Sources

- `melee/docs/geno.md`: section 7 (geno.json), 10 (multi-jump and its log line), 14.3 (`gd.attrs`),
  14.8 (`MELEE_SCENE`), 14.9 (keys), 14.10 (hot reload), 14.11 (MOVES mode), 15.5 (`ORIG`).
- `melee/pc/platform/geno_registry.c`: the `geno:` log formats (lines about 1215 to 1300 and 1755 to 1765).
- `docs/mods-packaging.md` sections 2.1 and 4 (where mods are looked for, `mod.json`, `enabled.txt`).
- `docs/scripting.md`, Quick start (the console, `= expression`).
- `tools/release/build_release.ps1` (the release ships `mods/geno-lab`); `README.md` (Download).
- `ports/kirby-ultimate/README.md` (a real overlay on Kirby that uses the same keys).

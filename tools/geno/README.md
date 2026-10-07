# Geno author tools

The Geno engine's native-definition tools (format 6, widened to 7 in slice 2 and to 8 in slice 3) generate and check a source-only Mario-reference fighter. This path is offline only.

Slice 5 (2026-10-07): `check` knows the `lua` block of a define and the `lua` key of its states (the file named by `script`, the functions each state names, `ctx.go("State")` counting as a reference to that state, `state.<name>` spellings against the declared slots). The sandbox itself is native: `tools/port/build.sh --native-test geno-lua`.

Slice 2 additions: `python -m tools.geno.report <folder> [--frames]` prints which of the 351 motion rows are `own`, `inherited` or `donor-special (unreachable)`, the eight special entries (bound state or `DONOR`) and, with `--frames`, hitbox start/end, damage, angle, size and IASA per overlay (readout convention: hitbox live from action frame N-2); `check` now also errors on a motion out of 0..350, a subaction out of 0..302, an IASA script with callback none, an unreachable state and a mistyped tag, and warns on a special bound to the donor; `new --template striker-skeleton` emits the Striker's header and empty move stubs; a `moves` block in `geno.json` expands at export to the overlay and the `common_states` row. Slice 3 (geno 8): `check` accepts a define's `articles` and `sounds` table, errors on an article naming a sound that is not in `sounds` (no donor fallback), a duplicate name or an id outside 1..999999; `report` lists the resources (sounds, articles, effect, spawn and end sounds). Fixtures: `melee/pc/geno/mods/vanilla-hero`, `vanilla-striker` and `vanilla-caster` (a projectile special); lesson `docs/learn/geno-fighters/11-defined-fighter.md`.

```text
python -m tools.geno.new vanilla-hero --name "Vanilla Hero" --base mario --output mods/vanilla-hero
python -m tools.geno.check mods/vanilla-hero
python -m tools.geno.export --package mods/vanilla-hero --out packages/vanilla-hero
python -m unittest tools.geno.test_define tools.geno.test_native_define
```

The folder contains `mod.json`, `geno.json`, authored move scripts and an empty `files/` mount root. Export copies the validated source inputs and writes a SHA-256 manifest, refusing archive payloads. Restart after changing definitions. Only the `mario` donor, `melee.common.v1` behavior and `retail:mario` resource preset are supported in slice 1; unsupported donors/resources and simultaneous `attach`/`define` are errors. This manifest is a packaging foundation, not an online admission certificate.

Run from the workspace root with Python 3.10+ and the game checkout at `melee/`.
Install the checker dependency with `python -m pip install -r tools/geno/requirements.txt`.
No game build or launch is needed. The codec imports the existing IR encoder unchanged.

```text
python -m tools.geno.check docs/learn/geno-fighters/starter
python -m tools.geno.check path/to/geno.json --json
python -m tools.geno.asm move.genoasm -o move.txt --words
python -m tools.geno.disasm move.txt -o move.genoasm
python -m tools.geno.schema
python -m tools.geno.schema --check
python -m unittest tools.geno.test_author_tools -v
```

`check` requires a neighboring `mod.json`. Exit status is 0 on success, 1 on errors.
Editor output is `{ "ok": false, "errors": [{ "path": "...", "message": "...", "source": "..." }] }`;
JSON syntax errors also have `line` and `column`. Comments (`//`) and trailing commas are
accepted like the registry. Duplicate keys, unknown keys, truncation and invalid references
are author errors even where the engine would ignore, clamp or substitute them. This is a
strict authoring contract, not an emulator of the engine's recovery from malformed input.
The generated [schema](geno.schema.json) works with Draft 2020-12 editors; all keys, defaults,
limits and references are in the [template](../../docs/learn/geno-fighters/template/geno.json.md).
Source fingerprints and registry-key coverage make regeneration and review necessary when
the engine changes. Keys and semantic annotations that cannot be extracted reliably are
reviewed against the registry, rather than guessed from C syntax.

## Text scripts

One command per line; `#` introduces a comment. Integers may be decimal or `0x` hex.
The assembler produces a JSON word array by default; `--words` produces the engine's
whitespace hex file format. It does not append End; the registry appends it on load.

```text
wait 5
hitbox slot=0 joint=43 damage=8 size=4 angle=361 kbg=100 bkb=30
wait 3
clear_hitboxes
wait 6
iasa
```

Hitboxes accept `slot joint damage size x y z angle kbg fkb bkb element shield ground air`.
Defaults are slot/joint/offset/element/shield/FKB/BKB 0, damage 8, size 4, angle 361,
KBG 100, ground/air 1. Size and offsets use the existing encoder's 1/256 units; damage
uses its established integer encoding. Choose skeleton joints in the LAB.

All vanilla opcodes 0–58 are enumerated in [reference.md](reference.md). Named fields come
from decompiled command bitfields: `sfx behavior=0 sfx_id=123 volume=127 panning=64`,
`gfx boneId=2 gfxID=123 offsetY=256`, `cmd_var idx=1 value=1`. Use full `w0.field`
names when short field names are ambiguous. Unspecified fields are zero. The reference
lists each field's bit width, signedness and containing word. These are encoded integers,
not automatically converted coordinates. Every opcode also accepts positional
`name low26_payload remaining_word...`. One-word commands accept no arguments for zero
payload. Timers use `wait 5` or `wait_until 12`; loops use `loop 3` and `loop_end`.
Aliases include `frame`, `endloop`, `subroutine`, `clear_hitbox`, `clear_hitboxes`,
`sound`, and `throw_hitbox`.

Geno commands use uppercase names. In particular **`CALL` is Geno's hook call**,
while lowercase `call` is vanilla's relocated subroutine pointer. Portable overlays
cannot resolve those absolute pointers; the checker and exporter refuse them.

```text
SET la_i:0 1
ADD ra_f:0 0.5
GET la_f:0 STICK_X
PUT ANIM_RATE 1.5
IF la_i:0 EQ 1 0
IFV AIR EQ 1 0
CALL geno.brake -1
CHG motion:14 FRAME 12 ONCE
CHGAND AIR
REHIT 1 6
LINK 1 SPEED
HBDMG 1 5.5
HBFLAGS 1 NO_HITLAG|FLINCHLESS
```

Grammar for every escape:

| Command | Operands |
|---|---|
| NOP, ORIG, CHGCLR | none |
| SET, ADD, SUB, MUL, DIV, RAND, SETBIT, CLRBIT | variable, operand |
| GET | destination variable, engine value |
| PUT | writable engine value, operand |
| IF | variable, comparison, operand, forward skip **words** |
| IFV | engine value, comparison, operand, forward skip **words** |
| SKIP | forward skip **words** |
| CALL | hook name, optional integer argument (default 0) |
| CHG | target, condition, optional NOT and/or ONCE |
| CHGAND | condition, optional NOT and/or ONCE |
| REHIT, LINK, HBDMG, HBSTUN, HBFLAGS | hitbox mask (0–15), operand |

Variables: `la_i:0` / `ra_i:0` / `la_f:0` / `ra_f:0`, indices 0–63.
An operand is a literal, variable, or `bits:0x...` for exact IEEE bits. Float banks,
float values and HBDMG use float literals; FRAME conditions use **integer** frames.
SETBIT/CLRBIT operate on integer banks. REHIT/LINK require literals.
Comparison names and every engine value/hook are in the generated reference.
`SPECIAL_F:0` and `SPECIAL_I:0` address special words 0–264 and are read-only.
PUT's writable values are separately listed there. Button, hitbox flag and link-mode
names can be joined with `|` as integer operands.

Conditions: `ALWAYS`, `ANIM_END`, `GROUND`, `AIR`; `PRESSED mask`, `HELD mask`,
`FRAME integer`; `BIT variable bit_index`; `VAR variable comparison operand`;
`VALUE engine_value comparison operand`. Targets: `motion:14`, `special:0`,
`geno:0`, `auto`, `helpless`, `stay`; optional `|RAW` / `|KEEP_FRAME`.
The Python API `assemble(text, states=[...])` also resolves `geno:state_name`.
The standalone CLI uses numeric state indices because it has no fighter context.

Disassembly reassembles each friendly command before accepting it. Any unusual bits,
extra payload or noncanonical representation use `NAME raw=0xWORD,0xWORD,...`.
That single-command form preserves every word exactly, including NaN payloads and unused
bits. Decoding is lossless; lossless decoding alone does not prove gameplay validity.

## Export from your own disc

```text
python -m tools.geno.export kirby --row 305 --out D:/private-geno-edits/kirby-b
python -m tools.geno.export PlKb.dat --row 305 --row 306 --disc akaneia --out D:/private-geno-edits/kirby-pair
```

Use a **fresh directory outside both repositories**, including `_build`. The exporter
requires `--out` and refuses overwrites. `--iso` overrides `GW_ISO_VANILLA`,
`GW_ISO_AKANEIA` or `GW_ISO_ACE` from the environment or `.env`; the image path is never
logged or stored in the manifest. Exported text is disc-derived and **must not be shared
or committed**, even after assembly or editing. Each script and manifest carry this notice.

The existing `tools.mex_port.mex_hsd.Gcm` / `Archive` readers support the registry's 27
retail fighter names and aliases, or an explicit `Pl*.dat`/`.usd` archive on the chosen
image, if its layout matches: one `ftData*` root (excluding Kirby-copy roots), relocated
action table at +0x0C or demo table at +0x14, or public `ftcmd`; 0x18-byte rows with
relocated animation and script pointers. Select with `--table action|demo|ftcmd`.
The manifest records each selected row's animation name. This is selected-row extraction,
not archive copying. Empty rows, ambiguous roots, incompatible custom/m-ex layouts,
relocated Subroutine/Goto, standalone Return, truncated scripts, unknown opcodes and
scripts without End within 2,000 commands stop cleanly. No real image was exported during
this task; tests use stub archives through the actual reader path.

## Checks that still require the game

Without opening the installed fighter archive, animation/subaction existence, motion-row
semantics and skeleton joints cannot be established. The checker validates syntax and
numeric table bounds, declared states/articles, local files and model public symbols,
hooks/callbacks, package references, effect binding structure, command boundaries and
pool limits. Disc rows and animations remain explicitly unverified. Global profile,
overlay and FX binding-set caps also depend on **other mounted mods**.
Static CHG/CHGAND counting is conservative across branches; the vanilla loop stack is
conservatively restricted because its decomp declaration marks the size uncertain.
Effect simulation, collision, transitions, visual/audio fidelity, rollback and online
compatibility need the LAB and normal game acceptance tests.

The refusal list catches recognizable whole fighter/stage/menu/table archives, disc images,
executables, game audio banks and patches. It is a packaging guard, not a provenance proof
for renamed files or arbitrary custom assets. The starter contains original data only.

## Authored fighters (slice 4, first steps)

- `python -m tools.geno.check_art <art folder>` validates an authored art package (manifest, skeleton, hurtboxes, glTF, costume textures) with file-and-field errors; `test_check_art.py` is its test.
- `tools/geno/build_courier.sh [--art-rebuild] [--out DIR] [--scale S] [--install]` builds the Courier's model files, animation bank and `plan.json` from `ports/vanilla-original/` into `_build/geno-slice4/courier/` (never committed); `--install` copies them into `melee/pc/geno/mods/vanilla-courier/files/` (git-ignored). Converter: `ports/ir/tools/authored_fighter.py` (test: `test_authored_fighter.py`) and `fighterbuild ... build <mesh> - <out>` (template `-` = authored material, no disc file).
- `check.py` and `report.py` do not yet understand `base: "none"` (the engine does not accept it yet; `melee/docs/geno.md` 22.3).

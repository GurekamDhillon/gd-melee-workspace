# Halberd: Meta Knight, Brawl → Melee

Halberd (named after Meta Knight's battleship) is a port of **Meta Knight from *Super Smash Bros.
Brawl*** into GD's Melee. It is an m-ex fighter that runs on the ACE disc, and it uses the port's
**Geno** engine for everything m-ex can't express: Brawl's specials, glide, root-motion states and
script logic.

> **No Nintendo assets are in this repository.** This folder holds research only: notes, the
> decoded move data's *analysis*, the conversion tools and hand-written configs. Every model,
> animation, texture, effect, sound and menu graphic is built locally from **your own legally
> obtained copies** of *Brawl* and *Melee*, and `.gitignore` keeps all of it out of git.

## Status

Playable in local and online matches on the Geno build. Feel isn't tuned yet (the numbers are
Brawl's), and a few moves are still approximations.

| Area | What exists |
|---|---|
| **Slot** | An m-ex row on the ACE disc (internal 52 / external 51), a Melee Kirby clone base, name "Brawl Meta Knight", scene token `p1=brawlmetaknight`. |
| **Model** | 105 joints: Brawl's 77 bones keep their ids, plus the cape article merged in. 6 costumes. Both eyes render with a 3-layer eye material; a reflection shine layer; mask specular. |
| **Animations** | 241 clips, root motion under a per-clip policy (`anim/transn_policy.json`), 111 eye-UV clips, win and lose poses. |
| **Moves** | All normals, grabs and throws with Brawl's hitboxes on Meta Knight's bones; the rapid-only jab; the forward-tilt 3-chain; 6 jumps. |
| **Specials** (30 Geno states) | Mach Tornado (tap B to rise; the spin animation follows the spin rate), Drill Rush (rebuilt from Brawl's code; the model pitches with the drill), Shuttle Loop (root motion into a helpless glide), Dimensional Cape (steerable vanish, hidden and intangible, slash or not, forward/back variants), Glide (Brawl's maths), taunts. |
| **Effects** | Its own effect bank: 25 Brawl effect models converted about 1:1 plus 4 particle generators, and a sword trail. |
| **Sounds** | Its own sound bank: 76 sounds (48 SFX, 28 voice clips), Brawl's DSP-ADPCM copied byte for byte. |
| **UI** | Character select icon, 6 portraits, 6 stock icons and the results-screen name, all from Brawl's menu art. |

### Known gaps

- **Mach Tornado:** the starting B press also counts as the first lift, and it rehits every 10
  frames (Brawl rehits every 180° of spin). Both are open design choices.
- **Up-B** goes into Glide rather than GlideStart (the `upb_glide` knob).
- **Guessed, not verified:** the ledge flag meanings, the cape's stick threshold (0.3), and the
  special-fall landing lag.
- **Not ported:** the Final Smash, sword hiding (the parts system allows only 2 models) and the
  entrance.
- **Feel:** not tuned; the knobs are `tuning.json` and `tuning.melee-feel.json`.
- **Memory:** 3 players including Meta Knight can run out of the match-load heap; the animation
  file is 4.9 MB.
- The drill and cape particles are approximations.

## The pipeline

Everything goes through a **character IR** first: a validated JSON description of the Brawl
fighter (attributes, actions, subactions, PSA scripts, hitboxes, skeleton, relocatable code),
built from the decoded files and checked against the shared schema in [`../ir/`](../ir/).

```
Brawl files (yours)  ──decode──►  ir/metaknight.brawl.ir.json  ──port plan──►  build  ──►  m-ex slot
                                       (validated, ports/ir)     ir/metaknight.port-plan.md
```

| Folder | What it does |
|---|---|
| `tools/` | The orchestrator `build_mk_slot.py` and its steps: `decode_mk.py` / `rel_mk.py` / `sora_mk.py` (decode the moveset and the relocatable code), `mk_scaling.py`, `build_mk.py` (scripts, attributes, hitboxes → Geno), `verify_mk.py`, `mk_slot_files.py` + `build_mk_ui.py` (slot tables and menu art), `build_mk_effects.py`, `build_mk_sounds.py`, `build_mk_visuals.py`, and the in-game numeric checks (`ingame_v2.py`, `ingame_v4.py`, `ingame_visuals.py`). |
| `model/tools/` | `mkbuild` (C#, on HSDLib): Brawl model → Melee HSD model, costumes, the eye material; `install_mk.py` installs model and animations into a slot. |
| `anim/tools/` | CHR0 → Melee figatree encoder, root-motion policy, eye states, visibility events. |
| `effects/tools/` | `efbuild` (C#): Brawl effects → the fighter's own Melee effect bank; PSA graphic calls → Melee effect commands. |
| `sound/tools/` | BRSAR reader, SSM bank writer, PSA sound calls → Melee sound commands. |
| `ir/` | The Meta Knight IR instance, its builder and the port plan. |
| `mods-slot/metaknight-slot/` | The slot's hand-written configs: `mod.json`, `geno.json`, `TUNING.json` and the Geno script overlays (`geno/sub_NNN.txt`). The built files (`files/`) are not tracked. |
| `geno_v1_encodings.md`, `geno_v2_encodings.md` | The Geno script encodings the translator emits (copies of the relevant sections of the melee fork's `docs/geno.md`). |
| `PHASE1_REPORT.md`, `model_anim_ready.md` | Research notes from the first build and the model/animation phase. |

## Rebuilding it locally

This needs your own files; nothing here is playable on its own.

1. **Your own legally obtained copies** of *Super Smash Bros. Brawl* (extracted, for Meta Knight's
   fighter, effect, sound and menu files) and a *Melee* mod disc with m-ex (the ACE disc).
2. The Geno build of the port (the melee fork's `pc-port` branch) and the workspace tools.
3. Build the C# tools (`dotnet build -c Release` in `model/tools/mkbuild`, `effects/tools/efbuild`
   and `tools/ui/hsdresave`; they need HSDLib).
4. From this folder: `python tools/build_mk_slot.py`. It builds, verifies, installs the model and
   animations, the UI art, effects, sounds and visuals into `mods-slot/metaknight-slot/`.
   Wait while a `.build.lock` file exists; the build creates and removes it.
5. Point `MELEE_MODS_DIR` at a folder that holds (or links to) `mods-slot/metaknight-slot`, and
   start a match with `p1=brawlmetaknight`.

The paths to your extracted Brawl files and your disc image are set at the top of the tools
(`C:/iso/...` by default). Some shared helper tooling still lives in the local workspace outside
`ports/` and isn't published yet, so a from-scratch rebuild on another machine needs some path
editing.

## Legal

No Nintendo assets, ROMs or disc data are in this repository. You need your own legally obtained
copies of the games. Not affiliated with, endorsed by or sponsored by Nintendo; *Super Smash Bros.*,
*Melee*, *Brawl* and Meta Knight are trademarks of Nintendo.

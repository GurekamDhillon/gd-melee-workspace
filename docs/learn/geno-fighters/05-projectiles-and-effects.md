# Packet 5: Projectiles and effects (outline)

**Status: outline.** The definitions below are the documented formats. This packet has no worked
example an author can run, because the pieces that need art (an article model, an effect package)
are produced by tools that need data from other games. Packet 10 says what is missing.

**Goal:** define a projectile (an article), spawn it from a move, and know how effects and sound fit.

**Prerequisites:** packet 3.

## Articles

A Geno article is a Melee item that Geno defines from `geno.json` (`melee/docs/geno.md` 19.1). Melee
already moves, draws, hits and despawns items, so Geno reuses all of that and adds only the
definition, three callbacks and the reactions. Each profile can have 16 articles. Article `a` is
item kind `0x1000 + p * 8 + a` for the first eight, a second range for 8 to 15, always above m-ex's
custom item kinds, so no m-ex table is ever indexed with it.

A minimal definition, from the reference (19.2):

```json
"articles": [
  { "name": "Fire",
    "lifetime": 60,
    "spawn": [8, 8],
    "velocity": [2.5, 0],
    "max_live": 4,
    "despawn": { "hit": true, "shield": true, "stage": true, "clank": true },
    "hitboxes": [ { "damage": 7, "size": 4, "offset": [0, 0, 0], "angle": 45, "kbg": 50,
                    "bkb": 30, "element": 1, "start": 1, "end": 0,
                    "hits": { "ground": true, "air": true, "reflect": true } } ] }
]
```

Without a `model`, an article is invisible: hitboxes only (19.1). A model is an HSD archive (a
costume-style `.dat`) in the mod's `files/` plus its joint symbol (`"model": {"file": "...",
"symbol": "..._joint"}`), loaded once at boot into a reserved region that Geno takes only when a
mounted mod's `geno.json` defines articles. A mod enabled later by a hot reload gets no models until
a restart (19.1). **This course has no tool to make such a `.dat` for you.** The tree shows one
way: `ports/ir/tools/trail_magic_models.py` builds procedural shapes with the `fighterbuild` tool
(19.10).

Other keys (19.2, 19.8): `gravity`, `max_fall`, `accel`, `max_speed`, `homing`, `spin`, `scale`,
`angle`, `bone`, `children`, `effects`, `fx`, `spawns`, per-hitbox `slot` and `stun`.

### Spawning one from a move

Native hook 5, `geno.article.spawn`, argument = the article's index (`melee/docs/geno.md` 19.2).
From a script it is the `CALL` sub-command: sub `0x20`, length 3, word 1 the hook number, word 2 the
argument:

```
0xEE030000  0x00000005  0x00000000     # CALL hook 5 with argument 0: spawn article 0
```

(derived from the layout in section 8; not run). Put it in your move's word file after a wait, at
the frame the move throws it. The log reports each spawn, despawn and refused spawn (`geno: ... article`).

### Reactions

`despawn` says what ends the article besides its lifetime. Reflected articles turn with the
reflector. Counters, `on_hit` and extra hitstun (`stun`) are in 19.3, 19.4 and 19.12.

## Effects

Two routes (20, 19.11):

1. **Melee's own effects.** An article's `"effect"` or `"effects"` attaches Melee particle effects
   by id. Ids 5000 to 8999 are the *owner fighter's own m-ex effect bank* (19.11).
2. **Geno effect packages.** A directory `mods/<id>/fx/<name>/` holding `<name>.gfx.json`,
   `tex/*.png` and `mesh/*.json`, drawn by Geno's own runtime, not Melee's particles. Format and
   limits are in section 20 (the schema is `ports/ir/schema/effects.schema.json`). An article binds
   one with `"fx": "<name>"`. A fighter binds packages to its states with `"fx_bindings":
   "fx/fx_bindings.json"` (schema `ports/ir/schema/fx_bindings.schema.json`).

The only importer in the tree reads Ultimate's effect files (`ports/ir/tools/ultimate_vfx_geno.py`),
which you must own. **There is no hand-authoring guide and no sample package.** A person could write a
`.gfx.json` by hand from section 20, but nothing in the tree shows a minimal valid one.

Budget: 64 packages, 2000 particles, 256 emitter instances (20.3).

## Sound

Geno has no sound system. A move's script plays Melee's sound command (opcode 17, `sfx`; the LAB
colours it purple on the timeline). Sound banks come from the m-ex tables
(`docs/mods-packaging.md` 2.3). There is no documented way to add a new sound to a Geno-only mod.

## Check yourself (for the full packet)

- Why does an article without a model still hit?
- What reserves the article model region, and what happens if you enable the mod late?
- Which hook spawns an article, and where does its argument come from?

## Sources

- `melee/docs/geno.md`: 19.1 to 19.4, 19.8, 19.10 to 19.12, 20 to 20.3.
- `ports/ir/schema/effects.schema.json`, `fx_bindings.schema.json`.
- `ports/ir/tools/ultimate_vfx_geno.py`, `trail_magic_models.py`, `trail_magic_geno.py` (a generator of
  articles and states).
- `melee/pc/platform/gw_script.c` (`gs_cmd_names`: `sfx` is opcode 17).
- `docs/mods-packaging.md` section 2.3.

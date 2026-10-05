# 11. A fighter defined from scratch

Status: tested lesson, 2026-10-05 (slice 2). A `define` is a native fighter of its own that still wears Mario's model and clips. Two fixtures
ship: `Vanilla Hero` (one changed jab) and `Vanilla Striker` (a whole move set). They need only the vanilla disc. Looks and feel of both are unreviewed.

## 1. Make one

```sh
python -m tools.geno.new my-fighter --name "My Fighter" --base mario --output mods/my-fighter
python -m tools.geno.new my-fighter --name "My Fighter" --base mario --output mods/my-fighter --template striker-skeleton
python -m tools.geno.check mods/my-fighter
python -m tools.geno.report mods/my-fighter --frames
```

`geno.json` header: `{"geno": 7, "fighters": [{"define": {"key", "name", "base": "mario", "common": "melee.common.v1", "resources": "retail:mario"}, ...}]}`.
Use `"geno": 7` for anything the Hero does not use: the full attribute list, `special_attributes`, `fx_bindings`.

## 2. Own the behaviour, row by row

`python -m tools.geno.report` prints the 351 motion rows as `own`, `inherited` or `donor-special (unreachable)` and the eight special entries with
their bound Geno state or `DONOR`. "Not donor-dependent" for slice 2 means zero `DONOR` entries and every attack row `own`. Edit one move,
re-assemble (`python -m tools.geno.asm`), run `check` and `report`: the row flips to `own`.

- **Attributes** (`"attributes": {...}`): the 67 common names, for example `landingairn_lag`, `initial_shield_size`, `gravity`, `jab_2_input_window`. An unknown name is an error.
- **Moves**: a subaction overlay (`subactions`) plus a `common_states` row, or the `moves` sugar:
  `"moves": {"ftilt": {"motion": 53, "words": "moves/ftilt.words", "tag": "tilt"}}` (expanded by `tools.geno.export`; the engine reads only engine keys).
- **Specials**: `states` (Geno states) and `specials` binding all eight entries. The Striker's neutral special charges while B is held (a variable counts),
  its side special lunges with root motion, its up special rises with a steering window, its down special is a counter windowed by `on_hit`.
- **Tags**: declare `move_tag` on every row. For a define the declared tag wins, so `smash`-style hit rules and crits follow what you declared.

## 3. Test it (what was run, so you can repeat it)

In the LAB (`mode=lab;p1=geno:vanilla-striker/hu;p2=mario/cpu0`, then `gd.cpu_mode(2,"stand")`): `gd.player(1).motion` after each input is the Geno state number
(1024 and up) for the eight specials; `gd.timeline` differs from Mario's; `gd.cpu_attrs(1)` shows your attributes; a `gd.hit_rule_add` per tag class
multiplies your damage as it does Mario's; `gd.crit` with `tags`; `gd.rewind_test` mid-charge gives 0 simulation bytes differ. The log must say `interpreter attempts 0`.

## 5. Slice 3: a define with its own projectile (`"geno": 8`)

`pc/geno/mods/vanilla-caster/` is the smallest example: one `states` entry whose script is `wait 8; CALL geno.article.spawn 0; wait 22; CHG auto ALWAYS ONCE`, bound to the
neutral special on the ground and in the air; an `articles` entry `CasterBolt` (velocity, lifetime, one hitbox, `fx` naming the package in `fx/CasterGlow/`), and a `sounds` table the
article names with `spawn_sound` / `end_sound`. Check it (`python -m tools.geno.check`, `report` lists the resources). In the game: the special is state 1024, an item of kind 4096 appears
and travels at the declared velocity, its hit reports `move_tag=projectile` with the declared damage, it is cleaned up on a hit or its timeout, and `gd.rewind_test` with the bolt in flight gives 0 simulation bytes differ.
Sounds are names resolved to engine sound ids (no audio data); see `melee/docs/geno.md` 22.2 for what that supports.

## 4. Limits

Still Mario's body (slice 4), no own audio data (named engine sounds only), no CSS entry or voice (6), offline only (7). `10-known-gaps.md` section Z lists
the ranked gaps and the sweep. Reference: `melee/docs/geno.md` sections 22 and 22.1; fixtures `melee/pc/geno/mods/vanilla-hero/` and `vanilla-striker/`;
demo `demos/geno-define-striker`.

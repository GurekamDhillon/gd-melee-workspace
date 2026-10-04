# 11. A fighter defined from scratch

Status: packet stub, 2026-10-04. The Geno engine has a version 6 native Mario-reference backend. Author-tool and syntax checks are available; an integrator build and full game acceptance are still required.

Generate a source-only folder from the workspace root:

```sh
python -m tools.geno.new vanilla-hero --name "Vanilla Hero" --base mario --output mods/vanilla-hero
python -m tools.geno.check mods/vanilla-hero
python -m tools.geno.export --package mods/vanilla-hero --out packages/vanilla-hero
```

The generator supports Mario only in this slice. `define` creates a separate native identity; `attach` continues to change an existing fighter. `resources: retail:mario` references installed retail data. The package contains no model, animation, effect or sound archive.

The checked-in fixture is `melee/pc/geno/mods/vanilla-hero/`. Its walking-speed ceiling is 1.8 units/frame and its first jab has one 12-damage hitbox. It inherits every unmodified common action and Mario special through `melee.common.v1`, with independent effective attribute, animation descriptor and state-row copies. `common_states` can override native motion rows with `motion`, `like`, `subaction`, `flags`, `move_id`, and registered `anim`/`iasa`/`phys`/`coll` callbacks. This is a complete inherited reference definition, not new authored art.

After rebuilding, enable the Hero folder alongside the LAB; restart the process after edits. Select Vanilla Hero in the offline selector or use `geno:vanilla-hero` in a scene player field. Resident aliases come from unused legacy slots; admission refuses exhaustion. Do not hard-code its numerical slot.

Next teaching work: walk through ownership in the LAB, demonstrate every common action, compare the jab with Mario, run a full stock match, then repeat inputs across a snapshot. Record results before turning this stub into a tested lesson. Online use is blocked pending portable resource identity, admission negotiation and mapping contracts.

Sources: `melee/docs/geno.md` section 22; `tools/geno/new.py`; `melee/pc/platform/geno_define_registry.inc`; `melee/pc/geno/geno_define_data.inc`.

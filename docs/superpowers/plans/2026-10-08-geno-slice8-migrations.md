# Geno slice 8: customer migrations (2026-10-08)

Brief for the lane that moves the ported fighters onto the Geno `define` format, one at a time. Builds on the slice 2 plan's slice 8 row
(`docs/superpowers/plans/2026-10-05-geno-full-fighter-slice2.md`), `melee/docs/geno.md` sections 22-23, the Courier (slice 4) as the
authored-fighter reference, and the tooling of slice 4 (`tools/geno/moves_check/`). Tags: **[R]** read from source, **[M]** measured
in a run of this lane, **[I]** inferred. Outcomes are appended at the end of the lane (section "Result"); until then every statement is a plan.

**Rule for all three:** the generated package (models, clip banks, ACMD-derived words, Ultimate or Brawl effects, UI art) is Nintendo-derived and
stays LOCAL: the output goes under `_build/` (git-ignored), exactly like `ports/ir`'s installs. What is committed is the generator, the tests that
need no game data, and the docs. Custom/ported fighters are not shipped in releases (`tools/release` keeps them out; nothing in this lane touches it).

## What a define can say (the target) and what a port is today

| aspect | today (m-ex slot + `attach`) | define (`base: "none"`, geno 9) |
|---|---|---|
| identity | m-ex row 52/51 replaces ACE "Wolf SSBU"; MxDt, PlCo, MnSlChr, IfAll are patched | `define` header; no m-ex, no ACE disc |
| behaviour host | a Melee fighter's data and scripts (Marth, Kirby): common attacks, callbacks | Mario's common states and callbacks, with the package's attributes, rows and overlays on top |
| model, skeleton | `PlUs<Colour>.dat` built on a disc template; `PlCo.dat` parts table row | `fighter.costumes` model files, `plan.json` (joints, parts table, role joints, hurtboxes) |
| clips | `PlUsAJ.dat`, rows of the host's `ftData` table pointing at clips | `fighter.animation` bank; plan `motion_rows` / `row_clips` |
| moves | translated ACMD written into the host's script rows (63 rows for Sora) | `subactions` overlays (words) |
| specials, magic, articles, FX | Geno profile (`attach`): states, specials, articles, `fx_bindings` | the same keys on the define |
| expressions (eyes, mouth) | ModelVis states per mesh | none (gap G3) |
| UI | CSS icon, CSPs, stock icons patched into MnSlChr/IfAll | `presentation` `.gxtex` files (slice 6) |

## Sora (`ultimate-trail`): first, fully

### What maps to which define key [R from `INSTALL.json`, `geno.json` of the Oct 3 install and `geno.md` 22]

| old | new |
|---|---|
| `PlUs<c>.dat` x8 costumes (175 joints) | `fighter.costumes[]` (file, joint, matanim, name); the old files are reused after a name change, so the model is identical |
| `PlUsAJ.dat` (200 clips) and the host rows' (symbol, offset, size) | `plan.bank.clips` (read back from the installed host table) ; `row_clips` for every row 0..294 |
| `PlCo.dat` parts row, `ftData` joint fields, hurtboxes | `plan.parts`, `plan.ftdata`, `plan.hurtboxes` from `plan_parts.py` and `plan_hurtboxes.py` (the installer's own functions) |
| moveset rows 46..326 (63 scripts, 3,006 words) | `subactions` overlays, one `.words` file each |
| 32 Geno `states`, 8 `specials` (neutral special cycles by `la_i`) | the same keys, unchanged |
| overlays on rows 149-162 (Marth item rows used as stand-ins) and 303-326 | **own rows** (gap G1): the define declares rows `303+i` with a clip each |
| 12 `articles`, 4 article models (`GnTrail*.dat`) | `articles` (geno 8) with `model` and `fx`; the magic spheres need `show_model` (cherry-picked `e9342cc27`, v5.7) |
| `fx_bindings.json`, 113 effect packages in `fx/` | the same file; a define admits `fx_bindings` since geno 7 |
| calibrated attributes in `PlUs.dat` (`attr_calibration.json`) | `attributes` (the 67 named fields), read back from the installed block |
| ModelVis (47 states) | dropped (G3); the model is built with the default expression meshes only |
| CSS icon, CSP, stock (Ultimate BNTX) | `presentation` `.gxtex` when the BNTX sources exist; otherwise the letters fallback of slice 6 |

### Gaps the format lacks, and the cut I take [I until measured]

| # | gap | cut in this lane | engine/format decision |
|---|---|---|---|
| G1 | A define's animation rows are Mario's 303 (+ conflict extras). Sora's specials use 28 rows past that | `fighter.rows`: a list of clip names, rows `303..` in order; `subaction` / overlay index may reach `303 + len(rows)` for a base `none` define | additive key (inside geno 9); owner decision D1 below |
| G2 | `GPL_MAX_JOINTS` 128 < Sora's 175 joints; overlays 64 per profile (Sora needs about 100) | raise to 256 / 192 (storage grows by tens of KB per profile) | API limits: owner decision D2 |
| G3 | no ModelVis for a define: faces, eyes and mouth are separate meshes shown by expression | build the model with the default-visible meshes only; the others are cut | owner decision D3 (a `vis` table for a define is its own slice) |
| G4 | per-row root-motion flag (`0x80000000`, "animation driven") is a Mario row flag in a define | plan key `row_driven` (rows), OR-ed into the row flags | additive plan key |
| G5 | thrown-victim rows (author kind `0x21`) must keep a clip the victim's skeleton can play | keep the donor's victim clip (the loader already preserves the author id) ; Sora's own thrown clips are not used | owner decision (cosmetic) |
| G6 | the host's behaviour is Marth/Kirby, a define is Mario-shaped; unnamed `ftCo_DatAttrs` fields and callbacks (tipper, combo flow) differ | attributes are read back from the host block; the rest is reported by `moves_check` as a difference | accept, list |
| G7 | UI art is m-ex tables today | `.gxtex` conversion of the BNTX art | follow-up if the BNTX sources are present |
| G8 | Lua: the old Geno profile already expresses Sora's specials (states, `select`, counters, articles); nothing found that needs the slice 5 API | none planned | revisit only if a move cannot be reproduced |

### Plan of work

1. Engine (additive, game worktree): cherry-pick `e9342cc27` (done); G1 `fighter.rows`; G2 limits; G4 `row_driven`; tools `check`, `report` and the schema learn `fighter.rows`.
2. Generator `ports/ir/tools/trail_define.py`: reads a staged install folder (what `install_ultimate.py trail` writes) and writes the define package under `_build/`. No Melee disc byte is needed to run it; it reuses the installed Ultimate-derived model and clip files.
3. Baseline: the old Sora (the Oct 3 install, `ultimate-trail-slot`) run through the same scenarios as the define (`moves_check`, token `ultimatesora`); the log is the reference.
4. Parity: `moves_check.lua` (normals, aerials, grabs, throws, then Sora's own specials) on both, a line-by-line diff of the `MOVECHK` records (live hitbox frames, damage, angle, knockback, damage dealt to a placed Mario, launch), articles (spawn frame, lifetime, damage), then `gd.rewind_test` and `run.sh --test`.
5. Report every difference as accepted, fixed, or a decision.

Acceptance: the `ultimate-trail-define` folder boots on the vanilla disc with no m-ex, no ACE and `interpreter attempts 0`; the move-by-move diff is empty or each difference is explained; `diff_compared == 0` in the rewind test; the suite passes; nothing seen on screen is claimed (owed).

## Ultimate Kirby (`ultimate-kirby-slot`): next, if time allows

Smaller, and the state of the port decides: it is "walk, run, crouch, six jumps and uncharged side B" on a Kirby-host slot with an experimental model (`ports/kirby-ultimate/README.md`: face detail and limbs wrong in some poses). A define needs only what Sora's generator already does (model, bank, plan, moveset overlays, Geno side B state), so the same `trail_define.py` core is parameterised by fighter key. Gap specific to Kirby: the host is Kirby (inhale, copy hats); a define is not a copy-ability source and takes Mario's default arms (geno.md 22.1), so inhale/copy is a special case that stays on the m-ex slot until slice 6's Kirby-copy policy exists. Recommendation: migrate movement, normals and side B; leave the copy ability out and say so.

## Meta Knight (Halberd, `metaknight-slot`): last

Brawl source, 105 joints, 241 clips, 30 Geno states, its own effect bank (25 models), a 76-sound bank and Brawl UI art. What fits: model, clips, plan, moveset, states, articles (the cape), `fx_bindings`. What does not: **its own sound bank** (a define has named retail sound ids only; own audio is open work of slice 3/6), **the Brawl effect bank** (`efbuild` output are m-ex effect files, not Geno `.gfx.json` packages), **glide / drill / tornado behaviours** run as `geno.glide`, `geno.drill`, `geno.tornado` states and are available to a define, the **eye UV clips** (texture animation) and the **second model** (cape merged in is fine). Special cases that must stay: sounds and effect files until the resolver can mount them. Recommendation: do Meta Knight only after Sora is accepted and the owner has decided the audio and effect-bank questions; it is not attempted in this lane unless time remains.

## Decisions for the owner (also in the report)

- D1 `fighter.rows` (G1) as a format key inside geno 9, or a version number.
- D2 raising `GPL_MAX_JOINTS` and `GENO_MAX_OVERLAYS` (G2).
- D3 dropping expressions for a define (G3) versus a ModelVis-for-defines slice.
- D4 whether a migrated port is to be listed in the mod browser or stays a local build (it is never in a release).

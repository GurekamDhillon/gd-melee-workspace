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

## Result: interrupted-lane continuation, 2026-10-08

This dated result supersedes the planned format numbers and G6/G8 assumptions above.
The format remains **10**; no format bump or shared engine behavior change was made in this continuation.

- [M] Converted the inherited baseline `_build/agents/geno-s8/mods_old/ultimate-trail-slot`, using
  `_build/audit-20261003/sora-play4/staged-moveset.json`, its `staged-specials/clips.json`, and `_build/tmp/ir`.
  Local output: `_build/tmp/geno-slice8/continued/ultimate-sora-define`. It has 175 joints, 200 clips,
  33 own rows, 63 overlays / 8,645 words, 32 states, 12 articles and 76 common attributes.
  The nine previously unnamed fields are now in the inherited engine attribute table; none remain uncarried.
  Article models with effects explicitly use `show_model: true`.
- [M] `tools.geno.check` passes; `tools.geno.schema --check` exits 0. Build passes, bridge 18,829/18,829
  resolved, ABI audit 0. Headless suite: `TESTS: pass=332 fail=0 total=332`.
  Python verification: 51 tests, 4 skipped (art fixtures unavailable), plus one converter output-safety test.
- [R] Aerial Sweep's repeated change checks are re-found by the engine, rather than consuming a new slot.
  Corrected the checker's false capacity errors to match `geno_register_check` / `geno_and_check`, without
  raising budgets or changing the generated move. Specials are expressible in existing data, so no fighter Lua
  module is needed in this migration. Slice-5 Lua cannot replace ModelVis, arbitrary collision or article commands.
- [M] The converter restricts writes/deletion to descendants of the ignored `_build/tmp/geno-slice8` namespace
  and refuses source overlap. Parity diffs now refuse empty, failed and incomplete logs; locomotion's completion
  count is corrected to 22. These fixes have asset-free regression tests (observed failing, then passing).
- **Owed:** vanilla define admission/boot with `interpreter attempts 0`, all move/locomotion/defense comparisons,
  article rendering and rewind (`diff_compared == 0`). No scene or windowed runs were attempted in this continuation.
  The headless suite does not prove this generated fighter's gameplay. Historical scratch diffs are not acceptance.
  Exact coordinator commands and quoted evidence: `_build/tmp/codex-geno-s8-report.md`.

### Remaining owner decisions / proposed keys

1. **G3 expressions:** proposed `fighter.visibility` (default mesh groups plus indexed visibility states) and
   expression events in subactions. The current converter reuses costume bytes unchanged; it does **not** strip
   alternate expression meshes. Without ModelVis admission the expression presentation is unverified.
2. **ECB / IK / ledge geometry:** proposed plan `ecb` (joint-local offsets), `ik` (limb lengths), and `ledge`
   (snap offsets). These still inherit the Mario template; matching attributes and hurtboxes does not reproduce
   Marth's collision/reach geometry. Treat resulting parity differences as decisions, not automatic acceptance.
3. **G5 victim clips:** keep installed donor victim clips and their author-kind bits for compatible victim
   skeletons. A future `fighter.victim_clips` mapping could express recipient skeleton/preset explicitly; cosmetic
   parity is pending. No change to low six author bits is proposed here.
4. **G6 common callbacks:** Mario/common remains the host for a none define. Existing `common_states` can select
   registered callbacks; additional named combo/throw callbacks or data parameters should be added only after a
   measured mismatch identifies one. No evidence yet justifies a new key or guessing at native Lua physics.
5. **G7 UI:** existing `presentation` suffices; converter does not extract the old patched CSS/CSP/stock art.
   A source-BNTX-to-`.gxtex` conversion is a follow-up; letters fallback remains. No new format key needed.
6. **Audio and source-native FX:** existing named retail sounds and Geno FX cover the present package; own
   sound banks (`sounds[].file`, with event identity/resimulation rules) remain a separate owner decision,
   particularly before Meta Knight. No audio was imported here.
7. **D1/D2:** own rows, row flags/blend, 256 joints and 192 overlays are already inherited additive engine work;
   this lane keeps format 10. **D4:** generated ports stay local-only; public browser listing remains undecided.
   Ultimate Kirby and Meta Knight were not attempted: Sora's runtime acceptance is still owed.

Rulings: preserve existing data for specials because the runtime deduplicates checks; correct tooling rather
than expand limits or add unnecessary Lua. Preserve local costume bytes and report the ModelVis limitation
instead of claiming expression meshes were removed. User's no-git-write rule supersedes plan commit steps;
the coordinator owns commits. Final fresh review found the output-boundary and incomplete-log issues above;
both were fixed with failing-then-passing tests.

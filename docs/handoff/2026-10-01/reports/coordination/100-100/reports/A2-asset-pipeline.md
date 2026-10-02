# A2 — Asset/art pipeline reproducibility audit

Scope: `menu/out_roguelite`, `menu/out_effects_study`, `menu/out_brand`, `menu/out_roguelite_expansion`.
Read-only audit. No generator, build, game launch or git mutation was performed. All evidence is from
`git ls-files` / `git check-ignore` / `git status` / file reads.

## Summary table

| output dir | size | tracked in git? | generator command | its inputs tracked? | runtime-critical? |
|---|---|---|---|---|---|
| `menu/out_roguelite` | 26M | **0 files** (`git ls-files` empty) | `python3 menu/pipeline/roguelite_art.py` <br> `python3 melee/worktrees/linux/pc/tools/png2gx.py --layout menu/out_roguelite/manifest.json --outdir menu/out_roguelite/gx` <br> `python3 tools/roguelite/build_room_kit.py` | **NO** — generator `roguelite_art.py` itself is untracked | **YES** (`prepare.py:75-82` copies `manifest.json` + `gx/*.gxtex`; `prepare.py:11,24-30` requires all 47 `room-kit` files) |
| `menu/out_effects_study` | 5.0M | **0 files** | `python3 menu/pipeline/effects_assets.py` | **NO** — generator `effects_assets.py` itself is untracked | **YES** (`tools/effects_lab/recipes.py:10` `ASSET_ROOT`, read at install time by `prepare.py:62-65`) |
| `menu/out_brand` | 344K | **44 files, all `.svg`/`.ico`/`.md`** — the rasterised PNG set is absent (0 PNGs on disk; `*.png` globally ignored, no allowlist) | `python pipeline/build_brand.py` | generator `build_brand.py` **is tracked**; fonts tracked | no (marketing/README art only) |
| `menu/out_roguelite_expansion` | 13M | **0 files** | `_build/roguelite-art-venv/bin/python menu/pipeline/roguelite_expansion.py` | **NO** — generator untracked; the venv itself is not declared anywhere | no (review/preview only; `prepare.py` never reads it) |

Tracked vs untracked counts (`git status --short --untracked-files=all <dir> | wc -l`, and
`git ls-files --others --ignored --exclude-standard <dir> | wc -l`):
`out_roguelite` 108 untracked-not-ignored / 7 ignored; `out_effects_study` 36 / 1;
`out_roguelite_expansion` 163 / 93; `out_brand` 0 / 0 untracked (44 tracked).

## Critical findings

### C1 — The generators for the two runtime-critical outputs are not committed (highest priority)

`menu/pipeline/roguelite_art.py`, `roguelite_build_art.py`, `roguelite_feedback_art.py`,
`effects_assets.py`, `roguelite_expansion.py`, `roguelite_expansion_check.py` and the
`roguelite_expansion_review.{html,css,js}` triple are all untracked:

```
$ git status --short menu/pipeline
?? menu/pipeline/effects_assets.py
?? menu/pipeline/roguelite_art.py
?? menu/pipeline/roguelite_build_art.py
?? menu/pipeline/roguelite_expansion.py
?? menu/pipeline/roguelite_expansion_check.py
?? menu/pipeline/roguelite_expansion_review.css
?? menu/pipeline/roguelite_expansion_review.html
?? menu/pipeline/roguelite_expansion_review.js
?? menu/pipeline/roguelite_feedback_art.py
```

`tools/roguelite/README.md:156-162` documents these as the rebuild path, so the documented
regeneration recipe points at files that do not exist in a clean clone. Nothing about
`out_roguelite` or `out_effects_study` can be regenerated from the repository as committed today.

### C2 — Every runtime-critical output file is uncommitted (83 files, install hard-fails without them)

`prepare.py` (`tools/roguelite/prepare.py`) reads three untracked trees at install time:

| reader | file:line | required |
|---|---|---|
| `recipes.py` (called by `prepare.py:62-65`) | `tools/effects_lab/recipes.py:10`, `:16-22`, `:92-98` | `menu/out_effects_study/manifest.json` + all 16 `rgba/*.png`, sha256-verified; mismatch raises `ValueError` |
| `prepare.py:75-82` | | `menu/out_roguelite/manifest.json` + 18 `gx/ico_rogue_*.gxtex` |
| `prepare.py:11,24-30` | | `menu/out_roguelite/room-kit/` — 21 × `.gxmesh` + `.coll.json` (46) + `bf_kit{,_glass}{,.glow}.gxtex` (4) |

Verified state: `{'UNTRACKED+not-ignored': 17}` for the effects set, `{'UNTRACKED+not-ignored': 19}`
for the `out_roguelite` gx set, `{'UNTRACKED+not-ignored': 47}` for the room kit. Zero tracked.
On a clean clone `prepare.py` dies at `FileNotFoundError: Regenerate the BF room kit before installation`
(`prepare.py:26`) — but only after a human notices that `build_room_kit.py` and `roguelite_art.py`
are not in the clone either.

Note the assets are *not* protected by `*.png` ignoring for the two masks that matter:
`recipes.py` copies `ASSET_ROOT/'rgba'/<name>.png` directly. The `*.png` ignore is currently
negated for them by working-tree-only lines `!menu/out_effects_study/rgba/*.png` and
`!menu/out_roguelite/rgba/*.png` (`git diff .gitignore`), which are themselves uncommitted.

### C3 — Runtime dependency on a second, unpinned repository

`tools/roguelite/build_room_kit.py:11-13,22-28` drives Blender against
`melee/worktrees/linux/pc/assets_src/bf_interior/export_kit.py` and
`melee/worktrees/linux/pc/scripts/examples/map_editor/scripts/main.lua`.
`menu/pipeline/roguelite_art.py` (README block, `out_roguelite/README.md`) and
`docs/ASTRA-ART-DELIVERY.md:51` additionally need `melee/worktrees/linux/pc/tools/png2gx.py`.

Those three files *are* tracked in the `melee` fork (`pc-port`): confirmed via
`git -C melee/worktrees/linux ls-files`. But `/melee/` is git-ignored in this repo
(`.gitignore` "Sibling checkouts, each its own repository"), and **nothing in this repo pins a
`melee` commit for asset generation** — `DEPENDENCIES.md` pins Aurora/Dawn/SDL3 and says nothing
about `melee`. A clean gdm clone plus "whatever `pc-port` is today" is the only reproducible
recipe. `PENDING`: exact `pc-port` commit used for the shipped room kit — no record found.

### C4 — Asset toolchain is declared nowhere and contradicts DEPENDENCIES.md

`DEPENDENCIES.md:36` states the toolchain includes "Python 3 (**standard library only**)". The
asset pipeline needs Pillow, numpy, fontTools, playwright + Chromium, `rsvg-convert`,
ImageMagick, and Blender:

- `menu/pipeline/build.py:20-22` → `PIL`, `PIL.ImageCms`, `playwright.sync_api`; numpy at `:58`
- `menu/pipeline/build_brand.py:24-28` → `PIL`, `fontTools`, `playwright.sync_api`
- `menu/pipeline/roguelite_art.py:48-52` → `subprocess.run(['rsvg-convert', ...])`
- `menu/pipeline/effects_assets.py:7-9` (docstring) → NumPy, `rsvg-convert`, ImageMagick
- `menu/pipeline/roguelite_expansion.py:1-5` → Pillow, `rsvg-convert`
- `tools/roguelite/build_room_kit.py:46` → `--blender`, default `shutil.which('blender')`

`tools/port/bootstrap.sh` checks clang (`:24`), gwtool (`:29`), the melee worktree (`:34`),
four `.lib`s (`:41`), imgui/SDL headers (`:46`), two DLLs (`:53`), three ISOs (`:59`) and
vswhere (`:74`). **It checks zero asset tooling.** `SETUP.md` / `PORT_BOOTSTRAP.md`: no asset
tooling mention found. The Pillow/numpy environment used for the expansion pack lives at
`_build/roguelite-art-venv/` — it self-ignores via its own `_build/roguelite-art-venv/.gitignore:2:*`,
so it is untracked, undeclared and not rebuildable by any script in the repo. `PENDING`: the exact
`pip` invocation that produced that venv is recorded nowhere.

### C5 — `out_brand` is partially committed and its PNG half cannot be regenerated blind

`menu/out_brand` is the only dir with tracked content, and it tracks only the vector/source tier
(44 `.svg`/`.ico`/`.md`). `build_brand.py:818-943` rasterises the same art to
`logo/*@2x.png`, `keyart/*_1080p.png`/`*_4k.png`, `discord/*.png`, `social/*.png`. None of those
exist on disk now (0 PNGs) and `.gitignore`'s blanket `*.png` has no `menu/out_brand` allowlist,
so even after a successful build they cannot be committed without a new allowlist. `out_brand`
is not runtime-critical, so this is medium, not critical.

### C6 — Documentation drift and dead links in a clean clone

`tools/roguelite/README.md:170-171` says "Installation copies the **six** opaque room models";
`prepare.py:16-23` requires **21** meshes × 2 files + 4 atlases and raises if any is absent.
`tools/roguelite/README.md:175` links `../../menu/out_roguelite/feedback.html`, and
`docs/ASTRA-ART-DELIVERY.md:33-40` links eleven `menu/out_roguelite_expansion/preview/*.png`
(plus a `.gif`) — every one of those paths is untracked, so all links break in a clean clone.
`menu/out_effects_study/README.md` calls the set "review-only … have not been installed in any
runtime recipe", which `recipes.py:10` contradicts outright (C2).

### C7 — Non-committable input found (correctly not committed, but it makes one path unreproducible)

`tools/roguelite/build_bindings.py:18` reads `ROOT/'_build/agents/linux/scripts-data/character_parts_lab_main/*-analysis.json'`
— measured character-part reports that only exist after running the game, i.e. after discs are
supplied. This is the correct project rule (disc-adjacent data stays out of git) and
`build_bindings.py` is **not** invoked by `prepare.py` (`prepare.py:34` bundle list contains no
`bindings` module; only a `test_roster.py` import), so it is not runtime-critical. Recording it
here so nobody "fixes" it by committing the reports.

## Provenance: authored vs disc/Nintendo-derived (task item 4)

**Original authored art — fine and required to commit.** Every mask and atlas here is generated
from vector paths or analytic fields held in the pipeline source; each module says so on its own
first lines and the claims are auditable rather than asserted:

- `menu/pipeline/roguelite_art.py:1-5` — "No game/disc images, fonts or model references"; the
  18 `ICONS` paths are literal inline SVG (`roguelite_art.py:17-36`).
- `menu/pipeline/roguelite_expansion.py:1-5` — "No game/disc pixels are inputs"; reuses the same
  `ICONS` vocabulary verbatim (`roguelite_expansion.py:41-43`), which is a deliberate, documented
  in-repo reuse, not a Nintendo import.
- `menu/pipeline/effects_assets.py:1-5` — 16 original fire/ice textures; the two data maps
  (`noise_soft`, `flow_curl`) are analytic with a fixed seed recorded in `manifest.json`
  (`'seed'` key). `menu/out_effects_study/README.md` states two consecutive builds produced
  identical hashes.
- `menu/pipeline/build_brand.py:6-12` — "no Nintendo/HAL logos, lettering, characters, stages or
  screenshots, and nothing traced, recoloured or sampled from them."
- `melee/worktrees/linux/pc/assets_src/bf_interior/` — two tracked Python files, fully
  procedural; `export_kit.py:237` creates its atlases with `bpy.data.images.new`, and there is no
  image-file load anywhere in the directory. `grep -n "load\|open(\|\.png\|\.blend"` on both files
  returns only `open("wb")` output writes at `export_kit.py:269` and `:325-326`. So the runtime
  room kit is original procedural geometry.
- Fonts: `menu/SourceSans3/` (3 `.otf` + `LICENSE.md`) and `menu/Hasklug/` are **tracked**
  (`git ls-files menu/SourceSans3` → 4 files). Source Sans 3 is SIL OFL, redistributable with the
  licence, which the pipeline copies out as `font-LICENSE.md` in each output.

**Disc / Nintendo-derived — must never be committed.** No such input was found for any of these
four outputs, and the mechanism that protects them is sound. `menu/meleedump/` (the Melee-derived
index of names and hashes) is explicitly ignored (`.gitignore`, "the menu pipeline: its
Melee-derived index"), and none of the four generators references it. `grep -n "iso\|disc\|romfs"`
over the map-editor script that `build_room_kit.py:22-25` copies into the scratchpad returns
nothing. This is the correct outcome: **every input these four pipelines consume is either
original authored source or an openly-licensed font.**

**Gray areas, called out explicitly.**

1. **`.gxtex` / `.gxmesh` in `menu/out_roguelite/`.** These are the port's *own* runtime formats
   produced by the port's own `png2gx.py` from original masks — not Nintendo data, and
   committing them is defensible. But the repo's stated policy is that outputs are "large and
   fully regenerable" and so are not tracked (`.gitignore` header). Committing `gx/*.gxtex` and
   `room-kit/*.gxmesh` therefore contradicts the header policy unless an exception is written for
   them. Recommendation in the next section resolves this by committing the *regenerated* outputs
   as a bootstrap snapshot and documenting the regeneration path alongside — that is a policy
   decision for the owner, not a technical one.
2. **`tools/roguelite/build_bindings.py`'s measured character-part reports** (§C7). Disc-adjacent
   measured data. Keep out of git. It is optional, so it does not block reproducibility.
3. **`.gitignore` allowlist for `menu/out_effects_study/rgba/*.png` and `menu/out_roguelite/rgba/*.png`
   is itself an uncommitted working-tree change.** Whoever committed C2's fix must commit these
   two negations in the same change, or `git add` of the runtime PNGs will silently fail/succeed
   depending on which `.gitignore` is in the index. Flagging the trap, not endorsing it.

## Recommended minimal "authored inputs to commit" list

Priority order. Group 1 unblocks the runtime-critical path; Group 2 closes the tooling gap.

**Group 1 — must commit (without these, `prepare.py` cannot install on a clean clone):**

| path | why | is it safe under the project rule? |
|---|---|---|
| `menu/pipeline/roguelite_art.py` | sole generator for `out_roguelite/{svg,rgba,manifest.json}` and thus for `gx/*.gxtex` | yes — original authored vector source |
| `menu/pipeline/effects_assets.py` | sole generator for the 16 runtime FX textures | yes — original authored SVG + analytic fields |
| `menu/pipeline/roguelite_expansion.py` | generator for the expansion pack (review-only, but currently only on disk) | yes — original authored vector source |
| `menu/pipeline/roguelite_build_art.py`, `menu/pipeline/roguelite_feedback_art.py`, `menu/pipeline/roguelite_expansion_check.py`, `menu/pipeline/roguelite_expansion_review.{html,css,js}` | the other three committed-uncommitted generators / the review page | yes |
| `menu/out_effects_study/manifest.json` + `menu/out_effects_study/rgba/*.png` (16) | runtime-critical; sha256-pinned by `recipes.py:19-21` | yes — generated from original authored SVG |
| `menu/out_roguelite/manifest.json` + `menu/out_roguelite/gx/*.gxtex` (18) | runtime-critical; `prepare.py:76-80` | yes — port's own format from original masks |
| `menu/out_roguelite/room-kit/*.gxmesh`, `*.coll.json`, `bf_kit*.gxtex`, `manifest.json` (47) | runtime-critical; `prepare.py:24-26` raises otherwise | yes — original procedural geometry from `pc/assets_src/bf_interior/` |
| `.gitignore` — commit the two `!menu/*/rgba/*.png` negations **together with** the above | the negations are currently working-tree-only | — |

Commit the two review/preview dirs (`out_roguelite/{index,build,feedback}.html`, `preview/*.png`,
`out_effects_study/{index.html,preview/,*.zip}`, all of `out_roguelite_expansion/`) **only if**
the delivery docs' links are meant to resolve on GitHub; otherwise add the PNG/GIF paths to
`.gitignore` and fix `docs/ASTRA-ART-DELIVERY.md:33-40` instead. Do not leave it half-way as now.

**Group 2 — tooling declarations (no new art, but without them the committed generators still
cannot be run):**

1. Extend `tools/port/bootstrap.sh` with a "Asset pipeline" block: `python3 -c "import PIL,numpy,fontTools"`,
   `command -v rsvg-convert`, `command -v magick` (or `convert`), `command -v blender`,
   `python3 -c "import playwright"`, plus a note that `playwright install chromium` is required.
2. Correct `DEPENDENCIES.md:36`: replace "Python 3 (standard library only)" with the real split
   (stdlib for `tools/replay` + research; PIL/numpy/fontTools/playwright for `menu/pipeline`).
   Add a "Regenerating menu art" subsection with the exact five commands from
   `tools/roguelite/README.md:156-162`, and record the `melee` commit that
   `pc/assets_src/bf_interior/export_kit.py` and `pc/tools/png2gx.py` were taken from (see C3).
3. Publish the venv recipe that produces `_build/roguelite-art-venv` (currently recorded nowhere),
   or replace that documented command with a plain `python3` invocation like the other four.

## Tooling reference

| tool | required by | declared anywhere? |
|---|---|---|
| Pillow (`PIL`, `ImageCms`) | `build.py:20`, `build_brand.py:24`, `roguelite_expansion.py` | **no** |
| numpy | `build.py:58`, `effects_assets.py:19` | **no** (contradicted by `DEPENDENCIES.md:36`) |
| fontTools | `build_brand.py:26-28` | **no** |
| playwright + Chromium | `build.py:22`, `build_brand.py:27` | **no** (`menu/README.md:17` mentions it in prose only) |
| `rsvg-convert` | `roguelite_art.py:48`, `roguelite_expansion.py` | **no** (`tools/roguelite/README.md:164` prose only) |
| ImageMagick | `effects_assets.py:8` docstring | **no** |
| Blender | `tools/roguelite/build_room_kit.py:46` | **no** (prose at `tools/roguelite/README.md:165`) |
| `melee/pc/tools/png2gx.py` | gx conversion for both out_roguelite and the expansion pack | tracked in the fork; **commit not pinned here** |

`PENDING` markers, all undeterminable without running anything:
- the exact `melee` `pc-port` commit the shipped `room-kit` was exported from (C3);
- the Blender version used, which determines whether a re-export is byte-identical (`PENDING`);
- the pip command that created `_build/roguelite-art-venv` (C4);
- whether `out_effects_study`'s "two consecutive builds produced identical texture hashes" claim
  still holds on a different numpy/rsvg-convert build (`PENDING` — not re-run, per read-only scope).

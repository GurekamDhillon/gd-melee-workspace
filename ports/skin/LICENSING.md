# Licensing checklist for the skin tool

This is an engineering compliance checklist, not legal advice. Anything marked **uncertain** needs a human decision
or a check by someone qualified before a public release. Facts were checked on 2026-11-11 from the repositories'
LICENSE files at the commits given.

## Components

| Component | Source, commit | How the tool uses it | Licence (from the repo) | Obligations |
|---|---|---|---|---|
| Our code: `ports/skin/*.py`, `costumebuild/` (C#), `test_synthetic.py`, `frontdoor.py`, `ui.py`, `autogroups.py`, `brawl_root.py` | this project | — | to be chosen: **GPL-3.0-or-later** recommended (below) | full source, LICENSE, notices |
| HSDLib / HSDRaw | github.com/Ploaj/HSDLib, 6d45b7f4dbb0f1596deab1eb5760f78f2f715eb5 | `costumebuild` (and any future `mexcostume`) links it as a project reference | **MIT** (Copyright (c) 2021 Ploaj) | keep its copyright and licence text in the release. It already contains the m-ex data structures (`HSDRaw.MEX` namespace: `MEX_Data`, `MEX_FighterData`, `MEX_CostumeFileSymbolTable`, `MEX_CostumeIDs`, `MEX_CostumeRuntimePointers`, `MEX_Stock`, `MEX_mexSelectChr` and others), all under that MIT licence |
| BrawlLib (inside BrawlCrate) | github.com/soopercool101/BrawlCrate, a4c1ee3385010d5c64a88df9c56267c61f213321 | `model_export.exe` and `brawl_matdump.exe` (Brawl model reader, ours) link `BrawlLib.dll` | **LGPL-3.0**: the repository root LICENSE is the GNU LGPL v3 text; `BrawlLib/` has no licence file of its own | ship the LGPL text; ship (or offer) the corresponding BrawlLib source for the exact DLL; allow users to replace the DLL. **Uncertain:** the `BrawlLib.dll` copied into `ports/halberd/model/tools/` and `experiment/brawl-kirby/tools/model/` is a prebuilt binary of unrecorded version. A release must build BrawlLib from a recorded commit instead. **Uncertain:** whether older files carry BrawlBox-era headers with other terms; not audited file by file |
| `BrawlLib.dll`'s bundled dependencies (OpenTK.dll, System.*.dll next to it) | prebuilt, unrecorded | loaded by the reader | OpenTK: MIT; System.* (.NET runtime packages): MIT. **Uncertain:** these exact binaries' provenance is not recorded | prefer restoring them from NuGet at build time over shipping copies |
| `model_export.cs`, `brawl_matdump.cs`, the Halberd helpers in `ports/halberd/model/tools/` | this project; git author "GD" (the owner) | our code | the project's own code | they use BrawlLib's API but copy no BrawlLib source (checked by reading the headers and imports) |
| `tools/mex_port/mex_hsd.py` | this project | HSD archive reader imported by `skin.py`, `jointdiff.py`, `coverage.py` | the project's own code. **Uncertain:** whether it was written from HSDLib or m-ex sources; its git history should be checked before it moves to the new repo | — |
| PySide6 (Qt for Python) 6.11.1 | pip | imported by `ui.py` / `frontdoor.py` | LGPL-3.0 (or GPL-2.0/GPL-3.0, or commercial) | using it as an installed, unmodified dynamic library is allowed. Do not ship a frozen bundle without providing the LGPL relinking terms; simplest is to require `pip install PySide6` |
| NumPy 2.4.4 | pip | imported by `skin.py`, `autogroups.py`, `ui.py`, tests | BSD-3-Clause | keep its notice if bundled |
| Pillow | pip | **not imported** by `ports/skin` | (MIT-CMU / HPND) | none unless added |
| Python standard library | — | runtime | PSF | none |
| .NET 8 runtime / SDK | user-installed | runs the C# helpers | MIT | none if not bundled |
| DolphinTool (`unpack_disc.py` drives it) | user-installed Dolphin | separate process; **we ship nothing of it** | GPL-2.0-or-later | none (it is not distributed with the tool); document it as a user-supplied prerequisite |
| m-ex, mexTool, MexManager / mexLib | github.com/akaneia/m-ex c9f25da0, github.com/akaneia/mexTool 30ec8653, github.com/Ploaj/MexManager aecc921d | **must not be used**: no LICENSE file in any of them, so all rights are reserved | none granted | nothing from them may be linked, copied or shipped; see "Must not be in a release" |
| Game data (Melee, Brawl) | the user's own discs | read at run time | Nintendo's copyright | never shipped |

## Which licence for our code

**GPL-3.0-or-later.** BrawlLib is LGPL-3.0. The LGPL-3.0 is compatible with GPL-3.0 but not with GPL-2.0-only, so a
combined work that links BrawlLib cannot be GPL-2.0-only. MIT (HSDLib, OpenTK), BSD (NumPy) and LGPL-3.0 (PySide6)
are all compatible with GPL-3.0. GPL-2.0-or-later would also allow a GPL-3.0 combination, but stating 3.0-or-later
says plainly what the combined work is. **Uncertain:** if a future dependency is GPL-2.0-only, this choice blocks it.

## A compliant release must contain

1. `LICENSE`: the GPL-3.0 text, and a header or `COPYING` statement in our sources ("GPL-3.0-or-later", copyright owner).
2. `THIRD_PARTY_NOTICES`: the HSDLib MIT notice, the BrawlLib LGPL-3.0 text and source pointer (exact commit), the OpenTK and .NET package MIT notices if any binaries are shipped, the NumPy BSD notice if bundled, and the PySide6 LGPL note.
3. Complete corresponding source for every binary we distribute:
   - `costumebuild`, `model_export` and `brawl_matdump`;
   - BrawlLib at the commit we build (or a written offer per LGPL §4);
   - the `.csproj` files and build scripts (`dotnet build -c Release` steps) needed to rebuild them.
4. How users rebuild and replace: build commands, and how to substitute their own `BrawlLib.dll` (LGPL requirement).
5. The test suite (synthetic data only) and the docs.

## Must NOT be in a release

- Anything from m-ex, mexTool or MexManager/mexLib: code, ported code, binaries, generated tables, assets.
- The `mexcostume` draft (moved to `_build/mex-spec/local-mexcostume-not-clean/`): it was written after reading mexLib, so it is not a clean-room implementation even though it links only HSDLib. Keep it as a local test oracle.
- Any disc-derived file: models, textures, costumes, `.pac`/`.pcs`, `.dat`, role tables or templates generated from the discs. **Uncertain:** the `maps/*.bones.json` and `maps/*.roles.json` files hold only bone/joint names, indices and counts read from the discs. Names and counts are facts, but whether to ship them is a decision for the owner. The safe default is to have users generate them (`make_templates.py`, `autogroups.py tables`).
- Prebuilt third-party binaries of unknown provenance (the copied `BrawlLib.dll`, `OpenTK.dll`, `System.*.dll`).
- Screenshots that show game models (the `docs/*.png` in this folder show only the synthetic model and are fine).

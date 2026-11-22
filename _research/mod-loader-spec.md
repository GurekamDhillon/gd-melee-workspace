# Endgame mod loader: spec draft (v0, 2026-11-22)

Status: this is a draft for review. The code-execution design (section 7) is **OPEN for sc00p**: this spec lays out the options and does not choose one.
Sources were read at these commits: m-ex `91ac74d`, melee-unlocked `aaeccff`, HSDLib `0ca3980`, rigswap `5152589` and ssbmNucleus `18f17ae`.
Links use the form `github.com/ssbmNucleus/<repo>/blob/<sha>/...#L<n>`. Our own sources are the workspace docs and the `worktrees/slippimenu`
checkout, which was on branch `port/rankedrow` when read. No code was copied from any repo.

## 1. Goals

1. **One loader** that takes Geno defines and m-ex mods in any packaging: a compiled disc or ISO overlay, an unpacked folder, a zip, or a MexManager package.
2. **Several backends for each code piece.** These are an interpreter fallback, AOT-converted code (wasm or native), a conversion cached at launch, and hand-ported overrides that people can turn on piece by piece.
3. **A content-hash conversion cache.** Each conversion is keyed by a hash of its input bytes plus the converter version, never by file name.
4. **Hot reload** for unpacked folders, offline and in the LAB only.
5. **A content fingerprint** that both netplay peers check and that is embedded in the `.slp`.
6. **A per-piece differential conformance corpus.** Every code piece has a recorded reference behaviour, and every backend is tested against it.
7. **Compatibility reports** for each mod and each piece: what runs, which backend runs it, and what is missing.
8. **Load order, conflicts and dependencies** that are deterministic and explainable. A later mod never silently wins over gameplay content.

Not goals for v1: authoring tools, re-hosting anyone's content, and ranked play with mods (Hero's rule is that mods never enter Unranked).

## 2. Inputs

| # | Input | What it is | Defined at |
|---|---|---|---|
| I1 | **m-ex disc or extracted dir** (ACE, Akaneia, Nucleus builds) | An ISO or FST dir with `MxDt.dat` (one public symbol, `mexData`), a patched DOL, `codes.gct` and the Pl/Gr/It `.dat` files | MxDt root layout: HSDLib [`MEX/MEX_Data.cs#L8-L38`](https://github.com/ssbmNucleus/HSDLib/blob/0ca3980/HSDRaw/MEX/MEX_Data.cs#L8). Compiler: m-ex [`mexLib/MxDtCompiler.cs#L197`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/MxDtCompiler.cs#L197). Path that adopts an existing build: [`MexWorkspace.cs#L199-L209`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/MexWorkspace.cs#L199) |
| I2 | **`ftFunction` / `grFunction` / `itFunction` code blobs** | Relocatable PPC code inside a Pl or Gr `.dat`. Each holds the code, an instruction-reloc table, a function-reloc table of `{ReplaceThis, ReplaceWith}` pairs, the code size and a debug table. `itFunction` is a count followed by an array of the same header | m-ex [`HsdObjects/HSDFunction.cs#L5-L57`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/HsdObjects/HSDFunction.cs#L5). Ours: `_research/mex-ppc-interpreter.md` §1 and `tools/mex-import/src/mexfn.rs#L1` |
| I3 | **MxDt function tables** | Each fighter has 46 callback slots (OnLoad, OnRespawn, MoveLogic, SpecialN and so on). There is also a Kirby function table, a stage function table, and embedded MoveLogic, MapGOBJ and moving-collision arrays | m-ex [`Types/MexFighterFunctions.cs#L14-L80`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexFighterFunctions.cs#L14) and [`Types/MexStage.cs#L91-L109`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexStage.cs#L91). Ours: the header of `rust/melee_engine/src/mex_host.rs` |
| I4 | **MexManager fighter package (zip)** | `fighter.json`, the fighter's files, CSS and stock assets (`icon.png` and others), `sound.zip` (holding `group.json`, `scripts.sem`, `scripts.json` and the `.ssm`), one `<costume>.zip` per costume, and ending media | Writer: [`Types/MexFighter.cs#L625-L670`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexFighter.cs#L625). Reader: [`#L674-L795`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexFighter.cs#L674). Sound: [`Types/MexSoundGroup.cs#L287-L315`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexSoundGroup.cs#L287). Assets: [`Types/MexFighterAssets.cs#L64-L73`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexFighterAssets.cs#L64) |
| I5 | **MexManager stage package (zip)** | `stage.json`, the stage `.dat` files and `sound.zip` | [`Types/MexStage.cs#L339-L465`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexStage.cs#L339) |
| I6 | **Classic MexTK `fighter.yml` / `stage.yml` packages** | Older packages. The fork only keeps compatibility for their embedded MoveLogic and MapGOBJ arrays and for the `iASACallBack` spelling | Comments at [`MexFighterFunctions.cs#L16-L43`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexFighterFunctions.cs#L16) and [`MexStage.cs#L100-L103`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexStage.cs#L100). **The fork has no yml parser**, so we need our own reader or a converter |
| I7 | **MexManager project dir** | `data/mex.json`, `css.json`, `sss.json`, `series.json`, `music.json`, `scene.json`, plus numbered JSON files per fighter | [`MexProject.cs#L445-L639`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/MexProject.cs#L445) |
| I8 | **Gecko codes** (`codes.gct`, INI; types C2, 04 and others) | The m-ex main code plus user codes | [`Utilties/CodeLoader.cs#L15-L141`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Utilties/CodeLoader.cs#L15). Used-address and conflict check: [`Types/MexCode.cs#L148`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexCode.cs#L148) and [`MexCodeBase.cs#L43`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Types/MexCodeBase.cs#L43) |
| I9 | **DAS stage variants** | `<Gr>_00..NN.dat` plus a loader dat | [`Installer/DASInstaller.cs#L33-L135`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/mexLib/Installer/DASInstaller.cs#L33) |
| I10 | **Grafted roots** | A `.dat` with an `ftFunction` root copied in from another file (`mexcli copy-root`) | [`MexCLI/Commands/CopyRootCommand.cs#L6`](https://github.com/ssbmNucleus/m-ex/blob/91ac74d/MexCLI/Commands/CopyRootCommand.cs#L6) |
| I11 | **Geno** | `<mods>/<id>/mod.json` and `geno.json` (v5 to v5.5), words files, `fx/<name>.gfx.json` and article models | `docs/specs/geno-v5.md` §3 (L53-71) and the schema at `docs/specs/geno-v5.schema.json` |
| I12 | **mod-c-v1 code mods** | A `.wasm` or native object with a `GDMD` manifest, using hooks from `hooks-v1.tsv` | `docs/specs/mod-c-v1.md` §7 (L175-203) and `docs/specs/gdmod.h`. Host: `rust/melee_modhost/src/lib.rs#L1-L30` |
| I13 | **Loose-file and Nucleus post overlays** | `mods/<id>/{mod.json, files/<disc path>}`, plus Nucleus posts (costume, stage skin, effect, menu, audio, GD mod zip) | Ours: `rust/melee/src/nucleus/install.rs#L1-L18`. Hero's equivalent is `--mod-iso/--mod-dir/--mod-gci`, in melee-unlocked [`docs/native-mod-imports.md`](https://github.com/ssbmNucleus/melee-unlocked/blob/aaeccff/docs/native-mod-imports.md) |
| I14 | **xdelta bundles (`.ssbm`)** | Nucleus's "one-click xdelta patches + texture packs" | ssbmNucleus [`README.md#L54-L55`](https://github.com/ssbmNucleus/ssbmNucleus/blob/18f17ae/README.md#L54). Apply the patch to the user's own disc, then treat the result as I1 |

Container rule: ingest first unwraps every input into a **file tree**. An ISO becomes an FST diff against the clean disc, a zip becomes a tree, and an xdelta becomes a patched disc and then an FST diff. Every stage after ingest sees only trees.

## 3. Canonical internal representation (CIR)

There is one `ModSet` per launch. Each `Mod` normalizes into five kinds of record. Every record is content-addressed by the SHA-256 of its canonical bytes.

| Record | Contents | Notes |
|---|---|---|
| **Asset** | Disc path, hash of the bytes, kind (fighter, costume, stage, item, menu, sound, music, effect or model), and which mod declared it | HSD archives are kept as bytes and parsed lazily. Identity is by content, never by filename; the Nucleus install already works this way |
| **DataTable** | Typed rows. A fighter slot has internal and external ids, Pl code, costumes, sound bank, Kirby rows, effects and items. There are also stage slots, CSS/SSS layout, music and playlists, and scenes | Normalized from MxDt (I1), fighter.json and stage.json (I4, I5), yml (I6) and Geno attributes (I11). Retail rows 0 to 26 are implicit |
| **CodePiece** | One callable unit: its owner (fighter, stage, item or global), its source form (`ppc-blob` plus reloc entry, `gecko`, `wasm`, `native` or `geno-script`), its entry offset and its source hash | A blob is split into pieces by the entries of its function-reloc table: one piece per overridden slot or hooked address |
| **HookBinding** | A (target, piece) pair. The target is one of: a **slot** `(table, kind, slot#)` (Category 1 in `mex-tier-c-hooks.md` §2); a **func-address hook** (top bit set in `ReplaceThis`), re-expressed as a named native hook point; a mod-c `hooks-v1` row; or a Geno hook number | Within one mod, the last write wins per `(table, kind, slot)`, as in m-ex, which does no chaining. Between *different mods* the same overlap is a conflict (§4.3) |
| **Meta** | Id, name, version, author, licence, source URL, packaging, requires/conflicts/after, declared features and the required engine ABI | Comes from `mod.json` or the MexManager JSON. For a bare disc it is synthesized, with the id set to the hash |

The CIR can be serialized as CBOR or JSON, so a resolved ModSet can be cached and compared between peers.

## 4. Pipeline

```
ingest -> normalize -> resolve -> convert/cache -> bind -> run      (+ hot reload loop)
```

### 4.1 Ingest
Detect the packaging by content: ISO magic, zip, xdelta, or a folder holding `mod.json`, `fighter.json`, `stage.json`, `MxDt.dat`, `geno.json` or `*.wasm`. Unwrap it to a tree. For ISO overlays, diff against the clean disc and keep only changed or added files, as Hero does. Apply the size, path and charset limits from Geno §3 and mod-c §7, and refuse `..`, absolute paths and executables.

### 4.2 Normalize
Parse every recognized file into CIR records. For m-ex content:
- Read MxDt with the `mex_host.rs` readers.
- Split each `ftFunction`, `grFunction` and `itFunction` into pieces (mex-import `mexfn.rs`).
- Turn MoveLogic arrays into slot bindings.

Unknown files stay as Assets. The output is a CIR per mod plus a **normalize report** listing unknown symbols, blobs nothing references and unsupported Gecko types.

### 4.3 Resolve (order, conflicts, deps)
- **Order**: Geno's rule, generalized. Sort bytewise by mod id, then run a stable topological pass for `after` and `requires`. The profile order is part of the layout (Geno §3), so readers on both peers must sort the same way.
- **Dependencies**: `requires: [{id, version range}]`. If a requirement is missing, refuse the mod that needs it and report why.
- **Conflicts**, by record type:
  - Cosmetic Asset overlays: the later mod in the order wins, and the overlap is reported. Hero's loader and our Nucleus install both work this way.
  - DataTable slots or HookBindings from **two mods** that hit the same `(table, kind, slot)` or the same func-address: refuse both and report it (Geno's "neither applies" rule). Within one mod, the last write wins (m-ex semantics).
  - Gecko codes that patch overlapping addresses: detect them with the m-ex used-address check (I8).
- **Slot assignment**: map m-ex internal and external ids to our dense slots by Pl file name, not by index. Hero matches by file name too (`akaneia/INTEGRATION.md`).

### 4.4 Convert / cache
Each CodePiece gets its backend (§7) from a **backend preference list**, tried in this order:
1. a hand-ported override, if the user turned it on;
2. a cached conversion;
3. an AOT conversion shipped with the mod;
4. a conversion made at launch;
5. the interpreter.

The cache key is `sha256(piece bytes, reloc context, bridge table version, converter version, target)`. The cache dir is shared across mods. Entries never change once written, and old ones are evicted by LRU. A conversion that fails its conformance rows (§6) is not used.

### 4.5 Bind
Binding runs these steps:
- write bindings into the engine tables after vanilla init, through the Tier C API (`register(event, kind, fn)`);
- allocate guest regions per mod (the memory model in `mex_guest.rs`);
- register mod-c hooks;
- mount Assets into the DVD overlay.

Binding also produces the **fingerprint** (§5).

### 4.6 Run
The engine calls every bound piece through one dispatch shape, whatever its backend. All backend state lives inside the rollback snapshot. That is already true today for the wasmi host and for `mex_guest.rs`.

### 4.7 Hot reload (unpacked folders only)
Watch the mod folders. When one changes:
1. Re-ingest and normalize that mod.
2. Re-resolve the whole set.
3. Convert only the pieces whose hash changed.
4. Rebind at a frame boundary.

If the layout changes (slot count, profile index or article kinds), refuse with a message, as Geno's LAB rule does. Hot reload never runs online, and never runs while recording an `.slp` that is meant to replay.

## 5. Fingerprint, netplay and `.slp`

- **Hashes.**
  - **Piece hash**: sha256 of the piece's canonical bytes.
  - **Mod hash**: a hash over the mod's sorted record hashes and its meta version.
  - **Set fingerprint**: a hash over the engine build id, the resolved order, every binding as `(target, piece hash, backend class)`, every gameplay Asset hash and the DataTable rows.
- **Cosmetic vs gameplay split.** Cosmetic-only Assets (skins, CSPs, menus, music) go into a separate *cosmetic fingerprint*, and peers may differ on it. Hero's cosmetic importer has its own online validation, and we do the same. The gameplay fingerprint must match exactly.
- **Backend class.** Interpreter, AOT and hand-port must give **bit-identical** game state. A hand-port that has not been proven equal on the corpus counts as a different gameplay identity and goes into the fingerprint.
- **Netplay.** Peers exchange the set fingerprint plus identities for each fighter and stage. This extends today's `gw_mexid` and `melee_net` lobby identities; Geno ids fold into the target fighter's identity as in geno-v5 §5. On a mismatch, that fighter or stage is greyed out. If the whole set differs for a pack both players are required to run, the match is refused. Mods never enter Unranked or Ranked.
- **`.slp`.** Write a mod block into the game-start metadata. It holds the set fingerprint, the ordered list of `(mod id, version, mod hash, source URL)` and the identities per slot. A replay player refuses or warns when its own resolved set differs. Slippi Dolphin should ignore the unknown metadata keys; check that before relying on it.

## 6. Conformance corpus

- **Unit**: one CodePiece.
- **Row**: (piece hash, entry state snapshot, inputs, frame count) maps to the expected outputs. Those are the game-state hash for each frame, a digest of the memory the piece touched, and the calls it made out through the bridge, in order.
- **Oracle**: Dolphin running the real m-ex disc, captured with the existing hash-oracle tooling. Agent runs use no adapter and 3% volume. For Geno and mod-c pieces, the oracle is the C build or the reference interpreter.
- **Differential**: every backend (interpreter, AOT-wasm, AOT-native, cached, hand-port) runs the same rows. Any difference is a failure, reported with the first frame and field that diverge. A hand-port can be selected for netplay only after it passes every row of the piece it replaces.
- **Coverage**: rows are generated for each slot named in the function-reloc table, so coverage follows the content (as `mex-ppc-interpreter.md` §1 notes). Each fighter also gets scripted scenarios: every special, on the ground and in the air, and Kirby's copy.
- **Storage**: `corpus/<piece-hash>/rows.*`, tagged by oracle. No disc bytes are stored, only hashes and our own state dumps.

## 7. OPEN for sc00p: execution backends

The open questions are how foreign PPC code runs, how it reaches engine functions and globals (the **address bridge**), and whether converted code should be wasm or native. The options:

| Option | What | Pros | Cons |
|---|---|---|---|
| A. **PPC interpreter**. This already exists: `tools/mex-import` has `ppc::Machine` and `remap::GuestSpace`, and `melee_engine/src/mex_guest.rs` uses them | Run the blob bytes as they are | Works for any blob from day one. Exact Gekko float mode is already in. Easy to snapshot. Self-modifying patches just work | Speed, since a machine is made per call. A call that is not bridged ends the callback. The bridge (`mex_bridge.rs`, about 15k generated lines) is the real cost, and every option shares it |
| B. **AOT PPC to native, one build per mod set**. This is Hero's Static Recomp approach | Translate blobs ahead of time to C or Rust and compile them into the exe | Fastest. Hero proved it on Akaneia ("matching Direct builds") | One exe per mod set, so users cannot add mods without a toolchain. His recomp "cannot execute instructions the guest writes into RAM" ([`port/recomp/gecko.py#L1-L13`](https://github.com/ssbmNucleus/melee-unlocked/blob/aaeccff/port/recomp/gecko.py#L1)) |
| C. **AOT PPC to wasm** | Translate blobs to wasm modules and run them in the existing deterministic wasmi host | Sandboxed, portable, can ship with the mod, easy to snapshot, reuses the mod-c host | wasmi is also an interpreter, so the speed gain over A is unclear unless we add a compiling wasm runtime, and that runtime must stay deterministic. The guest memory model must map into linear memory |
| D. **Convert at launch and cache** (B or C, run on the user's machine and keyed as in §4.4) | Convert on first launch and store the result | No exe per mod. The first launch pays the cost and later launches are free | The shipped build needs a converter. Native output means a code generator or JIT inside the exe (W^X, antivirus false positives) |
| E. **Hand-ported overrides**. This is Hero's main path: native C per fighter, and "No PowerPC is run or translated" ([`sourceport/game/akaneia/INTEGRATION.md#L7`](https://github.com/ssbmNucleus/melee-unlocked/blob/aaeccff/sourceport/game/akaneia/INTEGRATION.md#L7)). He has 7 Akaneia fighters plus 24 ACE fighters in `sourceport/game/ace/` | Native replacements per piece, turned on one by one | Fastest, debuggable, readable | Does not scale to arbitrary mods. Hero's code is GPL, so we cannot pull it in without licence care. Each port must pass the corpus to count as equal for netplay |

| F. **Compile the fighter's MexTK C source natively, as a plugin** (Hero's `nucleus-compat` branch, "mexft", Nov 22) | When a port's C source is available, compile it for the native engine and load it as a fighter plugin | Native speed with no per-fighter hand port. The fighter's own logic is unchanged, so it scales to every port whose C exists. Nucleus can build plugins from a kit | Only works when the source is available; many blobs ship without it. Needs a stable native layout ABI. Source licences are unclear (§7.1) |

### 7.1 Option F in detail: Hero's "mexft" (melee-unlocked branch `nucleus-compat`, commits `0d0d36a`..`846cdfa`)

Read only, and no code copied. Paths are under `sourceport/game/mexft/` and `tools/mexft/` on that branch.

- **Prepare step** (`tools/mexft/mexft_prepare.py`). It takes a port's MexTK C and leaves the fighter's own code unedited:
  - points its `mex.h` include at a native MexTK header set (`mexft/mex.h`; MexTK's headers are vendored under `tools/mexft/m-ex/include`);
  - turns each raw console function address into the decomp function at that address;
  - matches m-ex exports by name against `ftFunction.txt` / `itFunction.txt`.
  The fighter becomes one module and each article (`item_<n>.c`) another, as on the console, plus a generated `MuAkFighter` descriptor. A slot the C does not export falls back to the m-ex default (the donor's function). A raw address that is not the start of a function, or an export with no native slot, fails the build by name.
- **Plugin ABI** (`mexft_plugin.h`):
  - Format: one relocatable COFF x86-64 object, file extension `.mufighter`, magic "MUFT", version 2.
  - Exported record: `{magic, version, abi[16], fighters[], count}`. Each entry is a descriptor plus the fighter's m-ex name.
  - `abi` is a hash of the layouts the code was compiled against (MexTK headers, adapter, descriptor header; `mexft_abi.py`). The game refuses a plugin whose ABI differs.
  - Earlier commit (`3c55300`): plugins were pre-linked against one build's addresses.
  - Latest commit (`846cdfa`): the game links the object itself at load time. It places the sections in the low 4 GB beside the image and resolves game symbols by name from `melee_game.syms`, which carries the library's build id. Code is left read-only. So a plugin is tied to the layouts, not to one exe.
- **Discovery and loading** (`mexft_plugins.c`):
  - Where: every file in `MELEE_FIGHTER_PLUGINS` or in `fighters/` beside the game library.
  - When: on the first registry lookup.
  - Matching: by the MxDt fighter name, case-insensitive, in any slot; the file name is the fallback. This is the same name-not-index rule as our §4.3.
  - Limits: a cap on the number of plugins. Windows only for now.
  - Build: `MEXFT_PLUGINS=ALL|names` builds plugins. `mexft_kit.py` packs headers, symbol lists and flags into a kit, so a tool such as Nucleus can build a plugin with only MinGW GCC (`mexft_build.py`).
- **`mexft.txt`**: a tiny manifest per fighter with the fighter's display `name` and its m-ex `file` (for example a `PlMs_0NN.dat` donor file).
- **`native.edits`**: present only for bcman, loxodont and ranno. These are commented unified-diff-style hunks against `code/fighter.c`. Each fixes a spot where the C assumed console layout, such as a pointer stored in a 32-bit int, a raw byte/bit offset into the fighter struct, or a raw console field offset. Each hunk is replaced with the decomp's named native field. This is the "hand edit" escape hatch on top of an otherwise unchanged source.
- **Determinism and fingerprint**:
  - Each plugin's writable variables are registered as rollback snapshot ranges.
  - Each fighter gets a digest: FNV-1a over the plugin's file name and contents. The digest is folded into the online state checksum (`shim/mu_online.c`), so both peers must load the same plugin file.
  - No proof of equality with the console/Dolphin is stated beyond replay and p2p tests.
  - For our spec: this digest is the "backend class" identity of §5. A plugin is a different gameplay identity from the interpreted blob until our conformance corpus shows they match.
- **The 15 fighters** ("All Ports Test 2"): bcman, byleth, cloud, duckhunt, fishbunjin, greninja, ike, incineroar, ittle, jenny, loxodont, ranno, shulk, wolf, zetterburn. Each has `code/fighter.c` (+ `item_N.c`) "as Nucleus built it" and `mexft.txt`.
- **Source and licence status**:
  - The fighter `.c` files carry **no licence header, copyright line or author credit**.
  - The commit names Nucleus as where they came from, not who wrote them. They are almost certainly the MexTK ports' original authors' work.
  - The vendored MexTK headers (`tools/mexft/m-ex/`) also have no stated licence.
  - Only Hero's own glue and tools are tagged GPL-2.0-or-later.
  - So we must **not** copy, redistribute or ship those fighter sources or the MexTK headers. We may only reproduce the *approach*, and our own plugin source must be the user's, obtained from its authors.
  - Also: the branch's commits are co-authored by "Claude Fable 5.2".
- **Also on the branch** (`8c54151`): when a build renames costumes, the game serves costumes from the disc's m-ex costume table. A build that only removes costumes is also served from that table. Our MxDt reader should behave the same (§8).

What it changes for our plan:
- Add `native-c` as a CodePiece source form, and "plugin" as a backend between hand-port and conversion in the §4.4 preference list.
- Treat the plugin ABI hash plus the file digest as cache and fingerprint inputs.
- The conformance corpus is how a plugin earns equality with the blob.

Questions that cut across all options, for sc00p:
- How fine should the bridge be: one entry per vanilla function, or one per field access?
- How do func-address hooks (top-bit `ReplaceThis`) become named hook points?
- Do pieces share one guest heap, or does each mod get its own?
- What float exactness rules must converted code follow (fused multiply-add, `frsp`, paired single)?

### 7.2 Where source comes from (and where it doesn't)
- An m-ex ISO, or one unpacked with the m-ex tool, holds only **compiled** fighter code: the `ftFunction` / `itFunction` blobs inside each `.dat`. The C source never goes onto the disc.
- So unpacking gives the interpreter and conversion backends (A–E) their input, but never option F's input.
- Option F needs the author's published MexTK C source.
- From a compiled blob, the only ways to C are a decompiler's rough output, or a decomp-style reconstruction by hand. Either way the result is our own work, not the author's source, and it must pass the conformance corpus like a hand-port.
- Expectation: most community fighters are compiled-only, so the interpreter or conversion stays the universal path. Option F is the fast path for fighters whose source is published.

## 8. Compatibility with Nucleus / m-ex output (must match byte for byte)

| Must | Why |
|---|---|
| Read any MxDt that MexManager or mexcli compiles, including the Nucleus additions: fighter duplication, DAS, sub-characters and team colours, the SSS L/R page fix, and embedded MoveLogic | Nucleus builds its discs with mexcli, and we read those discs |
| Relocate and split `ftFunction`, `grFunction` and `itFunction` exactly as m-ex's `Init ftFunction` does (Reloc, then Overload) | The same piece bytes then give the same piece hash on every install |
| Accept fighter and stage package zips exactly as `FromPackage` reads them, including `fighter.json` field names such as `iASACallBack` | Users have libraries of these packages |
| Treat m-ex's `codes.gct` as data the loader understands (C2 hooks, 04 writes) | Its hooks are the engine contract that custom code assumes (`mex-port-triage.md`, Tier C) |
| Produce the same game state as Dolphin on the m-ex disc | Needed for netplay against Slippi Dolphin and for `.slp` parity (the Hero-parity focus) |

We do **not** need to write MxDt or ISOs; Nucleus and mexcli keep that role. An "export to m-ex package" option can come later.

## 9. Buildable now (no backend decision needed)

1. Ingest and container unwrapping (ISO diff, zip, folder, xdelta) into trees.
2. CIR types, and normalizers for MxDt, fighter.json and stage.json, sound.zip, Geno and mod-c manifests. Also a `fighter.yml` reader.
3. The resolver: order, dependencies, conflict rules and slot assignment by Pl name, with a resolve report.
4. Content hashing, the set and cosmetic fingerprints, the `.slp` metadata block, and the lobby exchange (extending the `melee_net` identities).
5. A piece splitter over function-reloc tables, plus the dispatch interface and preference list that do not depend on a backend. Backend A plugs in, as it does today.
6. The conversion-cache store (keys, immutability, eviction), with a converter that does nothing yet.
7. The conformance corpus format and a runner that compares backend A against the Dolphin oracle.
8. The compatibility report, per mod and per piece: what is bound, which backend, and which calls are not bridged. The `MELEE_MEX_REPORT` counters already exist.
9. Hot reload for Geno and loose assets, including the refusal on layout changes.

## 10. Licensing

| Repo | Licence | Use |
|---|---|---|
| ssbmNucleus/m-ex (a fork of MexManager / mexLib; m-ex itself is by akaneia) | **None stated**, upstream or in the fork | Read only. Formats are described from observation and no code is copied. Interoperating with the formats is fine, but the implementation must be our own |
| ssbmNucleus/melee-unlocked (Hero) | GPL-3.0. Some files are GPL-2.0-or-later, for example `ppcleaf/ppc.h` | Read only. Copying its hand-ports or recomp would put GPL-3 obligations on our code. We have Hero's OK to use his repo, but the current direction is to keep ours independent |
| ssbmNucleus/HSDLib (Ploaj) | MIT | Reusable with attribution. It gives a complete HSD archive model and typed `MEX_*` accessors: the MxDt layout, items, Kirby tables, stages, scenes, sounds and the Akaneia extras. Most useful as a layout reference for our Rust readers; a C# side tool could also use it as is |
| ssbmNucleus/rigswap | GPL-3.0 | A tool that puts a 3D model on a fighter's rig. It only outputs costume `.dat`s and is not part of the code pipeline, so its output is treated as plain Assets |
| ssbmNucleus/ssbmNucleus | GPL-3.0 | A mod manager and catalog. It installs skins and stages, builds `.ssbm` xdelta bundles and runs mexcli. Its posts are our inputs I13 and I14 |

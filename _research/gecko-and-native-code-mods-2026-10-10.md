# Gecko codes and a native code-mod interface for GD's Melee (2026-10-10)

Lane `ws/research-gecko`. Question from the owner: "Gecko codes are probably trivial right? <https://github.com/ExpansionPak/ModernGekko>".
Short answer: **no, not in general; a small data-only subset is nearly free, and a function-level hook interface is a real but bounded piece of engine work.**
Nothing here changes the engine. Tooling added: `tools/research/gecko_classify.py` (counts a GCT/INI by code type, target section and hook placement).

Tags: **[R]** read from code/docs (source named), **[M]** measured by a script on the named input, **[I]** inferred, **[K]** known background not re-checked in this lane.
No disc bytes are committed: the note quotes addresses, code-type counts and decomp symbol names only.

## Answer in six lines

1. **[M]** ACE's 1169 Gecko codes: 778 `C2` (insert asm) + 391 `04` (32-bit write). Only **10 of 1169 (0.9%)** write data (`.data`/`.sdata2`); 381 `04` and 749 `C2` land in `.text`. Of the 749 text `C2`s, **29 (3.9%) sit on a function's first instruction, 720 (96%) are mid-function**.
2. **[M]** Slippi's console core INI (one sample, 58 code groups): 33 `04` + 25 `C2`; 6 `04` are data writes (10%), 0 of 21 text `C2`s are at a function entry.
3. **[R]** The port has **no PowerPC text**. Game code is native x86 from the decompiled C; the guest-address -> native table (`gw_mex_bridge.c`) has 18830 function entries, 4158 data-object entries. A code that patches an *instruction* has nothing to patch; a mid-function injected `C2` has no PPC register state to run against (the compiler allocated registers its own way).
4. **[R]** Data writes *are* tractable: the bridge already carries `gw_mex_bridge_guest_data(guest_addr)`, which resolves any address inside a sized global to its real storage in the exe's `.data`. So a `04/02/00` write to a symbol's bytes is "translate address, write big-endian" -- if the native code actually reads that object (see section R1.2 for the pitfalls).
5. **[R]** ModernGekko is **not** a Gecko-code engine and cannot host our port as-is: it is a Dolphin-derived host for **DolRecomp** output, with native-DLL mods written against a PPC `CPUState`. Its hook model (keyed by guest function address; entry/return hooks; replace-function patches) maps onto what our bridge can do at *function granularity*. Licence: GPL-3.0(-or-later); our tree is GPL-2.0 (section R2.5).
6. **[I]** Recommendation: (a) a declarative **data-patch** format (accepts a Gecko `00/02/04/06` subset, with an expected-value check) -- days; (b) **our own** small function-hook interface behind the existing Lua/mod system, not native DLLs -- 1-2 weeks; (c) keep **hand-porting** popular codes as flags (what we do for UCF/ACE). Do not adopt the ModernGekko ABI as the primary interface.

---

## R1. What Gecko code types can work in our port

### R1.1 The architecture facts that decide it

- **[R]** `melee/pc/platform/gw.h`: game TUs are compiled for PowerPC by clang, then rewritten by `gwtool` to x86 with **every memory access byte-swapped**; "pointers are 32-bit and mean the same addresses natively". `gw_runtime.c:87-117`: MEM1 is `VirtualAlloc`ed at **0x80000000** (48 MB), so heap objects (fighters, items, GObjs, loaded .dat files) are at their original-style guest addresses.
- **[R]** `gw_runtime.c:49-52`: "**game globals are not in MEM1** (melee-pc.map puts them at 0x106Fxxxx, in the exe's own data section)". The statics (`.data`, `.sdata`, `.bss`) have guest addresses only on paper; their storage is the exe's.
- **[R]** `tools/mex_port/gen_bridge.py` (generated into `gw_mex_bridge.c`): `gw_mex_bridge_table` (guest -> native, kind 1 function / 0 data object), `gw_mex_bridge_guest_data()` (any guest address inside a sized data object -> native address, "interior pointers resolvable") and `gw_mex_bridge_is_native_data()` (the reverse). Objects without a recorded `size:` in `symbols.txt` are deliberately absent.
- **[R]** The interpreter (`gw_ppc.c/h`, driven from `gw_mex_ftfunction_runtime.c`) runs m-ex's guest PPC blobs and bridges `bl` out to native functions via that table; it is reentrant. It reads/writes guest memory with `gw_r32/gw_w32`, so it can touch MEM1 and (through `guest_data`) the exe's statics.
- **[R]** Function bodies call each other directly (x86 `call`); the table is used only by the interpreter. There is **no dispatch hook** between native functions (contrast: DolRecomp dispatches every guest function through `dispatch(state, address)`, which is where ModernGekko hooks in).
- **[R]** Netplay identity (`gw_netplay.c:2937`): the handshake compares a 64-bit build id = hash of simulation-relevant *sources* (`tools/port/build_id.py`) + a measured *numerics* digest, deliberately **platform-neutral** so a Windows and a Linux build of one commit can play each other. Mod sets are matched by content identity per fighter/stage; "global game data" differing refuses (`gw_mods.h:96-110`, `gw_mexid.h`).
- **[R]** Today's "codes" are hand reimplementations: `_research/slippi-gameplay-codes.md` (UCF 0.84 pieces, Init Player Data, FreezeGlitchFix, WhispyBlowDirFix... each read as PPC and rewritten in C at the decomp site with a `Mex_Enabled`/codeset flag) and `docs/MEX_PORT_STATUS.md` (49 `Mex_Enabled` flags, e.g. `default_4_stocks`, `default_8_minutes`, `default_no_items`).

### R1.2 Class by class

Gecko code types ([K] from the Gecko codehandler spec; not re-fetched, the wiibrew page I tried does not list them): `00/02/04` write 8/16/32-bit; `06` string write; `08` serial write; `20-2E` if-equal/not-equal/greater/less (32/16-bit) with `E0/E2` end-if; `30-3E` counters; `40-4E` loops/jumps/subroutines; `80-8E` register load/store/ops; `C0` execute asm; `C2/C3` insert asm; `C4/C5` insert asm at a "code" address; `C6/C7` branch; `CC` and `D2/D4` pointer/register ops; `F0` end of codes; `F2/F4` ("patch"/conditional asm).

| class | codes | works in the port? | why |
|---|---|---|---|
| **A. data write** `00/02/04/06/08` to `.data/.sdata/.sdata2/.rodata/.bss` | ACE: 10 of 1169 (0.9%). Slippi console INI: 6 of 58 (10%) | **yes, if** the native code reads the object | translate through `guest_data`, write BE. Pitfalls below |
| **B. data write to heap/MEM1** (fighter table, loaded `.dat`, stage data) | ACE: 0 (all 10 are statics) | yes at the right time, **but** the data does not exist at match start | address is only valid after the object is allocated; needs an event ("after stage load") not "match start" |
| **C. instruction overwrite** `04` on `.text` (`li`, `cmpi`, a `bl` retarget, a `nop`) | ACE: **381** (97% of ACE `04`); Slippi INI: 25 of 33 `04` | **no** | no PPC text. Each is a one-line *semantic* change; port it by hand at the source site |
| **D. `C2` at a function entry** | ACE: 29 (3.9% of text `C2`); Slippi INI: 0 | **maybe** | native prologue hook + interpreted payload; entry state is just the ABI args (r3..r10, f1..f8, r1, r2/r13 = guest rtoc/small-data bases), which a thunk can build |
| **E. `C2` at a function's last instruction (return)** | ACE: 0 exact `blr` hits by the symbol-size test | maybe, same mechanism | return values only (r3/f1) |
| **F. `C2`/`C6` mid-function** | ACE: **720 of 749 (96%)**; Slippi INI: 21 of 21 | **no** | payloads read live registers (r27-r31, f-regs) and scratch whatever the original function left; the native compiler assigned none of that. Only a hand port from the decomp site works |
| **G. conditionals / loops / registers** `20-8E` | ACE: 0; Slippi console INI: 0 (toggles are done by the Slippi bootloader instead) | only as a *host-side* rule (apply patch X if toggle Y) | these are the code handler's scripting for *when* to write; our equivalent is the mod system's own conditions |
| **H. m-ex infrastructure caves**: `C2` on `0x803D70xx` (20 codes) and `0x800056xx` (7, over `extab`), 2 outside the DOL | ACE: 29 | n/a | not hooks: m-ex *places code* there (cf. `gw_mex_ftfunction_runtime.c:134,559,2718`, "behaviour of m-ex's own C2 payload"). The port already implements m-ex natively + interprets m-ex's real PPC blobs, so these are covered by the m-ex path, not a Gecko loader |

Numbers behind the table:

- **[M]** `python tools/research/gecko_classify.py --iso "$GW_ISO_ACE" --splits melee/config/GALE01/splits.txt --symbols melee/config/GALE01/symbols.txt`:
  `total codes 1169; by type {'C2': 778, '04': 391}`; `('04','.text') 381, ('04','.data') 9, ('04','.sdata2') 1`; `('C2','.text') 749, ('C2','.data') 20, ('C2','extab') 7, ('C2','outside-dol') 2`; text hook placement `('04','entry(+0)') 5, ('04','mid-function') 376, ('C2','entry(+0)') 29, ('C2','mid-function') 720`; C2 payload size 68104 bytes total, 403 of 778 are two lines (one replaced instruction + the return branch). (Sections come from the decomp's `splits.txt`, function boundaries from `symbols.txt` `size:`.)
- **[M]** ACE's ten data writes, by symbol: `lbHeap_803BA380+0x2C`, `preload_cache_scene+0xC`, `un_803FA258+0`, `@2315` (a `.sdata2` float literal), `gmMainLib_DefaultGameRules+0/+4/+8` (3 words), `gmMainLib_DefaultGamePrefs+0/+0x10/+0x18` (3 words). **[I]** The six `gmMainLib_Default*` writes are the same setting family as the already-hand-ported `Mex_Enabled` flags `default_4_stocks/8_minutes/no_items/stock_mode/tournament_stages`, i.e. the one place a data-patch layer would have applied to ACE is already covered natively.
- **[M]** Slippi console core, `slippi-ssbm-asm/Output/Console/GALE01r2.ini` (shallow clone of the public source into the scratchpad; source text only, no binaries): the single `[Gecko]` group (58 line groups) = 33 `04` (25 `.text`, 6 `.data`, 1 `extab`, 1 outside the DOL) + 25 `C2` (21 `.text`, 4 `extab`); entry-point C2s: 0. Its content is the *console* core (boot-to-CSS, unlock all, the Slippi recorder). Note this INI is not the gameplay codeset (UCF etc. are separate `g_*.bin`/`.txt`, not measured: owed).
- **[R]** Slippi's source is 312 `.asm` files, 310 with an `# Address:` injection header, 83 with a register-saving `backup` prologue (full injections), 54 tagged `affects-gameplay` (`slippi-ssbm-asm`, `Makefile` builds with JLaferri/gecko). `_research/slippi-gameplay-codes.md` records 40 distinct gameplay codes of which the port implements ~16 by hand, and that the unimplemented ones are mostly *online-only timing/DVD-streaming* workarounds that do not apply to a native port.
- **[I]** For the wider community set (20XX/Melee Code Manager, UnclePunch's training-mode codes, Akaneia's other packs) I could not measure here: no corpus is local and I did not download GCT binaries. The two measured sets (a 1169-code mod pack, a 58-group recorder core) agree on shape: **~90-98% of Gecko code lines are instruction-level patches or mid-function injections** that only a hand port can express; the data-write share is 1-10%. `gecko_classify.py --gct/--ini` will give the number for any set the owner wants measured.

**Pitfalls for class A (so "trivial" is not the right word).**

1. **[R]** Objects with no `size:` in `symbols.txt` are absent from the guest-data table (`gen_bridge.py`: "deliberately absent"). 10 of 10 ACE data writes hit sized objects (`gecko_classify.py`: `data writes vs symbol table: {'.data': in-sized-object 9, '.sdata2': in-sized-object 1}`), so the table is adequate for this sample.
2. **[I]** The compiler may not read the object at all: a `.sdata2` float literal such as `@2315` is a pooled literal that clang may have folded into an immediate, kept in the exe's read-only `.rdata`, or merged. A write that "lands" can be a no-op or fault (read-only page). Each accepted address needs a one-line proof (a Lua/native read-back plus a behaviour check); this is what the compatibility list in R3(a) records.
3. **[I]** Where sections differ from the original (alignment, string/literal pooling, `.sdata` vs `.data` placement), only addresses that the link map ties to a *named, sized* symbol are safe; "address + offset inside a struct" is exactly what `guest_data` supports, a write spanning two objects is not.
4. **[I]** Timing: statics are initialised from the binary at process start; most are then *copied* to heap state at scene init (e.g. Default prefs -> save-file state). A patch must be applied before the copier runs (boot), and "restore to vanilla on unmount" means keeping the original bytes.
5. **[R]** Determinism: a data patch is constant for the run, so it cannot itself desync rollback; it must be identical on both peers (netplay, R3).

### R1.3 Could injected PPC run in our interpreter at a hook?

**[I]** Yes at a *function boundary*, no inside a function.

- Entry hook (class D): put an x86 detour on the native function's first bytes (runtime `VirtualProtect`/`mprotect` patch, or a compile-time probe in the function prologue), have the thunk build a `gw_ppc_ctx` from the native args (needs the function's signature; `tools/mex_port/gen_sigs.py` already derives signatures for the bridged subset, `_research/bridge-signatures.md`), run the payload in the interpreter, copy back r3/f1, continue. Reentrant interpreter, BE memory model and the guest-data translation already exist.
- Caveats: (1) **inlining**: the decomp is compiled by clang, which may inline a function the DOL called, so a hook at a DOL function address might not fire at some call sites; fix: compile-flag audit or a `noinline` list for hookable symbols (owed, not measured); (2) the payload's own `lwz rX, off(r13)` to small-data statics resolves through `guest_data` only for sized objects; (3) the native build has no PPC code at the *return* address, so return hooks need the thunk to wrap the call (fine on x86: a trampoline frame).
- Mid-function hooks (96% of ACE's `C2`): no register image exists. A faithful way would be to retarget the original PPC instructions of the *whole function* into the interpreter, i.e. run the function from the DOL bytes instead of the native body. That needs the **disc's PPC text** for that function (the interpreter can run it if the DOL bytes are read at runtime, as the m-ex blobs are), plus the function's call/stack ABI with the native callees (already bridged). This is the one route to real Gecko `C2` compatibility, but it makes that function slower and breaks the "no disc data in the build" convenience only if shipped; reading the DOL at runtime from the user's own ISO is allowed by project rules. **[I]** I would not build it before the hand-port pipeline has been exhausted: it is large (function-granular PPC fallback + per-function native/guest state mirroring) and every mid-function code is a *different* function.

---

## R2. ModernGekko

### R2.1 What it is

- **[R]** Repo `ExpansionPak/ModernGekko`, 81 commits, last push 2026-09-17, default branch `master`, GPL-3.0 (`LICENSE`), README says "A runtime for GameCube/Wii recomps." Source tree: `src/` (audio, gpu, hardware, input, memory, runtime, timing), `include/moderngekko/`, `tools/` (launcher, runner, netplay session/compat, `dol_patch.cpp`), `tests/`, `mod-template/`, `vendor/dolphin` (submodule `ExpansionPak/RecompCore`, itself a fork of `aharonahdoot/RecompCore`, itself Dolphin).
- **[R]** `PROVENANCE.md`: "Dolphin-derived runtime ... StaticRecomp ABI/loader integration"; recompiler is **DolRecomp** (GPLv3, pinned submodule). The runtime loads a DolRecomp-generated **module** exporting `staticrecomp_get_module` (`module_abi.h`, version 3): `dispatch(CPUState*, address)`, code/SMC/chunk ranges, REL modules.
- **[R]** README Hall of Fame lists "Literally God / MrPoloGit - Super Smash Bros. Melee" among supported recomps. **I do not know whether that is related to this project** (our port is not a DolRecomp output); it is a Melee DolRecomp build by a different author, or at least a different pipeline. Worth the owner knowing the name appears.

### R2.2 The mod ABI (`include/moderngekko/mod_abi.h`, `ModManager` in `src/runtime/mod_loader.cpp`)

- Package `<id>.mgm/` containing `mod.dll|.so|.dylib` (or dev file `<id>.mgm.dll`), loaded from `Mods/` beside the exe and `<user-dir>/Mods`; `--mods`, `--no-mods`. Export symbol `moderngekko_get_mod` returns a `ModernGekkoModDesc`.
- Descriptor: `abi_version` (=1), `cpu_abi_version` (=4), `sizeof(CPUState)` (must match), 8-byte `game_id` (e.g. `GALE01`; mismatch rejects), `id`/`version`/`display_name`, dependencies (id, minimum version, optional), **patches** `{u32 address, void fn(CPUState*), flags}` (replace the function at `address`; second patch to the same address is a conflict unless `FORCE`), **hooks** `{address, fn, kind ENTRY|RETURN}`, exports/imports (named `fn(CPUState*)` pointers between mods), events + callbacks, `on_load(host_api)`/`on_unload`. Load order: dependency topological, then package filename.
- Calling convention: **PPC register file by value**. `void fn(CPUState *s)` reads args from `s->gpr[3..10]` (`moderngekko_mod_arg_u32`), returns by writing `gpr[3]` and `pc = lr`; memory via `s->external_read/external_write(state, addr, value, size)` (`moderngekko_mod_read/write`). Floats are in `s->fpr[]`.
- Dispatch semantics (`ModManager::Dispatch`, `mod_loader.cpp:563-602`): called by the generated dispatch at a guest *function address*. Entry hooks run with a `CPUState` copy that is **restored afterwards** (`const CPUState saved = *state; fn(state); *state = saved;` -- observe-only, they cannot change args or results). Return hooks are queued keyed on `(lr, sp)` and run when dispatch next sees that return address with the same stack pointer (also state-restoring). Only a **patch** can change behaviour, by replacing the whole function. There is no mid-function hook. Max 4096 pending return hooks.
- Netplay: README "Netplay fingerprints include every loaded package binary and its filename."
- `tools/dol_patch.cpp` is a separate CSV mechanism (`address,expected,replacement`) for 32-bit word patches of the DOL itself with an expected-value check -- the same idea as a Gecko `04` with a guard, applied before recompilation.

### R2.3 Does it assume a specific recompiler/runtime?

**[R] Yes.** The ABI struct is DolRecomp's `CPUState` (header guard `DOLRECOMP_CPU_H`, "must stay byte-compatible", `tests/cpu_abi_conformance_test.c`), hooks are keyed on addresses that the **DolRecomp-generated** dispatch function visits, the optional **MAP file** input makes DolRecomp emit `DOLRECOMP_SYMBOL_<name>` constants for mods (README + `mod-template/README.md`); without a MAP, literal addresses are used. The runtime itself is Dolphin's CPU/MMU/GX/AX/DSP emulation fronted by recompiled code with a fallback JIT ("yielding fallback jit").

### R2.4 Could our port host that ABI?

**[I]** Partly, as an *adapter*, not by linking ModernGekko:

| ModernGekko concept | what we have | gap |
|---|---|---|
| guest function address key | `gw_mex_bridge_table` (18830 functions, GALE01 addresses) | same address space as the Melee DOL; good fit |
| `CPUState` args | none; native args | thunk must marshal r3..r10 / f1..f8 per function **signature**; signatures exist for the bridged subset only (`gen_sigs.py`), need the whole symbol set from decomp headers |
| entry/return hook | no dispatch between native functions | x86 prologue detour or compile-time probe; inlining caveat |
| patch (replace function) | none (could swap the bridge's native pointer for the interpreter, but native->native calls ignore the table) | detour at the callee body; same mechanism |
| `external_read/write` | `gw_r32/w32` + `guest_data` | trivial |
| native DLL mods | the port has no DLL mod loader | Windows `LoadLibrary`/Linux `dlopen`; per-platform binaries |
| fingerprint of binaries | build-id is cross-platform source hash | **conflict**: DLL hashes differ per OS, so a Windows peer and a Linux peer can never match a mod's fingerprint |
| `CPUState` ABI v4 + `sizeof(CPUState)` | we would have to freeze a copy of that struct | tying our API to a third-party struct |

Existing mods compiled for ModernGekko's Melee recomp would also assume DolRecomp semantics (same function boundaries, same register conventions) -- most would likely work at function level, but I did not obtain any such mod to test (none seen; the repo ships only `mod-template` and test fixtures). **Owed:** a hello-world `.mgm` against our port would settle it; that is an engine change, out of scope.

### R2.5 Licence facts (the owner decides)

- **[R]** ModernGekko: GPL-3.0 per GitHub and `LICENSE`; `PROVENANCE.md` says "GPL-3.0-or-later"; vendored Dolphin parts are mostly GPL-2.0-or-later, "the combined source tree is GPLv3-compatible"; DolRecomp GPLv3.
- **[R]** Our trees: workspace `LICENSE` and `melee/pc/LICENSE` are the GNU **GPL version 2** text. `melee/pc/DEPENDENCIES.md` already carries GPL-2.0-or-later-derived code (Dolphin float tables, Slippi's wire codec), MIT/BSD/Apache dependencies (Aurora, ENet, Dawn...).
- **Facts that follow.** (1) Copying ModernGekko *source* into the game would make that part GPL-3.0; the combined work could be distributed under GPL-3.0 only if all our GPL-2.0 code is "or later" -- I did not audit per-file SPDX headers. (2) Merely implementing a compatible *interface* (the `ModernGekkoModDesc` layout and symbol names) is a different thing from copying code; whether copying the header's structs counts is a legal question I cannot settle. (3) Third-party mod DLLs are separate programs under their own licence; whether loading GPL-incompatible DLLs into a GPL process is allowed is the usual "plugin" question and is contested. (4) Hosting their *runtime* (Dolphin-derived, GPL-2.0-or-later with GPL-3 additions) is not what we would do.
  No relicensing recommendation made here.

---

## R3. Recommendation: "codes" in GD's Melee

Principles: platform-neutral and deterministic (cross-OS netplay is a stated property of the build id), no arbitrary native code from a browser, everything a code does must live in the simulation snapshot, additions must be opt-in so vanilla == vanilla.

### (a) Data patches -- do this first. Effort **~2-4 days**, low risk.

- **Format [I]:** a mod file `patches.json` (declarative; the Nucleus browser already ships `mod.json` + files): `[{ "game": "GALE01", "addr": "0x803D4A60", "expect": "0x...", "write": "0x...", "size": 4 }, ...]`, plus an import tool that converts a GCT/INI's `00/02/04/06` lines to it and **reports every other line as unsupported** (that report is the compatibility list). Modelled on ModernGekko's own `dol_patch` CSV (`address,expected,replacement`), which has the same guard idea.
- **Apply [R]:** at boot after fixups, before scene init, through `gw_mex_bridge_guest_data()`, big-endian via `gw_w32`; refuse when `expect` does not match the current value (stale address, wrong DOL), refuse an address with no sized bridge object, log each applied/refused patch.
- **Compatibility list [M-able]:** a generated list of which GALE01 addresses are patchable = every sized object in `symbols.txt` `.data/.sdata/.bss` minus objects proven unread; start with the families the port's flags already cover (`gmMainLib_DefaultGameRules/Prefs`, the CSS/rules tables). Reuse: `dump_gct.parse`, `ace_gecko_map.py`, `gecko_classify.py`.
- **Value:** small. It would let creators ship rules/default tweaks and table edits without us writing a flag, and make ACE's six `Default*` writes data instead of `Mex_Enabled`. It does **not** touch the 99% of codes that are code patches.
- **Netplay [R/I]:** a patch set that changes simulation must be identical on both peers: add a digest of the applied patch set into the handshake alongside `gw_Mods_Fingerprint` (the current fingerprint covers files a mod mounts; a patch file would be one). Handshake field = build id word today; a new field would be a protocol bump (**decision**). Rollback: constant data, no snapshot impact, provided the original bytes are restored when a patch set changes between matches.

### (b) Function-level native hooks -- do second, as OUR interface. Effort **~1-2 weeks** for a first cut.

- **Why not ModernGekko's:** DLLs break cross-platform netplay identity, run arbitrary native code from a downloaded mod (the Nucleus browser's trust model is data + Lua today), tie the API to DolRecomp's `CPUState`, and entry hooks there are observe-only anyway. **[I]**
- **Shape [I]:**
  - Hook points are **named decomp functions** (not raw addresses): `symbol` from `symbols.txt`, with the address kept for Gecko import. A compile-time probe (`GW_HOOK_ENTRY(sym)` / `GW_HOOK_RETURN(sym)` in a generated TU list, or an x86 detour installed at boot for the allow-listed symbols) calls into a **hook table**. Avoids the inlining problem by only allowing symbols the build marks `noinline`.
  - Hook bodies are **Lua** (the existing `gd.*` scripting runs in the simulation and is already in the netplay/snapshot story; `docs/scripting.md`) *or* interpreted PPC blobs (class D `C2` payloads, via `gw_ppc`), selected per hook. Lua first; PPC blobs only if someone wants verbatim Gecko `C2` at entries (3.9% of ACE's text `C2`).
  - Capabilities: entry hook may read args and mutate guest memory; a *replace* patch is a hook with a return value; return hooks may adjust the return value.
- **Determinism/rollback [R/I]:** hook state must live in guest memory or in a registered snapshot region (`Snap_CuratedRegion`; the echo state is the precedent from `_research/ace-hitbox-slot4-2026-10-10.md`), not in Lua globals/native statics, or a rollback resimulation diverges. This is the main design risk and the reason (b) is "1-2 weeks", not "days".
- **Netplay:** the hook set and the hook scripts' content hash join the same patch digest as (a); both peers must have identical sets or the handshake refuses.

### (c) Keep hand-porting popular codes as flags -- ongoing, already the working method.

- It is the **only** route for classes C and F (97% of ACE `04`, 96% of ACE text `C2`). Method: `ace_gecko_map.py` -> decomp symbol; read the payload with `ppc_disasm.py`; implement at the decomp site under `TARGET_PC` + a `Mex_Enabled`/codeset flag; validate against console traces (`tools/replay/first_div.py` as in `_research/slippi-gameplay-codes.md`).
- Effort **[I]**: 0.5-3 days per code. Prioritise by popularity: UCF (done), Slippi gameplay set (16 of 40 done), Akaneia/ACE rules, 20XX-style toggles (not measured here).
- Value: highest per effort for gameplay-bearing codes; netplay-clean because it is part of the source hash.

### What the Nucleus browser could then install

**[I]** Three kinds of "code" entries, all declarative and Win/Linux-identical:
1. `kind: "patch"` -- a `patches.json` (class A), shown with its compatibility report ("14 of 16 lines supported");
2. `kind: "script"` (exists) -- Lua hook scripts using the (b) API;
3. flag toggles for hand-ported codes (`requires: engine.<flag>` the way `engine.pobj_palette` is gated in `gw_mods.c`), so a mod can say "needs UCF 0.84" and the game refuses/enables accordingly.
Not native DLLs, not raw `.gct` (a raw `.gct` is useful only as an *import source*: a converter that rejects what it cannot map). Because both peers need identical patch/hook sets, the browser should publish each code's digest and the lobby should show "you lack X" via the existing `gw_Mods_Describe` diff.

---

## Decisions for the owner

1. **Scope.** Options: (i) data patches only, (ii) data patches + our function hooks, (iii) + ModernGekko-compatible DLL adapter. Recommend (ii), staged (a) then (b); (iii) only if a concrete ModernGekko-Melee mod library appears that people want to run here.
2. **Protocol.** Adding a patch/hook digest to the handshake is a protocol-version change (currently "no packet changes, protocol 5" for the build-id word). Needs the owner's call and a version bump.
3. **Licence.** Any copy of ModernGekko/Dolphin-derived source into a GPL-2.0 tree needs an "or later" audit; recommend no code copy (clean-room interface at most).
4. **Native code from the browser.** Recommend no DLL mods via Nucleus (trust, cross-platform identity).

## Owed

- A measurement of a community set (20XX / Melee Code Manager / Slippi's gameplay `g_*.bin`): run `gecko_classify.py --gct/--ini` once a GCT is available (no binary was downloaded here).
- Proof for each candidate data patch that the native code reads the object (and the `.sdata2` literal case, `@2315`) -- needs a build and a run.
- Whether clang inlines DOL-visible functions in the port build (determines hook reliability); not measured.
- A hello-world `.mgm` run against our bridge to confirm R2.4's adapter assumption; not attempted (engine change).

## Sources

- <https://github.com/ExpansionPak/ModernGekko> (README, `PROVENANCE.md`, `include/moderngekko/mod_abi.h`, `cpu_state.h`, `module_abi.h`, `src/runtime/mod_loader.cpp`, `tools/dol_patch.cpp`, `mod-template/`), read via `gh api` on 2026-10-10.
- <https://github.com/project-slippi/slippi-ssbm-asm> (shallow clone; `Output/Console/GALE01r2.ini`, 312 `.asm`).
- Local: `melee/pc/platform/gw.h`, `gw_runtime.c`, `gw_ppc.h`, `gw_mex_bridge.c` (generated), `tools/mex_port/gen_bridge.py`, `gw_mex_ftfunction_runtime.c`, `gw_mods.h`, `gw_netplay.c:2937`, `melee/pc/DEPENDENCIES.md`, `melee/config/GALE01/{splits,symbols}.txt`; `_research/slippi-gameplay-codes.md`, `_research/ace-hitbox-slot4-2026-10-10.md`, `docs/MEX_PORT_STATUS.md`, `tools/research/ace_gecko_map.py`, `tools/mex_port/dump_gct.py`.

# Bridge call signatures from decomp prototypes (task #15)

**Tool:** `tools/mex_port/gen_sigs.py`
**Output:** `_build/gw_mex_sigs_gen.inc` (table) + `_build/gw_mex_sigs_gen.inc.report.txt` (audit)
**Status:** generated and statically validated. **Not yet wired into the build** (see
[Integration](#integration-step-not-done)).

## The bug

`gw_ppc_bridge_call` (`melee/pc/platform/gw_ppc.c`) defaults every bridged target to
`float_args=0, n_args=8, ret_float=0`, so every argument is read from r3..r10 and the result from r3.
PowerPC EABI passes each float parameter in the next FPR (f1..f8) and each integer or pointer in the
next GPR (r3..r10). The two sequences are interleaved in declaration order, and a float result comes
back in f1. For any target that takes or returns a float, the default reads the wrong registers and
throws the result away. Nothing crashes. The numbers are just wrong. This is what made `atan2f` hang
neutral-B.

## Approach

1. **Bridged targets:** scan `_build/sonic_ftfunction_reloc.bin` (base `0x807F4D60`, 22392 bytes).
   A bridged call is a `bl` (opcode 18, LK=1, sign-extended 24-bit displacement, AA honoured) whose
   target is outside `[base, base+len)`. Result: **101 distinct targets**.
2. **Names:** look each target up in `melee/config/GALE01/symbols.txt`.
3. **Prototypes:** scan the include roots the PC build actually uses (`melee/src`,
   `melee/extern/dolphin/include`, `melee/extern/dolphin/src`, `melee/build/GALE01/include`, taken
   from `melee/pc/build/masstest/pipe_win.sh`). Other roots are left out on purpose:
   `extern/aurora` and `dusklight/` hold other projects' GX prototypes.
   - The scanner handles multi-line prototypes. It needs a `;` or `{` after the parameter list, and
     it rejects call statements (`x = f(a);`, `return f(a);`).
   - Candidates are ranked. Tier 0 is a header declaration whose `/* XXXXXX */` address tag matches
     symbols.txt. Tier 1 is a header declaration with no tag. Tier 2 is a `.c` definition. A tag that
     contradicts symbols.txt disqualifies that candidate outright. The best tier is used, and every
     candidate in it must give the same signature, otherwise the function is refused.
4. **Types:** typedefs are resolved transitively across the same roots. Each parameter falls into one
   class:
   - **INT:** integers, enums, `bool`, pointers (`Vec3*` included), arrays and array typedefs
     (`Mtx` decays to a pointer), function pointers and function-typed parameters.
   - **FLOAT:** `float`, `f32`, or any typedef that resolves to them.
   - **Refused:** `double`/`f64` (the native callee wants 8 bytes in two cdecl slots, and the bridge
     writes 4), by-value struct or union, varargs, a return type that is a struct/union or array
     (sret), more than 8 slots, `f()` (unspecified), `UNK_PARAMS`, unresolved typedefs, and symbol
     names that map to more than one address.
5. **Signature:** bit *i* of `float_args` is set when slot *i* is FLOAT. `n_args` is the slot count.
   `ret_float` is set when the return type resolves to FLOAT. This is the same slot model
   `gw_ppc_bridge_call` walks: a FLOAT slot takes the next FPR and any other slot takes the next GPR.

**Sibling tool, not an extension of `gen_bridge.py`.** `gen_bridge.py` answers *where* a guest
address lives natively (symbols.txt + linker map, re-run on every relink). `gen_sigs.py` answers
*what shape* the function has (symbols.txt + headers, independent of the map). The inputs, the re-run
cadence and the failure modes don't overlap. The only shared code is the ~10-line symbols.txt
parser, which is duplicated rather than coupling the two tools.

## Coverage (blob scope, default run)

| | count |
|---|---:|
| Distinct out-of-blob `bl` targets | **101** |
| … that are vanilla functions in symbols.txt | 98 |
| … that are m-ex's own routines over vanilla `.data` (no symbol) | 3 |
| **Resolved (emitted)** | **96** (96/98 vanilla functions) |
| Not emitted | 3 (the m-ex routines; the 2 varargs are now derived - see below) |
| Resolved entries with a float argument or float return | 14 |
| **Float-bearing targets NOT covered by the hand-written table** | **10** |

All 98 vanilla targets have a `gw_` counterpart in `_build/melee-pc.map`, so the bridge does
resolve them. The only thing missing was their shape.

### New float-bearing targets (currently marshalled wrong)

Each of these is a live silent-garbage bug today. The generated table fixes all of them:

| guest | function | float_args | n | ret_float | prototype |
|---|---|---|---:|---:|---|
| 0x800704F0 | ftAnim_800704F0 | 0x04 | 3 | 0 | `(Fighter_GObj*, int tobj_idx, float frame)` |
| 0x80075AF0 | ftPartSetRotY | 0x04 | 3 | 0 | `(Fighter*, int part_idx, f32 rotate_y)` |
| 0x8007C930 | ftCommon_CalcGroundAccel_Deaccel | 0x02 | 2 | 0 | `(Fighter*, float)` |
| 0x8007C98C | ftCommon_CalcGroundAccel_DashRun | 0x0E | 4 | 0 | `(Fighter*, float, float, float)` |
| 0x8007CE94 | ftCommon_CalcSelfAccel_Deaccel | 0x02 | 2 | 0 | `(Fighter*, float)` |
| 0x8007D344 | ftCommon_CalcSelfAccel_DriftSimple | 0x0E | 4 | 0 | `(Fighter*, float, float, float)` |
| 0x8007D494 | ftCommon_Fall | 0x06 | 3 | 0 | `(Fighter*, float, float)` |
| 0x80096900 | ftCo_80096900 | 0x30 | 6 | 0 | `(Fighter_GObj*, int, int, bool, float, float)` |
| 0x800D5CB0 | ftCo_LandingFallSpecial_Enter | 0x04 | 3 | 0 | `(Fighter_GObj*, bool, float)` |
| 0x80380528 | HSD_Randf | 0x00 | 0 | **1** | `f32 (void)` |

That is gravity, terminal velocity, ground and air friction, drift, dash acceleration, landing lag,
part rotation and every `HSD_Randf()` roll. All of them currently read garbage in the Sonic mod code.
If Sonic's physics looks off (floaty, sliding, odd drift) or anything random behaves
deterministically, this is a likely cause. **Inferred, not observed:** the game was not run.

The full 96-entry list with the prototype each came from is in
`_build/gw_mex_sigs_gen.inc.report.txt`.

## Not emitted (keeps the integer default)

| guest | name | reason |
|---|---|---|
| 0x803D7058 | (m-ex `MEX_IndexFighterItem`) | no vanilla symbol; m-ex code over `gmResultCharacterData` |
| 0x803D7088 | (m-ex `MEX_GetFtItemID`) | no vanilla symbol |
| 0x803D7094 | (m-ex `MEX_GetData`) | no vanilla symbol |

The three m-ex routines never reach the signature path. `gw_mex_interp_resolve` sends them to
native shims (`gw_mex_shim_index_item`, `gw_mex_shim_get_ft_item_id`, `gw_mex_shim_get_data`)
before the bridge lookup. I checked those shims: every parameter is `uint32_t`, so the integer
default is correct for them. **Verified by reading the source.**

## Cross-check against the hand-written `gw_mex_sigs`

The generator always resolves the 13 hand-written addresses, even the ones outside the blob scope,
and exits 1 on any disagreement.

- **Agreements: 12 of 13, disagreements: 0.** expf, powf, atan2f, acosf, asinf, atanf, tanf, cosf,
  sinf, logf and fmodf all match exactly.
- **`Fighter_ChangeMotionState` (0x800693AC) matches exactly.** Derived `float_args=0x38` (bits
  3, 4, 5), `n_args=7`, `ret_float=0` from `ft/fighter.h` (tier 0, address tag verified). In PPC
  terms that is gobj/msid/flags in r3-r5, anim_start/speed/blend in f1-f3, then arg3 in r6.
- **Not covered: `__cvt_fp2unsigned` (0x803228C0).** The generator refuses it, and I did not
  special-case it:
  - Its prototype is `unsigned long __cvt_fp2unsigned(register double d)`
    (`src/Runtime/runtime.h`). The argument is a **`double`**. The hand-written entry marshals it
    as a 4-byte float. That would only be correct if the native callee took a `float`.
  - **But the entry is dead code:** there is no `gw___cvt_fp2unsigned` in `_build/melee-pc.map`
    (`runtime.c` is `ASM`), so `gw_mex_bridge_lookup` returns 0 and the resolver logs "unresolved"
    before it ever consults `gw_mex_sigs`. It is also not among the blob's 101 targets.
  - Verdict: this is not a generator bug. The hand-written entry is unreachable, and if it were
    reachable its shape would be doubtful. See Q2.

## Independent validation: guest call sites

The prototypes are one source of evidence. The compiled m-ex code is a second, independent one:
before each `bl` the guest loads its float arguments into f1..fN. The tool walks back from every
call site (up to 12 instructions, stopping at `b`/`bl`/`bc`/`bclr`/`bcctr`) and records the highest
FPR written.

- **96 of 96 resolved targets agree** with the derived float count. None are flagged.
- Spot-checked by hand in the disassembly:
  - `ftCommon_Fall` @ 0x807F60CC: `lfs f2,84(r30)`, `lfs f1,80(r30)`, `mr r3,r31`, `bl`. That is
    one GPR and two FPRs, matching mask 0x06, n 3.
  - `ftCommon_CalcGroundAccel_DashRun` @ 0x807F71F8: f2, f1 and f3 loaded plus `mr r3,r31`.
    Matches mask 0x0E, n 4.
  - `HSD_Randf` @ 0x807F8908: no argument setup before the `bl` (consistent with n=0). The float
    return comes from the prototype and was not traced through the code after the call.
- This check is **advisory**. It gives an upper bound on the float count but can't say which slots.
  It can miss loads placed before an earlier branch, and a float left over from a previous call's
  return is invisible to it.

Bug found while building this: PPC opcode 19 covers `bclr`/`bcctr` and also the CR logical ops.
The first version of the walk stopped at `crset 6`/`crclr 6`, which is the varargs "floats are in
FPRs" flag the compiler emits right before a varargs call. The fixed walk only stops at XO 16/528.

## Static checks I ran (no build, no game run)

- Classifier unit cases: `Vec3*` → INT; `Vec3` by value → refused; `double` → refused; `...` →
  refused; `Mtx` (array typedef) → INT; `void (*cb)(f32,int)` → one INT slot (the inner comma does
  not split it); struct return → refused; `f32(void)` → `0,0,1`; `()` → refused;
  `(f32,int,f32,int)` → mask 0x5, n 4 (FPR and GPR interleaving); 9 ints → refused.
- `--all-symbols` over every function in symbols.txt (19,827): 19,415 resolved, 412 refused, 985
  float-bearing, and still 0 hand-written disagreements. The main refusal causes: 187 ambiguous
  names (statics repeated across TUs), ~95 unresolved typedefs, 68 `UNK_PARAMS`, 45 with more than 8
  slots, 35 `()`, 20 varargs, 15 by-value struct params, 7 `double`, 3 sret returns. This mode is
  for future blobs and hasn't been audited the way the blob set has.

## Integration step (NOT done)

The build owner still has to do all of this. Nothing under `melee/pc/platform/` was modified.

1. Generate into the platform directory:
   `python3 tools/mex_port/gen_sigs.py --out-c melee/pc/platform/gw_mex_sigs_gen.inc`
   The report lands next to it as `.report.txt`; `.gitignore` it or write it elsewhere with
   `--report`. The file is a `.inc` on purpose, so no source glob can compile it as its own
   translation unit.
2. In `gw_mex_ftfunction_runtime.c`, `#include "gw_mex_sigs_gen.inc"` and extend
   `gw_mex_sig_lookup`: search the hand-written `gw_mex_sigs` first (it can stay as an override),
   then binary-search `gw_mex_gen_sigs` (sorted by `guest`). The field layout is identical to
   `gw_mex_sig_entry`.
3. `n_args` can now be **0** (gm_8016B168, GXClearVtxDesc, HSD_Randf and others).
   `gw_ppc_bridge_call` already handles 0 correctly (the loop does nothing). Only the `/* 1..8 */`
   comment in `gw_ppc.h` is out of date.
4. Suggested follow-ups: delete the 12 hand-written entries the generator reproduces exactly, and
   the dead `__cvt_fp2unsigned` entry. Run the generator in CI so a header change that alters a
   signature shows up.
5. Behaviour to check in-game afterwards: Sonic's fall speed and gravity, air and ground friction,
   drift, landing lag after specials, and anything driven by `HSD_Randf`.

## Open questions

- ~~**Q1: float varargs**~~ **- FIXED (2026-09-19).** The premise was right and the conclusion
  was wrong: it *is* marshalled per call site, and the call site states its own shape. The
  PowerPC EABI requires a variadic caller to record in CR bit 6 whether it put any argument in an
  FPR (`creqv 6,6,6` = crset) or not (`crxor 6,6,6` = crclr), and MWCC emits that instruction
  immediately before every variadic `bl`, so the bit is still live when `gw_ppc_bridge_call` runs.
  CR6 set -> the first variadic value is a double in the next FPR and takes two native slots;
  CR6 clear -> the tail is words from the remaining GPRs, which is what the integer default
  happened to do (and why `efSync_Spawn` worked - now confirmed, not inferred: all five of its
  call sites in PlSn.dat assemble `crxor 6,6,6`).

  Carried as bit 31 of `float_args` (`GW_PPC_SIG_VARARGS`) - argument slots are 0..7, so the
  mask's high bits are free and every existing signature table keeps its wire format byte for
  byte. `gen_sigs.py` derives variadic prototypes instead of refusing them and emits exactly two
  entries: `efSync_Spawn` (2 fixed) and `HSD_ForeachAnim` (5 fixed). Covered headlessly by the
  `ppc_varargs_bridge` test, which exercises both halves against a genuinely variadic helper.

  Only the FIRST variadic value's class is knowable this way: the PowerPC register assignment has
  already lost the relative order of a mixed tail. A call site that passed a float vararg followed
  by values of other classes would need a hand-written adapter; none does today.
- **Q2: `__cvt_fp2unsigned`.** If a future blob calls it, what should the native side be? The PPC
  argument is a double in f1. A native `gw_` shim would need `double` (8 bytes), and the bridge
  can't express that today.
- **Q3: `double` in general.** 7 functions in the full symbol set take a `double`. None are in the
  blob. Supporting them means a `double_args` mask in `gw_ppc_sig` and two-slot marshalling.
- **Q4: sret.** 3 functions in the full set return a struct by value. None are in the blob. PPC
  passes a hidden sret pointer in r3. Whether MSVC i686 also uses a hidden pointer depends on the
  struct's size (≤8 bytes comes back in EAX:EDX), so no single rule works for all of them. They are
  refused. Handling them would need the struct size, from a compiler or the map, which this tool
  doesn't have.
- **Q5: tier-2 prototypes.** `Item_8026862C` came from a `.c` definition (tier 2, `it/item.c`). The
  call-site check agrees with it, but it is the one blob entry that doesn't come from a header
  declaration.

## Verified vs inferred

**Verified** (static, reproducible by re-running the tool):
- the 101-target count
- 98 targets symbolised, all with `gw_` natives in the map
- 96 resolved
- 0 disagreements and 12/13 hand-written matches, including Fighter_ChangeMotionState
- 96/96 call-site agreement
- the three m-ex shims are all-integer
- the `__cvt_fp2unsigned` entry is unreachable
- `HSD_ForeachAnim` passes a float vararg in f1

**Inferred** (not observed, because the game was not run):
- that the 10 newly covered float targets are producing wrong physics today, and that the table
  fixes them at runtime
- that the i686 cdecl float-slot trick used by `gw_ppc_bridge_call` behaves for every new target
  exactly as it does for the libm entries (same mechanism, not re-tested)

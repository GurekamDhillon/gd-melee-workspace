# `mex_port` — porting m-ex behavior into the decomp engine

[akaneia/m-ex](https://github.com/akaneia/m-ex) is a PowerPC assembly mod of the retail
`GALE01` DOL. Our engine is the *matching decompilation* retargeted to x86, so m-ex's
patches cannot be applied — there is no PPC code in the shipped binary to patch, and no
mechanism to execute m-ex's DAT-stored PowerPC payloads.

What transplants cleanly is the **behavior**. An m-ex patch is an insertion at a fixed
address in the retail binary:

```
#To be inserted at 802274f0
.include "../../Globals.s"
  load  r4,0x804c1fac
  ...
```

That address *is* a decomp location. `melee/config/GALE01/symbols.txt` maps every retail
address to its symbol, so each patch resolves to the decomp function it modifies — turning
"port m-ex" from a manual read of 1,169 files into a mechanical pipeline.

## Attribution requirement

m-ex publishes **no licence**. Consult it, do not copy it:

- Do **not** vendor, copy or compile `.asm`, `.s`, `.h` or `.dat` files from m-ex into this
  project or the `melee` fork.
- Reimplement the behavior in original C.
- Attribute m-ex at the change site, naming the source patch (see below).

## Pipeline

```
tools/mex_port/resolve_patches.py   # address -> decomp symbol inventory
_research/mex-port-triage.md        # generated report
```

```
python3 tools/mex_port/resolve_patches.py \
    --mex <m-ex checkout> \
    --symbols melee/config/GALE01/symbols.txt \
    --out _research/mex-port-triage.md
```

Every `.asm` file carries its insertion address in the directive header. **Two spellings
are in use** — both must be matched:

| Directive spelling | Count |
|---|---:|
| `#To be inserted @ <hex>` | 991 |
| `#To be inserted at <hex>` | 178 |

Matching only the word `at` silently drops 85% of the corpus, so `resolve_patches.py`
accepts `at`, `@`, an optional `0x` prefix, and any case. With both forms matched, all
**1169 of 1169** `.asm` files yield an address and **1130 (96.7%)** resolve to a decomp
function — including **1041 files / 1009 resolved** under `asm/m-ex`, which is where the
content-expansion work lives.

The m-ex build assembles these with `gecko assemble -p m-ex/ -o codes.gct`; the address in
the directive becomes the `GTI_FILE_INJECTION_ADDRESS` symbol for that file.

`MxDb.dat` is **not** involved in locating patches. It is a debug database of function
signatures (`MemcardSave_ScheduleSaveTask(r3=SaveStructInfo,...)`) consumed by m-ex's
stack-trace/`mexDebug` code, not a patch index.

## Change-site attribution

Every ported behavior is marked at the point of the edit:

```c
#if defined(TARGET_PC)
/* Ported from m-ex (https://github.com/akaneia/m-ex).
 * Source patch: asm/<path>.asm  ("<insertion address>")
 * Behavior: <one line description>. */
...
#endif
```

Game-source changes stay inside `#if defined(TARGET_PC)` so the matching non-PC build is
byte-identical, per the fork's convention.

## Getting the exact original instruction

A patch is only unambiguous when its insertion address is the function's **entry** address
(a `blr`/`nop` there neutralises the whole function). Only **7 of the 169** resolved
addresses are at-entry; the other **162 are mid-function**, so porting them faithfully
requires the instruction that was actually there.

The retail DOL is the ground truth. Extract it from your own disc:

```
python3 - <<'EOF'
import struct
iso = "<path to GALE01 v1.02 ISO>"
f = open(iso, "rb"); header = f.read(0x440)
off = struct.unpack(">I", header[0x420:0x424])[0]
f.seek(off); dh = f.read(0x100)
offs = struct.unpack(">18I", dh[0x00:0x48])
addrs = struct.unpack(">18I", dh[0x48:0x90])
sizes = struct.unpack(">18I", dh[0x90:0xD8])
f.seek(off); open("orig_main.dol", "wb").write(f.read(max(o + s for o, s in zip(offs, sizes) if s)))
EOF
```

Then disassemble around any patch address. The shipped LLVM has a PowerPC *codegen* target
but no PowerPC **MC** layer, so `llvm-objdump`/`llvm-mc` cannot help — use the bundled
decoder instead:

```
python3 tools/mex_port/ppc_disasm.py --dol orig_main.dol --start 0x80182FBC --count 16
```

It maps retail virtual addresses to DOL file offsets through the section table and prints
`address  encoding  instruction`, with branch targets resolved. This is how a patch's
intent is confirmed: *"`asm/qol/Disable Movies/Title InGame Demo.asm` inserts `b 0x2c` at
`0x80182FBC`"* becomes *"the stock `bne 0x80182FE8` is replaced by an unconditional branch
to the same target, so the demo-start block is never entered."*

`DOL_SECTIONS` in the script covers the two text sections; extend it if you patch into
data.

## Verifying ports

Both scripts exist because the obvious check is wrong. **`pipe_wsl.sh` calls `exit 0` in its
failure handlers**, so a non-zero return code never occurs — the only reliable signal is
`CC_FAIL`/`GW_FAIL` appearing in the output, and the script deletes its own diagnostic file. A
number of "compile clean" claims were made against `$?` before this was noticed.

```
tools/mex_port/verify_changed.sh [prefix]      # prefix defaults to src/
```

Compiles every changed translation unit in **two** configurations: with `-DTARGET_PC`, and without
it. The second pass is the only thing that ever compiles the `#else` branches carrying the original
code — which is exactly what keeps the matching non-PC build byte-identical, and what no other
check in this project exercises. `pc/platform/` files compile with clang directly; `pc/gameworld/`
and `pc/tests/` go through the game pipeline like `src/`.

```
python3 tools/mex_port/lint_ports.py src/melee
```

Checks every `Mex_Enabled()` site for:

- a `#if defined(TARGET_PC)` earlier in the file,
- an attribution comment citing the m-ex URL within 20 lines above,
- a **globally unique** feature name — two files sharing a flag would toggle unrelated behaviours
  together.

Both scripts were falsified against deliberately broken input before being relied on, and both exit
non-zero on failure.


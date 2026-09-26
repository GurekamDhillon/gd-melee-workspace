# PC matrix palettes beyond ten envelopes

**2026-09-26 — research only.** This note answers `docs/prompts/codex-matrix-palette.md`.
It supplements `_build/tmp/codex-bodypieces-report.md`; it does not supersede that
note's weight/deformation results. It supersedes the assumption that ten envelopes
is an unavoidable PC GPU limit. No implementation, build, game run, or additional
Codex process was used. The only file written for this task is this note.

Source baseline: workspace HEAD `078350df6796b4d408ba3e342f6377ab7112883c`, game
HEAD `506b45c65641b63c01cacaad4368790e592df071`, plus the existing working trees.
Existing changes were left alone. Aurora is inspected inside the game checkout;
the paths and line numbers below refer to these local files, not upstream Aurora.
Runtime performance quoted by the task is prior evidence, not a measurement here.

## Finding and recommendation

**Yes, a PC extension can draw more than ten skinning envelopes per POBJ, but the
current path cannot.** Ten is enforced by the converter, HSD's matrix setup,
Aurora's SDK emulation and XF address map, and its shader data layout. Changing
one constant would either assert, misaddress texture matrices, or mis-size uniforms.

Recommend a **versioned, explicitly marked PC palette path, initially 64 entries**,
with unscaled byte indices and separate position/normal palette storage. Preserve
the existing GX matrix namespace and vanilla shader path. Reuse Aurora's existing
storage buffer for the extended palette if practical; a separate uniform palette
is also feasible. Keep 128 as a selectable capacity after validating 64: the same
byte encoding supports both, and the simulation gives 24 pieces at 128 versus 52
at 64. This is a medium-sized renderer feature, approximately 1–2 engineer-weeks
including integration and regression work, not a ten-to-64 constant edit.

The strongest measured result here is **619 → 129 / 52 / 24 body pieces** at
32 / 64 / 128 envelopes, with unchanged weights and geometry. That is substantial
headroom for the reported approximately 2 ms shortfall, but does not prove 60 fps.

## 1. Trace: POBJ to WGSL

An envelope here is a particular bone-plus-weight combination, **not one bone**.
HSD blends the bones on the CPU into one matrix per envelope; the vertex shader
selects that already blended matrix. Thus 2,080 distinct envelopes do not mean
2,080 skeleton joints or 2,080 matrices in every draw.

| Boundary | Evidence and consequence |
|---|---|
| Exporter packing | `experiment/tooling/HSDLib/HSDRaw/Tools/POBJ_Generator.cs:65` groups triangle envelope sets with ordinal string ordering and first-fit insertion. `HSDRaw/Tools/TriangleConverter/PrimitiveGroup.cs:59` and `:80`, under that same HSDLib directory, enforce at most ten nodes. `POBJ_Generator.cs:70` separately caps a primitive at 32,766 corners because its reader uses a signed count. |
| Exporter encoding | `experiment/tooling/HSDLib/HSDRaw/Tools/POBJ_Generator.cs:362` initially encodes envelope IDs as `id * 3`; `:482` maps each piece to local `slot * 3`; `:498` writes PNMTXIDX and `:499` writes TEX0MTXIDX as PNMTXIDX + 30, also copied to TEX1. `:506–512` batches a piece into one triangle-list primitive. |
| Serialized/runtime POBJ | `melee/src/sysdolphin/baselib/pobj.h:17–43`: both structures have 16-bit flags and display-list length units, a display pointer, and an envelope pointer/list. The envelope descriptors are joint/weight pairs (`:62`). **Their null-terminated lists have no ten-entry storage cap:** `pobj.c:202–228` loads all envelopes; `:280–294` attaches them. |
| Material/piece traversal | `melee/src/sysdolphin/baselib/dobj.c:295–307` sets the DOBJ material, then dispatches every POBJ. `pobj.c:1271` sets its matrices before `:1243` calls `GXCallDisplayList(display, n_display << 5)`. One batched POBJ normally means one draw per applicable render pass, not necessarily one draw per whole frame. |
| Envelope computation | `melee/src/sysdolphin/baselib/pobj.c:1144` explicitly stops at ten. `:1154–1162` handles the rigid-weight shortcut; `:1181–1193` sets up each joint, concatenates its inverse bind, and accumulates its weighted matrix. `:1201–1213` loads view-space position, inverse-transpose normal, and optional reflection/highlight texture matrices. |
| HSD slot conversion | `melee/src/sysdolphin/baselib/util.c:31–57` maps only 0…9 to 0,3,…27 and asserts otherwise. `tobj.c:1385–1414` maps ten texture slots, returns identity for index ten, and panics above that. Increasing only the loop still fails. |
| Attribute setup | `melee/src/sysdolphin/baselib/pobj.c:450–472` sets descriptors but deliberately skips normal component-format setup for matrix-index attributes. They are not arbitrary integer vertex formats selectable by `GXSetVtxAttrFmt`. |
| Game/native shim | `melee/pc/platform/shim_gx.c:685–738` reads big-endian guest matrices into native float arrays and forwards the original numeric ID to Aurora. `:632–657` forwards descriptors and big-endian attribute arrays. `:590–595` forwards display lists. **The shim itself adds neither a ten-slot array nor an index division.** Its conversion, lifetime, and ordering duties still apply to an extension. |
| Aurora SDK/FIFO writes | `melee/extern/aurora/lib/dolphin/gx/GXTransform.cpp:56–91` checks IDs against GX_PNMTX0…9; writes positions at XF address `id * 4` and normals at `0x400 + id * 3`. `:93–96` validates and packs current-matrix selection into six bits. `GXDispList.cpp:49–62` flushes pending SDK state and publishes the display-list bytes into the FIFO. |
| XF decoding/state | `melee/extern/aurora/lib/gx/regs.cpp:1204–1261` recognizes position addresses `[0, 0x78)`, texture addresses `[0x78, 0xF0)`, and normal addresses `[0x400, 0x45A)`. Position slot ten would be address `0x78`: **the first texture slot**, not extra position storage. `gx.hpp:67` defines `MaxPnMtx = (GX_PNMTX9 / 3) + 1`; `:336` allocates that many position/normal pairs. |
| Vertex bytes to shader | `melee/extern/aurora/lib/gx/attr_fmt.cpp:11–22` and `:52–63` make each matrix index one byte. `command_processor.cpp:371–394` derives vertex stride; `:696` takes the packed vertex data and `:725` uploads it. `:536–574` uploads indexed attribute arrays separately. `shader.cpp:702–726` generates raw-buffer loads and decodes PNMTXIDX using **`raw_fetch_u8_1(...) / 3u`**. This is storage-buffer vertex pulling, not a conventional fixed-function vertex-input layout (`pipeline.cpp:15–20`). |
| Default/current index | With PNMTXIDX absent, `melee/extern/aurora/lib/gx/shader.cpp:560–562` uses `imm.current_pnmtx`; `regs.cpp:586` and `:760` decode it from six bits and divide by three. A raw-byte extended attribute does not automatically extend this separate current-matrix mechanism. |
| Uniform layout/upload | `melee/extern/aurora/lib/gx/shader_info.cpp:240–241` literally budgets **30 matrices**. `:400–409` writes ten position, ten texture, then ten padded normal matrices. `shader.cpp:1120–1122` declares `postex_mtx[MaxPnMtx + MaxTexMtx]` and `nrm_mtx[MaxPnMtx]`, currently 20 and ten. |
| Final transform | `melee/extern/aurora/lib/gx/shader.cpp:1073–1077` transforms position through `postex_mtx[in_pnmtxidx]`, then projection. `:1106–1108` transforms/normalizes the normal using `nrm_mtx[in_pnmtxidx]`; `:1274–1275` also uses it for bump tangents/binormals. `pipeline.cpp:23–43` binds the uniform range and issues Draw/DrawIndexed. |

### Hidden coupling: texture matrices and uniform size

The position and texture tables share a shader index space. GX texture IDs start
at 30, so `30 / 3 = 10` selects the first texture matrix after ten positions
(`melee/extern/aurora/include/dolphin/gx/GXEnum.h:291–305`). Both indexed and fixed
texgens use this encoding (`lib/gx/shader.cpp:1299–1306`). Merely changing
`MaxPnMtx` would move the texture table in memory without moving these accesses.
Envelope-driven normal projection also needs more than ten corresponding normal
transforms; it cannot keep calling `HSD_Index2TexMtx` with the extended slot.

Aurora also has a **3,840-byte application limit**, not just a GPU limit:
`melee/extern/aurora/lib/gx/gx.hpp:69`, the fatal check in
`shader_info.cpp:365–367`, the bound size in `lib/gfx/frame.cpp:507–511`, and the
tail padding in `lib/gfx/recording.cpp:1177`. All matter for a larger uniform.

WGSL gives `mat3x4<f32>` a size of 48 bytes and alignment of 16. A layout replacing
the ten position/normal slots with N slots, while keeping ten ordinary texture
matrices, therefore consumes the following **matrix bytes only**. These numbers
exclude projection, lights, material parameters, fog, and alignment of the whole
uniform. [WGSL layout specification](https://www.w3.org/TR/WGSL/#alignment-and-size)

| N | Position + normal | With ten texture matrices: `48 * (2N + 10)` |
|---:|---:|---:|
| 10 | 960 B | 1,440 B |
| 32 | 3,072 B | 3,552 B |
| 64 | 6,144 B | 6,624 B |
| 128 | 12,288 B | 12,768 B |

Even 32 leaves only 288 bytes under Aurora's present cap; lit variants need more.
64 and 128 exceed it before other fields. This is still modest GPU storage: the
WebGPU specification's default uniform-binding limits are 65,536 bytes in core
and 16,384 in compatibility mode. The device's actual negotiated limit must be
checked; this research did not query a GPU. Aurora requests compatibility-stage
limits and only two storage bindings (`lib/webgpu/gpu.cpp:883–905`).
[WebGPU limits](https://www.w3.org/TR/webgpu/#limits)

## 2. A compatible N-entry design and its scope

The following is a proposed design, not an existing Geno encoding or API.

**Format and opt-in.** Keep ordinary files' bytes, flags, envelope lists and GX
semantics unchanged. Mark extended POBJs explicitly, for example with a registered
versioned `HSD_PObjDesc.class_name` such as `GenoPalettePOBJ_v1`, plus a required
renderer capability/version in the containing port's metadata. Retain
`POBJ_ENVELOPE` for list load/free behavior. Validate capacity, list length, every
local index, primitive length, and supported texgen modes when loading. An
unextended runtime must reject this asset before HSD dispatch or select a separately
generated vanilla fallback: **unknown class names currently silently fall back to
ordinary HSD_PObj** (`melee/src/sysdolphin/baselib/pobj.c:309–323`). A marker alone
does not protect an old runtime. No unused flag bit has been established here;
do not silently assign one or change the meaning of `0x3000` type bits
(`forward.h:124–132`).

For a marked piece, use the existing **one-byte DIRECT PNMTXIDX payload as an
unscaled local envelope slot, 0…N-1**. A shader/config mode selects this decoding;
unmarked pieces retain `/ 3`. Thus both 64 and 128 fit without widening vertices.
Keeping the old scaled encoding could numerically represent 86 slots (0…85,
last value 255), but it would not fix XF aliases or SDK validation; 128 would
overflow (`127 * 3 = 381`). GX_INDEX16 describes attribute-array indexing, not a
drop-in 16-bit matrix-value format. For an initial extension require DIRECT
PNMTXIDX; do not accidentally depend on the separate six-bit current-matrix field.

**HSD.** For marked pieces, traverse the validated N-entry list and retain the
existing rigid shortcut, weighted blend order, view concatenation and normal
inverse transpose. Route matrix outputs into extended palette uploads instead
of `HSD_Index2PosNrmMtx`/GX's legacy slots. Preserve ordinary HSD functions for
unmarked POBJs. The loader already supports arbitrary list lengths. Implement
normal/reflection/highlight texgens against the extended normal palette where
their old per-envelope TEXnMTXIDX selected an inverse-transpose matrix; ordinary
texture transforms remain in the ten-slot GX table. The exporter must explicitly
identify these texgens and encode their indices consistently, replacing the
current `PNMTXIDX + 30` assumption. An unsupported texgen needs fallback/rejection,
not plausible-looking but incorrect lighting. Preserve NBT semantics as well.

**Shim and FIFO.** Add a scoped, validated palette upload/draw mode. Convert guest
floats using the existing big-endian boundary convention and copy palette bytes
into an ordered Aurora extension command. A single palette upload per piece
amortizes the per-matrix calls. Do not write `g_gxState` directly from the game
thread or retain pointers to stack matrices. Define begin/upload/end or an atomic
extended draw so the mode cannot leak into a following vanilla draw. Aurora
already has an extension opcode family
(`melee/extern/aurora/include/dolphin/gx/GXAurora.h:11–110`). Keep the existing XF
address map, SDK GX constants, and their assertions unchanged.

**Aurora palette and shader.** Prefer separate extended matrices uploaded into
the already bound `abuf` storage arena (`shader.cpp:2051–2056`,
`lib/gfx/recording.cpp:1209–1214`). Reconstruct position and normal matrices from
that region for marked draws. This avoids changing vanilla's 30-matrix uniform,
its texture-slot placement, or adding a third storage binding. The current
64-byte immediate block has a four-byte padding field which could carry a palette
base offset (`gx.hpp:80–88`, `shader.cpp:2036–2044`); capacity/encoding can be in a
validated header and shader configuration. This is a design opportunity, not a
claim that the field is already an API. Include the extension mode in shader and
pipeline keys (`gx.hpp:492–511`), draw caching, dirty-state handling, and merging
predicates. Snapshot the palette with the draw; later uploads must not overwrite
earlier draws' data.

A uniform alternative is also reasonable. Use distinct extended arrays or
explicitly remap legacy texture indices; update the CPU byte budget, upload
order, WGSL declarations, binding range and tail padding together. Replacing
the legacy position/normal arrays adds 11,328 bytes at N=128; adding an entirely
separate 128-entry position/normal pair adds 12,288. The latter plus the current
3,840-byte ceiling is 16,128, close to the compatibility limit. Treat this as
arithmetic headroom, not a validated maximal shader layout. Storage gives more
room for later growth and leaves vanilla allocations unchanged, at the cost of
additional shader storage loads whose runtime cost is unmeasured.

### Change estimates and risks

These are engineering estimates, not measured implementation times. Ranges overlap;
approximately 700–1,500 production lines across the layers is a planning scale,
with additional focused validation work. Reflection/interpolation scope can push
the upper bound higher.

| Area | Approximate change | Principal risk |
|---|---|---|
| Exporter + capability/format metadata | Small–medium, 100–250 lines; 0.5–1.5 days | Parameterize `PrimitiveGroup` and packing only for the new format; change local PN/TEX encodings, validate bounds, retain the legacy path. Incorrect mode/version can reinterpret every vertex. |
| HSD class/dispatch + palette setup | Medium, 150–300 lines; 1–2 days | Preserve class lifetime, envelope arithmetic, lazy JObj setup, normals and normal projection. Avoid changing ordinary structure ABI and vanilla slot functions. |
| Guest/native shim + ordered command | Small–medium, 100–200 lines; 0.5–1.5 days | Endianness, payload bounds, FIFO ordering, ownership, and mode reset. New guest-callable entry points also require the normal bridge integration when implemented. |
| Aurora state, shader, upload and cache | Medium, 250–500 lines; 1.5–3 days | Position/normal lookup, texgen separation, cache keys, binding/alignment and draw merging. Globally enlarging `MaxPnMtx` has much higher vanilla risk than an opt-in path. |
| Frame replay/interpolation and restore handling | Medium, 100–250 lines; 1–2 days | Extended matrices must survive frame recording/replay and be invalidated or reconstructed across restores. This is required integration, not an optional afterthought. |

There are two particularly easy-to-miss renderer traps:

* **Interpolation uses 32-bit pending-slot masks.**
  `melee/extern/aurora/lib/gx/regs.cpp:999–1000` and `:1138–1170` record legacy
  loads with `1u << slot`, key them by XF address/POS array, and blend before the
  draw. A global increase to 64/128 would introduce invalid shifts as well as
  missing address handling. Give extended palettes their own capacity-safe
  tracking and stable object/slot identity, or explicitly document a first
  version's lack of interpolation for these meshes.
* **A generic Geno callback is not automatically replayable.**
  `melee/extern/aurora/lib/gx/command_processor.cpp:976–984` skips
  `GXAuroraCallback` while replaying. It is useful ordering precedent, but blindly
  using it for palette setup would omit the setup on repeated frames. Replay
  restores GXState and reprocesses recorded commands
  (`lib/gx/fifo.cpp:359–400`); use a replayable palette command and re-upload its
  bytes for each recorded frame, not a stale transient storage offset. Separate
  external palette state must participate in that lifecycle too.

### Vanilla and rollback/netplay risk

Vanilla visual risk is **low-to-medium with explicit opt-in and separate storage**,
but high for a global `MaxPnMtx`/XF rewrite. Remaining shared risks are renderer
cache invalidation, state leakage, ordered uploads, and replay behavior. Palette
repacking can also alter triangle order; preserve opaque/cutout/translucent
ordering rules and material boundaries rather than assuming every material is
order-independent. Unchanged weights establish no intentional deformation, not
pixel identity under all blend/depth modes.

Simulation determinism risk is **low in principle, nonzero in implementation**.
Keep palettes, transformed vertices and shader results render-only, with no GPU
readback into gameplay and no changes to joint animation, collision, RNG, or
frame progression. Reuse HSD's envelope math rather than changing summation order.
HSD rendering does call `HSD_JObjSetupMatrix`, so lazy caches and guest writes
still deserve verification. `melee/pc/platform/gw_snap.c:7–13` snapshots MEM1 and
selected game globals but excludes renderer/shim state; native cached guest
pointers can therefore outlive restored data. Rebuild/invalidate render caches on
asset reload and restore. Repacking also changes HSD object allocations, so do
not promise byte-identical snapshots between old and regenerated costume files;
use matching assets/feature versions for a parity comparison.

Later acceptance work should cover mixed legacy/extended draws, multiple fighters,
all used normal/texgen modes, pause and high-refresh frame replay, rewind and
rollback with skipped render callbacks, and existing deterministic replay checks.
No such runtime validation was performed for this research.

## 3. Offline packing results

Input: `_build/tmp/ultimate-mods/ultimate-trail-slot-marth/_work/mesh_c00.json`,
`body_highShape`, subindex 0. SHA-256:
`56e77e78122630b124125fdc2d6094c836a19eb9073459317f7c22d91132874d`.

The existing `ports/ir/tools/analyze_envelopes.py` supplies float32-exact envelope
keys (`:38–44`), first-seen IDs (`:77–95`) and packing (`:98–137`). Its SHA-256
was `526bbb5bebfb3aea945b2dde7852d21285411820adb8dba95a761a559da7a2b0`.
I executed those definitions from its AST in memory with `python -B`, changing
only the in-memory `MAX_ENVELOPES` value. This avoided importing animation tools,
creating bytecode, modifying the script, or invoking its report-writing `run()`.
No weights, triangle topology, or mesh files were modified.

All cases retain the generator's 32,766-corner cap. The baseline reproduces the
prior report's 15,337 triangles, 46,011 corners, 2,080 distinct envelopes, 234 bone
sets, and exactly 619 pieces. The optional reordered heuristic was also evaluated;
it is not uniformly better at larger capacities.

| Envelopes per piece | First-fit pieces | Pieces removed vs 619 | Reduction | Reordered heuristic pieces | Total loaded envelope slots, first-fit | Largest piece, corners |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 619 | 0 | 0% | 595 | 6,186 | 2,262 |
| 32 | **129** | 490 | **79.16%** | 129 | 4,098 | 3,909 |
| 64 | **52** | 567 | **91.60%** | 56 | 3,290 | 5,151 |
| 128 | **24** | 595 | **96.12%** | 26 | 2,947 | 9,117 |

The total-slot column sums each piece's actual unique envelopes, including
envelopes duplicated across pieces; it is a proxy for HSD envelope setup work,
not a measured GX call count. At 64 it falls approximately 46.8%, at 128
approximately 52.4%. I observed bin contents with an in-memory copy of `pack`
returning its `bins`, confirmed its count against unmodified `pack`, and checked
that each run retains all 15,337 triangles and respects both limits. None of
these capacities hits the corner-count cap. The global `ceil(2080/N)` lower
bounds (208, 65, 33, 17) are not expected achievable counts: triangle connectivity
and duplicate envelopes across bins matter.

Minimal reproduction from the workspace root, without creating a script:

```python
import ast, json, struct
from collections import Counter
from pathlib import Path
p = Path('ports/ir/tools/analyze_envelopes.py')
t = ast.parse(p.read_text())
names = {'f32_bits', 'envelope', 'prepared_triangles', 'pack'}
defs = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in names]
ns = {'struct': struct, 'Counter': Counter, 'MAX_VERTICES': 32766,
      'MAX_ENVELOPES': 10}
exec(compile(ast.Module(body=defs, type_ignores=[]), str(p), 'exec'), ns)
m = json.loads(Path('_build/tmp/ultimate-mods/ultimate-trail-slot-marth/'
                    '_work/mesh_c00.json').read_text())
body = [d for d in m['dobjs']
        if d['object'] == 'body_highShape' and d['subindex'] == 0]
assert len(body) == 1
tris, envelopes, bone_sets = ns['prepared_triangles'](body[0]['tris'])
for limit in (10, 32, 64, 128):
    ns['MAX_ENVELOPES'] = limit
    print(limit, ns['pack'](tris), ns['pack'](tris, improved=True))
```

### What this predicts about speed

The table predicts pieces and envelope work, not frame time. It applies to this
body only, per render pass; other Sora meshes, effects, materials, GPU fill and
game logic remain. Aurora rebuilds uniforms when matrix loads mark them dirty
(`regs.cpp:1219–1220`, `command_processor.cpp:621–624`), so fewer pieces can save
CPU submission, matrix setup, uniform construction and GPU draw overhead together.
Wider shader indexing and palette storage have their own costs.

Using the task's approximate 18.7 → 16.7 ms target, removing 567 pieces at N=64
would need an average **net saving of about 3.53 microseconds per removed piece**
to recover 2 ms, if the affected cost is on the frame's critical path. That is a
break-even calculation, not a measured per-draw cost or an fps prediction.
Moving 64 → 128 removes only another 28 pieces and 343 loaded envelope slots;
64 captures most of the count reduction with smaller per-draw uploads.

## 4. Alternatives

| Approach | Rough cost and attainable reduction | Assessment |
|---|---|---|
| CPU pre-skin the body, then draw rigid geometry | Compute the 2,080 distinct blended matrices, apply position and inverse-transpose normal transforms on the CPU, and stream the results each rendered frame. This mesh has 8,137 distinct position/weight records (prior report) and 13,994 distinct full JSON vertex records (counted here, including normals/UVs). At 24 bytes for position+normal, a deduplicated full-vertex stream is about **328 KiB per frame / 20 MB/s at 60 Hz**; a naive 46,011-corner stream is about **1.05 MiB / 66 MB/s**, excluding UVs/indices and extra passes. Work is tens of thousands of vector transforms, order 10^6 scalar arithmetic operations, plus matrix construction, lookup and upload. Approximately 3–6 days plus validation for a native, cached single-material path. | Could reduce 619 pieces to roughly one or two draw submissions per material/pass, but moves per-vertex work and dynamic uploads onto the CPU. Two primitives are needed if keeping the generator's 32,766 submitted-corner cap. One indexed/native draw is plausible with deduplication; raw GX's unsigned 16-bit count itself accommodates 46,011 corners, unlike the current HSDRaw reader. Preserve UV/normal seams, cache invalidation and normal/reflection transforms. **Use as fallback**, not the first choice without CPU/GPU timings. |
| Merge consecutive same-material POBJs inside Aurora | Simple merging already exists when `g_gxState.dirty == 0`, layout matches, and array snapshots cover all references (`command_processor.cpp:690–721`); geometry is appended at `:724–757`. New POBJ palettes normally dirty uniforms, and local slot zero means different matrices in different pieces. A useful merger must capture each palette, remap vertices to a larger matrix pool or pretransform them, preserve order, and reconcile attribute-array bases and state. Approximately 1–2 weeks for a general safe path. | Material equality alone gives **no reliable additional reduction**. A true palette-aware merger can approach large-palette draw counts; a larger pool or pretransform path can approach one batch per compatible material run. It still executes the original 619 HSD traversals/envelope setups, so it misses much of the CPU-side gain from repacking assets. Greater global-renderer regression exposure than an opt-in POBJ extension. |
| GPU skin directly from bone indices/weights | New mesh vertex format with up to four influences here, bone/inverse-bind data, a native skinning shader, and integration with material/lighting paths. Approximately 2–4 weeks for a reusable route. One/few draws per material; the 2,080 envelope combinations stop being palette entries. | Attractive longer term, but materially larger scope. To preserve HSD appearance, derive the normal transform consistently with HSD's inverse transpose of the blended transform; simply blending bone normal matrices is not generally equivalent. |
| Keep ten; reorder packing / adjust weights | Reordering produces 595 pieces, only 3.9% fewer. Prior report shows tested weight changes reaching fewer than 150 pieces exceed the 0.05-unit displacement budget. | Lowest renderer risk but inadequate count reduction for the stated goal. Weight-loss experiments are already documented; no need to repeat them here. |

CPU skinning and runtime merging would share the same render-only ownership and
frame-replay concerns as the palette extension. Upload bandwidth alone does not
establish either alternative's frame time. With the large offline reduction and
manageable palette sizes, lifting the limit through a deliberate PC extension is
reasonable; CPU skinning is a contingency, not a prerequisite.

## Research boundary

Verified here: the source trace and hard-coded limits, exporter correspondence,
offline packing counts and occupancy, input identity, and arithmetic size/cost
estimates. Not verified: shader compilation, device support, visual parity,
actual draw counts after implementation, runtime memory/performance, or rollback
parity. Those require a separately authorized implementation and Windows testing.
No code, converter, mesh, build output, or game process was changed by this task.

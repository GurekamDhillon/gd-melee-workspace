# PC matrix palette, format and engine design (v1)

**2026-09-26, lane beta. Design; implementation in progress on agent/beta.** Builds on
`_research/pc-matrix-palette.md` (Codex). That note's source trace was spot-checked and holds: the
`MtxIdx < 10` loop (`pobj.c` PObjSetupEnvelopeMtx), `class_name` dispatch that silently falls back to
a plain POBJ (`HSD_PObjLoadDesc`), `raw_fetch_u8_1(...) / 3u` PNMTXIDX decode (`shader.cpp`
attr_load), the 64-byte immediate block with a free `_pad` word (`gx.hpp` DrawImmediateData), `abuf`
as a bound storage buffer, and `GX_AURORA_CALLBACK` being skipped on replay. This note fixes the
choices that note left open. Where the two disagree, this one wins.

Goal: Sora's body goes from 619 pieces to about 52 (64 envelopes a piece). Vanilla's data, code
path and shaders stay byte-for-byte as they are.

## 1. The marker: an HSD subclass, not a flag bit

An extended POBJ is an ordinary envelope POBJ whose `HSD_PObjDesc.class_name` points at the
NUL-terminated ASCII string **`geno_pal_pobj_v1`**. The engine registers an `HSD_PObjInfo` subclass
under that name at boot (`hsdInitClassInfo`, parent `hsdPObj`). `hsdNew` then builds it, and its
methods replace two of the base class's:

- `setup_mtx`: computes the palette (section 3) instead of loading the ten GX slots.
- `disp`: calls the base display, then ends palette mode.

Vanilla POBJs never reach this code. No flag bit is spent: the `0x3000` type bits and the cull bits
keep their meaning.

The runtime check is `pobj->parent.class_info == &genoPalPObj`. It lives in guest memory and is
set at load, so snapshots and rollback carry it like any other object.

**Old runtimes.** An exe without this class loads the POBJ as a plain one and draws garbage (a slot
byte of 17 decodes as 17/3). A mod shipping such files must declare
`"engine": {"pobj_palette": 1}` in `mod.json`. The mod loader refuses to mount a mod whose engine
requirement is higher than it supports, and logs why. That check lives in `gw_mods`, which is
delta's; I'll ask the coordinator to route it. Until it lands, never ship these files outside
agents' test folders.

## 2. What the converter emits (fighterbuild; Codex implements)

Per extended POBJ, all big-endian like every other HSD field:

| field | value |
|---|---|
| `HSD_PObjDesc.class_name` (+0x00) | pointer to `"geno_pal_pobj_v1\0"`, which may be shared by all POBJs in the file. Vanilla files have NULL here. |
| `flags` (+0x0C, u16) | `POBJ_ENVELOPE` (0x2000), plus the cull bits as today. No other bits. |
| `u.envelope_p` (+0x14) | pointer to a NULL-terminated array of `HSD_EnvelopeDesc*`, 1 to **64** entries. Entry *i* is palette slot *i*. Each is the usual NULL-terminated `{HSD_Joint*, f32 weight}` list. Weights must sum to 1 within 1e-5, and a single-joint envelope has weight exactly 1.0f (the rigid shortcut). |
| vertex descriptor list | `GX_VA_PNMTXIDX` is **required**, `GX_DIRECT`, 1 byte (`GX_POS_XYZ` / `GX_U8`, like today). Then POS, NRM, optional CLR0, TEX0, TEX1, as today. **`GX_VA_TEX0MTXIDX`..`TEX7MTXIDX` must not appear in v1.** |
| PNMTXIDX byte in the display list | the **unscaled** local slot, `0..n-1`, where n is the array's length. Not `slot*3`, and never 30+. |
| display list | GX triangles or triangle strips as today, at most 32766 corners per primitive. `n_display` counts 32-byte units as today. |

Packing (`PrimitiveGroup` / `POBJ_Generator`): allow up to 64 envelopes per group only when writing
extended POBJs, and keep the 10-envelope path unchanged for everything else. It is chosen per
fighter by a command-line switch, `--pc-palette 64`.

The converter must check and fail the build on each of these: a slot ≥ n, n > 64, a TEXnMTXIDX
attribute, a POBJ that is not an envelope POBJ, or a material that asks for normal-projection
texgens (env/reflection maps) on an extended POBJ. Sora's body has none of these.
`Verify.cs` should decode each extended POBJ back (bytes → slot → envelope) and compare the
triangles and weights with the input, as it does for the 10-slot path.

The file-level declaration is the `mod.json` `"engine"` key above, written by the installer.

## 3. The engine

**HSD (game half, `pobj.c` under `TARGET_PC`).**

- **Load:** the subclass `load` calls the base `load`, then checks the POBJ: envelope type, n in
  1..64, PNMTXIDX DIRECT u8 present, and no TEXnMTXIDX. A POBJ that fails is logged once and flagged
  *broken*; `disp` then skips it. It is never drawn wrong.
- **`setup_mtx`:** the same math as `PObjSetupEnvelopeMtx`, in the same order: the rigid shortcut,
  `MTXConcat(jp->mtx, jp->envelopemtx)`, `HSD_MtxScaledAdd` in list order, the `right`
  (`_HSD_mkEnvelopeModelNodeMtx`) concat, the view concat, and `HSD_MtxInverseTranspose` for
  normals. It loops over all n entries instead of 10. Results go into a native array
  `pos[n][3][4]` / `nrm[n][3][4]` (normals padded to 3x4) instead of `GXLoad*MtxImm`. It then makes
  one call, `GXAuroraLoadPalette(n, key, data)`.
  - If the POBJ's JObj does not have `JOBJ_LIGHTING`, the normal matrices are still sent: the shader
    ignores them, and this keeps the layout fixed.
  - `SETUP_NORMAL_PROJECTION` on an extended POBJ is the broken case above; the converter already
    forbids it.
- **`disp`:** runs the base `HSD_PObjDisp` (cull mode, `setup_mtx`, `GXCallDisplayList`), then
  `GXAuroraEndPalette()`.

**Shim (`shim_gx.c`) and the guest/native boundary.** The two calls are ordinary game-half externs
(`gw_` prefix, like the effects API). The guest→native conversion of the matrices happens once, in
`setup_mtx`: the matrices are native floats computed in game code, so there is no per-matrix
big-endian read.

`key` identifies the palette for interpolation (below). It is the POBJ's guest address XOR the JObj's
guest address. It is stable while the model lives and differs between two fighters sharing a model.

**Aurora (`extern/aurora`, patched like the effects callback, kept as a patch file with the lane).**

- **New subcommands:** `GX_AURORA_LOAD_PALETTE 0x0040` carries `u16 n, u32 key` and n×96 bytes of
  floats (pos 3x4, then nrm 3x4). `GX_AURORA_END_PALETTE 0x0041` carries nothing. Both are ordinary
  FIFO commands, not callbacks, so a replayed frame processes them again from the recorded bytes.
- **State:** `g_gxState.palette = {active, n, key, abufOffset}`. LOAD writes the floats into this
  draw's storage arena (the same per-frame arena `abuf` binds) and marks the state dirty, so no merge
  crosses a palette change. END clears `active` and marks dirty. So do a legacy
  `GXLoadPosMtxImm`/`GXSetCurrentMtx`, and the start of every frame; nothing can leak into a vanilla
  draw.
- **Shader and pipeline key:** `ShaderConfig` gets `u8 pnPalette` (0 or 1), which is part of the
  pipeline/shader hash. When it is 1:
  - PNMTXIDX decodes as `raw_fetch_u8_1(...)` with no `/3u`.
  - The position and normal matrices are read from `abuf` at `imm._pad` (renamed `palette_base`, in
    u32 units) + slot×24, instead of `postex_mtx`/`nrm_mtx`.
  - Texture matrices (GX slots 30+) still come from the uniform, unchanged.
  - When it is 0, the generated WGSL is textually identical to today's. This is a test (section 4).
- **Interpolation (120 fps depends on it):** regs.cpp's slot-mask interpolation stays for vanilla.
  Palette draws get their own path: the recorder keeps the previous logic frame's palettes in a small
  map by `key` (up to 256 keys), and at present time each palette entry is blended pos/nrm with the
  same `t` and method the legacy slots use. A key with no previous palette (spawn, or n changed)
  draws its current palette as is.
- **Replay:** the palette bytes are inside the recorded command. The arena offset is re-derived on
  every replay, never cached.

**Order of work** (each step builds and keeps the suite green; vanilla unaffected at every step):

1. Aurora: the subcommands, state, arena upload, `pnPalette` shader variant, and a native unit test
   that draws a palette triangle offscreen and compares vertex output numerically against the legacy
   path, with the same matrices in slots 0..9 and slots×3.
2. HSD subclass: registration, load validation, `setup_mtx`/`disp`, and a test that builds a
   synthetic 20-envelope POBJ in guest memory and checks its palette bytes against 2×10-slot legacy
   setups of the same envelopes, bit for bit (same float order).
3. Interpolation for palette keys.
4. The mods engine-requirement check (via the coordinator, delta's file).
5. Codex's fighterbuild output, installed into a copy of alpha's Sora slot, then the LAB and timing
   runs.

## 4. Proof

**Vanilla renders identically**, checked numerically, with no images:

- **(a) Shader text.** With the change, every pipeline vanilla creates generates the same WGSL as
  before. The runtime logs a hash of each generated shader. A vanilla match (Wolf vs Sonic, ACE) is
  run on the base and the new exe, and the two sets of shader hashes must be equal.
- **(b) Draw stream.** A `MELEE_DRAWLOG=frames` mode hashes, per draw, the pipeline key, the uniform
  bytes, the vertex/array bytes and the draw range, and logs one digest per frame. The same
  pad-scripted vanilla match with a fixed seed is run on the base and new exe; frames 300..1200 must
  match digest for digest. Because it is in-engine, this also catches a leaked palette state.
- **(c)** The suite stays at 191 or above, with the new palette tests.

**Rollback stays deterministic.** The palette is render-only: it is computed in `setup_mtx` from
JObj matrices HSD already computes, and it writes nothing into game state. The only guest-side
difference from a 10-slot POBJ is object size, and that is fixed at load. Checks:

- The existing rollback and netplay determinism tests.
- Two local netplay windows playing Sora vs Sora (one extended, the same file on both), 4000
  frames, 0 desyncs.
- A LAB savestate/rewind with Sora mid-move: the per-frame game-state checksum (gw_snap) equals the
  first pass's.
- The same pad script run on 10-slot and 64-slot Sora gives equal gameplay checksums frame by frame.
  Rendering must not feed back; `HSD_JObjSetupMatrix` runs for both.

**Speed.** The target is the Sora LAB with `MELEE_PROFILE_FRAMES`, comparing the game thread,
`aurora_end_frame` and draw calls against the 10-slot slot. The goal is ≤ ~8.3 ms per frame with
Sora for 120 fps, and each step is judged by its numbers.

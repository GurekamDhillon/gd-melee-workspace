# Research task for Codex: can the PC port draw more than 10 skinning matrices per mesh piece?

Written 2026-09-26 by the coordinating Claude session. **Research only.** No code edits, no builds,
no game runs, no other Codex processes. Produce one note and stop.

## Why

Sora's body (ported from Smash Ultimate) is 619 mesh pieces (POBJs) because the GameCube format
allows 10 skinning envelopes per piece and his body has 2,080 distinct envelopes (see
`_build/tmp/codex-bodypieces-report.md`: weight tweaks within 0.05 units of displacement don't get
below ~595 pieces). Each piece is a draw; Sora runs ~18.7 ms/frame vs 16.7 for 60 fps. On the PC
port the GPU is not a GameCube: the 10-matrix limit may be a format/emulation limit we can lift in
the port ("Geno" engine extensions are approved) rather than a real one.

## Questions

1. Where the limit lives: trace a skinned POBJ from HSD (`melee/src/sysdolphin/baselib/pobj.c`,
   envelope setup, `GXLoadPosMtxImm`/PNMTXIDX) through the GX shims (`melee/pc/platform/shim_gx*.c`)
   into Aurora (`melee/extern/aurora/lib/gx/`: how position-matrix indices, the matrix array and the
   vertex format reach the WGSL shader). Which of these hard-code 10 (or the index/3 encoding)?
2. What it would take to allow N matrices per piece (e.g. 64 or 128): the data format (the PNMTXIDX
   vertex attribute is 8-bit; how an extended piece would be marked so vanilla data is untouched),
   the HSD envelope loading, the shim, and the Aurora shader/uniform layout. Estimate the size of each
   change and the risk to vanilla rendering and to rollback/netplay determinism.
3. The expected gain: re-run the packing simulation from `ports/ir/tools/analyze_envelopes.py` with
   limits 32 / 64 / 128 and report the piece counts for the body.
4. Alternatives, if lifting it is unreasonable: e.g. CPU pre-skinning of such meshes into one
   unskinned piece per frame, or merging draws inside Aurora for consecutive pieces with the same
   material. Rough cost and gain for each.

## Output

`_research/pc-matrix-palette.md` with answers, file:line evidence, the piece-count table and a
recommendation. Final message: the path and a five-line summary.

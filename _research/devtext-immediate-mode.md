# Why the engine's own 2D does not draw: aurora, GXEnd, and the FIFO span

**2026-09-20.** Written while moving the F9 overlay off ImGui onto DevText. It applies to far
more than the overlay: it is why the merged loading screen does not cover a match, and it is the
best current explanation for the `.gxtex` sprite gap recorded in `bf9289e33`.

## The symptom

DevText - the engine's own screen-space text and panels - draws while the scene is not yet
drawing, and is gone the moment gameplay renders. GD saw it appear and be "quickly replaced back
into regular gameplay". Sampling captures at 5 s and 18 s misses that window entirely, which is
how this was first, wrongly, written up as "draws nothing".

## What is NOT wrong

Every one of these was measured, not reasoned about. Do not re-test them.

| Suspect | Evidence it is fine |
|---|---|
| Boxes leaving the draw list | List goes 3 -> 5 entries at frame 9 and is unchanged at frame 1059 |
| The draw callback not running | `DevText_DrawAll` walks every box each frame inside the `HSD_RP_BOTTOMHALF` branch |
| Nothing being submitted | ~817 primitives per frame, sampled across the loop with `gw_Gx_PrimCount()` |
| Depth | `GXSetZMode(GX_FALSE, GX_ALWAYS, GX_FALSE)` for the pass: no change |
| Camera ordering | DevText camera priority 11 -> 250: no change |
| Projection / viewport | Logged at draw time: type 1 (ortho), the exact -20..660 by -20..500 box, viewport 0,0 640x480 |
| Position matrix | Logged: identity with z = -1, exactly as `HSD_CObjGetViewingMtx` should give |
| Vertex coordinates | Logged at the shim: `(0,-2) (88,-2) (88,18) (0,18)` - a real plate, intact |
| TEV / channel / blend state | Forcing the minimal known-good untextured vertex-colour setup: no change |
| Primitive support | Aurora handles `GX_QUADS` and `GX_POINTS` (the latter expanded to a screen-space quad) |
| Attribute layout | Aurora's `attr_fmt.cpp` sizes `GX_POS_XY` as 2 components |

## What IS wrong

**Aurora finalises an immediate-mode primitive in `GXEnd`, and the game never calls it.**
`libs/dolphin/include/dolphin/gx/GXGeometry.h` makes `GXEnd` a `static inline` that expands to
nothing outside DEBUG - correct for real hardware, where there is nothing to do - so all **82**
`GXBegin` sites in the game submit vertices aurora is never told to close.

Making `gw_GXBegin` close the previous primitive proves it, because aurora immediately starts
complaining, 21,511 times in a 22-second run:

```
aurora[warning] aurora::gx: GXEnd: vertex data not evenly divisible: 62 bytes for 4 vertices
```

DevText's quad is 4 x (2 x f32 position + RGBA8) = **48** bytes. Aurora measures a primitive as
*every byte written to its FIFO since `GXBegin`*, so closing late sweeps up whatever else landed
there - register writes, state changes - and the batch is rejected. 62 is 48 plus that debris.

## Two ways to fix it, and why the obvious one failed

1. **Close in the shim at exactly the last vertex.** Tried: count `nVerts x attributes-per-vertex`
   writes and close on the last one. It needs the attribute count to be exactly right, and it is
   not knowable from `gw_GXSetVtxDesc` alone - indexed attributes (`GX_INDEX8`/`GX_INDEX16`) also
   cost one write per vertex, and counting only `GX_DIRECT` closes early and turns the warning
   into `aurora[fatal] draw vertex data overrun: need 52 bytes at pos 1118, have 26`. Correcting
   the predicate to "any attribute that is not `GX_NONE`" removed the divisibility warnings
   entirely but still overran twice, so something else still contributes a write. Backed out.

2. **Fix the measurement in aurora, which is where it belongs.** `GXEnd` should derive the vertex
   span from the current VCD/VAT times `nVerts` rather than from the FIFO buffer delta, so that a
   late `GXEnd` - or none at all, if aurora closes implicitly at the next `GXBegin` or flush - is
   harmless. Aurora is vendored in `extern/aurora`, so this is ours to change. **This is the
   recommended route.**

## Instruments built for this, worth keeping

- `gw_Gx_PrimCount()` - scalar GX primitive counter; sample it across a draw callback to prove
  whether that callback submits anything.
- `gw_Gx_LogState(tag)` - dumps the projection type, six matrix terms and the viewport in effect,
  so a callback can say what transform it actually ran under.
- A draw-list watcher in `DevText_DrawAll` that reports only when the list changes.

Scalar and pointer returns only, and no out-parameters: a game TU's stack accesses are
byte-swapped by gwtool, so a host out-parameter arrives reversed.

# Complete retail stage switching: hosting audit

2026-10-03. Supersedes the fix4 plan's acceptance target: partial native
initialization is not vanilla acceptance. This is an implementation audit, not a
completed engine lifecycle. Fix5's hang repair is separate and implemented.

## The normal path to preserve

`Ground_801C06B8` plans stage files and special render buffers in the preload
cache. `Ground_801C0754` clears stage state, installs the archive, parameters,
callbacks and display state. `Ground_801C0800` registers stage articles, installs
particle bank 0x1E, loads collision, applies background state, creates lights and
calls the stage's complete `on_init`. `Ground_OnLoad` calls `on_load`.
`Ground_801C0FB8` calls `on_start`, drains initialization requests, then creates
the global stage logic proc. Calling only a stage's `on_init` is not this path.

No audited legal-stage initializer has been shown inherently impossible to run
mid-match. Its prerequisites are currently owned by the surrounding scene.
These are the hosting changes needed to make the complete path legal.

## Concrete gaps

1. **Only immutable files should be cached.** `script_stage_slots.inc:124`
   currently instantiates models/markers for every loaded slot. Its parsed DAT
   descriptors are also mutable: Fountain zeros and replaces a public image
   descriptor. Cache raw input plus numeric metadata, then parse a private
   working copy per visit. Include Stadium's `GrPs1..4.dat`, not just `GrPs.dat`.
   Geometry metadata must cover every retail joint/line, rather than filter
   Stadium to joints 4/6. Bounds can be computed during preload using temporary
   objects which are then fully destroyed.
2. **Own the original stage too.** The current original host is hidden, not
   destroyed. Stage proc suppression checks classifier 3, while stage lighting
   uses classifier 13 and stage/reflection cameras use classifier 17. Capture
   creation during the normal stage initialization boundaries, including
   lights, cameras, text, effects, particles and item descendants. Retain its
   file cache so script unload can freshly initialize that original destination.
   Do not identify all classifier-17 objects as disposable: the match camera
   and unrelated scene cameras must survive.
3. **Use retail Ground destruction before raw GObj destruction.**
   `Ground_801C4A08` calls the per-object destruction callback, clears map links,
   frees material state, releases its linked camera, clears joint participation
   and general points, then frees the GObj. Full teardown must order those
   dependencies before releasing the working archive. Current borrowed model
   teardown only removes procs/render links. Avoid double-freeing cameras that
   a Ground destructor has already freed; natural destruction must unregister
   every ownership record.
4. **Reset registries, not just objects.** `ftdevice.c:51` registers Whispy in
   a one-entry wind table. Clearing/freeing its GObj without unregistering that
   entry leaves a dangling callback and the next registration asserts. The
   collision/device, bury and camera-quake registries need owner-specific
   removal, preserving any unrelated caller's entries. StageInfo's auxiliary
   lists and Ground's private map caches need their normal initialization reset.
5. **Own particle banks and raw render buffers.** `particle.c:117` installs
   bank descriptor arrays globally. A live outgoing particle can still read its
   old bank while an incoming stage replaces it. Drain stage-bound generator
   requests/children/joint references before clearing the bank and releasing
   its backing working DAT. Fountain's reflection image is allocated by
   `lb_800121FC`, potentially from a preload entry; freeing its camera alone
   does not release that image buffer. Ownership must distinguish a borrowed
   preload buffer from a fresh HSD allocation and clear the mutable descriptor.
6. **Separate stage buffer entries from fighter preload entries.**
   Fountain reserves buffer ID 2001; Stadium reserves 2002..2005 via
   `lbDvd_80017740`. These use heap 4, which also holds fighters. Re-running
   normal scene preload/heap teardown wholesale can free live fighter data.
   Provide individually owned stage entries, instantiate before retail init,
   and release only those entries after dependent cameras/models die.
   Stadium's asynchronous transformation read/completion must use cached raw
   files and either drain or cancel a visit's pending completion before teardown.
7. **Install complete retail collision topology.** The current adapter fans a
   source joint out to one reserved joint per line. Stadium uses native joint
   enable/disable/list operations and literal lines 0x55/0x6F; those do not pass
   through the single joint-matrix adapter. A complete active native map should
   retain its original indices and all disabled transformation geometry.
   Preserve/rebase the independent script seam pool, invalidate every fighter
   and portable-item contact before swapping the map, then place fighters using
   enabled retail floors. Calling existing `ScriptGame_StagePrepare` unchanged
   would reset independent script models, areas, targets and enemies.
8. **Release/reuse live stage storage without resetting shared HSD pools.**
   Heap 0 holds HSD allocations across fighters, cameras and stages, and
   `HSD_ObjAllocAddFree` feeds global free lists. An arena rewind or heap reset
   would leave those lists and live scene objects pointing into reclaimed data.
   Free stage-specific working archives/raw allocations individually; either
   retain shared pool backing with honest accounting or add safe chunk
   reclamation which never reclaims a chunk containing an unrelated live object.

## Required transition sequence

Preflight offline/fighter eligibility and working-copy/resource capacity before
changing the live stage. Freeze and cover; detach/bench fighters and clear all
stage contacts, attachments and registry references; cancel/drain outgoing
async work; retail-destroy owned stage objects and particles; release stage
buffers, banks and working data. Install the new working archives, complete
collision, StageInfo, article/bank/render resources; execute the normal complete
retail initializer/load/start sequence. Restore fighter participation and CPU
mode, safely place them on enabled geometry, uncover/thaw, and consume queued
music from the normal native loop. Keep the preload cache independent of this
live visit. Resource refusal before commit leaves the outgoing stage intact;
failure after commit needs a tested reconstruction of the old working visit.

## What remains in decompiled stage files

Fix5's hang portion does not alter a decompiled stage file. Fix4 left the
`TARGET_PC` early-return platform-only branch in `grIzumi_801CBE64`, and
`TARGET_PC` private-parameter swap helpers in `grizumi.c` and `grstory.c`.
The branch remains a known violation of the new full-startup target and must be
removed with the complete engine path above. The pointer helpers exist to
restore the old hidden host's private parameter pointer; a single live stage
reinitialized normally should eliminate that restoration scheme. Do not remove
the branch in isolation and call the resulting dual-stage scene vanilla.

Acceptance requires side-by-side normal/switched stages, same inputs/seed and
camera, plus teardown/resource fixtures and actual six-slot heap minima. No
build or game launch was performed in this audit.

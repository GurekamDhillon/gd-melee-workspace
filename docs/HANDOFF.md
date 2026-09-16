# Handoff — stage authoring / custom maps (2026-09-15)

> **DROPPED (2026-09-16).** Stage authoring and the "Blender as a level editor" arc are no longer
> being pursued, by user decision. Everything below the `MELEE_TRAINING` section is retained as a
> **historical record only** — do not resume it. The `MELEE_TRAINING` section is kept because it is
> still current and still correct.
>
> Existing committed work is **not** being reverted: the `.tt` mod loader, `MELEE_TARGET_TEST`,
> `hsd_export`/`stagec`, and the Blender I/O tooling all remain in the tree and remain functional.
> Dropping the project means no further development, not removal. The untracked `_build/` Blender
> artifacts (HSDLib, glTF/GLB, PNGs, DATs) are deliberately **not** committed.

Read `_research/port-dev-quickref.md` first (commands, env vars, toolchain). **§30–§33** of the
DEVLOG cover the stage-authoring reasoning; they are historical as of the drop.

## Objective (historical)

Make **custom stage maps work** in the port: author a map, load it in Fox's Target Test, and have the
geometry actually render and be standable. The longer arc is "use Blender as a level editor" with
`stagec` as the compiler (DEVLOG §33).

## Where it stands

### Proven and working

| Capability | Evidence |
|---|---|
| `stagec rt` — DAT round-trip, lossless | 21 symbols identical; all DL bytes/vert counts preserved (`.dat` 633,100 -> 618,032) |
| Geometry **removal** | every JOBJ's `Dobj = null`; in-game: empty stage, targets + HUD only |
| Emitted DAT **loads and plays** in the engine | Fox spawns and stands; no panic |
| Mesh -> HSD **encoding** (GX encoder) | cube OBJ -> `joints=1 dobjs=1 pobjs=1 dlBytes=160 verts=36` (36 = 12 tris), survives save/reload |
| `stagec coll` — collision dump | reads vertices/links/groups/category offsets of any stage |
| `hsd_export` — DAT -> per-group glTF | used to get Fox's Target Test into Blender (renders correctly) |

### Broken / open

1. **Grafted meshes do not render.** Four variants, all invisible (DEVLOG §31.2):
   group 0 is an anchor with 0 DObjs; group 2 + transform reset; PObj `SingleBoundJOBJ` re-point;
   and clone-and-swap. The clone-and-swap attempt additionally **crashed the game** and left the
   reloaded DL decoding to 4 verts instead of 36 -> **HSDLib's `DisplayListBuffer` setter is not a
   safe in-place DL edit.**
2. **Authored collision panics.** A single `Top` link — hand-rolled *and* via HSDLlib's own
   `GenerateCollData` — crashes on load: `mplib.c:5459 not found lineID=18`, assert `mplib.c:5229`
   (DEVLOG §32.2). Keep the vanilla collision.

Both are problems of **authoring data the engine accepts**, not of the pipeline.

## The next experiment (do this first — it is small and decisive)

**Patch a donor's display list in place, changing only vertex values.**

1. Take `GrTFx.dat` model group **2**'s existing DObj/PObj (its DL is 928 bytes and *does* render).
2. Leave every opcode, attribute descriptor, primitive and offset **byte-identical**.
3. Overwrite **only the position floats** with a box's corners (same vertex count, same layout).
4. Save, patch `melee_mod.iso`, launch with `MELEE_TARGET_TEST=fox`, press Start, capture.

If that renders, custom maps are essentially solved and the compiler becomes "read donor DL ->
rewrite positions". If it does not, escalate to authoring a DL explicitly with `GX_Attribute` /
`HSD_POBJ.FromDisplayList`.

**Do not** re-try: grafting `nj.Dobj` onto a JOBJ, `SingleBoundJOBJ` re-pointing, or DL buffer
swapping — all three are already falsified (§31.2).

## Environment

- Build host: **Windows + WSL**, workspace `/mnt/c/gdm` = `C:\gdm`.
- **Blender 5.2.2** (Steam): `D:\SteamLibrary\steamapps\common\Blender\blender.exe` — run headless
  with `--background --python <script>`, all paths **Windows** paths.
- **HSDLib**: `C:\gdm\_build\HSDLib` (built from source, .NET 10). **3 patches required** — see
  §30.6. Re-apply them if the tree is ever refreshed.
- **Tools**: `_build\stagec` (the compiler), `_build\hsd_export` (DAT -> glTF).
- **Test disc**: `_build\melee_mod.iso` (copy) — `GrTFx.dat` at FST entry `435`,
  disc offset `1296203776`, FST at `0x456e00`. **Restore vanilla `GrTFx.dat` when finished**;
  the current state already has vanilla restored and the game verified healthy.
- Input/capture helpers and their two timeout traps: quickref, "Windows/Blender helpers in `_build/`".

## Constraints and preferences from the user

- **Commit style**: melee fork `pc: <lowercase imperative>`; root `docs:` / `build:` / `tools:`.
  Never `git add -A`. Prefix git commands with `GIT_MASTER=1`; no global identity in WSL, so pass
  `-c user.name="GD" -c user.email="gd@gsd.sh"` per command.
- **Game-source changes** must be `#if defined(TARGET_PC)`-guarded with the original kept.
- The user wants **proof of concept fast** ("make a simple rectangle as a stage and load that with
  fox right quick") before polish. They play-test directly and report what they see.
- Budget matters — build/patch/launch/verify cycles are slow, and two PowerShell/`cmd` traps cost
  15-minute timeouts each (documented in the quickref; do not repeat them).
- Agreed architecture (DEVLOG §33): **Blender = meshes only**; stage semantics belong to a future
  custom editor on HSDLlib; `stagec` is the single source of truth for `.dat`.

## Artefacts to know about

- `_build/GrTFx.dat` — the untouched vanilla stage (keep; it is the restore source).
- `_build/rect.obj`, `_build/cube.obj` — the test meshes (Blender-exported).
- `_build/gltf/grTFx_*.glb` — the 3 model groups of Fox's Target Test, exported.
- `_build/stage_capture*/` — in-game captures from each attempt.
- `_build/press_start.ps1`, `launch_stage.ps1`, `capture_now.ps1` — the drive/capture harnesses.

## MELEE_TRAINING direct launch — RESOLVED

`MELEE_TRAINING=<ckind>` boots straight into Training Mode. Verified in-game: ~15 min continuous
run, `retrace=53520`, 2549 drawcalls / 294,732 verts, **0 FATAL/PANIC/assertion**, 0 allocation
failures.

**Root cause.** Jumping to state 2 skips `gm_801B1C24`, the CSS **exit** handler, which is what
turns `players[1]` — the training dummy — from `ChKind_None` (0x21) into a real character. Left as
`Cpu + ChKind_None`, `ftMapping_list[33]` reads one past a `[33]` array (indices 0..32), so the
match scene builds a fighter with a garbage id and the allocation overflows in
`lbMemory_80014FC8` (`memp_kouho`).

**Fix.** Seed `players[1]` (ckind, color, `cpu_kind`) in the hook. The stage seeding was already
correct — the dummy was the missing piece, which is exactly why all four earlier attempts failed
*identically*: none of them touched `players[1]`.

**Process note.** Six of my hypotheses were refuted; the answer came from Oracle, which had
finished 3h20m earlier but whose result was never delivered (see "background tasks" below). The
measurements were still what made the fix verifiable — and the failure-path diagnostic in
`lbMemory_80014FC8` remains useful.

The investigation history below is kept deliberately: it documents what did *not* work and why.

---

### History (superseded)

`MELEE_TRAINING=<ckind>` boots into Training Mode but dies at
`assertion "memp_kouho" failed in src/melee/lb/lbmemory.c on line 154`, within ~4 frames
(`retrace=4`, `prim=0` — nothing renders).

**What the assert actually means.** `HSD_ASSERT(0xE9, memp_kouho)` fires in
`lbMemory_80014FC8` (`src/melee/lb/lbmemory.c`, defined at line 117) when the arena free-list walk
finds **no block large enough** for the request — i.e. an *arena allocation failure*. It is not a
data-structure problem. Two earlier attempts — seeding `vs->start.rules.stkind` and
`gm_80473814.stage_id`, then `game_cache.stkind` — targeted the wrong subsystem and changed
nothing.

**Caller frames** from `melee-pc.log` resolve to load-related functions —
`_gw_lb_800192A8` (VA `1025FB60`, `lb_0192.c`) and `_gw_lb_800195D0` (VA `1025FDF0`) — with
`_gw_DVDGetDriveStatus` and `_gw_wait_idle` polling underneath. So the failing allocation happens
on a **file-load path during the mode transition**.

> Caveat: those frame attributions come from nearest-preceding-symbol matching, which can overshoot
> into the wrong function. Treat them as indicative. The assert's own location
> (`lbMemory_80014FC8`) is exact — it is read from source, not resolved.

**Why it differs from the working Target Test hook.** Training's state machine is
CSS (0) -> SSS (1) -> GS_TRAINING (2); the hook jumps straight to state 2, so neither the
character nor the stage files are loaded the way states 0/1 would have done. Target Test has only
one scene to skip, and its stage is fixed by the character.

**Attempts so far — four, all failed identically** (same assert, `retrace=4`, `prim=0`,
`drawcalls=0`, nothing renders):

| # | Change | Result |
|---|---|---|
| 1 | seed player + `game_cache.entries[0]` + `lbDvd_SetupVsPreloadCache()`, jump to state 2 | assert |
| 2 | + `vs->start.rules.stkind`, `gm_80473814.stage_id` | assert |
| 3 | + `game_cache.stkind` | assert |
| 4 | + `gm_801B06B0(&css_data, 0x17U, ...)` — the call the CSS state makes | assert |

Attempt 4 was **reverted**: it is unverified and demonstrably insufficient, and a change that
cannot be shown to help does not belong in the tree. The `gm_801B06B0` call may still be
*necessary but insufficient* — that remains unproven either way.

**What the four failures rule out.** The problem is not unpopulated preload-cache fields, and not
the missing match-building call. Both were tried and neither moved the failure. Since the failing
allocation sits on a *file-load* path, the next question to answer is **what is being loaded and
which arena is exhausted** — not more cache seeding. Instrument the allocation (log the requested
size and the arena) rather than guessing at more fields.

**Measurement — the useful output.** Instrumenting the assert to log the requested size gave:

```
lbMemory_80014FC8: ALLOC_FAIL size=0x133740
```

`0x133740` = 1,259,840 bytes (~1.2 MB). That is a **sane, file-sized request**, not garbage from an
uninitialised field — so the arena genuinely cannot hold a ~1.2 MB load. Together with the
file-load call path, this points at a **scene or archive load going into a heap too small for
it**, i.e. heap setup that the skipped CSS/SSS states would normally have performed.

**Arena identified.** Extending the log to include the arena handle gave:

```
ALLOC_FAIL size=0x133740 arena=0x107A9AF8
```

`0x107A9AF8` is neither MEM1 (`0x80000000`) nor ARAM (`0x373CE020`) — it is a **host** address,
because the exe is based at `0x10000000` and game statics land in its data section. Resolving it
against `melee-pc.map`:

```
arena 0x107A9AF8 -> lbMemory_804318B0  (base 0x107A94C0, +0x638)
```

`lbMemory_804318B0` is the **ARAM management structure** (`.bss:0x804318B0`, size `0x6F0`, per
`config/GALE01/symbols.txt`).

**So the failing request is an ~1.2 MB *ARAM* allocation — not MEM1 and not a heap.** That
materially redirects the investigation. The question is no longer "is a preload cache unpopulated"
but **why ARAM cannot satisfy a 1.2 MB request during the training-mode transition**, and whether
ARAM bookkeeping is left inconsistent by skipping the CSS/SSS states.

**Capacity, not fragmentation.** Logging the arena bounds at the failure gave:

```
ALLOC_FAIL size=0x133740 lo=0xF966A0 hi=0x1000000
```

`hi - lo = 0x69960` = **432,480 bytes (~422 KB)** available, against a request of
**0x133740 = 1,259,840 bytes (~1.26 MB)**. The request is roughly **3x the entire remaining
arena**, so the free-list search could never have succeeded — this is a *capacity* problem, not
fragmentation and not a corrupt list. That is why four attempts at populating cache fields changed
nothing: they were never addressing the failure.

`hi` is `0x1000000` (16 MB, host view), which matches the port's boot log (`ARAM 16 MB`,
`ARAM Free Size 9 MB`), so this is consistent with the ARAM arena having been largely consumed by
the time the training transition runs.

**Caller path — the first coherent causal chain in five attempts.** Re-resolving the crash trace
with containing-function bounds (the earlier nearest-symbol pass overshot and gave wrong names):

```
HSD_SynthSFXWaitForLoadCompletion +0x12
lb_800192A8 +0x21D      (load helper)
lb_800195D0 +0xA
lb_8001BD34 +0x317
hsd_803AAA48
OSDisableInterrupts
lb_8001CC84 +0x17       (load/card polling)
DVDGetDriveStatus
```

The failing ~1.26 MB request occurs **while waiting for an SFX to load**. With the arena living in
`lbMemory_804318B0` (the memory manager) and ARAM being the natural home for sound banks, the
coherent reading is:

> the training transition triggers an SFX/audio bank load of ~1.26 MB into an arena with only
> ~422 KB free, and the allocator asserts.

**Measured — and it refutes the "ARAM already drained" hypothesis.** Taking the same measurement
`gmmain.c` uses at boot, again at the top of the training hook:

```
boot:         ARAM Free Size 9 MB
before hook:  TRAINING_DIAG: free=10314080   (~9.8 MB, lo=0x629EA0 hi=0x1000000)
at failure:   lo=0xF966A0 hi=0x1000000       (~422 KB)
```

ARAM is **healthy (~9.8 MB free) when the hook runs**. Roughly **9.4 MB is consumed during the
transition itself**, leaving 422 KB — after which the 1.26 MB SFX-bank request fails.

So the drain is caused by the transition, not by anything preceding it. That also explains why
seeding cache fields changed nothing: the cache was never the problem.

**Preload call is not the drain — measured, hypothesis refuted.** ARAM immediately after
`lbDvd_SetupVsPreloadCache()`:

```
before hook:   free=10314080
after preload: free=10314080   <- unchanged
```

So a double `lbDvd_SetupVsPreloadCache()` consumes **no** ARAM. The ~9.4 MB is consumed **after**
`gm_SetGameModeStateId(2)`, during the state-2 transition and scene load, which leaves 422 KB —
and then the 1.26 MB SFX bank request fails.

**Drain localised to state-2 work.** Three measurements:

```
before hook:      free=10314080
after preload:    free=10314080   (unchanged)
at state2 enter:  free=10314080   (unchanged)
at failure:       ~422 KB
```

The entire ~9.4 MB is consumed **inside the state-2 handler and its scene load**, after
`gm_801B1F70` begins. Nothing before it accounts for any of the drain — which also explains why
every earlier attempt (all of which only touched things *before* state 2) had no effect.

**Correction — the drain is *after* the state-2 handler, not inside it.** Probing between the calls
in `gm_801B1F70` (including either side of `gm_80189CDC`, the match/scene load):

```
before hook:            free=10314080
after preload:          free=10314080
at state2 enter:        free=10314080
before gm_80189CDC:     free=10314080
after  gm_80189CDC:     free=10314080
at failure:             lo=0xF966A0  (same arena, hi=0x1000000)  -> ~422 KB
```

ARAM is untouched throughout the handler. The arena's `lo` moves from `0x629EA0` to `0xF966A0`
(≈ 9.4 MB) **after** `gm_801B1F70` returns — during the scene load the state machine triggers
next, which is also where the failing SFX request lives.

So the search moves out of `gmtrainingmode.c` and into the **GS_TRAINING scene load**. That is the
next file to instrument, not this one.

**Ruled out: port-side ARAM reservation.** `pc/platform/gw_runtime.c` allocates the full
`GW_ARAM_SIZE` (16 MB) up front; the AX shim (`shim_ax.c`) only *reads* sample data out of
`gw_aram`, and `shim_ar.c` implements the SDK AR API on top of that same buffer. The port
therefore does **not** take ARAM the console would have had, so the ~0.9 MB shortfall lies in the
game's own loading, not in port overhead.

**Standing summary:** ARAM is healthy (~9.8 MB) right up to the end of the training handler, and
the scene load then consumes ~9.4 MB, leaving 422 KB — after which a 1.26 MB SFX bank fails. The
load is roughly 0.9 MB short. Six hypotheses have now been refuted by measurement.

**Resolving frames:** the `gw: at melee-pc.map rva 0x...` lines in `melee-pc.log` are full VAs
into `_build/melee-pc.map` (symbol lines look like `<seg>:<off> <symbol> <VA> f <obj>`). Note the
nearest-symbol caveat above: match against the *containing* function's range, not just the closest
preceding symbol.

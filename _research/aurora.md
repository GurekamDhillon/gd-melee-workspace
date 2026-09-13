# Aurora (dusklight fork) — driving it from a new C app, and what its GX layer expects

All paths below are relative to `C:\gdm\dusklight\extern\aurora` unless noted.
Verified by reading source; line cites are `file:line`.

**Headline finding:** this fork of Aurora is *not* the old metaforce-style "GX call → immediate
state struct" library. It is a **GameCube FIFO emulator**. Every GX entry point writes real
GC command-processor opcodes into a byte buffer in **big-endian**, and a **worker thread**
parses that stream (`lib/gx/command_processor.cpp`) and turns it into WebGPU draws. That is
extremely good news for the melee port: the FIFO, display lists, indexed vertex arrays,
indexed XF (matrix) loads, and texture/TLUT data are all consumed as **native big-endian
GameCube data**. It also means a handful of GX entry points have *different signatures* and
several structs are *bigger than melee's*.

---

## 1. Init / frame / shutdown API

`include/aurora/aurora.h` — exact signatures:

```c
AuroraInfo aurora_initialize(int argc, char* argv[], const AuroraConfig* config);
void       aurora_shutdown(void);
const AuroraEvent* aurora_update(void);   // pumps SDL; returns array terminated by AURORA_NONE
bool       aurora_begin_frame(void);      // false => skip this frame entirely
void       aurora_end_frame(void);        // THIS is what presents

void aurora_set_log_level(AuroraLogLevel);
void aurora_set_pause_on_focus_lost(bool);
void aurora_set_background_input(bool);
void aurora_set_resampler(AuroraSampler);
void aurora_set_timescale(float);          // 0.0 = paused, 1.0 default, max 16
AuroraBackend aurora_get_backend(void);
const AuroraBackend* aurora_get_available_backends(size_t* count);
float aurora_get_timescale(void);
```

### `AuroraConfig` (aurora.h:80-125) — every field, in order

```
const char* appName;                 // NULL -> "Aurora"
const char* userPath;                // NULL -> SDL_GetPrefPath
const char* cachePath;               // NULL -> SDL_GetPrefPath
const char* resourcesPath;           // NULL -> SDL_GetBasePath
AuroraBackend desiredBackend;        // BACKEND_AUTO ok
uint32_t msaa;                       // 0 -> forced to 1  (aurora.cpp:118)
uint16_t maxTextureAnisotropy;       // 0 -> forced to 16 (aurora.cpp:121)
bool vsync, startFullscreen, allowJoystickBackgroundEvents,
     pauseOnFocusLost, allowTextureDumps, allowCpuAdapter;
int32_t windowPosX, windowPosY; uint32_t windowWidth, windowHeight;
void* iconRGBA8; uint32_t iconWidth, iconHeight;
AuroraLogCallback logCallback;       // void(level, module, message, len)
AuroraLogLevel logLevel;
AuroraImGuiInitCallback imGuiInitCallback;  // void(const AuroraWindowSize*)
uint32_t mem1Size;                   // MEM1_DEFAULT_SIZE = 24MB; 0 disables
uint32_t mem2Size;                   // ARAM_DEFAULT_SIZE = 16MB; 0 disables
```

`AuroraInfo` returned: `{ backend, userPath, cachePath, SDL_Window* window, AuroraWindowSize windowSize }`.
`AuroraWindowSize` = `{width, height, fb_width, fb_height, native_fb_width, native_fb_height, float scale}`.

### Who owns `main()`

**Your app does.** `include/aurora/main.h` is a 6-line header that does
`int aurora_main(int,char**); #define main aurora_main` — i.e. on platforms where SDL needs to
own the real entry (iOS/Android/SDL_main), including `<aurora/main.h>` renames your `main` to
`aurora_main` and Aurora's `lib/main.cpp` provides the real one. On desktop you can simply write
`int main(...)` and not include that header. Aurora never runs your game loop for you; it has no
callback-driven mode.

### Minimal correct C skeleton

Derived from `examples/simple.c` (the whole file is the canonical example):

```c
#include <aurora/aurora.h>
#include <aurora/event.h>
#include <aurora/main.h>      /* optional on desktop */
#include <dolphin/gx.h>
#include <dolphin/vi.h>

int main(int argc, char* argv[]) {
  const AuroraConfig cfg = { .appName = "Melee", .logCallback = &log_cb };
  AuroraInfo info = aurora_initialize(argc, argv, &cfg);

  GXInit(fifoBuf, fifoSize);      /* returns GXFifoObj*; see §5 */
  VIConfigure(&GXNtsc480IntDf);   /* sets render-mode / fb size */

  bool exiting = false, paused = false;
  while (!exiting) {
    for (const AuroraEvent* e = aurora_update(); e && e->type != AURORA_NONE; ++e) {
      switch (e->type) {
      case AURORA_EXIT:            exiting = true; break;
      case AURORA_PAUSED:          paused = true;  break;
      case AURORA_UNPAUSED:        paused = false; break;
      case AURORA_WINDOW_RESIZED:  info.windowSize = e->windowSize; break;
      case AURORA_SDL_EVENT:       /* e->sdl */ break;
      default: break;
      }
    }
    if (exiting || paused || !aurora_begin_frame()) continue;

    VIWaitForRetrace();     /* YOU must implement this; see §3 */
    game_tick_and_draw();   /* all GX calls here */

    aurora_end_frame();     /* drains FIFO, blits EFB->swapchain, Present() */
  }
  aurora_shutdown();
  return 0;
}
```

Event loop detail: `aurora_update()` returns a pointer into a contiguous array; you walk it with
`++event` until `type == AURORA_NONE`. `AuroraEvent` (`include/aurora/event.h`) is
`{AuroraEventType type; union { SDL_Event sdl; AuroraWindowPos windowPos; AuroraWindowSize windowSize; SDL_JoystickID controller; };}`.
**It embeds `SDL_Event`, so your shim TU needs SDL3 headers** (or you wrap the event pump in C++).

`aurora_begin_frame()` returns false when the window isn't presentable / is paused / surface is
lost (`lib/aurora.cpp:235-259`). You must `continue` — do NOT call `aurora_end_frame()`.

---

## 2. How dusklight structures the game loop

`C:\gdm\dusklight\src\m_Do\m_Do_main.cpp:225-361` (`main01`). **Single-threaded, main thread owns
everything**; Aurora spawns its own FIFO worker internally.

Order per iteration:
1. `aurora_update()` + drain the event array (`:231-269`)
2. `if (!aurora_begin_frame()) continue;` (`:272`)
3. **`VIWaitForRetrace();`** (`:277`) — placed *inside* the frame, right after begin_frame
4. game sim + draw: `mDoCPd_c::read()` → `fapGm_Execute()` → `cAPIGph_Painter()`; this is where
   TP's `GXCopyDisp` lands, deep inside JFWDisplay
5. `aurora_end_frame();` (`:331`)
6. optional frame limiter: `Limiter::Sleep(1e9/maxFrameRate)` (`:340-358`, `src/dusk/time.h:26`)

There is **no separate render thread** and **no VI interrupt thread**. 60 Hz pacing comes from
either Aurora's vsync (`AuroraConfig.vsync`) or dusklight's own `Limiter`, never from VI.

TP's `VIWaitForRetrace` is *not* Aurora's — dusklight implements it in
`C:\gdm\dusklight\src\dusk\stubs.cpp:314-370`:

```cpp
static u32 sRetraceCount = 0;
void VIWaitForRetrace() {                 // does NOT block
    sRetraceCount++;
    if (sVIPreRetraceCallback)  sVIPreRetraceCallback(sRetraceCount);
    if (sVIPostRetraceCallback) sVIPostRetraceCallback(sRetraceCount);
}
u32  VIGetRetraceCount() { return sRetraceCount; }
void VISetBlack(BOOL)    { STUB }
void VISetNextFrameBuffer(void*) { STUB }
void* VIGetCurrentFrameBuffer() { return NULL; }
VIRetraceCallback VISetPre/PostRetraceCallback(cb) { swap+return old; }
```

The comment at `stubs.cpp:310-314` states the design explicitly: the retrace interrupt is
*simulated* by one synchronous call per frame from the main loop, which fires the game's own
pre/post retrace callbacks so its message queues get pumped.

**Direct implication for melee:** HSD's `HSD_VIGetXFBDrawEnable`/`HSD_VIWaitXFBDrawEnable`
(`src/sysdolphin/baselib/video.c:195`) spins on `VIWaitForRetrace()` until a post-retrace
callback flips XFB state. Since `VIWaitForRetrace` never blocks and the callbacks run inline,
that spin terminates only if your retrace callback actually advances the XFB state machine.
Plan on driving `__VIRetraceHandler`-equivalent state yourself, exactly like dusklight does.

---

## 3. VI / GX presentation semantics — implemented / no-op / absent

| Symbol | Aurora status | Cite |
|---|---|---|
| `VIInit` | **no-op** | `lib/dolphin/vi/vi.cpp:37` |
| `VIConfigure(rm)` | **real** — stores `GXRenderModeObj`, and if `fbWidth`/`efbHeight` changed calls `window::request_frame_buffer_resize()` | `vi.cpp:20-29, 38` |
| `VIConfigurePan` | **no-op** | `vi.cpp:39` |
| `VIFlush` | **no-op** | `vi.cpp:45` |
| `VIGetTvFormat` | returns 0 (NTSC) | `vi.cpp:44` |
| `VIWaitForRetrace` | **ABSENT** (declared `include/dolphin/vi.h:17`, never defined in `lib/`) | — |
| `VISetNextFrameBuffer` | **ABSENT** | — |
| `VISetBlack` | **ABSENT** | — |
| `VIGetRetraceCount`, `VIGetNextField`, `VIGetCurrentFrameBuffer`, `VIGetNextFrameBuffer`, `VIGetDTVStatus` | **ABSENT** | — |
| `VISetPreRetraceCallback` / `VISetPostRetraceCallback` | **ABSENT** | — |
| PC extras: `VISetWindowTitle/Fullscreen/Size/Position`, `VICenterWindow`, `VISetFrameBufferScale`, `VILockAspectRatio` | **real** | `vi.cpp:47-53` |

> Verified by grepping the entire aurora tree for those symbols: the only hits are in
> `include/dolphin/vi.h`. **Every one of them is your shim's job.** Copy dusklight's 60-line
> `stubs.cpp` implementation.

GX side:

| Symbol | Status | Cite |
|---|---|---|
| `GXCopyDisp(dest, clear)` | **NO-OP, empty body** | `lib/dolphin/gx/GXFrameBuffer.cpp:211` |
| `GXSetDispCopySrc` / `GXSetDispCopyDst` | **no-op** | `GXFrameBuffer.cpp:158, 167` |
| `GXSetDispCopyYScale` | **returns 0** (real GX returns #xfb lines) | `GXFrameBuffer.cpp:180` |
| `GXSetDispCopyGamma`, `GXSetCopyFilter` | **no-op** | `GXFrameBuffer.cpp:207, 205` |
| `GXSetCopyClear` | **real** — writes BP 0x4F/0x50/0x51 | `GXFrameBuffer.cpp:182-203` |
| `GXSetTexCopySrc` / `GXSetTexCopyDst` | **real** — `GX_AURORA_LOAD_COPY_SRC/DST` | `GXFrameBuffer.cpp:160, 169` |
| `GXCopyTex(dest, clear)` | **real** — emits dest ptr + BP 0x52, then `fifo::publish()`; resolves EFB into a cached WebGPU texture keyed by `dest` pointer | `GXFrameBuffer.cpp:213-223`, `GXFrameBuffer.cpp:36-84` |
| `GXDrawDone()` | **real** — `GXFlush(); write BP drawdone; fifo::drain()` (blocks until worker caught up) | `lib/dolphin/gx/GXManage.cpp:253-257` |
| `GXSetDrawDone()` | **real** — same but `fifo::publish()` (async) | `GXManage.cpp:259-263` |
| `GXSetDrawDoneCallback(cb)` | **real**, returns old; fires **on the FIFO worker thread** | `GXManage.cpp:265`, `lib/gx/fifo.cpp:37-41, 66-68` |
| `GXWaitDrawDone()` | **ABSENT** — only declared, `include/dolphin/gx/GXManage.h` | — |
| `GXFlush()` | **real** but only flushes dirty shadow state (`__GXSetDirtyState`), does not publish | `GXManage.cpp:267-271` |
| `GXAbortFrame()` | **ABSENT** — declared `include/dolphin/gx/GXManage.h:22`, never defined | — |
| `GXSetMisc` | **ABSENT** — declared only | — |
| `GXPixModeSync`, `GXTexModeSync` | **real** (BP writes) | `GXManage.cpp:273-281` |
| `GXInvalidateTexAll` | **no-op** | `lib/dolphin/gx/GXTexture.cpp:347-349` |
| `GXInitTexCacheRegion`/`GXInitTlutRegion`/`GXSetTexRegionCallback`/`GXSetTlutRegionCallback`/`GXPreLoadEntireTexture` | **ABSENT** (`// TODO` at `GXTexture.cpp:341-346, 352-355`); `GXInit` has them commented out at `GXManage.cpp:180-190` | — |

**What actually presents a frame: `aurora_end_frame()` and nothing else**
(`lib/aurora.cpp:261-...`). It: `gx::fifo::drain()` → `fifo::end_frame()` → `gfx::finish()` →
computes present viewport → begins an "EFB copy render pass" that blits the resolved EFB texture
to the swapchain view with `g_CopyPipeline` → ImGui pass → `queue.Submit` → `surface.Present()`.
`GXCopyDisp` contributes nothing. So in the melee port, `HSD_VICopyEFB2XFBPtr`'s `GXCopyDisp`
calls are free, and exactly one `aurora_end_frame()` per displayed frame is what the game sees.

---

## 4. Endianness contract of Aurora's GX

**Aurora reads GameCube-format big-endian source data everywhere, and the FIFO itself is
big-endian.** This is the single most important compatibility fact for this port.

* FIFO writes byte-swap on the way in: `lib/gx/fifo.hpp:71-89`
  ```cpp
  inline void write_u16(uint16_t v){ auto out = bswap(v); write_data(&out,2); }
  inline void write_u32(uint32_t v){ auto out = bswap(v); write_data(&out,4); }
  inline void write_u64(uint64_t v){ ... }  inline void write_f32(float v){ ... }
  ```
  `bswap` at `lib/internal.hpp:42-74` (`__builtin_bswap16/32/64`). `write_u8` is raw.
  So the command stream in memory is byte-identical to a real GC FIFO/display list.
  The one documented exception: `GXBeginIndexed`'s index array is written host-endian
  (`lib/dolphin/gx/GXVert.cpp:70-71`, comment "Indices are host-endian even in a big-endian FIFO`) —
  but that's an Aurora-only extension melee never calls.

* **`GXSetArray` vertex arrays**: Aurora's signature is
  `void GXSetArray(GXAttr attr, const void* data, u32 size, u8 stride, bool le)`
  (`include/dolphin/gx/GXGeometry.h:36`, impl `lib/dolphin/gx/GXGeometry.cpp:218-235`).
  `le=false` (the default you want) means **the array is big-endian GC data**. The byte-swap is
  performed **in the generated WGSL vertex-fetch shader**, per-attribute, via
  `AttrConfig::le` (`lib/gx/gx.cpp:389, 400, 405`; shader emission `lib/gx/shader.cpp:606-608`).
  Arrays are never copied or pre-swapped on the CPU — Aurora reads the game's own memory.
  **Compat note:** melee's header already carries the compatibility macro
  `#define GXSETARRAY(attr,data,size,stride,le) GXSetArray((attr),(data),(stride))`
  (`C:\gdm\melee\extern\dolphin\include\dolphin\gx\GXGeometry.h:11`) and Aurora defines the
  5-arg version of the same macro (`GXGeometry.h:37`). So melee game code that uses `GXSETARRAY`
  ports cleanly; any *direct* `GXSetArray(attr, data, stride)` call site needs the extra
  `size` and `le` arguments. Aurora **requires** `size` (it bounds-checks indexed loads,
  `command_processor.cpp:266-268`).

* **`GXCallDisplayList(data, nbytes)`**: `memcpy`s the display list bytes straight into the FIFO
  and publishes (`lib/dolphin/gx/GXDispList.cpp:48-63`). Since the FIFO is big-endian, **melee's
  on-disc big-endian display lists are consumed verbatim, zero conversion.**
  `GXBeginDisplayList`/`GXEndDisplayList` redirect FIFO writes into the caller's buffer and
  save/restore the `__GXData_struct` shadow registers (`GXDispList.cpp:11-46`) — matches real GX.

* **Indexed matrix loads (`GX_LOAD_INDX_A..D`)**: `lib/gx/command_processor.cpp:251-275`.
  Reads `array.stride`-strided data out of the game's array and calls
  `copy_xf_data(dstAddr, srcData, len, array.le ? std::endian::little : std::endian::big)` —
  i.e. **big-endian by default**. Bounds-asserted against the `size` you passed to `GXSetArray`.

* **`GXInitTexObj` image data**: stores the raw pointer only (`GXTexture.cpp:76, 101-105`);
  the decoder in `lib/gfx/texture_convert.cpp` byte-swaps while untiling
  (`texture_convert.cpp:326, 338, 355, 432-433` — `bswap(in[x])`, `bswap(*(u16*)src)` for CMPR).
  So **GC-tiled, big-endian texture data is what it wants.**

* **`GXInitTlutObj` palettes**: pointer + format + entry count stored
  (`GXTexture.cpp:308-319`); conversion in `lib/gfx/tex_palette_conv.cpp` / `texture_convert.cpp`
  with the same `bswap` on 16-bit entries. **Big-endian palettes.**

* **`GXSetTexCoordGen*` / TEV / transform**: pure register writes into the BE FIFO
  (`GXGeometry.cpp:237+`, `GXTev.cpp`, `GXTransform.cpp`). No data pointers, endianness moot.

### Immediate-mode vertex entry points — real exported functions, not header inlines

`lib/dolphin/gx/GXVert.cpp` (266 lines) exports all of these as real `extern "C"` symbols that
append to the FIFO — there is **no `GXWGFifo` write-through-a-pointer macro** for them:

`GXBegin`, `GXBeginIndexed` (Aurora extension), `GXEnd`,
`GXPosition3f32/3u16/3s16/3u8/3s8/2f32/2u16/2s16/2u8/2s8/1x16/1x8`,
`GXNormal3f32/3s16/3s8/1x16/1x8`,
`GXColor4f32/4u8/3u8/1u32/1u16/1x16/1x8`,
`GXTexCoord2f32/2u16/2s16/2u8/2s8/1f32/1u16/1s16/1u8/1s8/1x16/1x8`,
`GXCmd1u8/1u16/1u32/1u64`, `GXParam1u8/1u16/1u32/1s8/1s16/1s32/1f32/3f32/4f32`.

`GXBegin` (`GXVert.cpp:37-54`) flushes dirty state, writes `vtxFmt|primitive` + `u16 nVerts`;
`nVerts == GX_AUTO` switches to an Aurora `GX_AURORA_DRAW_SIZED` command whose byte length
`GXEnd` back-patches. `GXEnd` calls `fifo::finish_draw()`.

**Melee impact:** melee's `dolphin/gx/GXVert.h` almost certainly declares these as inline
`GXWGFifo.f32 = x;` writes to the write-gather pipe at `0xCC008000`. Those inlines must be
removed/redirected to Aurora's real symbols, or the LLVM-swapped game code will write to a
pointer nobody reads. Check `C:\gdm\melee\extern\dolphin\include\dolphin\gx\GXVert.h` before
anything else.

---

## 5. Struct layouts on 32-bit, vs melee's definitions — **SIZE MISMATCHES**

Aurora's public `GXStruct.h` deliberately enlarges two objects under `TARGET_PC`
(`include/dolphin/gx/GXStruct.h:64-78`):

```c
typedef struct { #ifdef TARGET_PC u32 dummy[16]; #else u32 dummy[8];  #endif } GXTexObj;
typedef struct { #ifdef TARGET_PC u32 dummy[10]; #else u32 dummy[3];  #endif } GXTlutObj;
```

| Object | melee (`C:\gdm\melee\extern\dolphin\include`) | Aurora `TARGET_PC` | 32-bit payload actually stored | Verdict |
|---|---|---|---|---|
| `GXTexObj` | `u32 dummy[8]` = **32 B** (`gx/GXStruct.h:38-41`) | `u32 dummy[16]` = **64 B** | `GXTexObj_` = `4×u32 + 2 ptr + 5×u32 + GXTlut + u8` ≈ **52 B** on i686 (`lib/gfx/texture.hpp:67-113`) | ⚠️ **BREAKS.** melee-sized 32 B is too small; `static_assert(sizeof(GXTexObj_) <= sizeof(GXTexObj))` at `texture.hpp:113` would fail, and at runtime `GXInitTexObj` writes ~52 B into a 32 B slot. |
| `GXTlutObj` | `u32 dummy[3]` = **12 B** (`GXStruct.h:53-56`) | `u32 dummy[10]` = **40 B** | `GXTlutObj_` = `2×u32 + u16 + ptr + enum + 2×u32 + u8` ≈ **28 B** on i686 (`texture.hpp:115-129`) | ⚠️ **BREAKS.** 12 B far too small. |
| `GXLightObj` | `u32 dummy[16]` = **64 B** | `u32 dummy[16]` = **64 B** | `GXLightObj_` = `GXColor + 12 f32` = **52 B** (`lib/gx/gx.hpp:24-39`) | ✅ identical, fits |
| `GXTexRegion` | `u32 dummy[4]` = 16 B | `u32 dummy[4]` = 16 B | never written (all region APIs absent) | ✅ same size, inert |
| `GXTlutRegion` | `u32 dummy[4]` = 16 B | `u32 dummy[4]` = 16 B | never written | ✅ same size, inert |
| `GXRenderModeObj` | 14 fields, `viTVmode`…`vfilter[7]` (`GXStruct.h:11-26`) | **field-for-field identical** (`include/dolphin/gx/GXStruct.h:41-55`) | copied by value into `std::optional<GXRenderModeObj>` (`vi.cpp:16, 25`) | ✅ byte-compatible |
| `GXFifoObj` | `u8 pad[128]` (`gx/GXFifo.h:11-14`) | `u8 pad[128]` (`include/dolphin/gx/GXFifo.h:10-12`) | **nothing** — Aurora keeps one `static GXFifoObj sFifoObj` and never reads it; `GXInit` returns `&sFifoObj` (`GXManage.cpp:13, 30-33, 250`) | ✅ same size; contents meaningless |
| `PADStatus` | `u16 button; s8×4; u8×4; s8 err;` = 11 B, align 2 → **12 B** (`dolphin/pad.h:62-73`) | adds `#ifdef TARGET_PC u32 extButton;` → align 4, offset 12 → **16 B** (`include/dolphin/pad.h:92-106`) | `PADRead` writes 4 entries | ⚠️ **BREAKS.** melee declares `PADStatus status[4]` / `PADStatus now[4]` on the **stack** (`src/melee/db/dbinit.c:33`, `src/sysdolphin/baselib/controller.c:62,101`, `debugconsole_main.c:2461` uses `[8]`) — Aurora's `PADRead` would stride by 16 and smash 16 bytes past the array. |

**Byte-for-byte memcpy of any of these objects stays valid** *within* one world (all are POD; no
vtables, no self-pointers, no ownership) — `GXTexObj_` holds only raw `const void*` back-pointers
into game memory and integer ids, and Aurora itself memcpys `__GXData_struct` wholesale in
`GXBeginDisplayList` (`GXDispList.cpp:22, 41`). **But you cannot memcpy between a melee-sized and
an Aurora-sized object.** Melee's game code allocates all of these (HSD image/tlut descriptors
embed `GXTexObj`/`GXTlutObj` in heap structures), so the fix is mandatory, not optional.

**Recommended fix:** patch `C:\gdm\melee\extern\dolphin\include\dolphin\gx\GXStruct.h` and
`pad.h` under a `TARGET_PC` guard to match Aurora exactly (`dummy[16]`, `dummy[10]`,
`+u32 extButton`) — this is precisely what dusklight/Aurora did for TP. Anything that computes a
struct size numerically (`sizeof` in a decomp-matching assert, a hardcoded 0x20 offset in HSD's
image structs) must be re-checked. Grep melee for `0x20`-sized `GXTexObj` embeddings before
committing.

---

## 6. SDK module coverage

| Module | Status | Evidence |
|---|---|---|
| **OS** | **partial**. Real: `OSAlloc`/heaps, `OSArena`, `OSReport`/`OSPanic`/`OSFatal`, `OSTime`/`OSTick`/calendar, `OSPhysicalToCached` family, `OSGetPhysicalMemSize`, `OSInit` (stub body), `OSBootInfo`. **ABSENT: all threading, synchronization, interrupts and alarms** — `OSCreateThread`, `OSGetCurrentThread`, `OSInitMutex`, `OSInitMessageQueue`, `OSSetAlarm`, `OSDisableInterrupts`, `OSInitFastCast` return **zero grep hits** across `lib/`. Headers exist (`include/dolphin/os/OSThread.h` etc.) but no implementations. | `lib/dolphin/os/*.cpp` (8 files) |
| **PAD** | **real and substantial** (1200+ lines, SDL3 gamepad backend, remapping, rumble, virtual pads): `PADInit`, `PADRead`, `PADClamp`, `PADClampCircle`, `PADControlMotor/AllMotors`, plus PC extras `PADCount`, `PADSetPortForIndex`, `PADGetVidPid`, `PADSetButtonMapping`. `PADReset`/`PADRecalibrate`/`PADSetSpec`/`PADSetAnalogMode` are no-op-true stubs. | `lib/dolphin/pad/pad.cpp:314,378,397,712,1122` |
| **SI** | **stub** — only `SIProbe` exists (returns `SI_GC_CONTROLLER` / `SI_GC_WAVEBIRD` / `SI_ERROR_NO_RESPONSE`). Nothing else. | `lib/dolphin/si/si.cpp` (whole file, 21 lines) |
| **AR / ARAM** | **real emulation** — malloc'd `mem2Size` buffer, bump allocator matching `ARAlloc` semantics, `aramToHost()` translation. | `lib/dolphin/AR.cpp:1-60` |
| **AI** | **ABSENT** — header `include/dolphin/ai.h` declares the API (with a PC-only `AIInitDMA(uintptr_t,...)` variant) but there is **no implementation anywhere in `lib/`**. | grep `AIInitDMA\|AIStartDMA` in `lib/` → 0 hits |
| **DSP** | **ABSENT** — no implementation. | grep `DSPInit\|DSPAddTask` in `lib/` → 0 hits |
| **CARD** | **real** — full memory-card emulation: GCI folder + raw-file backends, BAT, directory, SRAM. | `lib/dolphin/card.cpp` (741 lines), `lib/card/*` (20 files) |
| **DVD** | **real** — ISO/FST-backed; `DVDInit` no-op, `DVDOpen`/`DVDRead*Async*`/`DVDGetCommandBlockStatus`/inquiry/streaming all implemented; dusklight mounts via the extension `aurora_dvd_open(path)`. | `lib/dolphin/dvd/dvd.cpp:717-948`, `lib/dolphin/dvd/fst.cpp`, used at `dusklight src/m_Do/m_Do_main.cpp:799,892` |
| **MTX** | **real** — the actual Dolphin SDK C reference implementations, ported (`C_MTXIdentity`, mtx44, mtxstack, mtxvec, quat, vec). | `lib/dolphin/mtx/*.c` (6 files) |
| **GD** | **real** — full display-list builder: base/geometry/indirect/light/pixel/tev/texture/transform + `GDAurora.cpp`. | `lib/dolphin/gd/*.cpp` (9 files) |
| *(extra)* **THP** | real (`THPAudio.cpp`, `THPDec.cpp`) | `lib/dolphin/thp/` |

### `OSGetTime` units

`OSTime` is in **GC timer ticks**, not nanoseconds: `duration_to_ticks()` converts a
`std::chrono` duration by `seconds * OS_TIMER_CLOCK + ns * OS_TIMER_CLOCK / 1e9`
(`lib/dolphin/os/OSTime.cpp:80-86`), with `OS_TIMER_CLOCK = OS_BUS_CLOCK / OS_TIMER_CLOCK_DIVIDER`
(`include/dolphin/os.h:102`) — i.e. the standard 40.5 MHz bus/4 tick, so
`OSTicksToMilliseconds` etc. work unchanged. `OSGetTick()` = low 32 bits of `OSGetTime()`
(`OSTime.cpp:93`). `OSGetTime()` is anchored so that it tracks Aurora's **game clock**
(`aurora::time::game_clock`, affected by `aurora_set_timescale`), offset once at first call to
agree with wall time (`OSTime.cpp:88-98`). `OSGetSystemTime()` is true wall time measured from the
**GCN epoch 2000-01-01 UTC** (`OSTime.cpp:18, 155`). `OSGetNativeTime()` is untimescaled.

---

## 7. 64-bit-only things that break on i686 MSVC

1. **`reinterpret_cast<u64>(pointer)` — 5 sites.** MSVC rejects `reinterpret_cast` from a 32-bit
   pointer to a 64-bit integer (ill-formed; `error C2440`). Must become
   `static_cast<u64>(reinterpret_cast<uintptr_t>(p))`:
   - `lib/dolphin/gx/GXExtra.cpp:27`
   - `lib/dolphin/gx/GXFrameBuffer.cpp:214` (`GXCopyTex` dest)
   - `lib/dolphin/gx/GXGeometry.cpp:229` (`GXSetArray` base)
   - `lib/dolphin/gx/GXTexture.cpp:83` (texobj data) and `:96` (tlut data)
2. **Matching reads**: `command_processor.cpp:589, 610, 640, 687, 701` do
   `reinterpret_cast<const void*>(reader.read<u64>())` — same problem in reverse (narrowing a
   `u64` to a 32-bit pointer via `reinterpret_cast` is also ill-formed). Route through
   `static_cast<uintptr_t>`. The FIFO wire format staying 64-bit is fine and desirable — just fix
   the casts. Note this means **8 bytes per pointer in the FIFO regardless of host width**, so
   the command stream is width-independent; do not "optimize" it to 32-bit or you break
   display-list compatibility with Aurora's parser.
3. **`GXTexObj_` / `GXTlutObj_` shrink on 32-bit** (two pointers, 8 B less each). Their
   `static_assert(sizeof(...) <= sizeof(GXTexObj))` still holds against `dummy[16]`/`dummy[10]`,
   so no build break — but it means **the same `GXTexObj` bytes are not portable between a
   32-bit and 64-bit build**. Any serialized/cached texobj must be regenerated.
4. **`OSTime` is `s64`** and is used in arithmetic throughout (`OSTime.cpp:80-86`,
   `s_gameEpochOffset`). Fine on i686 but expect `__alldiv`/`__allmul` CRT helper calls; make sure
   your LLVM byte-swap pass does not mangle 64-bit loads/stores of these *host-side* values —
   `OSTime` crosses the shim boundary into swapped game memory.
5. **`AIInitDMA(uintptr_t start_addr, u32 length)`** under `TARGET_PC`
   (`include/dolphin/ai.h:22`) — signature is pointer-width-dependent; melee's is `u32`. Moot
   today since AI is unimplemented, but flag it when you write the audio shim.
6. **Dawn/WebGPU itself**: `aurora_end_frame` and the whole `lib/webgpu` layer assume Dawn is
   available for the chosen backend. On 32-bit Windows only D3D11/D3D12/Vulkan are plausible;
   `PreferredBackendOrder` (`lib/aurora.cpp:63-90`) is compiled from `DAWN_ENABLE_BACKEND_*`
   defines, so verify your 32-bit Dawn build actually defines at least one, otherwise
   `AURORA_ASSERT(windowCreated, ...)` (`aurora.cpp:156`) aborts at init.
7. **C++20 requirements** in the parts you may need to touch: `std::stop_token`/`std::jthread`
   (`lib/gx/fifo.cpp:76-107`), `std::atomic<T>::wait/notify_all`, `std::endian`,
   `chrono::zoned_time`. MSVC 19.30+ / `/std:c++20` required; these are all width-agnostic.

---

## Practical checklist for the melee port

1. **Write the VI shim yourself** — Aurora has none. Port
   `C:\gdm\dusklight\src\dusk\stubs.cpp:310-370` verbatim and extend it to drive HSD's XFB state
   machine (`src/sysdolphin/baselib/video.c`), since `HSD_VIWaitXFBDrawEnable` spins on
   `VIWaitForRetrace()`.
2. **Add `GXWaitDrawDone` and `GXAbortFrame`** — melee calls the former
   (`src/sysdolphin/baselib/video.c:270`). `GXWaitDrawDone()` should be
   `aurora::gx::fifo::drain()`; `GXAbortFrame()` can be `fifo::clear_buffer()` or a no-op.
3. **Fix the three struct sizes** (`GXTexObj` 32→64, `GXTlutObj` 12→40, `PADStatus` 12→16) in
   melee's `extern/dolphin/include` before the first link, or you get silent heap/stack
   corruption rather than a compile error.
4. **Neutralize melee's `GXVert.h` write-gather-pipe inlines** in favour of Aurora's real
   `GXPosition*`/`GXColor*`/`GXTexCoord*` exports.
5. **`GXSetArray` needs `size` and `le=false`** at every call site; use the `GXSETARRAY` macro
   that already exists in both trees.
6. **Do not pre-swap any GX source data.** Vertex arrays, display lists, textures, TLUTs and
   indexed matrix arrays must stay big-endian — which is exactly what the LLVM byte-swap pass
   already guarantees for all game memory. This is the cleanest possible fit.
7. **Supply your own OS threading/mutex/message/alarm/interrupt layer, plus AI and DSP.**
   Aurora provides none of those.

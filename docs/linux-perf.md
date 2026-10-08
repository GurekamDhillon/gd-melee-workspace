# Linux performance: why an online match ran at ~48 fps, and what changed (0.2.1-perf1)

Written 2026-10-08 (lane `linux-perf`: game branch `agent/linux-perf`, workspace branch `ws/linux-perf`).
This note wins over older statements about Linux snapshot cost. Netplay protocol is still **5**; no packet changed.

## What the laptop logs showed

Owner's laptop: Hyprland/Wayland, Intel Iris Xe + NVIDIA RTX A500, 0.2.1-test1 Linux build, online against Windows.

| | Linux laptop | Windows |
|---|---|---|
| rollback snapshot SAVE per tick | 8.04 ms | 0.77 ms |
| `frame_work` mean | 18.1 ms (90 % of ticks over 16.7) | 4.95 ms |
| sim ("new iter") | 10.3 ms | 11.4-12.2 ms |

The simulation is not slower on Linux. The save is 10x slower.

## Root cause: Linux ran the snapshot code in FULL-COPY mode

`gw_snap.c` has two modes. **Dirty-page mode** copies only the 4 KB pages written since the last save; it needs the OS to say
which pages were written, which Windows does for free (`VirtualAlloc(MEM_WRITE_WATCH)` + `GetWriteWatch`). The Linux
`VirtualAlloc` shim refused `MEM_WRITE_WATCH`, so `gw_mem1_watched` was 0 and the log said
`snap: SyncTest k=8 (10 slots of 47873981 bytes), full-copy mode`. Every save then did, for each of the 10240 pages of
MEM1, a `memcmp` against the previous copy (reads 40 MB twice) and a copy of what differed. A match writes about 170
pages per tick, so almost all of that is wasted memory traffic. The laptop profile (`perf`) agrees: the SSE2 `memcpy` and
SSE4.2 `memcmp` loops are the hot spots, the kernel only ~4 %. It was not glibc, page faults, `madvise`, optimisation
flags or alignment.

## The fix: `pc/platform/gw_writewatch_linux.c`

Provides `GetWriteWatch` / `ResetWriteWatch` for MEM1 on Linux.

* **userfaultfd write-protect, async mode + `PAGEMAP_SCAN`** (Linux 6.7+). MEM1 is write-protected; the kernel resolves the
  first write to a page itself (no signal) and marks it written; one ioctl returns the written pages and re-protects them.
  Only MEM1 pays (one minor fault per page written per tick, ~170).
* A **self-test** runs at start (user write, kernel write via `read(2)`, a rewrite after reset, "nothing reported when
  nothing was written"). If it fails, or the kernel is older, `VirtualAlloc` returns NULL and the game runs full-copy mode
  exactly as before. The log says which: `snap: write-watch backend: ...`.
* **soft-dirty** (`/proc/self/clear_refs`) exists but is opt-in only (`MELEE_WRITEWATCH=softdirty`). `clear_refs`
  write-protects the whole process, so every heap page touched between two polls faults; measured in WSL2 it moved the cost
  out of the save and into the simulation (save 14.5 to 5.3 ms, sim 72 to 81 ms): no gain. It is kept to exercise the
  dirty-page code paths on kernels without `PAGEMAP_SCAN`.
* `MELEE_WRITEWATCH=auto|uffd|softdirty|off`.

`snap: save cost per op ... = write-watch poll + page copy + globals + other` is logged every 600 saves.

What the snapshot holds is unchanged: slots are supersets-by-construction (a page reported dirty that is not is copied
anyway); the dirty path is the same code Windows has always used. Rollback hash logs of the confirmed frames are
byte-identical between `MELEE_WRITEWATCH=off` and `softdirty` (see "Evidence" in the lane report).

## GPU selection

Aurora already requests Dawn's **HighPerformance** adapter. In the laptop logs only the NVIDIA ICD has a 32-bit build
(`lib32-vulkan-intel` missing), and the profiles show only NVIDIA driver code, so the game was on the RTX GPU. Nothing
logged it, though. Now:

* startup logs `gw: gpu: <device> [<vendor>, vendor 0x.. device 0x.., <type>, <backend>, driver ...] - chosen by ... | also available: ... | surface format ..., present mode ...`
* `MELEE_GPU=integrated|discrete|<text>` chooses (text matches device or vendor: `nvidia`, `intel`, `rtx`); `MELEE_GPU_LIST=1` also probes the other power
  preference so both adapters are named. A GPU with no 32-bit Vulkan driver cannot appear.
* NVIDIA PRIME offload variables (`__NV_PRIME_RENDER_OFFLOAD=1 __VK_LAYER_NV_optimus=NVIDIA_only`) only matter for GL/Vulkan
  loaders that see both GPUs; with a single 32-bit ICD they change nothing.

## Window size

`window 640x577` / `950x577` is not a bug. The game asks for 1280x960; a tiling Wayland compositor (Hyprland) gives the window its
tile, and Aurora's render scale `Auto` follows the window's pixel size. The log now prints `(requested 1280x960)` next to it.

## Other things in the logs

* Present mode `FifoRelaxed` (vsync) is right. `MELEE_VSYNC=0` asks for Mailbox, else Immediate; useful as an A/B on the laptop.
* The `worker` figure (render thread busy time) includes waiting in present under vsync (14 ms with 20 draws in the menus),
  so it is not CPU load. `submit` (~7.6 ms in a match, independent of draw count, against 2.6 ms on Windows D3D11) is the
  remaining Linux-specific cost: main-thread time in `aurora_end_frame` that also covers back-pressure from the render
  worker and the NVIDIA 32-bit Vulkan driver. Not fixed here; see the owner steps below.
* Aurora, Dawn and SDL were compiled `clang -m32` with **no SSE** (x87 float math) while Windows and the game use SSE2.
  `build_aurora_linux.sh` now passes `-msse2 -mfpmath=sse` (`GW_AURORA_CPUFLAGS=""` restores the old build). Effect on the
  laptop is unmeasured.

## Owner test (0.2.1-perf1 Linux build)

Run the same online match again, or an offline one. Please send back (from `~/.local/share/melee-linux/runs/<id>/`):
`melee-pc.log`, `perf.json`, `launch-diagnostics.txt`. The lines that matter:

```
grep -a -E "gw: gpu:|write-watch backend|SyncTest|save cost per op|rb: tick work|perf: scene" melee-pc.log
```

Expected: `write-watch backend: userfaultfd write-protect (PAGEMAP_SCAN)`, `dirty-page mode`, `save cost per op` around 1 ms or
less, `tick work ... save` under 1.5 ms, `over 16.7 ms` a few percent. If it says `full-copy mode` the reason is on the line
before it (`write-watch: uffd backend unavailable (...)`): send that line.

Optional A/B runs (one change each; start the game from a terminal): `MELEE_VSYNC=0`, `MELEE_GPU_LIST=1`,
`MELEE_WRITEWATCH=off` (to see the old cost again).

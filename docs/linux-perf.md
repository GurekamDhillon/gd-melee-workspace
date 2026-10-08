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

## Evidence (this lane, WSL2 Debian + Windows 11, same desktop)

* Baseline, WSL, rollback live test (`MELEE_RB_LIVETEST=1 MELEE_RB_FAKE=2 MELEE_RB_INPUT=live`, Fox vs Marth FD):
  `snap: SyncTest k=8 (10 slots of 47873981 bytes), full-copy mode`, `rb: tick work ... save 14.45 / 12.88 / 12.37 ms`.
* The WSL2 kernel is 6.6 (no `PAGEMAP_SCAN`), so the userfaultfd backend was exercised on a 6.12.107 kernel under QEMU
  (static 32-bit `tools/port/tests/writewatch_probe.c`, 600 frames of random writes, 200 to 2800 pages per frame):
  `backend = userfaultfd write-protect (PAGEMAP_SCAN)`, exact dirty sets, 0 missed pages, in a 32-bit process on the 64-bit
  kernel (the compat ioctl works). The game itself has not run on a 6.7+ kernel yet: the owner's laptop is the first.
* The dirty-page snapshot path on Linux (driven by the opt-in soft-dirty backend, `MELEE_SNAP_VERIFY=1` on):
  rollback runs with 1 and 4 rollbacks (depth up to 10): `rbhash.csv` (the confirmed per-frame gameplay hash) is byte-identical
  to the full-copy run over the common frames (1960 and 1189 frames); no `VERIFY FAIL`. Curated SyncTest (k=8): 0 mismatches
  for 4000 comparisons, then the same `CURATED MISMATCH` at frame 547 with the same hash values as the full-copy run
  (a pre-existing property of that scripted bench scene, not of the dirty path).
* Soft-dirty cost (why it is opt-in): save 14.45 -> 5.3 ms but simulation 72 -> 81 ms in the same run.
* Windows: `build.sh` OK, ABI audit `ldr ECX/EDX = 0`, `run.sh --test` 329/329. Scripted 6000-frame Fox vs Marth FD match:
  the 12 `DET:` state lines and the `rb` and `wide` per-frame digests (6001 rows) are identical between the 0.2.1-test1 sources
  (`ec495eb53`) and this branch. Windows vs Linux (`matrix.py`: fox-marth-fd, peach-puff-ys, four-dl): `rb` and `wide` identical
  over 6001 frames; `mem`/`glob` differ exactly as in `docs/xplat-netplay.md` (known residual).
* Linux: build id `068aa03a64d3fe65` equals the Windows exe's; native suite 319/319.

## Addendum 2026-10-08 (lane `desync-0221`): the write-watch in the real game on a 6.12 kernel

Not run before this: the real Linux game (the 0.2.2-test1 package, build `e0a6f1a267791af8`) on a kernel with `PAGEMAP_SCAN`,
in a QEMU/KVM VM (Debian trixie 6.12.107, THP `always`, 32-bit game on the 64-bit kernel, headless Xvfb + lavapipe; harness:
`tools/xplat/vm/`). Fake-network rollback session (`MELEE_RB_LIVETEST=1 MELEE_RB_FAKE=lat,jitter,loss% MELEE_RB_INPUT=padgen`, the rollbacks
come from mispredicted generated pad input: shield, smash, specials, jumps), `MELEE_SNAP_VERIFY=1` (live MEM1 compared with the slot after
every dirty-page save and load):

| scene | frames | rollbacks (max depth 7) | `snap: VERIFY FAIL` |
|---|---|---|---|
| Fox v Marth, Final Destination, items=3, fake net 3,4,3 | 14,922 | 359 | 0 |
| Fox, Samus, Yoshi, Mewtwo, Dream Land, items=3, fake net 4,5,4 | 11,875 | 298 | 0 |

Both logged `snap: write-watch backend: userfaultfd write-protect (PAGEMAP_SCAN)` and `dirty-page mode, verify`; poll 0.15-0.18 ms with
191-341 dirty pages (the verify memcmp is the rest of the save cost in those runs). The confirmed-frame hash log (`MELEE_RB_HASHLOG`) of the
first scene is identical, over the 2,824 frames the `MELEE_WRITEWATCH=off` twin run reached, to the full-copy run.

The owner's laptop (kernel 7.2.5, NVIDIA) confirmed the same backend in a real match against Windows: `userfaultfd write-protect (PAGEMAP_SCAN)`,
dirty-page mode, saves ~2 ms, 60 fps, and a vanilla-disc match of 4,950 frames with 7 rollbacks and 0 desyncs. The 0.2.2-test1 desync at frame
5212 was a disc mismatch (ACE against vanilla), not the write-watch: see `docs/xplat-netplay.md`, "Different discs".


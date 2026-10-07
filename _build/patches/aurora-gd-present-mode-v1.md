# Aurora GD present-mode v1 — carried patch

Adds `aurora_set_present_mode(int)` (gfx.h / gpu.cpp). With vsync off, mode 1 selects
`Immediate` (tearing allowed) instead of `Mailbox`; mode 0 (default) is unchanged. Also logs
the present mode whenever `aurora_enable_vsync` changes it. Used by `MELEE_VSYNC=2` (game side:
`pc/platform/main.c`, `shim_vi.c`). Touches only `gpu.cpp` and `gfx.h`; independent of the other
GD patches. Apply from the Aurora directory:

```
git apply --check --no-index <abs>/aurora-gd-present-mode-v1.patch
git apply --no-index <abs>/aurora-gd-present-mode-v1.patch
```

Cause it fixes: on D3D12 windowed, Dawn's Mailbox stays paced to the display refresh (DWM /
frame-latency waits), so `MELEE_FPS=u MELEE_VSYNC=0` topped out at the monitor rate.

Not yet applied to the shared `melee/extern/aurora` or its libs. The vsyncfix lane carries it as
a single object (`_build/agents/vsyncfix/build_gpu_obj.bat` -> `aurora_obj/gpu_present.obj`,
listed first in the lane link list). Merging the game branch brings the source change; the
integrator then runs `_build/build_aurora_melee.bat` once (see the aurora-rebuild notes) and drops
the extra object.

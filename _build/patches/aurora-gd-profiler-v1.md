# Aurora GD profiler v1 carried patch

MIT Aurora (encounter/Luke Street), local upstream revision cb0e279 plus existing
port/surface patches. `aurora-gd-profiler-v1.patch` is a separate diagnostics patch
relative to melee/extern/aurora, already applied here. Preserve prior dirty patches.
It adds a scalar duration sink, runtime enable switch and GPU availability/drop getters;
optional timestamp query feature negotiation; per-frame/pass async durations; CPU
worker/present/GX pipeline compilation slices; custom post identity and upload labels.
No Aurora build was performed. Patched headers require matching rebuilt libraries.

Check/apply from the Aurora directory on a matching fresh source copy:

```powershell
git apply --check --no-index C:/gdm/_build/patches/aurora-gd-profiler-v1.patch
git apply --no-index C:/gdm/_build/patches/aurora-gd-profiler-v1.patch
```

Integrator recipe from workspace PowerShell (adjust installed Build Tools location):

```powershell
$env:GW_VSDIR='C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools'
$env:GW_VCVARSALL="$env:GW_VSDIR\VC\Auxiliary\Build\vcvarsall.bat"
$env:GW_AURORA_ROOT='C:/gdm'
cmd /c _build\build_aurora_melee.bat
bash tools/port/build.sh
```

D3D11 in the bundled Dawn does not enable TimestampQuery; D3D12 conditionally supports
it. Existing32-bit D3D12 instability remains. Unsupported devices continue CPU-only.
Queries are opt-in (MELEE_PROFILER=1 or MELEE_PROF_GPU=1 at startup), four delayed
readback slots and127 zones per frame. Drops are counted. No synchronous GPU wait is
introduced. Results have an Aurora presentation ordinal, not a logic-frame identity.
GPU trace tracks are duration counters at callback arrival; no synchronized GPU timeline
is claimed. Runtime reset does not flush pending worker jobs/readbacks. CPU worker
samples are queue-item slices; post labels identify source paths; EFB surface work is
combined. GPU feature/runtime duration correctness and overhead remain unverified.

Acceptance: rebuild, ordinary baseline off/on, inspect D3D11 unavailable reporting,
then a supported backend trace with GPU frame/pass samples, shader compile identities,
no stale bridge and unchanged replay/sync results. See docs/profiling.md.

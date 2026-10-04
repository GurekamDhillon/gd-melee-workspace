# Aurora GD surface v1 — carried patch

Upstream: encounter/aurora, **MIT**, upstream vendor revision `cb0e279`
(recorded in `melee/extern/aurora/PORT_PATCHES.md`). Applies **after the existing
port patches**, against game repository
`378d79b20c46452cf43aec45c2d622471ed3a5e6`. It is not a patch against pristine
upstream. The patch is already applied to this workspace.

Files are relative to the Aurora directory. From a fresh matching vendored copy:

```powershell
git apply --check --no-index <absolute-path-to>/aurora-gd-surface-v1.patch
git apply --no-index <absolute-path-to>/aurora-gd-surface-v1.patch
```

Run those commands with the working directory at the Aurora directory. The
integrator then runs `_build/build_aurora_melee.bat` from the workspace and uses
`tools/port/build.sh` to rebuild the port, regenerate the bridge and audit its ABI.
`gw_surface.cpp` is registered in `_build/melee_link_objects.rsp`. No build was
performed by this packet. Do not combine patched headers with the old Aurora
libraries: the GX configuration version/layout and public symbols changed.

The patch introduces replayed FIFO command `0x0046`, 256 process-local immutable
source IDs, load-time scoped WGSL validation and a pure surface function inserted
just before generated colour output. Parameters are copied, not pointers. The
shader/pipeline configuration contains the program ID; custom configurations are
excluded from disk warm-up tables. Pipeline version changes 13→14 and old cache
rows are invalidated. Failed pipelines are never passed to `SetPipeline`.

No object-ID attachment is introduced. Normals use the existing public resolve
API, with its existing support and lifetime limits. See `docs/shaders.md` and
`_build/tmp/codex-shaders-fighters-report.md` for exact inputs and limitations.

Review/test checklist for the integrator:

1. Build Aurora, then the port; check the bridge fixpoint/ABI audit and fresh EXE.
2. Compare no-mod captures and frame times against the unpatched baseline after
   warm-up. Default generated WGSL is byte identical in the four tested fixtures.
3. Enable `surface-shaders`; P1 should quantise and darken inward silhouette edges.
   Switch to rim, then dissolve. Check P2, stage, items and HUD remain appropriate.
4. Assign different shaders to P1/P2; swap costumes/stages and exercise palette
   fighters. No shader may leak between tagged callbacks, materials or cameras.
5. Test at 60 and 120/uncapped interpolated presentation. The FIFO selection command
   must replay; paused single-step frames must retain their recorded parameters.
6. Load malformed WGSL, forbidden bindings and a shader exceeding varying/resource
   limits. Source errors return `nil,error`; GX pipeline errors log and skip only
   the affected draw. Original selections survive failed source loads.
7. Unload/reload the mod, end the match, change scenes, disable a script through
   errors and attempt another script's overwrite. Check selections and scope count.
8. Request normals from packet G on the GX recording thread; handle next-frame/null
   views and test MSAA/offscreen exclusions. Do not bind an object-ID texture.
9. Measure `gd.perf()` frame percentiles at 120 fps, command deltas and selection
   count. Profile source × TEV variant growth and cold compile hitches separately.

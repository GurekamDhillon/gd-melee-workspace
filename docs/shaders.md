# Custom shader author guide

Source implementation added 2026-10-03. The standalone CPU and Dawn Null tests
validate contracts and compilation. The integrated game build, actual frame
ordering, appearance and 120 fps acceptance remain integrator checks.

## Opt-in behaviour and ownership

Shader state is native visual state: it writes no game memory, collision, camera,
inputs, fighter attributes or rollback snapshots. These APIs are available online
because the simulation never reads their output. Different clients may use
different pictures without changing the game-state hash. They do not run Lua
hooks during rollback replay. Visual time is elapsed host time, not a logic clock.

With no post chain/custom effect/custom material, no shader file polls, custom
draws, snapshots, offscreen targets or GPU allocations are requested. Existing
models and effects keep their original shader path. Shader handles belong to the
calling script's load generation (including the console); foreign/expired handles
are rejected. Unload and scene/match end clear Lua shaders, post chains, lights and
effect overrides. Immutable package shaders remain package-owned. Materials are
pinned to their model asset until the scene's model cache resets.

## Bodies and parameters

A `.wgsl` file contains a **fragment function body**, returning `vec4f`. Do not
declare bindings, an entry point or `@fragment`. An optional vertex file contains
a body returning a displaced world-space `vec3f`, with arguments `position`,
`normal` and `uv`. Billboard displacement changes its centre; oriented quads and
mesh vertices can change individually. Displacement is visual and never moves
collision. Every body is spliced into a fixed module and checked by Dawn.

The fragment receives plain struct `in`:

| Field | Type | Meaning |
|---|---|---|
| `uv` | `vec2f` | Quad/mesh UV, or full-screen UV |
| `screen_uv` | `vec2f` | Fragment pixel position divided by this target's resolution |
| `color`, `color1` | `vec4f` | Particle colour ramps and vertex colour; white for post/model |
| `normal`, `world` | `vec3f` | World normal/position; billboards use camera facing and centre |
| `fresnel` | `f32` | `1 - abs(normal dot camera-forward)`; mesh rim factor |
| `param` | `f32` | Particle's animated scalar; one for post/model |
| `ii` | `u32` | Particle instance index; zero for post/model |

Common helpers are `time_seconds()`, `resolution()`, `scene_color(uv)`,
`scene_depth(uv)` and `linear_depth(raw_depth)`. The last solves the current
projection equation, supporting orthographic/perspective and reversed Z. Depth
is a snapshot of the chosen insertion point, not a fighter mask: translucent
surfaces generally do not write it. Unsupported depth snapshots bind zero;
outline is best used at `world`. Final depth can include the retail HUD's draws.

Named parameters are declared by a load/add `params` table or effect/material
data. At most 16 names, each a finite float within +/-100000 or a four-float array.
Names start with a lowercase letter, followed by letters/digits/underscore (max
48 bytes); WGSL keywords cannot be names. Slots are sorted lexicographically.
**Every name occupies 16 bytes and is declared `vec4f`: use `.x` for a scalar.**
A scalar fills lane zero, with the other lanes zero; vec4 fills all four lanes.
An empty block still occupies 16 bytes. Updates preserve the declaration/type,
reject unknown names and commit atomically. Example:

```lua
local s, err = gd.shader_load("shaders/tint.wgsl", {
  params={amount=0.5, tint={0.6,0.8,1,1}}
})
-- body: return previous_color(in.uv) * mix(vec4f(1), params.tint, params.amount.x);
```

## Effect packages and Lua effect overrides

An emitter's `material.shader` may contain:

```json
{"type":"custom","fragment":"shaders/fire.wgsl","vertex":"shaders/displace.wgsl",
 "params":{"strength":0.5,"tint":[1,0.5,0.1,1]}}
```

Paths are relative to that package's directory and must remain inside its
containing mod. Omit `vertex` for the existing geometry. Existing `sprite`, `warp`
and `distortion` data remains unchanged. Three package textures `t0,t1,t2` and
samplers `s0,s1,s2` are bound. `parts[in.ii]` exposes the existing read-only
particle storage; `uv_of(parts[in.ii], slot, in.uv)` applies the package's animated
UV/atlas transform. `u.view` and `u.proj` are arrays of 3/4 **row vectors**, not
WGSL column-major matrices. The scene/depth copies precede the Geno effect draw.
Custom fragment output feeds the existing alpha test, blend and effect bloom.
Custom effects pay one shared scene/depth snapshot per effect frame.

Lua can load an effect body and override a named emitter without changing its
emission or simulation:

```lua
local shader, err = gd.shader_load("my-mod/shaders/effect.wgsl", {
  kind="effect", params={tint={1,0.5,0.1,1}}
})
assert(shader, err)
assert(gd.fx_shader("MyPackage", "MyEmitter", shader))
gd.shader_set(shader, {tint={0.2,0.5,1,1}})
gd.fx_shader("MyPackage", "MyEmitter", nil) -- restore package material
```

`kind` defaults to `post`; an effect shader cannot be used as a post pass. The
override is owner-scoped; replacing another script's active override is refused.

## Post chains and insertion points

```lua
local p, err = gd.post_add("shader-demo/shaders/vignette.wgsl", {
  order=10, stage="world", half=false,
  params={strength=0.5, radius=0.3, softness=0.4}
})
assert(p, err)
gd.post_set(p, {params={strength=0.7}})
gd.post_remove(p)
gd.post_clear() -- calling owner's chain only
```

The first argument can be a previously loaded **post** shader handle. Each pass
has its own parameter values; changing shader defaults does not change existing
post instances. A path-owned pass frees its hidden shader when removed/cleared.
There are 32 passes and 128 live Lua/package shader handles total. Lower `order`
runs first, with creation order breaking ties; orders range from -100000 to 100000.

| `stage` | Exact insertion point |
|---|---|
| `world` (default) | After the main camera's last world walk, including effects and near translucent kit pieces; before retail HUD cameras |
| `final` | After all game/HUD rendering, before the host/ImGui overlay and console |

There is no independent pre-effects stage and no post-host-overlay stage.
Aurora exposes the **current pass**, not these named phases; the game invokes
our GX callback at those two points. Auxiliary/refraction camera draws do not run
the world chain. `scene_color` reads the snapshot at the beginning of that
stage's chain; `previous_color` reads the preceding pass, or the scene for pass
one. `scene_depth` stays the original depth snapshot through the chain.

Every pass renders into its own single-sample offscreen colour target, then the
last output replaces scene RGB while preserving EFB alpha and depth. `half=true`
uses floor(width/2), floor(height/2), at least one pixel; the next pass uses
normalized UVs, and the final composition upsamples. Depth still has the original
scene resolution. Failed compilation/pipeline preparation skips that pass.
Failed recording never promotes a cleared target to the next pass or the scene.

The sample mod is `melee/pc/geno/mods/shader-demo`. It includes LUT-free
lift/gamma/gain/saturation, vignette, a depth outline, and whole-scene bloom
(half-resolution extraction/blur plus full-resolution composition). Its README
contains independent examples and tap counts. Normalized scene targets limit
bloom dynamic range; this feature does not make the vanilla renderer HDR.

## Custom model materials and light

Next to `part.gxmesh`, add `part.material.json`:

```json
{"builtin":"glass","opacity":0.32,"tint":[0.65,0.85,1,1],"roughness":0.25,
 "albedo":"atlas.gxtex","normal":"atlas.normal.gxtex","emissive":"atlas.glow.gxtex",
 "emission":1}
```

Built-ins are `lit`, `unlit`, `glass`. Or select `fragment` (and optional `vertex`)
with `params` instead of a built-in. Paths are relative to the sidecar and remain
inside its mod. Maps are GXTX v1 RGBA8, dimensions 4..4096 with whole 4x4 tiles.
Omitted albedo uses the existing model atlas; omitted emissive uses the existing
glow atlas; normal is optional. Emissive is added unlit. Normal maps use a tangent
frame derived from world/UV derivatives. Roughness is an edge-shape scalar for
glass, not a physical BRDF. Missing material files, and `{}`, retain the GX path.
Malformed/failed opt-in materials skip only that model draw and log the error.
Sidecars/maps load with the asset; restart the scene after editing their data.
The referenced shader bodies themselves hot reload.

```lua
gd.light_set{dir={0.25,1,0.55}, color={0.92,0.92,0.94}, ambient={0.36,0.38,0.44}}
```

The directional light plus ambient apply only to these opt-in model materials.
Defaults match the existing fixed key's direction and colours. Last writer owns
the light; its unload, or scene end, restores defaults. Vanilla GX models are
unchanged. Models use the existing world-space batch and draw order: opaque once
in camera mode 2 (depth test/write), translucent far/near around the fighter plane
(depth test, no write). **Keep `"alpha":1` in the existing collision sidecar for
glass/opacity materials** so the game selects the translucent buckets. Material
data does not alter collision or instance sorting fields.

Glass uses authored opacity, replacing the nearly transparent old glass atlas's
alpha, plus tint and a power-shaped Fresnel-style edge. The existing room-kit
glass has not been switched automatically: its exporter/installer must ship
`<glass-part>.material.json` sidecars (the sample supplies a template) alongside
the mesh and existing alpha collision sidecar. No new art is required.

## Errors, containment and edit/save workflow

`shader_load`, `post_add`, updates and `fx_shader` return a handle/true on success,
or `nil,error` on failure. `shader_status(handle)` returns `{valid,error}` and
also polls the body; an expired/foreign handle returns `nil,error`.
Errors are logged with body path/line/column. WGSL has no `#line`, so the wrapper
maps body lines using splice offsets. Wrapper/pipeline errors may name generated
code or a pipeline diagnostic rather than a body line. Failed compiled modules
are never bound to a draw.

Paths reject traversal, absolute/drive paths, backslashes, alternate streams,
embedded NULs, empty components and trailing dots/spaces. On Windows the runtime
opens the mod root and source, checks their **final handle paths**, and reads
the same source handle; junction escapes are rejected. This also applies to
hot reload and material/map reads. The non-Windows author workflow is not
claimed race-resistant.

Active shader bodies poll at most every 250 ms. Timestamp, size and freshly read
content participate in change detection. A source change recompiles; invalid
edits skip the affected draw/pass until fixed. Successful modules share a cache
by full generated content (hash collisions are checked with byte equality).
Snapshots/queued draws retain immutable program/resource references while a
replacement loads. Shader-module diagnostics are available at load; target-specific
pipeline failures also appear in `shader_status` after that target is prepared.

## WGSL differences that matter

WGSL uses `vec4f(...)`, `fn`, `let`/`var`, explicit types and attributes, not GLSL
`gl_FragColor` or HLSL semantics. It has no text preprocessor/includes, `#line`
or implicit scalar/vector casts. Struct/matrix memory alignment matters: use the
named 16-byte slots instead of assuming GLSL packing. Our matrices are rows;
project with dot products as the fixed module does.

`textureSample` and derivatives require appropriate uniform control flow.
Per-particle branches or early returns can make implicit-derivative samples
invalid; sample before branching or use `textureSampleLevel(tex,sampler,uv,0.0)`.
Vertex sampling always requires explicit LOD. Depth is unfilterable R32Float:
use the helper/`textureLoad`, not a filtering sampler. No compute/storage-write
contract or arbitrary binding layout is exposed.

These rules were checked against the [W3C WGSL specification](https://www.w3.org/TR/WGSL/),
particularly its uniformity and alignment sections. The bundled Dawn compiler
remains the authority for the engine's supported language version.

## Cost and measurement

Effect emitter materials may opt into `"additive_batch":true` to merge
compatible additive groups within an uninterrupted additive run. This helps
repeated pickups share draws. Non-additive groups remain ordering barriers.
Custom effect bodies, including Lua shader overrides, otherwise retain their
original groups: their `in.ii` and `parts[in.ii]` indexing may depend on group
boundaries. Opt in only when the body accepts regrouped indices and draw order.
The pickup-juice radial shader uses UV and vertex colour and is safe to opt in.
Particle bucketing scans the pool once rather than once per emitter instance.
These are structural reductions; native timing remains unmeasured.

Warm custom effects keep the existing draw/group/particle uploads, add 16..256
parameter bytes plus 16 time bytes per draw, and share one colour/depth snapshot.
Material draws expand 48 bytes per triangle vertex into transient storage, plus
224 uniform bytes and 16..256 parameter bytes per batch. Their built-ins need no
scene snapshot; a custom model body snapshots colour/depth for its inputs at its
draw point. Maps decode/upload once per asset. Batching and alpha split remain
the existing ones; large/custom models still pay CPU conversion and fill rate.

A post stage pays one full scene colour/depth snapshot. Each pass pays one
offscreen render and resolve; a full pass shades W*H pixels and a half pass about
W*H/4. The stage pays a final full-resolution composition. Vignette/grade sample
one colour; outline loads five depths; bloom averages 25 samples at half resolution
and samples two colours in its full-resolution compose. Resolve bandwidth and
MSAA make GPU cost device-dependent. Cold compilation and edit/save reload can
stall; the 120 fps target is for warm frames and is not yet measured.

`gd.perf().shaders` supplies cumulative `compiles`, `cache_hits`, `errors`,
`reloads`, `draws`, `passes`, `resolves`, `skipped`, `pixels`, `uniform_bytes`,
`vertex_bytes`, `record_ms`. Subtract two snapshots over a warm interval.
`pixels` counts scheduled post pixels, not measured overdraw; `record_ms` covers
post/material GX-thread preparation, not GPU time. Custom effect worker draws
are included in `draws`; the existing FX diagnostics still report their own
preparation time. Use `gd.perf().frames` for total, GX and worker time. A 120 fps
presentation has an 8.33 ms budget; measure with realtime rendering, no turbo,
and the same resolution/MSAA before/after.


## Module-form helpers and timed passes

Fragment files can opt into reusable WGSL helper functions by putting
`// @module` on the **first line**. The rest is module-scope `const`/functions,
including `fn mod_fragment(in: Input) -> vec4f`; the engine does not wrap it in a
second function. The existing `Input`, Params, helpers and fixed bindings remain
available. No resource declarations or entry points are added by the mod;
attributes (`@` anywhere after the marker) are refused. This intentionally also
refuses attributes in comments. Existing body-only files are unchanged. The same
format works for post, model and effect fragment files; vertex files remain bodies.
Errors continue to map to the original fragment file's line numbers, including
helper functions. This format is exercised by `experiment/clank_impact`.

Optional Lua post options are `duration_frames=N` and `clock=true`. N counts
nominal 60 Hz presentation time (N/60 seconds), not logic updates or refreshes.
`clock=true` requires `params={elapsed=0,progress=0,...}` with both names declared
as scalars. The engine updates elapsed seconds and normalized progress once per
presentation tick and removes the pass at expiry. Use `params.elapsed.x` and
`params.progress.x` in WGSL. The deadline continues while `gd.hitstop` or manual
pause stops game logic; errors, unload and scene cleanup cannot strand the pass.
Ownership/type validation remains unchanged. Removal/clear retires the timer;
no clock/duration option means the original indefinite pass behavior.


## EM1 fighter surface composite

`melee/pc/scripts/examples/envoy/shaders/modifiers_surface.wgsl` is one native GX
surface program containing seven separately named status functions and two
ordered equipment layers. It receives the completed retail GX color, blends
bounded color treatments, and preserves retail alpha and geometry. Equipment
runs before statuses, but statuses reserve the three stronger slots first;
equipment yields to faint tint when those slots are exhausted. Remaining statuses
contribute faint tint. Intensity zero is identity.
Burn ember rim, Shock arc pattern, Chill frost/desaturation, Curse inverted rim,
Haste streaks, Guarded facets and Momentum stack climb are surface treatments.
Heat refraction and an extra glass shell are not implemented in this compositor.
FX1 adds separate pose-history afterimages and point ribbons in source; their GPU
and visual acceptance is pending, and Envoy wiring belongs to the Envoy job.

Sixteen float parameters, in order: logic seconds, intensity, Burn, Shock, Chill,
Curse, Haste, Guarded, normalized Momentum, equipment-one encoded look+hue/strength,
equipment-two encoded look+hue/strength, guard flash, combined hue/strength.
Encode equipment look as 1 Burn, 2 Shock, 3 Chill, 4 Curse, 5 Haste, 6 Guarded,
7 Momentum, plus normalized hue 0..1 (hue must be strictly below 1). Zero look
uses hue tint. Strengths and combined hue are normalized 0..1. The shader never uses host `s.time`. Missing normals use a
bounded constant rim. `modifiers_chain.wgsl` uses post `progress` and `strength`
parameters; progress must be driven by Lua logic, with strength clamped to 0.06.
It is a single gentle edge pulse, without a strobe or timed host-clock option.

Native selection and parameter state remains visual-only and unsnapshotted.
Rewind clients restore these uniforms from their own snapshotted Lua state.
Current loaded fighter and sub-fighter material pipelines can be warmed after
surface selection, but new GX variants remain cold until captured. Actual
appearance, six-fighter cost and 120 fps acceptance require the integrator's
Windows game run; standalone tests do not establish them.


The Envoy `mod_display` adapter warms each loaded fighter's selected composite,
then warms its chain post with a zero-strength pass and polls `gd.post_ready`
for that exact pass. It removes the invisible warming pass once prepared. Later
moments reuse the precompiled program and pipelines, using 18 logic frames and
at least 30 logic frames between pulses. A pulse requires at least two distinct
modifier labels in the chain; its peak edge blend is bounded by 0.06 times the
intensity setting. There is one smooth rise/fall and no repeated strobe. No safety
or appearance acceptance is inferred without the integrator's game run.

The adapter snapshots only deterministic Lua visual metadata through the modifier
engine. Restoring while paused rebuilds surface selection only for previously warmed
ports, reuses cached native programs/pipelines, and restores logic progress
without advancing timers or calling `gd.warm` (which forks rewind history).
An unavailable host cache is reported; new variants wait for normal live warmup.
Scene transitions invalidate cached handles; manual same-scene clear reuses them.


## FX1 motion history (source implementation; unverified on screen)

Afterimages retain Aurora draw output: vertex/index bytes, indexed attribute and
skin-palette storage, uniforms, texture handles and bindings. Replay reprojects
the captured pose into the current camera; no fighter JObj or MEM1 state is
rewritten. Copies reuse the surface pipeline generator with own-look tint,
silhouette or UV gradient, alpha/additive blend, depth test and no depth writes.
Historical materials requiring mutable EFB textures, fog-range LUTs, or separately
rendered held items are rejected as a whole instead of replaying incomplete poses.

Ribbons use original procedural solid/glow/fire/electric/frost/dark WGSL, logical
time and camera-facing Catmull-Rom geometry. They write scene RGB, preserve EFB
alpha and auxiliary attachments, and never write depth. Cold variants skip.
Declare `gd.warm{fighters={1},tracers=true}` after installing emitters, before play.
Use `gd.motion_intensity(0)` to reduce the presentation to zero. See the Motion
history API in scripting.md and the FX1 report for limits and pending validation.
Aurora ABI/FIFO changes require a rebuild; the carried patch is
`_build/patches/aurora-gd-motion-v1.patch`.

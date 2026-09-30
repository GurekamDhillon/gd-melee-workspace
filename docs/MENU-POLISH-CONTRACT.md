# Gate 8 menu polish — integration hook contract

Worker-owned Gate 8 output (commands, menus, HUD, onboarding, feedback). This
file is the handoff to the live-integration worker that owns `main.lua` and
`prepare.py`. It records exact files, exported APIs, the data handshake, and what
is and is not verified. Nothing here is a claim of native or human acceptance.

## Frozen / owned files

Game checkout (`melee/worktrees/linux/pc/scripts/examples/roguelite/`):

| file | state | notes |
| --- | --- | --- |
| `commands.lua` | modified | default tree and all exported functions preserved; loadout API added |
| `menus.lua` | modified | existing collection/rest/reward/error behavior preserved; new screens added |
| `feedback.lua` | modified | existing priorities/coalescing preserved; `tutorial`, `tell`, layout gate added |
| `hud_layout.lua` | new | pure HUD geometry, safe areas, fallback anchors |
| `onboarding.lua` | new | pure first-run tutorial state |

Workspace (`gdm/`):

| file | state |
| --- | --- |
| `tools/roguelite/test_menu_polish.py` | new wrapper test |

Not owned and untouched: `main.lua`, `prepare.py`, `core.lua`, `route_map.lua`,
`progress.lua`, `runtime_*.lua`, and all other workers' files. `main.lua` is
dirty from the integration worker and was left exactly as found.

## Compatibility guarantees

- `commands.lua`: `C.new() / C.reset(s,b) / C.view(s,fn) / C.update(s,b,fn)` keep
  their signatures, return shapes and the authored default tree byte-for-byte
  behavior. `test_commands.py` is unchanged and passes.
- `menus.lua`: `M.new/reset/view/update/apply/draw` keep signatures. Existing
  menus (`collection`, `rest`, `reward`, `error`) keep their controls, ids,
  actions and preview semantics. `test_menus.py` is unchanged and passes.
- `feedback.lua`: `F.new/reset/notify/dismiss/reward/clear/finish/update/view/draw`
  keep behavior. Queue priorities for existing kinds are unchanged. `test_feedback.py`
  is unchanged and passes.
- Bundle order is unchanged; all new modules are dependency-free, lexically
  bundled, never call `require`, and never touch `gd` at load time.

## Exact new APIs

### commands.lua

```lua
local tree = C.plan(run, opts)      -- build from installed loadout only
C.install(state, tree_or_nil, buttons)  -- install; nil restores default tree
C.loadout(state, run, opts, buttons)    -- C.plan + C.install, returns tree
C.assignments(tree)                 -- {root={left,right,down}, abilities={left,right,down}}
```

`run` needs only `run.hosts.player.slots[slot]` and `run.genes[id].kind`. No
catalogue is read. `opts`:

- `order`: permutation of `{'assault','guard','traversal'}` (exactly three).
- `labels`: `{[kind]=..., [slot]=...}` readable, stable family/placement labels.
- `capacities`: `{items={restore=n}, supplies=n}` declared inventory only.
- `assign`: `{root={left,right,down}, abilities={left,right,down}}` prepared
  branch assignments. Unknown values are refused (`assert`/`pcall`).

The loadout tree: root forks `left=Abilities, right=Item, down=Special`;
Abilities forks to the three placed genes (two presses from root); empty slots
are honestly blocked; Item shows a declared supply or "No supplies"; Special
keeps `loadout/route/collection`. `route` opens the discovered map.

Main hook: after a run starts or the loadout/progress changes between rooms, call
`Commands.loadout(command_state, run, {capacities=..., assign=...})`. Keep the
existing `availability` callback; `C.update` already emits `family` and `slot`
on both execute and blocked events. Emit `{kind='command_navigate'}` /
`{kind='command_back'}` to the onboarding state on navigate/back events.

### hud_layout.lua

```lua
local layout, why = Hud.layout{width=w, height=h, dpi=d, new_hud=bool,
                               command=bool, compact_menu=bool}
Hud.aspect(w,h)               -- '16:9' | '4:3' | 'other'
Hud.command_expanded(layout, depth)  -- temporary panel, avoids screen center
Hud.avoids_center(layout, rect)
```

`layout` fields: `safe`, `rail`, `notification`, `compact_notification`,
`opponent`, `fallback.lives`, `fallback.damage`, `command`, `command.max_width`,
`replace_vanilla`, `aspect`, `scale`, and the responsive scales `content_scale`
(rail/fallback), `note_scale` (normal notification), `compact_scale` (workbench
strip) and `opponent_scale`. Each scale is `min(dpi, safe.w / design_w)`, so a
scaled component box never exceeds the safe width even when the viewport is
narrow at dpi 2. `opponent` prefers the space right of the rail and otherwise
stacks fully above it, so it can never cover a charge bar; `rail` and `opponent`
are disjoint. `replace_vanilla` is true **only** when `new_hud==true`.

Main hook: pass `layout` and `new_hud` (true only when the compact HUD is
actually installed) into `Feedback.draw`. In `Feedback.draw`, `replace_vanilla`
false draws only the minimal life/damage anchors and leaves the native cluster
readable; true draws the compact rail.

### onboarding.lua

```lua
local s = Onboarding.new{first_rooms=3, steps={...}, skip=bool}
Onboarding.observe(s, event)   -- event.kind: move|charge|command_navigate|
                               -- command_back|cast|tell|door|reward|breed|fuse
Onboarding.view(s)             -- read-only; view().pause is ALWAYS false
Onboarding.toast(s)            -- feedback-ready {kind='info',key='tutorial:<id>'}
Onboarding.set_room(s, i); Onboarding.skip(s, on); Onboarding.revisit(s)
```

Grammar steps (`branch`, `back`) only apply inside `first_rooms`; past that
window they lapse silently. `genealogy`/`fusion` complete only when the caller
passes `event.available=true`. Onboarding never pauses combat. Main hook: call
`observe` from the same places events already fire, then route `Onboarding.toast`
to `Feedback.tutorial`.

### feedback.lua

```lua
F.tutorial(s, step_or_string)  -- kind='tutorial' (priority 15, below warnings)
F.tell(s, {key,title,detail,ttl})  -- kind='tell' (priority 55, non-celebratory)
F.draw(s, {layout=..., ...})   -- new optional layout gate described above
```

Tutorial and tell coalesce by key, honor lifetimes, are frozen while paused, and
never preempt `blocked/error/failure`.

### menus.lua new screens

`M.view`/`M.update`/`M.draw` now accept these read-only context menus. All are
optional-declared: absent data yields an honest message, never an invented
option. All controls go through the existing focus/controller/mouse path.

| `ctx.menu` | required context | notes |
| --- | --- | --- |
| `map` | `ctx.map` = `RouteMap.build()` output | renders only rooms/exits present in the map; hidden rooms never leak |
| `onboarding` | `ctx.onboarding` = `Onboarding.view(s)` | exposes `no_pause`; SKIP/ENABLE via `onboarding_skip` |
| `settings` | `ctx.settings={items={{id,label,value}}}` | only declared items; returns `{kind='setting',id,value}` |
| `ending` | `ctx.ending={outcome,lines,next}` | returns `{kind='ending_continue'}` or `ctx.ending.next_kind` |

Capacity/confirmation handshake: pass `ctx.capacity={count,max,full}` on
`collection` (and `reward`). When `full==true` the screen shows a note and a
`discard` control whose action is `destructive`. `M.update` requires a second
press on the same control before returning it; the first returns
`{kind='blocked',confirm_pending='discard'}`. The mutation itself stays in
main/Core (no discard API is invented here). `map_inspect` selection stays
in-menu; `map_close`, `settings_close`, `onboarding_close`, `onboarding_skip`
are returned to main.

## Integration hook checklist for the main worker

1. Construct `command_state`; after run start / loadout change call
   `Commands.loadout(command_state, run, {...})`. Keep `Commands.reset` on pause
   and travel (it preserves the installed tree).
2. Build `layout = Hud.layout{...}` for the current viewport; decide `new_hud`
   from the actual compact-HUD availability, not optimism. Pass to
   `Feedback.draw`.
3. Drive `Onboarding.observe` from existing move/charge/navigate/back/cast/tell/
   door/reward call sites; feed `Onboarding.toast` to `Feedback.tutorial`. Do not
   call `gd.pause` from onboarding.
4. Add pause-menu entries for `map`, `onboarding`, `settings`, `ending` using
   `Menus.reset(menu_state, which)` and the declared context above.
5. Populate `ctx.map` from `RouteMap.build(manifest, progress)` and
   `ctx.capacity` from the real collection count/max. Never synthesize either.

## Review follow-up (fixed defects)

- **Onboarding cast hint** now describes the real command control: Left/Right/Down
  on the final branch auto-executes; it no longer tells the player to press A
  (A is the combat attack, not the command confirm).
- **Destructive confirmation** is bound to the exact action identity, menu/section
  context and a source generation. `M.reset` and any selection/context change
  invalidate a pending prompt, so a prompt raised for gene `g1` cannot discard
  `g2` on the next click; two deliberate presses on the same action are required.
- **`Feedback.draw` fallback** no longer concatenates a nil opponent label; it
  uses the safe `OPPONENT` default.
- **Prepared assignments** are reconciled into a permutation of the allowed
  values: a partial assignment (`abilities.left='guard'`, `root.left='special'`)
  fills the remaining directions in stable order so no installed slot/node is
  dropped or duplicated. Unknown directions, unknown values and repeated values
  are refused.
- **`Commands.install(state, nil)`** (and any rebuild) resets the cursor to the
  valid root and clears held-button edge history, so a capability disappearing or
  changing mid-branch cannot leave a stale node or callback.
- **HUD real draw** now applies the declared layout in full: rail and notification
  boxes come from `layout.rail`/`layout.notification`, and all metrics scale with
  `layout.scale` (dpi 2 rail height 122, not 61). The compact rail is only drawn
  when the layout says the new HUD is actually available; otherwise only the
  minimal life/damage anchors draw.
- **Declared zero supply** (`capacities.items.restore=0` or `capacities.supplies=0`)
  yields a blocked "No supplies" entry, never an enabled "Restore x0".
- Existing main/legacy APIs are unchanged; the default (no-layout, default-tree)
  paths are byte-for-byte preserved.

### Follow-up 2 (residual blockers)

- **Responsive HUD.** `Hud.layout` no longer caps the rail with a `0.62*safe.w`
  clamp while letting content scale at full dpi. Each component gets its own
  clamped scale (`content_scale`, `note_scale`, `compact_scale`) so the scaled
  design box always fits the safe width; `feedback.draw` uses those scales for
  every metric. At 640x480 dpi2 the rail is now 516 wide (was 362) and the third
  charge bar stays inside it. The opponent block is placed by `Hud.layout`
  (right of the rail, else stacked above) and never intersects it; the previous
  clamp that pulled it over the ability is gone.
- **Inward shadows.** `Feedback.surface` and the fallback anchors inset their
  drop shadow so every fill stays strictly inside its declared box; draw
  bounding-box tests can then assert exact rect ownership.
- **Compact notification.** The paused-workbench notice draws a single line
  positioned so its baseline plus caption height stays inside the strip
  (`compact_notification`); the two-line `ny+30` detail that spilled the 23px
  strip is only used by the normal notification, whose `note_h` is sized for two
  lines.
- **Held Up across rebuild.** `Commands.install` returns the cursor to root but
  now **preserves** `previous`/`up_latched` (and clears only `chord`). Rebuilding
  the tree while Up is held can no longer fabricate a root taunt; the latch
  survives until release. An optional `buttons` argument lets a caller sync the
  exact held word. `test_menu_polish` regresses: press-Up-hold → rebuild → same
  Up emits no event/mask 15 → release → fresh Up taunts.
- **Real draw bounding boxes.** `test_hud_feedback_fallback_and_replace_gate`
  records actual `gd.fill`/`gd.kit.text` coordinates and asserts each fill/text
  lies inside its owned rail/opponent/notification rect, rail and opponent are
  disjoint, the third bar is inside the rail, and the compact line fits its
  strip — at 640x480 dpi1/dpi2 and 854x480 dpi1/dpi2.

## Verification (this worker, no native build)

- Command: `python3 -m unittest tools.roguelite.test_menu_polish -v` → 6/6 pass.
- Regression: `test_commands`, `test_menus`, `test_feedback`, `test_route_map`
  all pass unchanged.
- Full discovery `python3 -m unittest discover -s tools/roguelite -p 'test_*.py'`
  → 120 tests, 4 errors. All four are missing generated art/export assets
  (`menu/out_effects_study/manifest.json`, `menu/out_roguelite/...coll.json`) in
  `test_runtime.py`, `test_certify_rooms.py`, `test_rooms.py`; they are
  pre-existing environment failures outside this worker's scope (art generation
  is root/Astra-owned and was not run). No failure touches the owned files.

## Unavailable evidence (not claimed)

- Native compile/install/game/controller/screenshot evidence is **pending and
  root-exclusive**. Linux native builds and runs are available to root on this
  host; this worker was not authorized to build, install or launch. HUD
  readability, menu feel, focus restoration after scene exit, and real
  controller hotplug remain human-unverified, not blocked by an invented
  machine constraint.
- No new raster art or interactive viewer; only existing reviewed kit roles
  (`rogue_*` icons, `gd.kit.button/panel/text`) are referenced.
- Screenshots are root's future acceptance work.
- `main.lua` is not wired yet; until it calls the hooks above, the new screens
  and loadout tree are not reachable in the live game.

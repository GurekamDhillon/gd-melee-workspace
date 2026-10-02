# Model-test result: campaign acceptance finish + compact command UI wiring

Lane: `gdm/_build/model-tests/campaign-integration`
Game worktree: `melee/worktrees/linux` (`agent/model-test-campaign-20260930`)
Date: 2026-09-30. No build, no install, no launch, no commit, no push. The user's
8BitDo Bluetooth profile was not touched.

This is one bounded part of the offline TBD roguelite goal. It is **not** a claim
that the route, the 12 certification gates, the enemy/gene families or the native
slopes are done.

## 1. Exact commands and results

Reproduced in this worktree, from
`/home/gd/melee_linux_test/gdm/_build/model-tests/campaign-integration`:

```
python3 -m unittest discover -s tools/roguelite -p 'test_*.py'
```

| run | tests | result |
|---|---|---|
| seed baseline, before any edit of mine | 199 | `OK (skipped=1)` — matches `MODEL-TEST-BASELINE.log` |
| seed campaign baseline (`MODEL-TEST-CAMPAIGN-BASELINE.log`) | 27 | `OK` |
| final, after my edits | **214** | `OK (skipped=1)` |

Focused runs (from `tools/roguelite/`):

```
python3 -m unittest test_v2_runtime            -> Ran 28 tests ... OK
python3 -m unittest test_presentation_runtime  -> Ran 14 tests ... OK
python3 -m unittest test_commands              -> Ran 1 test ... OK
python3 -m unittest test_menu_polish           -> Ran 6 tests ... OK
python3 -m unittest test_feedback              -> Ran 6 tests ... OK
```

`test_runtime.py`, `test_persistence.py` and `test_legacy.py` are import-time
suites (they run Lua at import, not named methods); `unittest` reports
`NO TESTS RAN` for them and their result is the pass line they print. All three
are green in the 214-test discover run, including the v1 legacy acceptance suite
`test_runtime.py`. The skip is pre-existing and unrelated.

Growth 199 -> 214 = 1 new campaign regression + 14 new presentation tests. No
existing assertion was weakened, removed or reworded to pass.

## 2. Files I changed (patch vs seed)

`MODEL-TEST-SEED.json` was not modified. Compact patch manifest:

| file | seed sha256 | final sha256 |
|---|---|---|
| `melee/worktrees/linux/pc/scripts/examples/roguelite/main.lua` (modified) | `2ded519eb170e951…` | `70dfe560ceacb87c…` |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_presentation.lua` (**new**, 293 lines) | — | `4a5b70db69ce0f7a…` |
| `tools/roguelite/prepare.py` (modified) | `972fda8c8af68da4…` | `3dc92cda02fc6cef…` |
| `tools/roguelite/test_v2_runtime.py` (modified) | `085fc2d6f56f069e…` | `e18bcf9821ff915a…` |
| `tools/roguelite/test_presentation_runtime.py` (**new**, 654 lines) | — | `72c004a13a5eaa3d…` |

Full diffs are `git diff` in the game worktree for `main.lua`, and `git diff` /
new-file content in the wrapper. Nothing outside my ownership list was edited:
`runtime_campaign.lua`, Core, codecs, recipes, inventory, enemies, gene-actions,
native source and generated art are untouched. The seeded dirty files remain
coordinator baselines, not my output.

### 2.1 `prepare.py`

Appended three names to the bundle list, after every earlier runtime module so
each existing name keeps its exact relative order and no earlier name is renamed:

```
('runtime_campaign', 'RuntimeCampaign'),
('hud_layout', 'Hud'), ('onboarding', 'Onboarding'),
('runtime_presentation', 'Presentation')
```

All three still land before `main.lua`, which the installer appends last.
Nothing was removed. `inventory.lua` / `equipment.lua` were **not** in the
installed bundle before this task and were not added or dropped here; a bundle
test asserts that (`BundleTests.test_bundle_carries_the_presentation_modules_before_main`).

## 3. Phase A — what I verified and what I fixed

I reproduced each of the seven invariants with real modules and the native-correct
`gd.player` copy snapshot before assuming the fifth pass held them. The four P1s
in `docs/MODEL-TEST-integration-review-3.md` are genuinely fixed in the seeded
code — I confirmed each against the current source and by probe rather than by
trusting the historical report:

1. Retired owners are identity-bound (`get_run` returns `self.run`;
   `replace_run` is only ever called on the live campaign). Confirmed: a probe
   that breeds `g4` into a new run reusing id `r4` leaves the new run untouched.
2. Refused retirement never permits overlapping worlds. `retiring` keeps the
   engine paused, builds nothing, retries boundedly (16) and retains the owner
   on exhaustion with orphan de-duplication.
3. Native effect ownership is never discarded by `teardown`, `drop_pending`,
   retirement or unload: `reset(false)` refuses while `effect_pending` is set.
   Probed directly: `teardown({drop_pending=true})` -> `false`,
   `effect_pending` retained, `reset(false)` -> `false`.
4. A mismatched heal readback keeps rollback ownership (the responsibility is
   recorded *before* the write).

Defects I found and fixed are all in `main.lua`:

- **A terminal campaign error left the player stranded.** `main` retries
  recovery every 30 ticks, so a campaign that *does* recover (pending save, or a
  refused native rollback, once storage/engine returns) stayed behind the error
  page forever. That page has no usable control unless a `pending_finish` retry
  exists, so "recoverable path" was not actually reachable. New `v2_recovered()`
  retires the page with the error, called from the recovery-confirm path and once
  the campaign is verifiably running again with isolation intact. Isolation-loss
  and placement-timeout errors still require a restart, unchanged.
  Regression: `test_old_owner_effect_rollback_survives_leave_and_blocks_replacement`.

- **A refused Restore was a silent no-op.** `campaign:use_supply()` returns
  `false, reason`; the dispatcher discarded both. A refused spend rolled its
  heal back and spent nothing (correct) but the player saw nothing at all. The
  real refusal reason is now surfaced, and the tree is rebuilt on a real spend.

- **A renderer failure escaped `on_draw` every frame.** `on_draw` is now a
  `pcall` around a pure `draw_scene`; a failure is logged and contained. Drawing
  mutates nothing, so a partial frame can never be read as a run or save change.

Honest scope note: the effect-pending case is *stricter* than the handoff implies.
While an effect rollback is unresolved the campaign blocks the whole dispatcher,
so a replacement run cannot even be requested — strictly stronger than
"promotion may not unpause/build while an old owner remains". The regression
asserts the real behaviour (leave retains the owner, nothing is promoted, the
bounded retries surface a drivable recovery, the heal restores to its exact
pre-effect percent, then the owner retires normally).

## 4. Phase B — what is now actually wired

New `runtime_presentation.lua` is pure glue over the four already reviewed
modules. It owns no run, save or engine state. Every public method is total: a
layout, drawing, input or planning failure is contained and logged.

- **Bundle order / no missing module** — Hud, Onboarding and Presentation are
  bundled before main; earlier names and order unchanged (bundle tests).
- **Real `Hud.layout` into `Feedback.draw`** — the rail, the opponent block and
  both notification strips are now drawn at reviewed layout coordinates instead of
  the hardcoded `12,407,254,61` fallback. Verified against a real `on_draw`:
  rail at `14,407 258x61`, exactly `Hud.layout{width=640,height=480}.rail`.
- **Coordinate system** — the port documents one fixed 640x480 virtual canvas
  (`docs/scripting.md`) and exposes no viewport or pixel-DPI API, so none is
  invented. A larger window cannot enlarge HUD coverage, and the test asserts
  every drawn box stays inside the canvas.
- **Intentional compact rail + honest HUD ownership** — hiding the vanilla
  cluster and enabling the replacement rail are one decision, taken only while a
  room is live. Ownership is returned on leave, on the error page, at match end
  and on unload. `gd.hud_visible(false)` returning `false` is treated as the new
  state; only a throw or a missing API is a failure.
- **Recursive D-pad tree preserved** — left/right/down fork, Up returns to the
  parent, only a fresh Up at root taunts, a rebuild while Up is held keeps the
  latch (no fabricated taunt), A has no navigation role, and ordinary combat is
  never paused. Tested through real `Commands.update` edges recorded by main.
- **Loadout-derived tree** — `Commands.loadout` is installed from the run's real
  installed genes after a resume, a current-run commit, a promotion and a real
  Menus placement/reward, with the current button word passed so a held Up keeps
  its latch. Observed live: root `Abilities/Item/Special`; abilities showing
  `CINDER / ASSAULT`, `RIME / GUARD`, `EMPTY TRAVERSAL`; `Restore x2` with the
  real charge reason (`Charge 0 / 3`); at zero supplies `No supplies` disabled
  with reason `No supplies in this run`. Availability still gates everything, so
  no unsupported mechanic can execute.
- **Door vs item precedence** — the cleared-door proximity check still runs
  before `Commands.update`, in both the live-v2 and legacy paths. Proven in both
  directions: on a cleared door one Down press travels and spends nothing; away
  from a door the same press only forks the item branch.
- **Truthful onboarding** — `Onboarding.observe` is fed only from real paths:
  sustained grounded movement, a rising ability charge, real `navigate`/`back`
  edges, a successful cast, a genuinely telegraphing enemy, a real door travel
  and a committed reward. Hints travel through the existing toast queue with
  step-keyed identities, below enemy tells in priority, coalesced, never pausing
  combat. Genealogy/fusion are only taught when the caller declares them
  available, which they are (Menus implements both). Route depth drives the
  early-grammar window, so those steps lapse instead of nagging.
- **Reduced motion** — the port exposes no switch, so nothing is invented: the
  value is read from the mod's own `config.txt` (`reduced_motion=true`) and is
  reported honestly to the menu as OFF by default.
- **UI failure isolation** — a throwing renderer and a throwing planner are
  asserted to leave the run snapshot, the write count and the campaign phase
  untouched.

## 5. Residual issues and documented native needs

- **The loadout tree is live-v2 only.** `sync_loadout()` is a no-op without a
  campaign. The authored default grammar stays on the legacy v1 slice because
  `tools/roguelite/test_runtime.py` encodes the default gesture depth
  (`root -> magic -> fire -> gene` is three presses; the loadout tree is two).
  That file is outside my ownership, so changing the legacy grammar is a
  root-coordinated edit rather than something I should do silently. **Root's
  call:** either accept the legacy default tree, or update that suite's gesture
  sequence and drop the `campaign` guard.
- Because production room recipes are still uncertified, `routes.create` refuses
  and **every new run in the shipped build takes the legacy v1 path**, which is
  exactly the path where the loadout tree is not installed. The certification
  gate stays closed; I did not touch it. The v2 presentation is fully wired and
  tested, and the loadout hook is one guard away from covering both.
- **Native owner cleanup on unload is still missing** and is Root/Sol's seam.
  `on_unload` still never fabricates `reset(true)`; a refused release is logged
  and the handles are retained.
- **Charge effects remain honestly unavailable**; no new gene families were wired.
- **Reduced motion is not a real setting.** There is no native API; it is a
  config-file value. If the port later exposes one, `Presentation.reduced` is the
  single place to read it.
- No native build, run, install or playtest happened. Every result above is a
  deterministic stub with a native-correct `gd.player` copy snapshot. Nothing
  here certifies a recipe, a room, the slope joins, or the full goal.

## 6. Root's integration steps

1. Take the four files in section 2 (`main.lua`, `runtime_presentation.lua`,
   `prepare.py`, the two test files) as this lane's patch; the seeded dirty files
   stay coordinator-owned.
2. Build/install as usual. `prepare.py` now ships three more lexical modules into
   `mods/roguelite/scripts/main.lua`; no asset or recipe change.
3. Decide the legacy-v1 grammar question in section 5.
4. Watched retest, when you next have the pad free: start a run, confirm the
   compact rail shows lives / percent / three ability segments with real charge,
   open the D-pad tree, fork with left/right/down, back out with Up, cast once,
   place a gene at rest and confirm the tree and the rail both follow, then leave
   and confirm the vanilla stock/percent display comes back.
5. The Sol floor-link work and the certification gate are untouched by this lane.

I am stopping here for root review.
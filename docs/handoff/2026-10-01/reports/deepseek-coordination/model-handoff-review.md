# Independent frozen model handoff review

Reviewed 2026-09-30 in
`/home/gd/melee_linux_test/gdm/_build/model-tests/campaign-integration`.
Read the lane handoff, AGENTS.md, seed manifest, authored result, completion plan,
and frozen campaign followup/review evidence. No frozen-lane or native edits,
build, install, launch, commits, or production recipe admission changes.

**Verdict: corrective integration required.** The full suite is green, but three
campaign recovery/finish failures remain reproducible, and HUD release loses
ownership after a thrown restore. The authored live-v2 presentation/loadout work
is otherwise suitable to carry forward after these corrections and the separately
acknowledged legacy grammar correction.

## Verification and patch boundary

Exact full command, run from the lane root:

```
python3 -m unittest discover -s tools/roguelite -p 'test_*.py'
```

Result: **214 tests, OK (skipped=1), 15.990 seconds**. Import-time persistence,
legacy, and runtime suites printed their pass lines. The historical seed
baseline is 199; this reviewer did not reconstruct that baseline again.

Compared all entries of MODEL-TEST-SEED.json against current bytes. Only seeded
`main.lua`, `prepare.py`, and `test_v2_runtime.py` differ. Authored new
`runtime_presentation.lua`, `test_presentation_runtime.py`, and result documentation
are absent from the seed. `runtime_campaign.lua` is seed-identical. Do not take
other seeded modules as this model's patch, especially the older runtime_rooms
over root's subsequent floor-link integration.

Independent probes used the real modules, actual Core transactions, and the
fixture's native-correct copy-snapshot gd.player. Bundled probes temporarily
opened recipe admission in `_certified_source()` and removed that temporary copy
afterward. No probe replaces a runtime service method with an unconditional
success result. All failure injection is at the engine/storage boundary.

## P1-A: terminal rollback retry unpauses with two owned rooms

Locations: `main.lua:919-939`, `runtime_campaign.lua:839-844`.

A travel save failure plus refused collider cleanup reaches terminal error with
`tx` and destination ownership retained. On the periodic retry, retry_recovery
sets phase to recovering and attempts rollback. If cleanup still refuses, phase
remains recovering, but the helper reports success because it is no longer
`failed()`. Main does not recheck blocked/running after the retry: it dismisses
the page, resumes the engine, and marks active true.

Observed same-tick state:

```
before: phase=error, pause=true, rooms:total()=2
after:  phase=recovering, pause=false, active=true, menu=nil, rooms:total()=2
```

The next tick pauses again, but native physics can run between ticks while both
rooms and the failed placement rollback remain owned. on_frame's guard does not
freeze the native simulation. Resume only after a running campaign with genuine
settling/cleanup completion; retain the error reason while recovery is pending.

Bundled-main probe body:

```lua
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step();assert(settle(400))
local c=assert(roguelite_v2())
fail_atomic=true;refuse_stage_remove=true
assert(c:request_travel(c:current_node().exits[1]))
for i=1,240 do
  step()
  if c:failed() and state().menu=='error' then break end
end
assert(c:failed() and c.tx and pause==true)
local saw=false
for i=1,90 do
  step()
  if c.phase=='recovering' then
    saw=true
    assert(pause==false and state().active==true and state().menu==nil)
    assert(c.tx and c.rooms:total()==2)
    break
  end
end
assert(saw)
```

## P1-B: automatic page dismissal resurrects a zero-life run after finish refusal

Locations: `main.lua:397-398`, `main.lua:939`, `main.lua:452-455`.

The new healthy-campaign error-page guard treats every error page as a resolved
campaign error. A refused Core.finish checkpoint restores an active run and sets
pending_finish with the real Retry finish control. Because the campaign itself
is still running, the very next tick dismisses that page and resumes gameplay.
pending_finish remains undriven. The real last-KO path reproduces this with
run.stocks zero; no direct state fabrication or finish stub is needed.

Observed after actual third KO with only the finish write refused:

```
menu=nil, active=true, pause=false, run.stocks=0, run.status=active
```

Distinguish campaign recovery pages from refused finish and unrelated errors.
Never dismiss or resume while pending_finish still requires its transaction.

Bundled-main probe body:

```lua
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step();assert(settle(400))
local c=assert(roguelite_v2())
for i=1,2 do
  ps[1].stocks=98;tick=tick+1;on_frame();step()
end
assert(state().run.stocks==1)
local atomic=gd.data_write_atomic;local calls=0
gd.data_write_atomic=function(...)
  calls=calls+1
  if calls==2 then return false,'finish refused' end
  return atomic(...)
end
ps[1].stocks=98;tick=tick+1;on_frame()
assert(calls==2 and not c.pending_save)
assert(state().menu=='error' and pause==true and state().run.stocks==0)
step()
assert(state().menu==nil and state().active==true and pause==false)
assert(state().run.stocks==0 and state().run.status=='active')
```

## P1-C: recovery of a settling save skips final completion and reward opening

Locations: `runtime_campaign.lua:403-405`, `422-429`, `831-837`.

If marking the newly entered noncombat objective cannot be saved, settling queues
a pending save and waits. Once retries exhaust, phase becomes error. A successful
terminal recovery forces phase active, losing the suspended settling continuation.
For a finish destination, its objective becomes durably done but finish_run is
never called. For a reward/rest destination, reward_room is never scheduled.
Further ticks in active do neither piece of work.

Observed with actual services after traversing the fixture route and failing only
the finish-room objective write:

```
phase=active, objectives.r6=done, FINISHED=nil
```

The state remained unchanged through 30 subsequent ticks. Preserve the pending
save's continuation phase and resume settling before ordinary combat/input.
This defect predates the authored patch but invalidates Phase A acceptance.

Real campaign fixture probe body:

```lua
local camp=reset(7)
assert(enter(camp)=='active')
for _,pair in ipairs{{'r1','r2'},{'r2','r4'},{'r4','r7'},{'r7','r5'}} do
  clear_current(camp)
  for i=1,20 do camp:frame(ps[1],ps[1]);clear_current(camp) end
  local ok,why=camp:request_travel(exit_to(pair[1],pair[2]));assert(ok,why)
  assert(drive(camp)=='active')
end
assert(camp:request_travel(exit_to('r5','r6')))
assert(tick_until(camp,function()return camp.phase=='settling'end))
save_fail=true;camp:tick()
assert(camp.pending_save and camp.phase=='settling')
for i=1,10 do camp:tick() end
assert(camp.phase=='error' and camp.pending_save)
save_fail=false;assert(camp:retry_recovery())
for i=1,30 do camp:tick() end
assert(camp.phase=='active' and FINISHED==nil)
assert(ROUTE.progress.objectives.r6=='done')
```

## HUD release ownership defect

Location: `runtime_presentation.lua:110-116`.

release_hud clears compact even when gd.hud_visible(true) throws before applying
the change. Native HUD remains hidden; later release_hud returns 'not owned' and
does not retry. Retain the claim until a successful restore. This agrees with
root's independent finding. The new presentation test currently asserts the
incorrect ownership loss and needs correction, not merely another test.

Real presentation fixture probe body:

```lua
local p=make{}
assert(p:take_vanilla_hud(true))
assert(hud.visible==false and p:hud_owned())
hud.throw=true;assert(p:release_hud()==false);hud.throw=false
assert(hud.visible==false and p:hud_owned()==false)
local calls=#hud.calls;p:release_hud()
assert(#hud.calls==calls and hud.visible==false)
```

Feedback.draw does respect layout.replace_vanilla=false (`feedback.lua:219`):
failed/missing hide uses minimal life/damage fallback anchors, not the full rail.
Do not characterize that existing fallback as an unconditional compact rail.

## Coverage and smaller integration limits

- Add regressions for terminal recovery where cleanup remains refused, a
  settling-origin pending save, and a refused finish after a real terminal KO.
  Existing active pending-save recovery and ordinary nonterminal rollback tests
  do not cover these states.
- Test native HUD restore refusal while checking both retained ownership and
  the engine visibility, then recovery/retry through main.
- The advertised A-confirm campaign recovery code is unreachable while the
  campaign remains failed: main returns at line923 before the menu branch.
  Automatic recovery does run every 30 ticks. Either wire A in that failed branch
  or describe only automatic recovery. This is a control/coverage defect rather
  than another permanent recovery blocker once the P1s are corrected.
- The live-v2-only sync_loadout guard leaves every currently admitted new run on
  the default legacy tree. The author explicitly disclosed this; root has already
  chosen to correct it with the legacy gesture suite. It remains required work,
  not an accepted shipped compact-command integration.
- Legacy successful doorway travel has no Onboarding.observe door event; live-v2
  does. The main tutorial test completes movement only; its door travel occurs
  while charge is still current, so it does not assert actual door-step completion.
  Similarly it does not exercise every listed cast/tell/reward event in sequence.
- UI settings/onboarding context exists, but skip/revisit methods are not
  dispatched from main. Avoid claiming full functional tutorial/settings screens.
- Recipe certification remains closed. No stub result certifies native geometry,
  slope joins, owner cleanup, controller ergonomics, or the full completion goal.

## Reproducing the snippets

From the lane root, prepend `tools/roguelite` to Python sys.path and import
test_v2_runtime. Campaign bodies run with PRELUDE and the real runtime directory:

```python
subprocess.run([t.LUA, '-', str(t.RT)],
               input=t.PRELUDE + body, text=True, capture_output=True)
```

Bundled-main bodies use the test-only source and real prepare bundle:

```python
s = t._certified_source()
try:
    bundle = '(function()\n' + t.prepare.bundle(source=s) + '\nend)()\n'
    result = subprocess.run([t.LUA, '-', str(t.RT)],
                            input=t.PRELUDE_MAIN + ';\n' + bundle + body,
                            text=True, capture_output=True)
finally:
    shutil.rmtree(s)
```

The HUD snippet uses test_presentation_runtime.PRELUDE. All four probes exited
zero while asserting the defect states above. Corrective regressions must assert
their safe opposites.

## Root disposition after corrective integration

Accepted and landed 2026-09-30 after the four findings above were fixed in root, with the frozen submitted lane preserved. Source commit `fed9dbf94`; wrapper/bundle/regression commit `a5fdad4`. Independent root discovery ran **243 tests, OK, 18.242 seconds**; log `model-handoff-root-final.log`. Root's newer room floor-link helpers and native work were preserved.

Recovery retries now require a running campaign before resuming; exhausted objective saves resume settling and execute finish/reward continuation once. Final-KO result save refusal retains the distinct Retry Finish page. HUD restore failures retain ownership and lifecycle retries, and draw/layout failures attempt vanilla fallback. The loadout-derived command tree is installed for both legacy and v2 routes; production legacy tests cover placement, held-Up latch, supply depletion/refund/resume and all eight observed onboarding steps.

No production recipe was certified by these tests. These are Lua/engine-stub checks; no native visual/menu/combat playtest of this handoff is claimed. Root separately verified live native instance/floor ownership fallback after a throwing unload hook, preserving the paused branch scene; that scope does not establish traversal or full-mode native acceptance.

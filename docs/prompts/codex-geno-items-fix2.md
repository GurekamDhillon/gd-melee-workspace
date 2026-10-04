# Packet P follow-up 2: a crash when item drives with models coexist with enemy spawns (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep files compilable). With the drive asset mod mounted (so each
drive item draws a loaded model) the game hit ACCESS_VIOLATION twice during Envoy runs; without the asset mod (fallback
visual) it never crashed across many runs. Both faults are at `Item_80267AA8` (map rva 0x1022947F), called from
`gw_it_8027B5B0` and `gw_ScriptGame_SpawnEnemy`: once during the spawn of a polar bear in wave 2 (fault read 0xFF73FF73),
once during the first Koopa spawn of a second run, right after `preload /GrNKr.dat kind=211 ready` (fault read 0x00000000).
Crash logs: `_build/audit-20261003/envoy-verify2/crash_env2-b.log`, `crash_env2-c.log`. Read `Item_80267AA8` and what it
dereferences, and find how a standalone Geno item with a bound model can leave the item system in a state that the next
enemy spawn trips over: candidates are the item's model binding using item fields the vanilla item code also uses (the
item's JObj/DObj or its article data pointer pointing at our visual), the kind dispatch returning a descriptor whose model
or attribute pointers are read by generic code for our kind, a use-after-free when a drive is collected or expires in the
same frame an enemy item is created (slot reuse while the visual binding still points at the freed item), the first-spawn
preload interleaving with an enemy file preload, or heap exhaustion from model loads. Fix at the root and add a fixture that
spawns and frees drives with bound visuals interleaved with vanilla item creation and asserts the generic item paths never
read our fields. Also: `runs.py status` showed `owner=untracked state=unknown` for runs started with `MELEE_RUN_OWNER` set
through a wrapper script: not yours, but if you see why from the item of the same report, say so.
Reply with the cause in three lines and file:line; `_build/tmp/codex-geno-items-fix2-report.md`.

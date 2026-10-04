# Packet O follow-up: link errors from the integrator's build (2026-10-03)

Everything compiles. The link fails on three symbols your game-side code references (the other three unresolved symbols in
the log belong to a different job that is still writing its native half: ignore `_gw_Geno_ItemParam`, `_gw_ItemEvent`,
`_gw_ItemDraw`). Log: `_build/audit-20261003/mission-integ/build12.log`.
```
pc_gameworld_script_game.c.obj : unresolved external symbol _gw_stage_datas referenced in function _gw_ScriptGame_StageSlotFile
pc_gameworld_script_game.c.obj : unresolved external symbol _gw_strchr referenced in function _gw_ScriptGame_StageSlotFile
pc_gameworld_script_game.c.obj : unresolved external symbol _gw_memchr referenced in function _st_dat_open
```
Game TUs are compiled as PowerPC and retargeted: every symbol gets a `gw_` prefix, so a game-side reference to `strchr`
becomes `gw_strchr` and must exist as a native shim or as game code (`melee/CLAUDE.md`, "The shim boundary"). The libc shim
does not provide `strchr` or `memchr`; `stage_datas` is not a symbol the link has under that name (check how the decomp
declares the stage data table and whether it is static, differently named, or in a TU that is not linked).
Fix at the root: use functions and symbols that exist on the game side (or add the two libc shims properly in the libc shim
file with tests if that is the right place, following its conventions), and reference the stage table through its real
symbol. Same rules: no build, no game launch, no commits; another job is editing `melee/pc/geno/` and `gw_script*item*`.
Reply with file:line changed.

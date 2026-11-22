# Codex packet: Linux mod surface shaders (2026-10-08)
Worktree exists; edit ONLY it; no git writes: game `E:\Projects\Melee Workspace\worktrees\linux-surface` (agent/linux-surface, from
integration; build root `E:/Projects/Melee Workspace/_build/agents/linux-surface`). You may build Windows + run the headless suite.
A Linux run of Envoy logs `surface shader shaders/modifiers_surface.wgsl: surface shader loading requires Windows` (twice): mod
surface shaders are Windows-only, so Envoy's modifier visuals are missing on Linux. Same family as two POSIX stubs just fixed on
agent/rc3-fixes (gs_mission_script_root realpath; item define + opendir scan in gw_script_items.inc) - read that commit (b8f7039dd)
for the house style. Find the `#ifdef _WIN32` gate(s) on the surface-shader path, implement the POSIX side (file reads/paths only;
the renderer is shared Aurora/WebGPU), keep Windows byte-identical, add a native or --test test that loads a surface shader
through the platform-neutral path. Check other `_WIN32`-only script/mod loaders in pc/platform/gw_script*.inc with a POSIX stub
that returns failure, and list them (fix the trivial ones the same way). The coordinator builds and runs Linux.
Report `E:\Projects\Melee Workspace\_build\tmp\codex-linux-surface-report.md`: gates found, fixes, tests, remaining Windows-only
loaders, commit message.

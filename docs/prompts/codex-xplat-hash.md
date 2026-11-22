# Codex packet: Windows-vs-Linux pre-match checksum mismatch (2026-10-08)

Worktrees exist; edit ONLY these; no git writes:
- game `E:\Projects\Melee Workspace\worktrees\xplat-hash` (agent/xplat-hash, from integration 021ea8ada), build root
  `E:/Projects/Melee Workspace/_build/agents/xplat-hash`
- workspace `E:\Projects\Melee Workspace\worktrees\ws-xplat-hash` (ws/xplat-hash)
You may build (Windows), run the headless suite and native tests. You cannot run windowed games or WSL two-client pairs in
your sandbox: write those commands for the coordinator.

## Evidence (0.2.2-rc2, game 81f9807ae, build id 571a306276d673ed, vanilla disc, Windows host vs Linux (Arch, i686 build) guest)
Every online match logs ONE `netplay: DESYNC at frame -80/-91/-95` (a PRE-MATCH frame, the negative entry frames) on both sides
with mirrored checksums (Win local E6DDD7D5 / peer 5D2DD899; Linux the reverse), then none: the periodic reports show
desyncs 0 and play stays visibly in sync. Both sides applied identical Envoy builds (same record/ops hashes), so Envoy's
rules are equal. The geno-s7 lane saw the same class Windows-v-Linux: isolated single-frame per-frame hash differences
(237/7434 frames with Geno; 127/7433 with retail Fox v Marth, no mods); Windows-v-Windows 0.
Logs: Windows `_build/release-022rc2-win/GDMelee-0.2.2-rc2-win64/userdata/runs/0efe2ba1-a654-4816-84ef-80e0007f676b/melee-pc.log`;
Linux: `gh gist view 676abeb3f6b9c33e0ff7fb11e976a51e -f 22-laptop-rc2-full.log`.

## Do
Read `docs/xplat-netplay.md`, `tools/xplat/` (cmp_xhash.py, build_both.sh, net_pair), the checksum code in `pc/platform/gw_rollback.c`
/ `gw_netplay.c` / the snapshot hash, and how negative (pre-match) frames are hashed.
1. Find WHICH state differs: add (or use the existing) per-region/per-word checksum breakdown logged on the first mismatching
   frame (and an env-gated per-frame region hash dump), so a two-client run names the region/offset/symbol.
2. Reason from code about platform-dependent state in the hashed range: pointers/addresses, padding bytes, uninitialised
   memory, host-side structs inside the hashed arena, float formatting/rounding (x87 vs SSE, already SSE2?), time, heap layout,
   ABI size differences (i686 both? struct packing, long/wchar), Lua heap (the Geno slice-7 note: 16 vs 12-byte values).
3. Fix it in the game (exclude host-only state from the hash with a written reason, or make the state platform-neutral),
   never by weakening the check for real game state. Add a native test that catches the class (e.g. hashing a struct with
   padding filled differently gives the same checksum after the fix).
4. Headless suite + native tests pass; no new failures.

## Deliver
Report `E:\Projects\Melee Workspace\_build\tmp\codex-xplat-hash-report.md`: the suspect state with evidence, the fix, tests,
the exact coordinator commands for a Windows-host vs WSL-Linux-guest pair (tools/xplat net_pair with --bind/--offscreen) that
should then show 0 mismatches including pre-match frames, and proposed commit messages.

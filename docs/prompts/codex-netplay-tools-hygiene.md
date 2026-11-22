# Codex packet: netplay test-tool and packaging hygiene (2026-10-08)

Workspace root `E:\Projects\Melee Workspace` (this repo only; do NOT touch the `melee/` game checkout or any other worktree).
The worktree `E:\Projects\Melee Workspace\worktrees\ws-tools-hygiene` (branch `ws/tools-hygiene`) ALREADY EXISTS; edit files ONLY there. Your sandbox cannot write `.git`: do NOT run git commands that write (no commit, add, worktree); the coordinator commits your changes.
Read `CLAUDE.md`, `tools/CLAUDE.md`, `tools/release/README.md`, `tools/netplay/server/README.md`.
Do not build or launch the game; Python and PowerShell unit tests only.

## 1. Netplay test drivers default to loopback

Windows Firewall prompts for every new exe path that listens on a non-loopback address, and an unanswered prompt stalls
the test. `MELEE_NETPLAY_BIND=127.0.0.1` (game, `gw_netplay.c`) avoids it. Make every automated netplay driver set it by
default for every client it launches, and start its local matchmaking server with `--bind 127.0.0.1`:
`tools/netplay/np_drive.py` (its `--local-server` path), `tools/xplat/envoy_set.py`, `tools/xplat/pair.py`,
`tools/xplat/net_pair.py`, and any other script under `tools/` that launches two netplay clients (grep for `MELEE_NETPLAY`).
Allow an explicit override (an env var already set by the caller wins, or a `--bind` flag). Never bind 0.0.0.0 by default.
Note: WSL-to-Windows cross-platform runs need a non-loopback address; keep those paths working via the override and say so
in the script's help text. Add/extend a unit test that asserts the default environment a driver builds contains
`MELEE_NETPLAY_BIND=127.0.0.1`.

## 2. Windows package: text files with LF line endings in mods

The Windows release package's mod text files have CRLF while the Linux package's have LF (git autocrlf on Windows). The
game's mod fingerprint now ignores CR, but packages should still be byte-identical across platforms where possible. In
`tools/release/build_release.ps1` (the mod copy, `Copy-In` or equivalent), copy text files (`.lua .json .md .txt .wgsl
.words .genoasm` and any other text types in `tools/release/mod_rules.json` allow-lists) with LF line endings
(convert CRLF to LF), leaving binaries untouched. Keep `check_release.ps1` and the release tests passing; add a test that a
CRLF text file in a mod is staged as LF and a binary file is byte-identical.

## Proof and delivery

Run the relevant Python tests (`python -m pytest tools/release tools/netplay tools/xplat -q`, or the specific test files)
and report counts (run them from the worktree). Do not commit (the sandbox forbids it); leave the changes in the
worktree, and write a proposed commit message at the top of the report. Report to
`E:\Projects\Melee Workspace\_build\tmp\codex-tools-hygiene-report.md`: files changed, test output, anything unverified.

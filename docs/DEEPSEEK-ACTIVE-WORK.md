# Active coordinated implementation — 2026-09-30

User closed the previous OpenCode session and authorized standard-effort
DeepSeek workers in as many isolated worktrees as useful. Root owns reviews,
landing, shared native builds, installed profiles and game runs. No release.

| Worker | Location | Owned output | State |
| --- | --- | --- | --- |
| Persistence | Main checkouts | main/checkpoint persistence, bundler, focused tests | Landed persistence seam; atomic-only refusal regression reviewed |
| Physical | `_build/deepseek-worktrees/physical` | `runtime_rooms.lua`, `test_physical_runtime.py` | Reviewed; focused tests green, integration pending |
| Encounters | `_build/deepseek-worktrees/encounters` | `runtime_encounters.lua`, `test_encounter_runtime.py` | Reviewed; focused tests green, integration pending |
| Certification | `_build/deepseek-worktrees/certification` | isolated certification script/mod and CLI/tests | Reviewed harness; root native probes uncovered scene/timing/output fixes |
| Rewards | `_build/deepseek-worktrees/rewards` | `runtime_rewards.lua`, `test_reward_runtime.py` | Reviewed; focused tests green, integration pending |

| Live integration | `_build/deepseek-worktrees/integration` | `main.lua`, optional `runtime_campaign.lua`, bundler, new v2 integration tests | Implementing; root preserves certification gate |

Each isolated lane has separate wrapper and game Git worktrees on an
`agent/deepseek-<task>-20260930` branch. Frozen Sol module/test changes were
copied in as baseline, not as newly owned work. Only copy/land each worker's
owned outputs after it stops editing; never indiscriminately commit its baseline
dirty changes. Review interfaces and dependency order before wiring main.

Task prompts and JSON event logs are in `_build/deepseek-coordination/`.
All workers use `deepseek/deepseek-flash` with default effort, `--pure`, and
bounded coding tasks. Root's direct API authentication test passed. Credentials
remain in the existing OpenCode store. See `DEEPSEEK-COORDINATION.md`.

Root completed native path-check follow-up `05d2f429a`, built the Linux binary
with bridge/ABI checks, and passed the 34/34 native scripting group, including
long-path refusal preserving old data. Root has not claimed the full new mode
is installed/live. Production recipes remain uncertified.

Next integration order: persistence acceptance → physical/encounter/reward module
review → live route creation/entry/doors/progress wiring → isolated native
certification harness runs → admitted generated-run acceptance. Then continue
later content/menu/FX/platform/polish gates from the full plan. Human feel and
unavailable hardware stay pending; they do not block independent engineering.

Selected PNG art-reference sheets are open in imv for the user's return. Add
useful in-game captures as normal acceptance work produces them; no new
interactive art viewers and no uncapped/turbo experiment.

Review update: helpers plus existing module/runtime suites passed 111 named tests on root (before later harness refinements). Physical 10/10, encounters 8/8, rewards 11/11 focused cases passed. Native room probe is not certified: actual stage isolation falls back after construction and remains under investigation; original FD visibility makes captures diagnostic only. Harness now waits through Ready/Go, retains partial cleanup ownership, parses multi-argument Lua commands correctly, uses absolute PNG paths and bounded trace pages. Do not admit recipes or claim generated runs playable from this evidence.

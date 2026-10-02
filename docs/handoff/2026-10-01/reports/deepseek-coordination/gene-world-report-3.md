# Gene-world adapter: root coordination report 3 (review-3 correction)

Lane: `agent/deepseek-gene-world-20260930`
Worktree: `/home/gd/melee_linux_test/gdm/_build/deepseek-worktrees/gene-world`
Status: **corrected and frozen for root review.**

Read: updated `AGENTS.md`, `gene-world-followup-3.md`, `gene-world-review-1.md`,
`native-hit-refusal-audit.md`, `GENE-WORLD-REVIEW-SEED.json`. (`gene-world-review-2.md`
was not present at freeze time.)

## Accepted dependencies (verified unchanged in lane)

| file | sha256 |
| --- | --- |
| core.lua | `30c025cfb87a56191a5440d51e80dca68c1e812add9e6dfeeffa5f96aa06dd8c` |
| gene_behaviors.lua | `daaa14d6388eec3d415eab4d84df8b28d0fe196097e16b6eb964f5afe34ced48` |
| gene_actions.lua (accepted) | `994bfe3d6cbf80ab0862e90a812e64a18cfb95aa35e2762985a12f7971326983` |
| docs/GENE-ACTION-CONTRACT.md | `7cd70e329a9237b7dd1e80bd2b356a6110bf66c06e272e5851ec6b01985a5f08` |

No Core/behaviors/main/prepare/native edits. `gene_actions.lua` remains the
accepted file plus the same three bounded optional hooks from pass 2.

## Files and new hashes

| file | sha256 |
| --- | --- |
| `runtime_gene_world.lua` | `0195e4c0135419ae89079e3df6f09e539af288bde1aa042152891a5ae16c6dc5` |
| `gene_actions.lua` (accepted + 3 hooks, unchanged from pass 2) | `f33fcedf3f2e25c5b3a71c44a2bd767def7ae4c3a2aad90c8ce9c8e2346f8d2c` |
| `test_gene_world.py` | `00da04b0591f57143ab636eb215761ec7f92adaebf6d76d1a67d18a281dbd116` |
| `GENE-WORLD-CONTRACT.md` | `24740b82715cb0ed31f5ff03b7d44e51e0fcd280e2810afdda8435e0f4adf683` |

## Confirmed defects fixed

1. **Provider false/nil plus token was forgotten.** `apply_contribution` now
   owns any identifiable token regardless of acceptance, attempts cleanup
   immediately, and retains it for `reset`/`release` retry if the release
   refuses. Regression: false+token and nil+token both refund the spend and call
   `provider.release` exactly once (adapter owned 0, no live token).
2. **`{ok=true,contrib}` table success was accepted.** Acceptance now requires
   the provider's exact `true`; a table success is treated as a refusal and its
   token is refusal-owned and cleaned up. Regression asserts refusal and cleanup.
3. **Cleanup used the latest run, not the owning run.** Records store their
   minting run; `release`/`reset` call `provider.release(record.run, token)` and
   never a later run after a `get_run` switch. Regression promotes the run then
   resets and asserts the provider saw the original run.
4. **Unknown eligibility granted damage.** Player eligibility now requires
   complete known `body_state`, `timed_state`, numeric immunity timers and a
   boolean `shield_on`; `?`/absent values and an `invulnerable` provider
   returning nil/error all fail closed. `false` is safe only because the
   provider contract explicitly defines it as "not invulnerable". Regressions
   cover `?` body/timed, omitted body/shield, nil/error providers, explicit-false
   success and known-normal success.
5. **Custom-enemy traversal began and spent.** `native_capability` now rejects
   `gd.impulse` for a non-player source, so `begin` refuses with no spend,
   refund or native call, while fighter traversal still succeeds and calls
   impulse.

## Test evidence (real counts)

- Lane contract: `python3 -m unittest tools.roguelite.test_gene_world -v` →
  **2 tests / 16 finding groups pass** against the accepted dependencies.
- Accepted pure action suite: root 34-group `test_gene_actions.py` run against
  this lane's hook-augmented `gene_actions.lua` → **2 tests pass**.
- Full lane discovery `python3 -m unittest discover -s tools/roguelite` →
  **188 tests, 3 errors, 4 skipped**. The 3 errors are the pre-existing
  environmental failures (missing generated `menu/out_effects_study/manifest.json`,
  missing room-kit sidecars, `test_runtime` import quirk). Discovery is **not
  green**; these are not caused by this lane.

Contract tests only: the `gd` double returns booleans and runs no native
collision/hitlag/armor/shield/projectile path.

## Unimplemented limits (honest handoff)

- No native LOS/occlusion; line attacks fail closed without an explicit
  trustworthy `visibility` provider.
- No native reflection read; optional provider only.
- No native guard/root/freeze/convert/siphon; optional provider only.
- No custom-vs-custom strike; no dodgeable startup/bounded collision.
- `x221C_b4` armor, `x1834` armorHP and `x221D_b6` immunity are not exposed.
- `gd.hit`/`gd.enemy_strike` native false may still have chipped armor until
  root's corrected native APIs land; the opt-in acknowledges this.
- No native/live collision, shield, controller or rollback evidence.

## Root integration notes

1. Merge the three bounded `gene_actions.lua` hooks or land the lane file.
2. Bundle `runtime_gene_world.lua` before `main.lua`; construct one world with
   the real `gd`, `get_run`, `current_room` and a trustworthy `visibility`
   provider; bind/unbind actors with a per-encounter `token`.
3. Set `native_hit_contract` only after confirming the accepted native
   damage-result semantics.
4. Live native validation (collision, shields, immunity, controller) remains a
   separate authorized pass.

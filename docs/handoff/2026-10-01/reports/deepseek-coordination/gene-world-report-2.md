# Gene-world adapter: root coordination report 2 (review-2 correction)

Lane: `agent/deepseek-gene-world-20260930`
Worktree: `/home/gd/melee_linux_test/gdm/_build/deepseek-worktrees/gene-world`
Status: **corrected and frozen for root review.**

Read: updated `AGENTS.md`, `gene-world-followup-2.md`,
`gene-world-review-1.md`, `native-hit-refusal-audit.md`,
`GENE-WORLD-REVIEW-SEED.json`. Accepted dependencies were re-seeded and verified
in-lane before the fix.

## Accepted dependencies (verified in lane)

| file | sha256 |
| --- | --- |
| core.lua | `30c025cfb87a56191a5440d51e80dca68c1e812add9e6dfeeffa5f96aa06dd8c` |
| gene_actions.lua (accepted) | `994bfe3d6cbf80ab0862e90a812e64a18cfb95aa35e2762985a12f7971326983` |
| gene_behaviors.lua | `daaa14d6388eec3d415eab4d84df8b28d0fe196097e16b6eb964f5afe34ced48` |

## Files and new hashes

| file | sha256 |
| --- | --- |
| `runtime_gene_world.lua` (rewritten) | `1f668244700a2cb17b55091375ba71fdcb539b19e369323f5bfa1b6bca8e5f24` |
| `gene_actions.lua` (accepted + 3 bounded hooks) | `f33fcedf3f2e25c5b3a71c44a2bd767def7ae4c3a2aad90c8ce9c8e2346f8d2c` |
| `test_gene_world.py` | `fd66f6f33cc78fda3012e691ec1976747bbf8fe89d1c21f26b1f4744253dde25` |
| `GENE-WORLD-CONTRACT.md` | `7e4ee0f820f835eb79cc813acc86e8bae161e1d6972139127326137f7cd200fe` |

The engine diff versus the accepted `994bfe...` is exactly three additive,
optional, generic edits: capture in `begin`, validate before spend in `release`,
and `intent` carried in `request` (plus the rec field). No Core/behaviors/main/
prepare/native edits.

## Review-1 findings fixed

1. **`can_start` clobbered the selected target token.** Removed all
   selected-identity state from `can_start`/`query`; it is side-effect-free.
   Unchanged bindings now succeed (group 11).
2. **Pending actions followed rebound actors, including Core-owned Rime marks.**
   `capture_intent` freezes run/source/target identity at begin; `validate_intent`
   runs before `Core.activate` and cancels any token/gen/ref/port/handle/run/room
   change with no spend. Movement, native strikes and Core-owned marks all cancel
   (groups 11, 12).
3. **Provider false/nil-plus-token acceptance and cleanup.** `apply_*` now
   requires the provider's exact `true`; false/nil plus token is a refusal with
   authored refund. Refused release retains the adapter-owned record and reports
   it; `reset(run)` releases owned tokens through the provider, refuses while a
   release is refused, and never forgets a token (group 13).
4. **Missing native/provider capabilities spent-then-refunded.** Capability is
   now proven per effect/direction against the actual `gd` functions and
   providers; a missing function/provider refuses at `begin` (and again at the
   spend point), with `capabilities()`/`eligible()` reporting the exact result
   (groups 1, 6, 7, 8).

## New corrections from the followup

- **Native hit/strike acceptance opt-in.** `gd.hit` and `gd.enemy_strike` require
  `native_hit_contract = 'accepted_damage'`; without it they refuse before any
  native call. `gd.enemy_hurt` and `gd.impulse` keep their audited separate
  contracts. The audit's armor-chip limit is recorded, not guessed around
  (groups 1, 2, 4).
- **Eligibility from real fields.** Player immunity is read from `body_state`,
  `timed_state`, `invincible`, `intangible` and `shield_on`; unknown eligibility
  fails closed. Enemy vulnerability requires `vulnerable == true`. The
  unexposed armor/immunity flags are documented limits (group 5).
- **No irreversible retry.** false/nil/throw are single refusals; the throwing
  callback is called exactly once (group 6).
- **Two simultaneous actions** are independent; no shared expectation exists
  (group 12).
- **Hookless-world compatibility** is preserved and tested (group 15).

## Test evidence (real counts)

- Lane contract: `python3 -m unittest tools.roguelite.test_gene_world -v` →
  **2 tests / 15 finding groups pass** against the accepted dependencies.
- Accepted pure action suite: the root 34-group `test_gene_actions.py` (read
  from the gene-actions worktree, run with this lane's hook-augmented
  `gene_actions.lua` and the accepted Core/Behaviors) → **2 tests pass**.
- Full lane discovery `python3 -m unittest discover -s tools/roguelite` →
  **188 tests, 3 errors, 4 skipped**. The 3 errors are pre-existing environment
  failures: missing generated `menu/out_effects_study/manifest.json`, missing
  room-kit sidecars, and the `test_runtime` `import prepare` quirk.

These are contract tests, not native hit proof; the `gd` double returns booleans
and runs no collision/hitlag/armor/shield/projectile path.

## Unimplemented limits (honest handoff)

- No native line-of-sight/occlusion; all line attacks fail closed without an
  explicit trustworthy `visibility` provider.
- No native reflection read; optional provider only.
- No native guard/root/freeze/convert/siphon; optional provider only.
- No custom-vs-custom strike; no dodgeable startup/bounded collision.
- `x221C_b4` armor, `x1834` armorHP and `x221D_b6` immunity are not exposed.
- `gd.hit`/`gd.enemy_strike` false may still have chipped armor until root's
  corrected native APIs land; the opt-in acknowledges this.
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

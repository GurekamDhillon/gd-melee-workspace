# Gene-world adapter: root coordination report

Lane: `agent/deepseek-gene-world-20260930`
Worktree: `/home/gd/melee_linux_test/gdm/_build/deepseek-worktrees/gene-world`
Status: **frozen for root review.** Report-only artifact outside the lane.

## Files

New, owned:

- `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_gene_world.lua` — native world adapter.
- `tools/roguelite/test_gene_world.py` — contract tests.
- `docs/GENE-WORLD-CONTRACT.md` — adapter contract and handoff.

Not touched: `core.lua`, `gene_actions.lua`, `gene_behaviors.lua`,
`gene_catalogue.lua`, `enemy_genes.lua`, `main.lua`, `prepare.py`, native code,
other workers, generated art. No build/install/game launch/commit/push/release.

## What it does

`GeneWorld.new(Core, engine, opts)` returns the plain `world` table expected by
`gene_actions.lua` (the frozen seam in `docs/GENE-ACTION-CONTRACT.md` section 5):
`get_run`, `observe`, `can_start`, `query`, `occluded`, `apply_effect`,
`apply_movement`, `apply_status`, `apply_guard`/`release_guard`,
`apply_conversion`/`release_conversion`. The runtime caller owns actor bindings
via `world.bind/unbind` and injects `gd` plus optional `current_room`,
`visibility`, `invulnerable`, `reflecting`, `status`, `guard`, `conversion`.

Key invariants enforced: active-run + `run.hosts` validation; monotonic
binding generations with an optional per-encounter `token`; native-identity
`ref`; finite snapshot positions; bounded bindings/targets/contributions;
deterministic nearest-target order; same-room/opposing-team/alive/vulnerable/
range/height/facing/free-state filtering; mutation-time revalidation (run,
source and target generation/reference, team, room, native bounds, occlusion);
fail-closed occlusion (absent provider refuses line attacks); no fabricated hit
evidence; no hidden target memory.

## Native APIs supported / refused

Supported (audited against `melee/worktrees/linux/pc/platform/gw_script.c` and
`docs/scripting.md`):

- `gd.player(port)` — schedule/shield/action/hitlag/facing/position read.
- `gd.enemy_state(handle)` — owned Adventure actor read, incl. `vulnerable`.
- `gd.hit(port, {damage, angle, kbg, bkb, from})` — fighter -> fighter.
- `gd.enemy_hurt(handle, {from, damage, angle, kbg, bkb, reach})` — fighter -> owned custom.
- `gd.enemy_strike(handle, port, {damage, angle, kbg, bkb, reach})` — owned custom -> fighter.
- `gd.impulse(port, {x, y})` — dash/hover locomotion, bounded; native refusals pass through.

Refused (missing from the confirmed build; no emulation):

- Line of sight / occlusion (no raycast API) — default deny.
- Fighter invulnerability and reflection (not in `gd.player`).
- Custom -> custom strike; native guard/root/freeze/convert/siphon seams.
- Dodgeable startup / bounded native attack collision behind the transaction.

Capability preflight: `world.supports(gene, slot)` / `world.capabilities()`
report only `cinder`/`rime` as admitted (`rime` assault/guard are Core-owned
native marks); every other family stays refused until a real provider exists.

## Tests run

```sh
python3 -m unittest tools.roguelite.test_gene_world -v
```

Result: 2 tests, passing. 16 finding groups cover the required cases
(fighter/fighter, fighter/custom, custom/fighter, correct fields, eligibility
refusals, host/run/actor drift, same-port new-encounter token, escape/LOS after
query, absent LOS, missing/false/nil/throw, unsupported mechanics with no side
effects, movement free/rebirth/hitlag, deterministic ties, forged/NaN/infinite
bounds, binding capacity/cleanup, contribution ownership/refusal, Core mark not
double-applied, Cinder guard counter as a strike).

Full discovery: 188 tests, 3 pre-existing environment errors (missing generated
`menu/out_effects_study` manifest, missing room-kit sidecars, `test_runtime`
import quirk). These are unrelated to this adapter and match the documented
baseline in `docs/GENE-ACTION-CONTRACT.md`.

The tests are a **contract test, not native hit proof**: the injected `gd`
double returns booleans and does not run Melee collision, hitlag, shields,
projectiles or the collision-loop callback.

## Honest remaining live wiring

This adapter is **not integrated**. Root still owns:

1. Bundling `runtime_gene_world.lua` in `prepare.py` and constructing the world
   with the real `gd` and encounter bindings in `main.lua`.
2. Binding each live host at actor creation and unbinding at retirement; passing
   a new `token` when a fighter port is reused for a different encounter.
3. Providing a trustworthy `visibility` provider if line-occlusion genes are to
   be offered; otherwise all line attacks stay refused (safe default).
4. Native live evidence (actual collision, shields, hitlag, reflection) and
   controller play — not established here.

## Recorded mismatches / notes for root

- Seeded `gene_actions.lua` drops `contrib` on release regardless of the return
  value; pass 7 retains it on refusal. The adapter owns contributions
  independently, so ownership/refusal are retained and reported under either
  engine; no contract was weakened.
- Fighter-port identity is only the port; callers must use `token`/rebind to
  distinguish a new encounter at a reused port.
- `gd.hit` emits no collision-loop `on_hit`; dispatch must not treat the
  adapter's acceptance return as a charge/hit callback.

Let me inspect the relevant modules for the migration-safety and generator-version details before editing.

Now update the fixture generator and scenarios in `test_persistence.py`.

Now extend `test_checkpoint.py` for malformed nested sections and restore-exception containment.

Let me refine the migration-safety gate to only refuse when the route actually has history the old record omits.

All four review findings are fixed and verified. No commits, native builds, or installs.

## Fixes

**1. Staged validation; no live mutation before a validated write** (`main.lua:save`)
`save()` now deep-copies the run (`Core.snapshot`→`Core.restore`), applies `route_mirror` to that staged copy only, encodes, and runs the full `checkpoint(text)` semantic validation **before any disk write**. The write is followed only by the byte readback equality check. Live `run` mirrors and `generation` are committed only after success, so a refused or failed save leaves previous in-memory state exactly intact and cannot clobber the last usable slot. A semantic refusal now reports `Save refused: …; previous checkpoint retained`; the raw `gd.data_write` fallback is explicitly documented as non-atomic.

**2. Explicit preserve flag, no free-text matching** (`checkpoint.lua`, `main.lua`)
`Checkpoint.decode` now returns `record` **or `nil, reason, preserve`**, where `preserve` is true only for versions newer than supported (outer envelope, inner manifest schema, inner progress version). `classify` keys protection off that flag, not `:find('preserved')`. `main.checkpoint` also detects an unsupported `generator_version` (vs `Topology.version`) and an unsafe schema-1 migration explicitly and returns `preserve=true`. Future-inner-schema slots stay protected and are never overwritten by a redirected save.

**3. Migration safety gate** (`main.lua:progress_migration_safe`)
Schema-1→2 migration is allowed only when the route carries no finite pickups/`grants_consumable` and no consumable-key gates that the old record omits; otherwise it is preserved/refused instead of inventing empty claims. The gate is per-history (`record.pickups`/`record.opened`).

**4. Decode containment** (`checkpoint.lua`)
Both `core.restore` calls are now wrapped in `pcall` and reported as `invalid profile/run section`; malformed manifest/progress JSON already returned controlled refusal. Added tests for real malformed nested sections with valid envelope/checksum, plus a throwing restore dependency.

## Test evidence
Added fixtures/scenarios (test-only in-memory certification + a temp-copy `Route.validate_save` refusal hook; tracked sources untouched; temp dirs managed by `TemporaryDirectory`):
- future generator version and future manifest schema preserved alongside valid old A
- schema-1 migration refused with insufficient history; genuinely safe migration loads and persists as schema 2
- forced semantic refusal and forced `data_write` failure with a protected sibling: last usable slot, protected sibling and live mirrors all unchanged
- malformed nested section / throwing-restore containment

```
python3 tools/roguelite/test_checkpoint.py   -> passed (incl. malformed sections, preserve flags)
python3 tools/roguelite/test_legacy.py       -> passed
python3 tools/roguelite/test_runtime.py      -> passed
python3 tools/roguelite/test_persistence.py  -> 10 scenarios passed
python3 -m unittest discover -s tools/roguelite -p 'test_*.py'
Ran 37 tests in 11.464s
OK
```
`git diff --check` clean; bundle Lua syntax (`luac -p`) passes. v2 gameplay refusal and uncertified recipes are unchanged.

## Changed files
- game `pc/scripts/examples/roguelite/main.lua`, `.../checkpoint.lua`
- wrapper `tools/roguelite/prepare.py`, `tools/roguelite/test_checkpoint.py`, `tools/roguelite/test_persistence.py`

Let me re-read the current module sections I need to change.

Now I'll implement the review changes. First, module constants and constructor eligibility:

Now update the tests. First extend the stub factory and add fighter-family/slot passes:

Addressed all review findings. Stopping editing.

## Owned files (same two; nothing staged/committed, dirty baseline untouched)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_encounters.lua`
- `tools/roguelite/test_encounter_runtime.py`

## API changes
- **Ordinary fighters now gene hosts.** `plan`/`spawn_entity` give every `fighter` a real Core host (slot-aware) unless `buff_fighters=false`; `champion` stays the stronger buff. Buff is a real `Core.apply_modifier` potency modifier.
- **New opts:** `fighter_family` (default `'cinder'`), `fighter_slot` (default `'assault'`), `buff_fighters` (default `true`), `fighter_potency` (1), `champion_potency` (4). Constructor asserts families/slots against actual `Core.definitions` variants.
- **Per-row policy:** `row.family` and `row.slot` accepted when supported. An explicit unsupported family/slot is refused for every kind (no silent conversion); omitted uses the deterministic default.
- **Eligibility surfaced:** static `RuntimeEncounters.families` (`cinder`,`rime`), `.slots`, `.default_fighter_family`; `e:eligibility()` and `status().eligibility`; `status().fighter` and `composition()` now carry `family`, `slot`, `buff`, `host`.
- **Active host exposed:** `e:active_entity()` returns `{id,kind,role,remaining,host,family,slot,buff}` so main can drive ability/activation/provenance exactly as for native opponents.
- **Lifecycle safety:** `has_live()` added; `reset()` refuses while live owned actors/hosts remain; `teardown()` preserves unremoved ownership and returns `pending`; `clear()` → `true` | `nil,reason,pending` (retryable). `begin` rollback keeps pending ownership instead of erasing it.
- Catalogue-authored mechanics (`kinetic`/`sigil`, champion authored phases, body-region effects) remain unsupported/not surfaced; the stock `phase` field is documented as observed-KO phase only.

## Tests (focused 8/8, full suite 45 OK / 1 skip)
New/updated: ordinary fighter buff attachment + immutability + supported `rime`/`guard` override + `buff_fighters=false` opt-out + `opts.fighter_family`; unsupported explicit family/slot refusal and constructor refusal; eligibility/status host exposure; `reset()` refusal with live ownership; persistent-refusal `clear()` returning pending ownership and succeeding on retry; mixed custom+fighter room cleanup (all hosts/modifiers released); duplicate/stale stock+defeat; partial wave/champion resume; vanished/escaped never a confirmed death.

Remaining main wiring (root): instantiate with the new opts, use `active_entity().host` for `apply_gene`/Visuals, call `begin/update/hit/defeat/stock/clear`, and honor `clear()`'s `pending` on refusal. No native combat/playtesting claimed.

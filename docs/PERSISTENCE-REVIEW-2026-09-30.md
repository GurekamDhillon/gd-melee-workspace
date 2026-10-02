# Persistence review — follow-up to Batch 1

Follow-up status: `ba6cce4ee` fixes the user-addressable `.tmp` collision and adds
sibling/failed-replace regressions. `35be19ff7` protects future envelope slots
and contains initial loader exceptions. `05d2f429a` commits checked native path
construction and long-root refusal coverage; root rebuilt and passed the 34/34
native scripting group. The inner-schema/actual progress wiring below remains
in the bounded continuation task. Findings below retain the original review
context; do not redo fixes already present.

Reviewed game commits `7fd8adc8d` and `c64741c28`, with concurrent implementation
left under the existing OpenCode worker's ownership. Root's delegated DeepSeek
Flash review was read-only. Native 212/212 and pure-suite success are reported
by that worker; root has not re-run the new native build. Green current tests
do not cover the following cases. Keep persistence acceptance open until fixed.

## 1. Atomic temporary filename destroys another valid data file

`pc/platform/gw_script.c:l_data_write_atomic` uses `path + ".tmp"`, then
`fopen(...,"wb")` and deletion/rename. The data filename grammar allows `.tmp`
as an ordinary suffix. These two calls therefore conflict:

```lua
gd.data_write('x.tmp', 'keep')
gd.data_write_atomic('x', 'new')
-- x.tmp must remain 'keep'; current helper overwrites then removes it.
```

Use a temporary namespace unavailable to script data filenames, with checked
path lengths and exclusive creation. Ensure retry/stale-file handling does not
delete user-addressable data. Check both path formatting results before using
them; the current `gs_data_path` and temp `snprintf` silently truncate. Add a
native regression preserving `x.tmp`, a failed-open/replace test retaining old
target bytes, and failure coverage for short write/flush/close where feasible.
The existing native test covers successful replacement, oversize preflight
refusal and empty output, not actual I/O/replace failure paths.

Do not adopt unverified platform atomicity claims from a model review. Check
the actual Windows replacement contract; document atomicity and durability
precisely for each supported platform.

## 2. Unsupported future A/B file is still overwritable

`main.lua:checkpoint` discards the refusal reason from `Checkpoint.decode`.
`load_data` takes a valid older slot when available; it only sets `save_error`
when neither slot decodes. `save` subsequently chooses its target by parity.
Thus an unsupported future file alongside a valid older generation can be
overwritten by the next save targeting that slot. The decoder's word
"preserved" does not enforce preservation at the writer.

Fixture: put a valid generation-2 save in A and an unsupported `TBD4 ...` save
in B. Load may offer the older run, but any subsequent generation-3 save must
leave B's bytes untouched and explain the write restriction. Also test unknown
manifest/progress versions inside a syntactically valid TBD3 envelope. Preserve
unknown files without treating them as corrupt disposable slots. Readback must
contain malformed semantic decoding exceptions as controlled refusal.

## 3. Remaining integration, not a completed progress migration

The new main save seam writes TBD3 and a v1 manifest. It does not yet pass a
progress section to `Checkpoint.encode`, pass expected schema versions to
`Checkpoint.decode`, or invoke the added legacy progress migration in its
loader. Current route creation remains `Dungeon.generate`; separate v2 progress
and semantic route validation remain Batch 2 work. Avoid claiming these are
live solely because helper functions exist.

Preserve frozen v1 resumes explicitly, then connect resolved v2 manifest and
schema-2 progress, full semantic validation and transactional Core/progress
mirrors. Add loader-boundary adversarial cases and resource/claim consistency
checks. Root did not modify runtime files during this review.

## Continue message for the active worker

> Continue Batch 2 autonomously in bounded committed patches, as already
> authorized. Read `docs/PERSISTENCE-REVIEW-2026-09-30.md` and first close its
> confirmed temp-file collision and future-version overwrite gaps with meaningful
> regressions. Keep persistence acceptance open until those cases pass. Then
> complete live v2 routes, per-socket geometry/traversal and manifest-driven
> encounters/rewards. Run available normal-speed native controller checks after
> integration; human feel and unavailable hardware remain pending, but do not
> stop independent implementation for them. Coordinate shared build/game ownership
> and preserve all existing work. No release and no uncapped FPS experiment.

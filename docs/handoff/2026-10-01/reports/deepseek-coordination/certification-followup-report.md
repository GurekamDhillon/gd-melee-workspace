I'll inspect the current state of my lane and the real API before changing anything.

Let me inspect the real current API for camera and related functions before implementing.

Now I have the full picture. Let me implement the fixes, starting with the Lua probe.

Now the non-fatal fixture placement and the camera command:

Now the Python classification and verdict logic.

Now restructure `run_certification` for exception-safe summaries and preview options.

Now update the tests for the new contract and add coverage.

Implemented the review findings in the three owned files. No native build/run/install/commit was performed.

## Changes

**Game probe `roguelite_certification/main.lua`**
- `certify_place`/`certify_place_at` no longer call `fail`: they emit `certify_place ok=true|false` and **preserve the constructed phase and isolation**, so a dead/respawning fighter yields an operational refusal the driver can retry instead of a permanent `phase=error`.
- `certify_build <template> [clean]` — `clean` sets `draw=false` on the diagnostic slabs only; collision is identical. Default stays diagnostic.
- `certify_camera auto|wide` — inspected the registered API first: there is no `gd.camera_pose`; it uses `gd.camera_detach` + `gd.camera_set{eye,interest,fov}` + `gd.camera_attach(0)`, is preview-only, mod-camera-owner scoped, and restored on cleanup/unload.
- `certify_result` now carries `header=1`; `certify_status` reports `draw/clean/camera/floor_y`.

**Driver `tools/roguelite/certify_rooms.py`**
- `classify_trace` distinguishes **expected drop** (`fell` + actual downward `descended`) from **unexpected fall** (`unexpected-fall`, a failure) and `failed-no-descent`; statuses are bucketed so `no-samples/error/fixture-only/placement-refused/unclassified` can never vanish from the verdict.
- `replay_until` replays ordinary pad samples in bounded 20-frame chunks, polling `certify_sample` and stopping at the arrival region or before leaving the room (no teleport/fly during the trace). Each probe re-places the fixture and re-arms a fresh window.
- `fixture_place` retries the native teleport with a bounded timeout (natural respawn), fails fast on unknown sockets, and `arm_window` rejects a missing/error arm — no fake success.
- `result` requires a valid `header=1`, pages all stable rows in ≤20-row responses, and treats a missing header as a game-command error, not a pass.
- `capture` deletes any stale file and confirms a fresh non-empty PNG; failure is not evidence.
- `run_certification` catches console timeouts/disconnects, records cleanup errors in the summary, and `main` always writes a JSON summary (no traceback-only exit). New `--clean-preview` and `--camera {auto,wide}` flags.

**Tests `tools/roguelite/test_certify_rooms.py`** — extended to 62 focused tests: real bundled-Lua build callbacks + operational-refusal phase preservation, retry/timeout, controller stop-on-arrival/out-of-bounds, fall-vs-drop/descent, result header+paging, capture freshness, run-summary-on-console-failure. Full suite: **99 tests OK** (1 pre-existing skip).

## Honest limits
Still no native traversal evidence from this worker; the wide-camera pose and drop-probe timings are unvalidated starting points, and every verdict remains pending/manual — never certified.

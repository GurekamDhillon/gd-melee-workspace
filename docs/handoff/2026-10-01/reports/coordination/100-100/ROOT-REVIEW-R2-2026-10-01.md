# Root follow-up: R2 remains open beyond notice repair

Read-only source review of the integration lane; no writer-owned files changed.

Verified main.lua now reports the selected export ID and full-capacity cause. Accept this as a truthful-notice subfix, not recovery/export completion.

Three concrete contradictions prevent closing R2:

1. `core.lua` C.finish does NOT force id=nil at capacity. It returns nil with `invalid export or collection full; choose no export` when a nonnil id cannot be accepted. main.lua clears the id and elects no export. Do not attribute that decision to Core.
2. C.finish records profile.finished and success. A subsequent call returns the existing result before doing another export. Menu resume accepts only active runs; main.lua loader clears run/route when the run is finished or not active. Keeping run.genes in the serialized checkpoint therefore does not establish a player-accessible recovery path. The current regression checks bytes/notice, not recovery.
3. The new notice tells the player to discard/replace despite the report confirming these actions do not exist; starting a new run does not recover the earned gene from this finished run. Do not call that instruction actionable.

Required acceptance: explicit choose-export/replace/discard flow, or durable pending export reachable through finished-run UI and after relaunch, with original-run ownership and exactly-once export. Full capacity must not silently/automatically choose no export. A player may deliberately decline with clear consequences. Preserve all old collection data, locked/owned constraints and transactional failure behavior.

Regressions must finish through the real product flow, relaunch, resolve full capacity, claim the SAME earned gene once, and prove a repeated claim/refused save does not duplicate/delete genes. Cover choosing no export as an explicit separate user action. Keep the current notice regression but label its scope correctly.

M1 is still partially complete while the ledger marks asset reproducibility and native patch landing missing. The adapter/hook pair is imported but remains uncommitted in the inspected lane. Record commit hashes before calling it committed/pushed.

R3 requires bundling plus constructors, dispatch, persistence and live native seams. Proceed with R6 and native ownership/API work independently; do not stop the full program for pending human tests.

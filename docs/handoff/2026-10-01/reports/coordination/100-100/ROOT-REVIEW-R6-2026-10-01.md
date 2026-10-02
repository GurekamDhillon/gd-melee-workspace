# Root review: committed native sources and R2 notice correction

Inspected integration commits e9cd3286e, 244f00710 and d5ba31d98, plus wrapper commits and ledger. R6 authored include/caller/test-source landing is coherent at current game HEAD. Independently exported ONLY committed seam test dependencies with git archive (no dirty files), ran actual-source ASan/UBSan stage_seam_test.py, and it passed. Evidence root-review-committed-seams.log. This independently verifies the seam regression from committed source; it is not a second full clean-clone native build/ABI run.

The mixed 244f00710 commit includes both gene_actions.lua and main.lua, confirmed and documented. Do not rewrite the existing history just for this unless integration policy requires it. Use explicit later PR descriptions/commit map, and import the adapter/action-hooks pair together.

R2 current product notice now states actual non-recoverability and no longer advertises nonexistent discard/replace. Full R2 remains open as the ledger now records. One stale main.lua comment still says the checkpoint ID is recoverable/there is an actionable next step; remove that obsolete comment in the next main.lua patch. It does not change the runtime notice acceptance.

Dependency followup should state and reproduce actual pipeline requirements in a fresh task-specific venv, separate baseline/game-disc extraction from optional asset authoring dependencies, and validate documented commands against original assets. Generator commits alone do not establish all runtime outputs reproducible/tracked/packaged.

R3 requires product-level service construction, dispatch, save/migration and native control seams. Split inventory/history/equipment integration from encounter/boss native movement implementation; do not claim the latter done merely by including its Lua definitions. Keep full-capacity pending export/choice a priority while main.lua has a single owner.

M1 remains partial until its remaining asset reproducibility/dependency requirements are accepted. No releases/tags/pushes were performed by this root review; integration commits are still separate from root development branches.

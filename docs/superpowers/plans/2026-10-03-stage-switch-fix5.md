# Stage switch fix5

User-approved scope: fix the frozen transition/music hang first, then host complete
retail stage lifecycles. No game build/launch, commit, reset or stash.

1. Trace stream spin, deferred DVD/AR completion and post-pass ownership.
2. Reproduce with source-extracted standalone fixtures; defer switch music until
   thawed normal loop, pump completion in the PC stream wait, protect engine posts.
3. Audit complete retail initialization dependencies and outgoing resource owners;
   implement full lifecycle only where ownership/restoration is established.
4. Verify syntax and regression fixtures; document exact outstanding integration
   dependencies, six-stage vanilla comparison checklist and before/after recipe.

Verified: hang/cover repairs, four standalone fixtures, before-behavior failures,
existing slot/fix3/fix4/ledge regressions, game/native C syntax, independent review.
Report: `_build/tmp/codex-stage-switch-fix5-report.md`.

Outstanding: step 3's complete retail lifecycle implementation. The audit is
`_research/stage-switch-full-retail-lifecycle-2026-10-03.md`; partial fix4 startup
still exists and does not meet the owner's new vanilla requirement. Full game
build/link, runtime reproduction and six-stage visual/heap acceptance remain
unperformed under the prompt's no-build/no-launch rules.

# Geno guide engine gaps implementation plan

**Spec:** `docs/prompts/codex-geno-guide-engine-gaps.md`.
**Constraints:** Preserve both dirty trees. No builds, game launch, commits, or edits
under `tools/geno/` and `docs/learn/geno-fighters/`. Stable instruction ids unchanged.
Execute inline; verification is syntax and standalone checks, with game acceptance deferred.

- [x] Add jump regression tests: continue through the final retail script gate,
  bounded impulses, helmet states, ordinary jump input, and inert fighters.
- [x] Repeat the penultimate multi-jump state while more jumps remain; bound the
  retail table read before Geno dispatch. Log the existing numeric clamp.
- [x] Add effective-script and opcode-59 decoder regressions. Permit reads only
  within installed Geno script slots in addition to MEM1, follow ORIG, and expose
  escape names/operands and conditional-path metadata to every LAB consumer.
- [x] Add reload classification tests. Restart on state row/callback/behavior
  changes; warn once per state at load when IASA has no effective callback.
- [x] Run LAB checker and syntax checks; correct the reference without renumbering.
- [x] Write `_build/tmp/codex-geno-guide-engine-gaps-report.md` with causes,
  file:line references, actual check results, limitations, and tutorial retest steps.

Verification boundary: C regression tests were added and syntax-checked, not executed;
the prompt forbids the game build/launch needed to run them. Full LAB checker: 68 PASS,
0 FAIL. Read-only review findings were fixed; report contains remaining acceptance steps.

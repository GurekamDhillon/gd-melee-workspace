# Direct DeepSeek workers through OpenCode

Root can now dispatch DeepSeek through the installed OpenCode CLI. Verified
2026-09-30: saved credential accepted a request to `deepseek/deepseek-flash` and
returned `AUTH_OK`. Listed models are `deepseek/deepseek-flash` and
`deepseek/deepseek-v4-pro`. Start with Flash for the user's cheap bulk-work
preference; Sol reviews and integrates, and Astra owns new final art.

Current ownership: the user closed the pre-existing OpenCode session after
commits through `6ed933614`. Root has taken coordination back. A direct Flash
worker now owns the bounded Lua progress-persistence task described in
`_build/deepseek-coordination/progress-persistence-prompt.txt`; its event log is
`progress-persistence.jsonl`. It may not commit, build native code or install/
launch the shared game. Root owns native builds and review/landing.

Root separately landed `05d2f429a`: checked data-path construction and a native
long-root regression that verifies prior file bytes survive refusal. Shared
Linux build/bridge/ABI checks passed; `MELEE_MODS=0 MELEE_SCRIPTS=0` scripting
group passed 34/34. Evidence: `native-path-build.log`, `native-path-tests.log`
and the isolated `native-path-owned.patch` in the coordination directory.
Unrelated pre-existing native changes were left unstaged.

Use bounded task files with explicit owned paths, tests, stopping conditions
and baseline state. Place prompts and JSON event logs under an ignored
`_build/deepseek-coordination/` directory. Preserve unrelated dirty work.
No credentials, private collections or disc contents in prompts. Check for
existing workers before handing out files or shared build/game ownership.

Example read-only review:

```sh
opencode run 'Carry out the attached read-only review.' \
  --pure --model deepseek/deepseek-flash --agent plan --format json \
  --file _build/deepseek-coordination/atomic-review-prompt.txt \
  > _build/deepseek-coordination/atomic-review.jsonl 2>&1
```

Put the positional message before `--file`: that option consumes an array and
can interpret a following message as another filename. `--pure` disables
external plugins. The plan agent is for review; use a coding agent for an
authorized implementation packet and its configured permissions. Never run
overlapping writers against the same files. Root retains shared native build,
installation/game ownership unless explicitly handed off for a bounded task.

JSON events include session IDs and reported token/cost usage. Extract summaries
without dumping whole tool outputs or sensitive files. Keep durable patch and
test evidence, review the diff, then run integration checks for changed behavior.
An API success is not evidence that an implementation is correct.

No release/tag. PNG previews only, preferably in-game when readily available.
The uncapped FPS experiment stays cancelled.

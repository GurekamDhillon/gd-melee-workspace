# EM2 native hit rules execution plan

Authority: docs/prompts/codex-hit-rules.md and approved Envoy design. Preserve
dirty source trees. No commits, resets, stashes, game builds or launches.

- [x] Audit creation/contact/resolution sites and action-family tags.
- [x] Add game-BSS bounded native rule/status tables, creation/contact helpers,
  gated script API, replay journal support and meaningful native fixtures.
- [x] Extend Envoy schema, native-rule composition, conversion/versus-status
  modifiers, traces, shader treatments, catalogue demo and Lua tests.
- [x] Review, syntax/isolated regression checks, final bundle, reach/side-effect
  and integrator acceptance report.

Ruling: no Lua during collision. Special original elements are immune. Optional
split-element fraction is refused rather than described as two real components.
Native rules/status writes issued by live modifier evaluation must join sim_commit
replay, not ordinary per-frame setters that fork history. Creation modifiers and
contact-only victim scaling remain separate; never rewrite a shared hit capsule
for one victim. Actual zero-byte LAB acceptance is unrun under the packet's
no-build/no-launch constraint; isolated deterministic helper evidence is labeled.

| Task interface | Producer / consumer | Ruling |
|---|---|---|
| Native creation/contact API → Lua schema | Native bounded rules/status bits; Lua static equip rules and status registry | Agree contract before adapter writes; no Lua at hit time. |
| Native tables → replay | Game BSS captured; sim_commit stores complete rule/status outputs | Native implementer owns both to avoid split ABI edits. |
| Audit → implementation | Read-only creation/family inventory; native implementer edits game sites | Audit agent does not edit implementation. |
| Native/Lua → tests/report | Source-only fixtures and syntax; root final report | No game-build acceptance claims. |

Source implementation/review complete. 265 Lua tests/32 suites, 12 Python tests,
16 PPC TUs + native bridge syntax and two isolated helper executables pass.
Catalogue baseline missing demo_zones persists. Live LAB rewind/build/visual
acceptance remains unrun as required; see _build/tmp/codex-hit-rules-report.md.

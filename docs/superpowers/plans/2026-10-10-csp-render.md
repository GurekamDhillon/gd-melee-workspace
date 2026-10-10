# Geno CSProject UI Rendering Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. Steps use checkboxes. The packet prohibits commands and design approval; tests are written first and execution is left to the lead.

**Goal:** Render original or explicitly selected retail-template fighter UI through portable Blender 3.5.1, then install schema-compatible GXTX presentation art in a generated Geno package.
**Architecture:** A runtime fetcher prepares a local sparse CSProject checkout and add-ons. A pure project/output layer prepares a JSON job; a Blender worker appends a template Scene (cameras, light objects and parents, World, compositor and render settings), replaces its fighter, and renders its nine cameras. The host converts PNGs and publishes presentation declarations only after every conversion succeeds.
**Tech Stack:** Python 3.10+, Pillow, pytest, runtime git, Blender 3.5.1; existing game png2gx.py.
**Spec:** docs/prompts/codex-csp-render.md; game pc/geno/presentation.schema.json and docs/geno.md §22.12.

Source-writing and file-only review steps are done; all execution remains pending.
The red-command items are historical tests-first checks that could not be run in this lane.
The restart instruction chooses .omo/evidence/report.md; the packet report path has the same content.

## Global Constraints
- SHELL IS UNAVAILABLE: file tools only; no fetch/run/build/git in this session.
- Write only inside this worktree. Tests first. No disc- or CSProject-derived files committed.
- No design approval stop. Record unknown CSProject internals for the lead.
- All generated assets/tools/jobs remain below workspace _build; fetch tools below _build/tools-ext.
- Workbench requires Blender 4.x; its button starts the separate portable Blender 3.5.1.
- Never touch panels.py or its Hitbox panel. UI build is optional, full-build-only.

## Review Focus
- Subset costume rendering must preserve list indices and existing art, with a valid costume-zero fallback.
- Alternate costumes without matching local art/recolor inputs must fail instead of repeating costume zero.
- Blender 4/5 art files need a GLB fallback; row names and animation time must resolve explicitly.
- Template scene dependencies, camera crop data, and add-on APIs cannot be inspected here: provide inventory and overrides.
- Failed rendering/conversion must leave package declarations intact; all cache paths and archive extraction stay confined.

### Task 1: Pure rendering contract and acquisition
**Files:** tools/csp/{__init__,outputs,project,fetch_csproject}.py; tools/csp/tests/{test_outputs,test_project,test_fetch}.py.
**Interfaces:** enumerate_costumes(entry, source, source_dir, overrides); select_costumes(costumes, selection); camera_outputs(names, overrides); fit_rgba(image, size); merge_presentation(existing, generated, count). load_project builds a JSON-safe job. fetch prepares tools.json containing Blender, template and scripts paths.
- [x] Write synthetic image tests asserting 64x56, 136x188, 24x24, 52x74, 80x64 outputs, RGB5A3/RGBA8 and no stock/results/emblem palettes; test alpha, crop/effects, missing/ambiguous cameras, costume indexing.
- [x] Write project tests for workspace-relative artifacts, package override, row pick.clip, modern .blend fallback, missing alternate inputs and generated-path guard.
- [x] Write acquisition tests for sparse scene selection, idempotent cache inputs and archive traversal rejection.
- [ ] Lead red command before applying implementation: python -m pytest tools/csp/tests/test_outputs.py tools/csp/tests/test_project.py tools/csp/tests/test_fetch.py -q. Expected: missing tools.csp implementation.
- [x] Implement focused helpers and runtime fetcher, no external execution here.
- [ ] Lead green command: same pytest command. Expected: all pure tests pass.

### Task 2: Blender worker and package publication
**Files:** tools/csp/{blender_render,render_ui}.py; tools/csp/tests/{test_render_ui,test_blender}.py; tools/csp/README.md.
**Interfaces:** render_ui.main(argv) loads project and tools, renders a job with --python-exit-code 1, post-processes nine PNGs, invokes png2gx, validates GXTX headers and merges declarations. Worker supports --inspect-template to write a numerical/name inventory, never vendored assets.
- [x] Write conversion/publication tests using real synthetic PNGs and game png2gx when available; injected subprocess failure must leave geno.json intact.
- [x] Write Blender integration test with skip unless exact Blender 3.5.1 plus local CSProject exist. Use a synthetic original rig/action, nine-camera inventory, outputs and enabled add-ons.
- [ ] Lead red command: python -m pytest tools/csp/tests/test_render_ui.py tools/csp/tests/test_blender.py -q. Expected: missing implementation; absent Blender is a skip.
- [x] Implement worker, inspection, processing and staged package writes; document override fields and every unverified scene assumption.
- [ ] Lead green command: same pytest command. Expected: passing synthetic conversion tests; Blender skip or passing local check.

### Task 3: Build and Workbench hooks
**Files:** ports/goku-xv2/tools/build.py; ports/goku-xv2/tests/test_ui_build.py; tools/blender/geno_workbench/{panels_ui,ui_command,__init__}.py; tools/blender/geno_workbench/tests/test_ui_command.py; READMEs.
**Interfaces:** --ui calls render_ui with the actual full-build package and fighter config; --ui plus --auto forces full; --gameplay-only --ui is rejected. Standalone panel starts a host Python render process and polls it without blocking Blender.
- [x] Write tests pinning off-by-default, full-only, failure propagation, auto full selection and command paths/pose.
- [ ] Lead red command: python -m pytest ports/goku-xv2/tests/test_ui_build.py tools/blender/geno_workbench/tests/test_ui_command.py -q. Expected: absent hooks.
- [x] Add hooks and documentation without editing panels.py.
- [ ] Lead green command: same pytest command, then python -m pytest tools/csp/tests tools/blender/geno_workbench/tests ports/goku-xv2/tests -q.
- [x] Fresh file-only review; address findings with tests first. Leave execution unverified and record exact lead commands in .omo/evidence/csp-render-report.md (<=40 lines).

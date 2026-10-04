# Codex packet GF1: Geno "define", slice 1: a fighter with no m-ex and no PowerPC (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (other jobs may still be running: stage lifecycle, afterimages, the Envoy
mod; stay out of their files). No commits, no `tools/port/build.sh`, no game launch; keep every file compilable. Do not
stop for design approval: the owner approved the design and slice 1 ("lgtm") on the integrator's summary of your spec
`docs/superpowers/specs/2026-10-04-geno-full-fighter-design.md`, with these decisions: (1) Geno owns complete native
definitions that inherit Melee common behaviour; (2) art path later is Blender/glTF compiled offline to HSD; (3) fighter
Lua later is stateless callbacks over typed snapshotted fields; (9) the direction plus slice 1 now, later slices planned
separately. In docs call ours "the Geno engine" on first use.

## Slice 1 only (your spec section 8, row 1), nothing from slices 2-5
Build the native `define` backend far enough that this acceptance holds:
- A fighter package ("Vanilla Hero": a Mario-reference clone, the spec's recommended first fixture; NOT the private
  character port) loads on the vanilla disc from one folder, is selectable beside retail and m-ex fighters, and plays a
  full stock match: every common state, all normals, specials, grab and throws, shield, ledge, items, death and rebirth.
- It references Mario's model, animations, effects and sounds by name from the retail data (nothing derived from the
  disc is in the folder), and OWNS its effective state graph, attributes and move scripts by definition or inheritance.
- At least one move and one attribute are visibly its own (changed from Mario), to prove ownership.
- No `MxDt.dat` row and no PowerPC callback is used for it: prove it with a counter or log line that would be non-zero
  if the m-ex interpreter ran for this fighter.
- Mixed loading works: retail, an m-ex fighter, an m-ex fighter with Geno `attach`, and this `define` fighter in one
  match. Exhaustion of any id/alias space is refused honestly with a message (spec question 4).
- Save/restore and repeated-input hashes agree (the LAB snapshot and rewind fixtures); offline first: online use waits
  for the full admission and identity contracts, say what is missing.
Work items as your spec lists them for slice 1: source-independent roster registration (build on the roster registry
work, `_build/tmp/codex-roster-registry-report.md`, and its integration requests); minimal selection and results
defaults; admission and resident mapping; attributes and descriptors; the every-state dispatcher with versioned common
behaviour inherited by default and per-state overrides; native donor adapters and script bindings for a referenced
retail fighter; dynamic profiles (the 32 cap goes); the snapshot and content-hash foundation; and the author tooling:
`tools/geno` `new` (creates a playable clone of a retail fighter in one command), `check` and `export` for the new
format version, with the schema accepting `define`.
Also: a learning-guide packet stub under `docs/learn/geno-fighters/` for "a fighter defined from scratch", a catalogue
demo, tests in the suite pattern, `melee/docs/geno.md` updated.
The private character port's engine requests (`_build/tmp/codex-geno-character-port-report.md`, "General engine
requests") are input for LATER slices: note which of them slice 1 already satisfies and which slice each belongs to.
Report `_build/tmp/codex-geno-define-slice1-report.md`: what the format looks like for the Hero fighter (show its
files), file:line for each engine piece, what could not be done, shared-file edits, whether the integrator must rebuild,
and a tester's script (select the Hero, the changed move and attribute to look for, the mixed match, the snapshot test).

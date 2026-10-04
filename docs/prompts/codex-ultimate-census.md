# Codex packet U0: census for porting every Super Smash Bros. Ultimate fighter and stage (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `ports/README.md`,
`ports/CLAUDE.md` if present, `ports/ir/README.md`, `melee/docs/geno.md` sections 1-4 and 15-20, `docs/NEXT-SESSION.md`,
`docs/HANDOFF-2026-10-03-ENGINE-DAY.md`). READ-ONLY research: do NOT edit any tracked file, do NOT commit, build, launch the
game, extract game data, or run long tools. Write only the report named below and scratch under `_build/tmp/ultimate-census/`.
Never print or write disc or game-dump paths taken from `.env`. Ultimate game data is copyrighted and local-only: nothing
derived from it enters either repository.

## The owner's goal (verbatim)
"Sending off a (singular) sonnet 5.5/6.1-sol swarm to port all ultimate maps, and characters. Damn to how long it takes."

One fighter has been ported end to end so far: Sora (`trail`), plus Ultimate Kirby as the pipeline proof and Meta Knight
research (`ports/halberd/`). Sora took most of a working day of agent time on top of an existing pipeline, with a full
fidelity pass (specials rewritten from the game's status code, magic, attributes, normals, effects, grabs, eyes) and still
has parked items. Before a swarm is launched, the coordinator needs facts. Produce them.

## Establish, with file paths and counts (tag each VERIFIED or INFERRED)
1. **What Ultimate data is on this machine and in what state**: the toolkit under `experiment/tooling/ultimate/` (its
   README, `extract_game.py`, `arc_assets.py`, manifests, `workspace/`, `verification/`, `references/`), what has been
   extracted (which fighters, which stages, which asset kinds: models, textures, animations, ACMD scripts, parameters,
   effects, sounds, stage collision/LVD), how much disk it takes, and what extracting ALL fighters and ALL stages would need
   (commands, time, disk). Do not run extraction.
2. **The port pipeline as it stands** (`ports/ir/tools/`: every tool with one line on what it does; the IR schemas in
   `ports/ir/schema/`; the recipe that produced Sora: `_build/audit-20261003/sora-final/regen.sh` and its inputs): which
   steps are generic (work for any fighter given its data) and which were written for Sora or Kirby specifically (name the
   files: `trail_*.py`, anything keyed to one fighter). What a fighter needs that is NOT in the dumped data: the status
   (state machine) code lives in compiled game code and was reverse-engineered for Sora with Ghidra
   (`~/ghidra-projects`: only Sora's projects exist): how much of a fighter's behaviour comes from ACMD scripts and
   parameters (portable by tool) versus status code (needs reverse engineering per fighter).
3. **The full roster**: every Ultimate fighter (internal name and common name; echo fighters and Mii fighters and the
   Pokemon Trainer trio noted), classified by porting difficulty with the reason: (a) Melee veterans whose Melee version can
   be the clone base (which ones); (b) standard fighters with no unusual mechanics; (c) fighters with a meter, stance,
   install, summon, puppet or article-heavy kit (list the mechanic); (d) fighters whose core mechanic has no Melee analogue
   (name it). Use what the tree knows (`ports/ir`, `_research/ultimate-*.md`, the toolkit's references); where you rely on
   general knowledge of the game, tag it INFERRED.
4. **Engine capacity**: the roster limit (94 added slots: `melee/pc/platform/gw.h` ~241, and why); the m-ex table
   dependency (a ported fighter's folder today ships disc-derived table files: `_research/vanilla-single-folder-mods-2026-10-03.md`
   and its eight owner decisions); costume counts; memory per fighter (the six-slot work measured heaps:
   `_build/tmp/codex-six-slots-report.md`); what Geno supports and lacks for the mechanics in class (c) and (d)
   (`melee/docs/geno.md`), as a gap list.
5. **Stages**: every Ultimate stage (count; internal names if the data or references list them), what a stage consists of
   in the dump (models, collision/LVD, cameras and blast zones, spawn points, animation, hazards code, music), and how each
   maps onto what we can load today: the mission-folder level format and Blender exporter (`tools/blender/gd_mission/`),
   stage slots, custom materials. Classify stages: static geometry only; animated but hazard-free (note every stage has a
   hazards-off form in Ultimate); moving/travelling stages; stages whose identity is a mechanic. What tool is missing to go
   from an Ultimate stage's files to a mission-folder level (a converter: inputs, outputs, size).
6. **Verification that exists per fighter** (so a swarm can be judged without a human): `ports/ir/tools/` checks
   (hitbox positions, frame data, loss accounting), the LAB frame-data tools, the test matrix in
   `_build/audit-20261003/sora-tests/` (what it covers and that it was mostly NOT RUN), and what an automatic acceptance
   gate per fighter and per stage could consist of today.
7. **Cost model**: from Sora's actual history (the ledger `docs/superpowers/plans/2026-10-03-audit-repairs.md`, the Sora
   evidence folders under `_build/audit-20261003/`), estimate agent-hours per fighter by class and per stage by class, the
   parts that parallelise and the parts that serialise (pipeline changes, shared tables, the one build, the game-running
   cap of 8 instances), and the total for everything, stated as a range with its assumptions.
8. **A proposed order**: what must exist before fan-out (generic pipeline, ledger, acceptance gate, extraction of all
   data, per-fighter reverse engineering of status code at scale), then waves.

## Deliverable
`_build/tmp/ultimate-census/REPORT.md`: the eight sections, a roster table and a stage table as CSV files beside it
(`fighters.csv`, `stages.csv` with the classification columns), the gap list for the engine and for the pipeline, and a
list of every claim you could not verify. Be blunt about what is not feasible with what exists.

# ports/

Fighters ported into GD's Melee from other games. Full ports use m-ex fighter slots, extended where
needed by the **Geno** engine (see the melee fork's `docs/geno.md`). Early proofs of life may attach
Geno to an existing Melee fighter.

Only **research** is tracked here: notes, analysis, conversion tools, hand-written configs and each
fighter's character IR. Game assets are built locally from your own legally obtained game files and
are gitignored; **no Nintendo assets are in this repository.**

| Folder | What it is |
|---|---|
| [`halberd/`](halberd/) | **Halberd**: Meta Knight from *Super Smash Bros. Brawl*. |
| [`kirby-ultimate/`](kirby-ultimate/) | **Ultimate Kirby proof of life**: walk, run, crouch, six jumps, and uncharged ground/aerial side B on Melee Kirby, verified in the LAB. |
| [`ir/`](ir/) | The character IR schema and validator shared by every port. |

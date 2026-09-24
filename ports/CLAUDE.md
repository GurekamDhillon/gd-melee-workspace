# ports/: fighters from other games

Research and tools only: the analysis of decoded move data, converters, hand-written configs and
each fighter's character IR. **No game assets are tracked** and `.gitignore` keeps built ones out;
every model, animation, texture, sound and menu graphic is built locally from the user's own copies
of the source game and Melee. Keep it that way in every commit.

| dir | what | reference |
|---|---|---|
| `halberd/` | Meta Knight from Brawl: an m-ex fighter on the ACE disc, extended by Geno for what m-ex cannot express | `halberd/README.md` (status, the pipeline, what is approximated), `PHASE1_REPORT.md` |
| `ir/` | the character IR schema (`schema/*.schema.json`) and its validator, shared by every port | `ir/README.md` |

## Rules

- The Geno encodings a port emits are **frozen**: `halberd/geno_v1_encodings.md` and
  `geno_v2_encodings.md` are copies of `melee/docs/geno.md` sections 15-16, and that file wins if
  they differ. A new need gets a new id in Geno, never a changed one here.
- `tuning.json` is the fighter's numbers as ported (Brawl's); `tuning.melee-feel.json` a feel
  pass. Both are data the Geno build hot-reloads; the LAB's A/B and frame-data diff are how a
  change is measured.
- Known limits worth not rediscovering: a 3-player match with Meta Knight runs out of memory at
  load (the 4.9 MB animation file); about 9 KB of UI heap headroom is left; Final Smash, sword
  hiding and the entrance are not ported; the ledge flags, cape stick threshold and landing lag
  are guesses (`halberd/README.md`).
- A second port should reuse `halberd/tools/` and the IR rather than start from the Brawl files
  again; the tools are the port kit.

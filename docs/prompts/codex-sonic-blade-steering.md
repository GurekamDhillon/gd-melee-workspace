# Research task for Codex: how Sora's Sonic Blade is steered in Ultimate

Written 2026-09-26 by the coordinating Claude session. **Research only.** Do NOT edit code, build or
run the game, or launch other Codex processes. Produce one note and stop. A Claude lane implements
it afterwards.

## Question

In Smash Ultimate, Sora's side special (Sonic Blade; Ultimate fighter id **`trail`**, never `sora`)
dashes up to three times, and the player can angle each dash with the stick. Our port (Melee PC port,
"Geno" engine extensions) dashes straight. We need the exact steering rules:

1. When the stick is read (which frames of which dash; once per dash or continuously).
2. The angle limits (max up / max down), and whether the angle snaps, is linear in stick Y, or turns
   at a rate.
3. Whether each dash re-reads the stick or keeps the previous angle; what left/right does (reverse,
   nothing).
4. Speed along the angled direction: constant, or different up vs down; ground vs air differences;
   what happens on hitting the ground or a wall.
5. Every parameter involved, with its name, hash, and value.

## Sources (use these; say which one each fact came from)

- Sora's params: the extracted `fighter_param` / `fighter_param_trail` data under
  `experiment/tooling/ultimate/workspace/extracted/` (find the exact file), decoded with the ParamXML
  tool there and the hash labels in `references/ParamLabels.csv`. Look for the `special_s` / Sonic
  Blade params.
- Our ACMD dumps (Ghidra decompilation): `C:/Users/Gurek/ghidra-projects/sora_acmd/` (`index.tsv`,
  `game/*.c`, `helpers/`); Sonic Blade's scripts are `game_specials*`. The dumps come from
  `lua2cpp_trail.nro`; the status code (where steering most likely lives) may be in the same NRO but
  was not dumped: say whether it is present there and, if so, where (function addresses), using the
  Ghidra project in `C:/Users/Gurek/ghidra-projects` (headless analyzer; the project path must not
  contain an apostrophe).
- `ports/ir/tools/trail_specials_geno.py` shows what the port does today (read only).
- Public documentation (frame data sites, the SSBU modding community's decompiled status scripts) is
  allowed for cross-checking only; mark anything from there as "external" and never let it override
  the game files.

## Output

`_research/ultimate-sonic-blade-steering.md`, with:
- the rules above, each with its source (file + offset/line, or "external"), and a confidence
  (confirmed from game data / inferred / external only);
- the parameter table;
- what could NOT be determined and why;
- a short "for the implementer" section: what engine inputs a Melee-side version needs (stick Y at
  frame N, a directed velocity at angle A and speed S, and so on), in engine-neutral terms.

Keep game-derived data to the numbers you need; don't paste decompiled code wholesale into the note.

## Rules

- No code edits, no commits, no game runs.
- If the steering logic is not in any file we have, say so plainly and give the best evidence you
  have; don't guess numbers without marking them as guesses.

Final message: the path of the note and a five-line summary.

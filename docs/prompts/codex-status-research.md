# Research task for Codex: what Sora's status scripts decide

Written 2026-09-26 by the coordinating Claude session. **Research only.** No code edits in the repo,
no game runs, no other Codex processes. Produce one note and stop.

## Background

Sora is ported from Smash Ultimate (fighter id **`trail`**, never `sora`). Our move scripts come from
Ghidra decompilation of the ACMD in `lua2cpp_trail.nro` (`C:/Users/Gurek/ghidra-projects/sora_acmd/`,
indexed by `index.tsv`). Ultimate's *status* scripts (state logic: transitions, stick reads, flags)
were not dumped. `_research/ultimate-sonic-blade-steering.md` found that the status-script factory is
in the same NRO; read that note first, including where it stopped.

## Questions (answer each with evidence)

1. **Counter rebound:** what makes Sora go into `speciallwrebound` / `specialairlwrebound`? (The
   params in vl.prc give rebound starts, distance 0.9..4.3, front/back speed multipliers.) Which
   status, which condition, which values.
2. **Sonic Blade steering details** the note left open: the exact frames the stick is sampled, any
   angle clamp, and what happens on hitting a wall or landing mid-dash.
3. **Work flag 0xe648** (`const_value_table + 0xe648`, read in `game_specials2/3`): where and when it
   is set and cleared (we assume "the previous dash connected").
4. Any other status-level behaviour of Sora's specials that the ACMD doesn't show (e.g. Counter's
   window extension, Sonic Blade's fall/helpless rules, Firaga/Blizzaga/Thundaga cycle order and
   when it advances), listed with one line each.

## How

- The Ghidra project in `C:/Users/Gurek/ghidra-projects` (headless analyzer; the project path must
  not contain an apostrophe; the .bat splits on commas and pipes). Dump the status functions you need
  to a new folder `C:/Users/Gurek/ghidra-projects/sora_status/` and cite them by address.
- Params: `vl.prc` decoded with ParamXML and `references/ParamLabels.csv` (see the steering note for
  where they are).
- External sources (community decompiled status scripts, frame data sites) are for cross-checking
  only; mark such facts "external".

## Output

`_research/ultimate-trail-status.md`: each question with answer, evidence (function address, file,
param name/value) and confidence (confirmed / inferred / external), then "for the implementer":
engine-neutral conditions and values. Keep decompiled code to short quotes.

Final message: the note path and a five-line summary.

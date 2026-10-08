# ports/: fighters from other games

Research, converters, schemas and hand-written configs live here. Built source-game models,
animations, textures, sounds and menu graphics stay local and gitignored. Never commit them.

| path | purpose |
|---|---|
| `halberd/` | Brawl Meta Knight: Brawl decoders, model/animation/effect/sound conversion and Geno configs |
| `ir/` | shared character schema and Melee/Ultimate tools; not only a validator |
| `geno-artist-samples/` | test characters for the artist pipeline (`tools/geno/artist`); parameters only, built files stay in `_build`; not shipped fighters |
| `ir/tools/install_ultimate.py` | install an Ultimate fighter on its own skeleton; `trail` is Sora, `kirby` is Ultimate Kirby |
| `ir/tools/trail_*` | Sora magic, physical specials and effect bindings; source-game key is `trail` |

Read `README.md` for the pipeline and slot naming. Both Ultimate installs default to m-ex
internal 52 / external 51, the Halberd slot; do not mount those default replacements together.
Display names default to `Ultimate Trail` / `Ultimate Kirby`, tokens `ultimatetrail` /
`ultimatekirby`; manifest ids are `ultimate-trail-slot` / `ultimate-kirby-slot`. `--name` changes
the installed name and scene token.

- Geno instruction ids are stable. `halberd/geno_v1_encodings.md` and `geno_v2_encodings.md`
  describe their version's subset; game `docs/geno.md` and `pc/geno/geno.h` define later additions
  (JSON version 5, additive v5.5 commands). Do not change an existing id to satisfy a converter.
- Reuse the IR and engine-specific tools. `build_melee_fighter.py` handles retail Melee fighters;
  Ultimate conversion lives in `ir/tools`, Brawl conversion in `halberd`.
- The Ultimate installer audits ACMD and installed hitbox positions and writes
  `conversion_losses.json` and `hitbox_positions.json`. `--skip-acmd-audit` marks these skipped;
  it is not a clean conversion result. Read explicit losses and fallback rows.
- `--pc-palette 64` requires engine `pobj_palette: 1`. `--tex-format auto` is opt-in; alternate
  costumes are included unless `--c00-only` is passed. These are converter flags, not run flags.
- Halberd's old three-player OOM report predates the larger fighter heap. Keep it as historical
  evidence, not a current player cap. Current memory and visual claims need a matching run.
- GD's move-graft request is estimate-only. Menu/platform/build-speed/effects follow-up is tracked
  in the 2026-09-27 state in `../docs/NEXT-SESSION.md`.

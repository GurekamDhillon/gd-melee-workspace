# Ultimate (`ssbu.switch`) IR conventions

The Kirby instance describes the locally extracted *Super Smash Bros. Ultimate* 13.0.2 build.
`ssbu.switch` is the source engine ID. Its numeric spaces are separate from Melee and Brawl spaces.

| Index space | Meaning |
|---|---|
| `ssbu.fighter_param_table.row` | Zero-based row in `fighter/common/param/fighter_param.prc`. Kirby is row 5. This is **not asserted** to equal the runtime fighter-kind enum. |
| `ssbu.motion_list.c00_entry` | Zero-based entry in Kirby body costume 00's `motion_list.bin`. It is **not** an action/status ID. |

The instance uses `engine.ssbu.switch` extensions only where an existing semantic field is
insufficient:

- Subaction records keep the motion-list animation filenames and script function names. Their
  `index` uses `ssbu.motion_list.c00_entry`; `clip` links a matching c00 animation when the
  filename resolves unambiguously. Action-to-motion runtime dispatch is untraced.
- Hitboxes keep the public Smashline ACMD call name and argument list, so a decoded value can be
  revisited without claiming equivalence to the local compiled NRO.
- The `lua2cpp_kirby.nro` code unit keeps its checked NRO0 section offsets and sizes. This is
  file-layout metadata, not function-level analysis.

The resource `container.format` and texture `format` fields use the source format's name, such as
`nuanmb`, `nusktb`, `nutexb`, and the decoded NUTEXB pixel format. The local builder records paths,
dimensions, counts, topology, and scalar parameters; it does not embed model, texture, audio, or
animation bytes.

Readable ACMD comes from the public `SSBU-Dumped-Scripts` reference and is not version-matched to
the local 13.0.2 `lua2cpp_kirby.nro`. Script-derived facts are inferred and must be checked before
driving a port. The instance's `coverage` and `issues` entries mark each remaining gap.

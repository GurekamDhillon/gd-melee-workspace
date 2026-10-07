# Aurora GD texgen fallback v1: carried patch

Two graceful degradations for GX draw states the game left half-set. Apply from the Aurora directory:

```
git apply --check --no-index <abs>/aurora-gd-texgen-fallback-v1.patch
git apply --no-index <abs>/aurora-gd-texgen-fallback-v1.patch
```

Touches `lib/gx/shader.cpp` and `lib/gx/texture.cpp` only; independent of the other GD patches
(`aurora-gd-motion-v1.patch` is untouched).

- `gx::build_shader`: a sampled texcoord whose texgen was never configured (`src == GX_MAX_TEXGENSRC`, the
  `TcgConfig` default; the panic said "unhandled tcg src 21") now sources (0,0) and logs once per texcoord:
  the TEV stages (coord, map, channel, color/alpha args, indirect fields), the texgens that were set, the
  indirect stage and the surface program. Before: FATAL, process dead.
- `gx::resolve_sampled_textures`: a sampled texmap holding a texobj with a format GX does not have (the
  panic said "convert_texture: unknown texture format 17") is treated as a texmap with no data and logs once
  per texmap. Before: FATAL.

Both fire on the pipeline worker or the GX thread for a draw that is already wrong; on hardware that state is
undefined, not illegal. The log line is the evidence for finding the draw.

Carried as lane objects until the shared libs are rebuilt: `_build/agents/tcgfix/build_gx_obj.bat` compiles
`gx_shader.obj` and `gx_texture.obj` with the flags of `_build/ax86m`; list them first in the link list. The game
branch `agent/tcgfix` already carries the source change; the integrator runs `_build/build_aurora_melee.bat`
once and drops the extra objects.

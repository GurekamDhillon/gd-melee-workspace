# Aurora GD motion — fix1 / ABI v2

Carried local patch against the already patched Aurora checkout (upstream cb0e279).
Apply after the existing GD surface/palette/recording patches, not to a clean
upstream tree. Aurora is MIT licensed; the new integration code follows that
license. The original patch filename is retained; its content now requires public
motion ABI v2 and FIFO opcode 0x0047. Adds retained draw capture,
arena preflight and replay-safe copied callbacks. Rebuild the i686 Aurora library
and game together through the normal port wrapper after parallel jobs integrate.
This packet performed source syntax checks only; no archive or EXE was rebuilt.

Fix1 adds named diagnostics, canonical texture-free variants, sampled-texture
fallbacks, unfogged matching uniforms, palette/scene-target warm variants,
byte-correct indexed array rebasing, atomic multi-pass replay and retain-only
held-item draw scopes. Rebuild Aurora and the native/game motion code together;
the old archive has incompatible/missing symbols. The patch includes the new
public header and all four original glue edits, against pre-FX1 saved baselines.
On the existing working tree, check it with:
`git -C melee apply --directory=extern/aurora --reverse --check --ignore-space-change ../_build/patches/aurora-gd-motion-v1.patch`.
This checks consistency without modifying files. Do not apply it again to the
already edited checkout.

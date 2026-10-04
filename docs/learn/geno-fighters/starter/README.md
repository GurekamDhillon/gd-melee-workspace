# Tutorial Kirby starter

This original data-only overlay gives Kirby nine total jumps and an original neutral B move.
It is based on `_build/audit-20261003/geno-guide/mods/tutorial-kirby` as found on 2026-10-03:
row 305, ground like-motion 44, air like-motion 65, joint 43. No disc bytes were copied.
This packaged starter has **not been run in the game by the tools author**. Verify those row,
motion and joint choices on your disc before claiming gameplay acceptance.

From the workspace root:

```text
python docs/learn/geno-fighters/starter/build.py
python -m tools.geno.check docs/learn/geno-fighters/starter
```

Copy this folder as `tutorial-kirby` beneath your mods parent. Keep `mod.json` and `geno.json`
beside each other. Boot with that mod and `geno-lab` enabled, select Kirby, count the jumps,
and use the LAB to check neutral B on the ground and in the air. Edit
`geno/tutorial_b.genoasm`, rebuild, check, then hot reload. See packets 1 and 3 for LAB controls.

The two-file jump-only version is in `../template/`. Neither version needs `files/` or m-ex tables.

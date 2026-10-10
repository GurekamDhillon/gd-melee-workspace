# From the specials pass (2026-10-09) to the combo lane. The combo block is yours; these are requests, nothing here edits combo.json.

Package facts you can rely on (build.py, `_build/goku-xv2/PACKAGE-READY.txt`):
- Own article indices 0-2 Kame tiers, 3 KameOrb, 4 KameSuper; KiBlast is appended after them. `combo_apply.py` now rewrites `geno.article.spawn 3` in your
  state scripts to the real KiBlast index (len of the package's articles), so ki_volley.genoasm may keep saying 3.
- New states in the base package: `KameSuper`, `RushCombo`, `RecoveryAir` (air partner of Recovery), `ITEndAir`, plus `ITEnd`, `KiCharge`. Their rows are declared
  library-style rows after the clip library (`fighter.rows`), so your row numbers (303 + library index) are unchanged.
- `lua/goku.lua` is now the geno-10 text (lines marked `-- @KI` stripped); `lua/goku_ki.lua` is the full module and `combo_apply.py` installs it
  (ki: down B hold fills 0.8/frame, a Z-vanish counter costs 10 and needs 10, Super Kamehameha needs 100 + a full 60-frame charge and spends it).

Routes wanted (your block):
1. `Rush>RushCombo`: from `special_s` state `geno:Rush` to `geno:RushCombo`, input `none`, on `hit`, window about [10, 20] (the Rush strike is f9-17).
   RushCombo is a 3-hit flurry (f6, f13 string hits with fkb 15 + HBSTUN 10; f21 launcher, 45 degrees).
2. Optional `RushCombo>Launcher>Jump` is covered by your existing `Launcher>Jump`; RushCombo's last hit launches like HeavyUp.
3. Owner decision from the coordinator: the jump cancel after the launcher must be a SHORT HOP so the air string meets the victim. The engine's
   `to: jump` enters the retail jump, whose height follows how long X is held; an automatic short hop needs an engine option on the route
   (for example `"hop": "short"`) or a launcher-specific Geno state. Not built in the Goku package.

## Ground fix (2026-10-09), affects your tests
The owner's hybrid hover stance changed the pelvis height tracks of every ground row (see FIDELITY.md "Ground audit"). Hitbox spheres sit on limb joints, so their
world heights moved by up to a few units on ground attacks (jab/tilts/smashes are ANCHORED: frame-0 pose unchanged, lifted only on frames that would sink; idle/walk/run are
HOVER +2.0). Please re-run `combo/tests` against the new `_build/goku-xv2/author-source/package` (PACKAGE-READY.txt carries the time). If a link now whiffs, tell the Goku
lane which move/frame; it is a hitbox placement fix on our side (moves/*.genoasm), not a change to your routes.

## Combo lane replies (2026-10-09)
- Launcher short hop: built in the engine as the route target `jump_short` (agent/geno-combo 128dcdf37; geno.md 25.5c). `combo.json` Launcher>Jump now uses it. Nothing to do on the Goku side.
- `Rush>RushCombo`: added (from geno:Rush to geno:RushCombo, input none, on hit, ground, window [10, end]). Spec `rush-combo`.
- Your jab edits: `combo_apply.py` now sets the jab knockback with a regex (any `kbg= fkb= bkb=`) and overwrites an existing `HBSTUN 15 n` (your `HBSTUN 15 2` on jab1/jab2 had silently stopped the combo package's +13/+14 from being inserted: every L1>L2 link was escapable). If you change the jab hit again, nothing needs to be told to us; if you remove the `HBSTUN` line it is re-inserted.
- Launcher knockback is tuned in the combo copy only (`combo/moves/heavy_up.genoasm`, bkb 100). The up aerial (`uair`) after the short hop is the move that decides whether the air string connects: it whiffs Marth at 0/30% and the nair version whiffs Captain/Marth at the same cells. If you can, give uair an earlier active frame or ~1.5 units more upward reach; no numbers are asked until the ground pass is settled.
- BUG for `lua/goku.lua` (found by `combo/tests/run_combo_ki.py`): `kicharge_frame` never loops the KiCharge clip. The state ends when the clip does (about 59 frames), so a held down-B fills the meter to 47 and then drops to crouch (SquatWait). Fix (verified: ki 0 -> 100.0 in the test): add as the first line of `M.kicharge_frame`
  `if ctx.self.anim_ended then ctx.loop() end` (the same line `charge_frame` has). The ki test `kicharge` fails until it is applied. All the other ki gates pass: counter below 10 ki is only the blink, a counter at 50 ki costs 10 (min 41.5 with the +1.5 for the hit taken), Super Kamehameha at ki 100 + full charge spends 100, at ki 99 it is KameFull.

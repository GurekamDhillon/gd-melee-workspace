# Goku HB-SAMPLE hitboxes (remake phase 2, 2026-10-11)

Owner, after playing phase 1: add sample hitboxes on everything "as per Xenoverse", covering the whole limb like Melee (Fox nair), not just the end of it. This reverses phase 1's "no generated hitboxes" **only as a labelled sample layer**: the ledger status **HB-SAMPLE** sits between HB-NONE and HB-AUTHORED. A sample is a starting point to edit in the Workbench; it never ships as final. Every sample script starts with an `# HB-SAMPLE` header and `tools/remake_hb.py check` fails a script that lies about it.

Generator: `python ports/goku-xv2/tools/remake_samples.py plan|write` (needs a built package). The audit (`build.py`, `audit_gameplay.py`) fails the build when a sample sphere's centre is farther than its radius from its limb bone segment in any active frame (tested: a sphere moved 6.7 units off the left forearm fails with "floats off the limb").

## What is derived from what

| thing | source | rule |
|---|---|---|
| when (active frames) | the XV2 BAC Hitbox events that play while the row's clip plays (start, duration) | mapped through the row's crop and speed; for a single-hit window the window is then **centred on the frame where the leading limb is farthest from the chest** in the built animation (BAC event frames run on the BAC's own clock; the earlier hand review had found the same offsets, e.g. the right straight peaks at f5, the BAC event says f9). Chained rows (Side B, Homing) use the BAC timeline 1:1. Multi-hit flurries keep the XV2 pulses. |
| which limb | the built animation bank (FigaTree pose) | among the limbs the owner's clip description allows (kick = feet, punch = hands, undescribed = any) the effector that travels farthest into the window |
| where | the mesh | the leading limb gets **3 spheres along its bone chain**: arm = hand end of the forearm, mid-forearm, upper arm; leg = foot, shin, thigh. Each centre sits on the PCA axis of that bone's skinned vertex cloud (so on the limb in every frame, since the sphere rides the joint). Radius = mesh limb thickness (92nd percentile distance to the axis) x 2.4, clamped to 2.0 .. 3.6 model units. |
| strength order | Melee sweetspot / sourspot by hitbox id | slot 0 = tip (full damage and base knockback), slot 1 = middle (85% damage, bkb -3), slot 2 = inner (70% damage, bkb -6); the lowest id wins an overlap, as in Melee |
| damage | XV2 Hitbox `Damage` | anchor table below, then capped per move class |
| angle, KBG, BKB | the XV2 BDM reaction named by the hit (DamageType, KnockbackStrength up / forward, KnockbackDuration) | tables below |

Anchors (XV2 damage -> Melee damage, linear between): 0 -> 0, 3 -> 2, 5 -> 3, 10 -> 8, 15 -> 10, 20 -> 12, 30 -> 15, 40 -> 20 (Marth-like: jab 3, tilts 8, fair 10, smashes 15-22). Caps: jab 7, tilt 12, smash 22, aerial 14, special 16.

## BDM reaction -> Melee knockback

| XV2 reaction | Melee angle | KBG | BKB |
|---|---|---|---|
| `Standard` (stumble sets, tiny pushback, 30-frame stun) | 361 | 50 | 6 + 0.8 x damage |
| a Standard hit that feeds the next link of a string (jab, Light 3-5, Rush, the nair / uair string sources) | 361, **fixed knockback** fkb 10 | 60 | 0 (+ `HBSTUN` carried from the earlier design) so the link is true at every percent |
| `KnockbackN` / `Heavy`, launch up/forward ratio >= 55 deg (the launcher) | 80 (85 above 80 deg) | 60 + 0.5 x (duration - 30), 50..100 | 20 + 1.5 x damage |
| same, 25..55 deg | 55 | as above | as above |
| same, under 25 deg (horizontal blowback) | 40 (45 for smashes and specials) | as above | as above |
| same, launch straight down (up/forward <= -45 deg; the XV2 slam is Knockback8, strength Y -2.6) | 270 (meteor) | as above | as above |
| Dair (owner brief: the spike; XV2's reaction for that clip is a plain Standard hit) | 270 override | 80 | 20 + 2 x damage |
| rapid-jab / nair pulses | 361, kbg 30, bkb 10; the last pulse a 45-degree finisher (kbg 60, bkb 25) | | |
| grab | capture element, damage 0 | | |

## The samples

| move | HB | active frames | damage (tip) | angle | KBG/BKB | limb | from |
|---|---|---|---|---|---|---|---|
| jab1 | SAMPLE | [[2, 6]] | 3 | 361 | 60/0 | hand.L | XV2 hit entry 300 |
| jab2 | SAMPLE | [[2, 6]] | 3 | 361 | 60/0 | hand.R | XV2 hit entry 301 |
| jab3 | SAMPLE | [[4, 8]] | 7 | 361 | 50/12 | foot.L | XV2 hit entry 302 |
| rapid_jab | SAMPLE | [[12, 15], [18, 21], [24, 27], [30, 33], [36, 39]] | 2 | 361 | 30/10 | foot.R | XV2 hit entry 336 |
| dash_attack | SAMPLE | [[5, 9]] | 12 | 361 | 50/16 | foot.R | XV2 hit entry 337 |
| ftilt | SAMPLE | [[3, 7]] | 3 | 361 | 50/8 | hand.R | XV2 hit entry 301 |
| utilt | SAMPLE | [[5, 8]] | 10 | 80 | 83/35 | hand.L | XV2 hit entry 342 |
| dtilt | SAMPLE | [[11, 19]] | 12 | 361 | 50/16 | foot.L | XV2 hit entry 370 |
| fsmash | SAMPLE | [[14, 18]] | 10 | 361 | 50/14 | foot.R | XV2 hit entry 312 |
| usmash | SAMPLE | [[8, 12]] | 10 | 80 | 83/35 | hand.R | XV2 hit entry 342 |
| dsmash | SAMPLE | [[7, 11]] | 8 | 80 | 66/32 | foot.R | XV2 hit entry 341 |
| nair | SAMPLE | [[12, 15], [18, 21], [24, 27], [30, 33], [36, 39]] | 2 | 361 | 30/10 | foot.R | XV2 hit entry 336 |
| fair | SAMPLE | [[15, 19]] | 14 | 270 | 83/41 | hand.R | XV2 hit entry 343 |
| bair | SAMPLE | [[6, 18]] | 11 | 361 | 100/12 | carried | carried unchanged from the earlier hand-authored spheres |
| uair | SAMPLE | [[12, 16]] | 14 | 80 | 60/41 | foot.R | XV2 hit entry 365 |
| dair | SAMPLE | [[10, 14]] | 8 | 270 | 80/36 | foot.L | XV2 hit entry 302 |
| grab | SAMPLE | [[9, 17]] | 0 | 361 | 100/0 | hand.R | XV2 hit entry 600 |
| dash_grab | SAMPLE | [[9, 17]] | 0 | 361 | 100/0 | hand.R | XV2 hit entry 600 |
| Rush | SAMPLE | [[40, 44]] | 8 | 361 | 60/0 | foot.L | XV2 hit entry 419 |
| RushCombo | SAMPLE | [[2, 10]] | 15 | 45 | 88/42 | hand.R | XV2 hit entry 427 |
| Homing | SAMPLE | [[33, 39]] | 8 | 45 | 95/32 | foot.R | XV2 hit entry 476 |
| Light3 (combo) | SAMPLE | [[10, 14]] | | | | | combo state |
| Light4 (combo) | SAMPLE | [[15, 19]] | | | | | combo state |
| Light5 (combo) | SAMPLE | [[3, 7]] | | | | | combo state |
| HeavyRush (combo) | SAMPLE | [[14, 18]] | | | | | combo state |
| HeavyFinish (combo) | SAMPLE | [[8, 12]] | | | | | combo state |
| HeavyUp (combo) | SAMPLE | [[13, 17]] | | | | | combo state |

Still HB-NONE (no XV2 hit data or no collider): pummel, fthrow, bthrow, uthrow, dthrow, rapid_start, rapid_end, Recovery, ITEnd. The throws carry their own throw damage data and need no collider; pummel has no XV2 equivalent.

Not claimed: these are sample numbers, not tuned; hit-feel, hitlag, effects and sounds are Melee defaults. Whether a sample connects was checked headless (`lua/samples_check.lua`: every ground and air normal, grab, Rush and Homing hit a Mario dummy; the jab string takes its routes); look and feel is owed to the owner at a monitor.

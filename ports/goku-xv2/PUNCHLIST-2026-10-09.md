# Goku owner punch list, 2026-10-09 (combo build, hands-on)

Owner's words, condensed. Each needs a fix and a fidelity-ledger note.

1. Idle floats (by design: hybrid hover 2.0), but grounded moves start ON the ground and end floating:
   - ftilt: foot starts on the ground, ends floating.
   - jab2: looks good on the ground, then floats off going to idle.
   Need consistent ground/hover blending: entry and exit transitions, no snapping.
2. utilt: "dumb move/animation". Re-pick.
3. Crouch floats. Should be grounded.
4. nair and fair are effectively the same animation. Re-pick one.
5. uair looks good. Keep.
6. dair uses a grounded animation. Re-pick an aerial one.
7. Landing from aerials: sometimes sinks through the ground to the torso. Suspect ECB/landing anchor.
8. The circle emblem on the back of the gi doesn't render properly (texture/material/alpha/UV).
9. Jump and double jump animations are poor choices. Re-pick.
10. Many hitboxes are on the wrong limb. Full audit: every attack's hitbox bone vs the limb that visibly strikes.

11. bair (now Melee Luigi's, CROSS-PORT): owner says it looks and works as intended; REACH needs tuning (foot ~8.4 behind vs scaled Luigi ~13; thigh-stretch SCAX not carried).
12. Landing lag (all aerials, starting with bair = 19): must sit between the min and max of native Melee characters' values for that aerial. Measure the real range from the disc for all 26 characters.

13. Thrown poses (agent/geno-thrown, stand-in Captain Falcon): owner says the throws look fine. Goku's OWN grab animations (grab, dash grab, pivot grab, catch-wait/hold, pummel, throws) "are not the best": re-pick.

14. IDLE (owner, 2026-10-09 22:20): the hybrid hover was meant to use XV2's FLOATING idle animation (flight-stance hover idle), sitting slightly above the ground. Right now idle is the standing pose lifted 2 units, which reads as "floating standing". Fix: Wait (and its variants and the transitions into and out of it) use the XV2 floating-idle clip, slightly above the floor.

Re-picks (2, 4, 6, 9, 13) go to the owner with a shortlist viewable in the clips viewer.

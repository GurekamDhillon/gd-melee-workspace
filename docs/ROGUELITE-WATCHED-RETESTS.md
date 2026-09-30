# Watched retests

User direction: when automated testing is difficult or inconsistent, record the
issue and move on to independent work. Retest with the user watching. Do not
certify uncertain results, and do not defer reproducible save/ownership defects
as subjective playtesting.

| Item | Evidence so far | Watched retest | Pending decision |
| --- | --- | --- | --- |
| Branch lower door | Native branch_y/Falco v7: ascent, return and upper fork arrived; lower fork fell. Long controller path may overshoot. | Show room, attempt ground route through passthrough ramp and then under solid upper landing, at normal 60 Hz; let user observe or drive. | Controller path defect versus room geometry defect. |
| Merge room | native-merge-v2: left entry fell; subsequent top placement refused. | Fresh fixture for each entry; observe movement, landing and native respawn readiness. | Reachability versus overshoot/fixture timing. |
| Ramp/landing seam | branch_y return trace flags grounded-to-airborne transition with nonpositive vertical speed. | Watch short ordinary movement across join, no debug fly. | Actual seam pop versus valid departure from a surface. |
| HUD readability/size | Corrected responsive menu suite and actual draw bounds pass; full presentation not yet wired. | Watch stock/percent/three abilities/opponent/tells in combat; inspect compact menu and toast. | Readability, clutter and desired scale. |

Existing native evidence lives under `_build/deepseek-coordination/`; PNGs under
`native-previews-clean` are actual game captures. No mockups or simulated game
screenshots are review evidence.

An exploratory lower-door analog-stick probe was queued before this direction;
it ended with console ConnectionRefusedError, without traversal evidence
(`native-ground-fork-v1-summary.json`). Do not repeatedly relaunch to force a
result. Resume these tests during watched review.

Confirmed campaign retirement, effect rollback, native unload ownership and
save safety defects remain engineering work and are not waiting for human
judgment. All recipes remain uncertified.

## Live watched evidence update

Bluetooth 8BitDo Ultimate2C physical pad observed bygd.pad(1). Usercontrolled
branchtrace `watched-branch-trace.json`:301grounded samples near lowerdoor
x52/y0 fromentryfixture, no scriptedinputduringtrace. Lowerdoor reachablewith
Falco; previousovershoot doesnotprovegeometryunreachable. Window900frames
truncated, stillnotfullrecipe certificate. Userexplicitlyreports snag/pop at
ALL stairs->balcony->ramp->upperlandingjoins. This confirms a movement-quality
defect for investigation, not humanacceptance. Native seams researchworker
inspecting MapLine links/independentjoints; no automaticflag flips. Merge room
loaded andunpaused foruser, secondtrace pendinguser movement.

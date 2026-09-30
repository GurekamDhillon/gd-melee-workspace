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

The Bluetooth 8BitDo Ultimate 2C physical pad was observed by `gd.pad(1)`.
The user-controlled branch trace (`watched-branch-trace.json`) contains 301
grounded samples near the lower door at x=52, y=0, starting from the entry
fixture with no scripted input during the trace. Falco reached the lower door;
the previous automated overshoot does not prove that the geometry is unreachable.
The 900-frame trace was truncated and is not a full recipe certificate.

The user explicitly reports snagging or popping at **all** joins between the
stairs, balcony, ramp and upper landing. This confirms a movement-quality
defect. A Sol worker is implementing explicit room-local native floor links;
its actual-source tests do not replace a watched retest. No certification flags
have been changed.

After reopening with the native owner-cleanup build, the user confirmed that
the merge room is accessible. The native sample at x=47.553, y=0 corroborates
arrival near the ground-level right doorway. This is reachability evidence for
Falco from the left entrance, not clearance or physics certification for every
character. The native cleanup build passed 213/213 tests. The shared ascent
snag remains open until the seam fix is integrated and retested with the user.


## Seam build prepared for watched review

The updated branch_y room reached native `phase=ready`: five colliders,
26 visual parts, stage isolation enabled, native `stage_link` API present.
Construction now requires all three authored ascent seams to link successfully.
This proves live construction, not movement quality. Evidence:
`_build/deepseek-coordination/native-seam-live-build.json`.

The entry placement command was refused while Falco was on a respawn platform.
Per the user's direction, do not repeatedly automate fixture timing to force a
result. The room is left paused; establish a stable fighter and entry fixture
with the user watching, then retest the three joins at normal speed. No controller
input was injected during this build check and no traversal was recorded.

Actual in-game PNG:
`_build/deepseek-coordination/native-previews-clean/native_seam_branch_ready.png`.
All recipes remain uncertified.

# MeleeVS / TagFighter: what it teaches us (2026-10-03)

Read-only research. Subject: https://github.com/Joyastick/melee-pc-TagFighter (branch
`melee-pc-TagFighter`, HEAD `0ef6afb`, 2026-10-01; 12 stars; created 2026-09-17; releases
`MeleeVS-v1.1.2` latest). Upstream port compared: https://github.com/999sian/melee-pc (master as cloned,
last commit 2026-09-29). Shallow clones sit in `_build/tmp/tagfighter/{repo,upstream}` (untracked scratch).

**Rule observed: consult, never copy.** Everything below describes mechanisms and cites `file:line` in THEIR
repo (paths relative to its root, `repo/`). No code was taken. Their decomp function names (`ftCo_*`, `fn_8016719C`,
...) are doldecomp symbol names that our own `melee/` checkout also has; naming them is not copying their code.
Our tree cites are workspace-relative.

I read: all of `src/melee/mod/tag_assist.{c,h}` (2766 + 195 lines), every hook site outside it, `README.md`,
`ROADMAP.md`, `CODING_STYLE.md`, `LICENSE.md`, `src/pc/net_snapshot.c` (snapshot and checksum parts),
`net_handshake.c` (tag-bind parts), the commit history (500 commits, full messages of the ~30 that matter), the
release list, issues (none open or closed) and PRs (17, all by the owner). I did not build or run anything.

---

## 0. Licence, exactly

`LICENSE.md` (repo root) splits the repo into three situations. GitHub's "Other" is that file.

| Part | Paths | Terms |
|---|---|---|
| Game code | `src/melee/`, `src/sysdolphin/` | **Not licensed.** "No permission to copy, modify or redistribute this code is offered or implied" (`LICENSE.md` section 1). It is a derivative of doldecomp/melee, which publishes no licence, and the author says they cannot grant one. |
| Port code | `src/pc/`, `tools/`, `platforms/`, `cmake/`, `.github/` | GPL-3.0-or-later, "Copyright (C) 2026 the melee-pc contributors", full text in `COPYING` (section 2). |
| Third party | aurora (MIT), Liberation Sans (OFL), SDL3 Android glue (zlib), others fetched at build time | their own licences (section 3). |

Consequences for us:

- **The tag mod itself is NOT under any licence.** `tag_assist.c` and `tag_assist.h` live in `src/melee/mod/`, which is
  inside `src/melee/`, i.e. the "not licensed" bucket. So the mod we care about grants us nothing. The README says the
  same: the repo "as a whole is not distributable under the GPL" (`README.md`, License section).
- The GPL parts (`src/pc/net_*.c`, launcher, tools) could in principle be reused under GPL-3 terms, but that would make
  anything we merge them into GPL-3, and our standing rule is consult-only anyway. Not recommended, not needed.
- Ideas, mechanisms and the bugs they hit are not copyrightable; we can reimplement from our own reading of the
  decomp. That is the whole use of this note.
- No game assets are in the repo (everything is read from the user's disc at runtime; `LICENSE.md` section 1).

---

## 1. Spawning and removing a fighter mid-match: they do not do it

**The headline, and it contradicts how the brief frames the question: nothing is spawned or freed mid-match.**
Header comment, `src/melee/mod/tag_assist.c:111-119`: "Both point and assist are REAL, already-existing player-slot
Fighters from the game's own normal spawn pipeline (assist ports set to CPU in CSS) -- nothing is ever spawned or freed
by this module, so each has its own independent stock/percent for free via the normal MatchPlayerData system, with no
risk of the flat/collapsed-model bugs an ad-hoc Fighter_Create() mid-match produced in an earlier version." (The
earlier version is not in the public history; only this comment records it.)

So a 2v2 tag match is a plain 4-player **Team Battle** (`rules.is_teams = 1`, forced: `mn/mncharsel.c:5949-5957`;
debug path `gm/gmvsmode.c:251`). All four fighters exist from the first frame. The "assist" is a fighter that is
**benched** (frozen, invisible, intangible, off camera) until called, then **unbenched** next to the point fighter.

### 1.1 Bench (hide)

`TagAssist_SetBenched`, `tag_assist.c:881-907`. Per fighter (and recursively for Nana, `:885-888`):

| Write | Why (their comments) |
|---|---|
| `fp->x221F_b3 = 1` | Skips the CPU AI think call (`Fighter_8006ABA0`, `ft/fighter.c`) and the whole input block, and makes `Fighter_procUpdate` early-return. This is the flag that makes the bench stick. Setting only render flags held for one frame, because the CPU AI kept running and every state Enter reset them (`tag_assist.c:121-132`). |
| `fp->cpu.kind = CpuKind_5` | Second layer: `ftCo_IsCpuControlled` treats kind 5 as "not CPU controlled" (`:889-890`, explained `:1711-1721`). |
| `fp->invisible = true` | render |
| `fp->x2219_b1 = 1` | intangible: skips hurtboxes, collision and the blast-zone/KO check (`ftCo_800D3158`), so a benched fighter can never lose a stock (`:871-875`). |
| `x221E_b1`, `x221E_b2`, `x221F_b1 = 1` | other hide/ignore bits (unnamed in the decomp; no comment says which does what) |
| scale reset to 1.0 | a frozen fighter caught mid squash-and-stretch stayed "flat" forever (`:980-990`) |
| `Camera_80028F5C(fp->x890_cameraBox, CmSubjectState_Inactive)` | remove from camera framing (`:904-906`) |

The bench is **re-asserted every frame while the assist is not called out** (`:2656-2658`), because any state change
the assist's own background logic performs resets `x221F_b3`; a one-shot write "loses that race unpredictably"
(`:2647-2655`).

Before the very first bench the fighter is forced into `ftCo_MS_Wait` via `Fighter_ChangeMotionState` (`:2643-2645`).
This was the hardest bug in the history ("slide on first call", commits `0458c42`, `6a9d16e`, `13c6ed6`): benching only
twiddles flags and never resolves a real action state, so the first call transitioned out of whatever half-finished
spawn-in state the fighter happened to be in. Every later call worked because the fighter had completed a clean cycle.
Same trick before every auto-bench (`:1632-1633`).

### 1.2 Unbench (show, place, hand over)

`TagAssist_Unbench`, `tag_assist.c:941-1115`. A raw `cur_pos` write is not enough; their findings:

1. `ftCommon_8007E2FC(gobj)` zeroes velocity (what a real respawn does); `gr_vel = 0` (`:952`, `:978`).
2. Ground state is copied from the point fighter (`ground_or_air`, `coll_data.floor`) instead of forcing air and
   hoping collision re-detects a floor the same frame. Forcing air produced ~60 frames at `self_vel.y == 0` while a
   move's scripted physics (Falcon Punch glide) ran as if grounded (`:954-967`, commit `6a9d16e`).
3. Position is set with `mpColl_80043680(&fp->coll_data, &fp->cur_pos)`, the engine's teleport helper that collapses
   `prev_pos`/`last_pos`; otherwise the floor segment test from the old platform keeps re-acquiring the old floor
   ("stuck on the last platform it ever landed on", `:1033-1042`).
4. `xF8_playerNudgeVel` (anti-overlap push) and the stale `input.*` history are zeroed because both sit frozen and replay
   in full on unfreeze (`:1057-1087`).
5. Spawn offset is 10 units in front of the point fighter. 150 cleared the anti-overlap push but "read as too far"
   (`:1007-1028`, commit `2d68125`): a known unresolved trade-off, not a fix.
6. `ftCamera_80076064(fp)` re-activates and re-seeds the camera box. Setting the state alone (`_Auto` vs `_Active`)
   left the camera not following (`:1095-1113`).
7. Flags cleared in the reverse of bench (`:1089-1094`). Deliberately **not** used: `CollData_X130_Locked`; leaving it
   set froze environment collision permanently and likely broke KO handling (`:995-1002`).

Airborne call: a floor is found by a downward `mpCheckFloor` ray (`:801-813`, up to 100000 units); no floor means the
call is refused (`:1278-1283`). The assist then drops to that floor "however far below" (`:1004-1006`). First version
refused all airborne calls (commit `a7a7601`), later added the raycast (`bdfbb5f`).

### 1.3 The move

The assist is dropped into one fixed move by calling that move's own `_Enter` function (`ftMr_SpecialN_Enter`, ...),
not by `Fighter_ChangeMotionState` to a motion id (`TagAssist_GetAssistMoveEnter`, `:701-759`; reasoning `:562-588`).
A bare state change plays the animation but never wires the callbacks the move script fires (Mario's
`accessory4_cb` fireball spawn, Game and Watch sausages). Two moves (Up Smash `:632`, Down Smash `:641`) have no
exported Enter, so three lines are mirrored. DK's Giant Punch needs a second B press that no frozen assist would
deliver, so DK enters the release state directly (`:676-699`).

### 1.4 When a call is refused

`TagAssist_TryCallAssist`, `:1229-1339`. Refused when: assist already out; the right input did not fire; point is
`TagAssist_IsUncontrollable` (`:1143-1227`: grabbed in any of ~8 character-specific capture ranges, hitstun
`DamageHi1..DamageFlyRoll`, `DamageFall`, screw-attack, ice, shield-break through `Furafura`, sleep, song/bind, bury,
`DownBound/DownDamage`, post-release `Thrown*` ranges, `CaptureLeadead`, `CaptureLikelike`); no floor below an
airborne point; character has no wired move. Deliberately still allowed: air dodging, being the grabber, and plain
knockdown get-up (`README.md`, "Call an assist"). Motion-id based on purpose, because `grab_timer` is not reliably
reset by every exit path (`:1147-1157`, commit `834ce1e`).

Despawn is the mirror: 300 frames (`ASSIST_DURATION_FRAMES`, `:295`), with waits and safety caps:
180 frames (`:516`) to let a hitstun or death sequence finish; 900 frames (`:522`) for a grab in progress (either
side, universally detected by `fp->victim_gobj != NULL`, `:1488-1491`). Release the victim with `ftCo_800DA698`
before benching (`:1497-1505`, commits `67e669a`, `5f6f169`).

### 1.5 KO of a called-out assist

Detected by **motion id range** `ftCo_MS_DeadDown..ftCo_MS_RebirthWait` (`:1446-1450`), not by animation-frame
bookkeeping, which has a one-frame gap at sub-state boundaries that benched a fighter mid-respawn and stranded its
percent digit (`:1425-1445`, commit `13c6ed6`). The assist is benched the instant it reaches the angel platform
(`ftCo_MS_Rebirth`/`RebirthWait`, `:1561-1565`, `:1583-1588`) so it never walks off as a normal CPU. Reason it is
safe to freeze there: the percent/HP reset runs at the start of `ftCo_800D4FF4`, before `Rebirth` is entered (`:1551-1560`).

### 1.6 Memory and animation files

Not an issue for them: all four characters are real slots, so the vanilla match start loads every fighter's files
once, exactly as in a normal 4-player match. Nothing loads on demand. (I did not read the decomp's load path; this
follows from "nothing is spawned".) **Implication for us: an enemy roster chosen at mission start is free; one
chosen mid-mission is not provided by anything here.**

### 1.7 Ice Climbers and Zelda/Sheik

- **Ice Climbers**: Nana is a separate `Fighter_GObj` sharing Popo's `player_id` (`is_sub_fighter`), found by
  `Player_GetEntityAtIndex(id, 1)` (`:857-864`). Bench, unbench, control roles and the per-frame hook all handle her
  separately: bench/unbench recurse (`:885-888`, `:947-950`), her real `cpu.kind` is captured at team init and restored
  later (`:1683-1699`, `:1811-1832`), she is skipped by the per-frame hook (`:2567-2569`, which otherwise thrashed the
  new-match detector). Cost them four commits.
- **Zelda/Sheik**: retail swaps which of two `Fighter_GObj`s is active on transform rather than changing `kind` in
  place (`:815-838`). The dormant half is still ticked every frame and reads real input if its own `cpu.kind` /
  `x618_player_id` say so, so every control write is mirrored onto both halves (`:1784-1809`, `:1850-1864`). A
  transform used to look like "a new match" and wipe the team, so `TagAssist_HandleNewMatch` recognises it and updates
  pointers in place (`:2270-2301`, commit `4d21893`). **Still broken**: `ROADMAP.md` "Known issues": a crash when
  Zelda is both point and assist and transforms at match start, plus role glitches after several tags.
- Both can occur only because all halves exist from match start. A fighter that does not exist at that time cannot
  be benched.

### 1.8 Our matching place

We have no bench/unbench. Closest code:
`melee/pc/gameworld/script_game.c:2588` `ScriptGame_CpuMode` (stand/fight for an existing CPU), `gd.teleport` and the
fly states with their refusal list `melee/pc/geno/geno_lab_mode.c:622-650` `fly_refused` (checks `x221F_b3`, death range,
capture/thrown ranges: the same class of list as their `IsUncontrollable`), and the scene launcher that can start a
match with four slots, teams, CPU levels (`_research/scene-launch.md`, `MELEE_SCENE="mode=vs;p1=fox/team0;...;teams=1"`).
`melee/src/melee/ft/fighter.c` already carries the same decomp flags (`x221F_b3` at lines 1640, 1719, 2010, 2661).

---

## 2. Control hand-off ("tag")

### 2.1 Input routing

Melee reads a fighter's input from `HSD_PadGameStatus[fp->x618_player_id]` unless `ftCo_IsCpuControlled(fp)`
(`ft/fighter.c:1870-1930` in their tree). Their model keeps one **physical pad port** per human and moves it between
fighter objects by writing three things (`TagAssist_ApplyControlRoles`, `tag_assist.c:1733-1901`):

1. `Player_SetSlottype(player_id, Human|Cpu)` on the new point / new assist. The slot-type flip matters because
   `ftCo_IsCpuControlled` checks `pkind` first.
2. `fp->cpu.kind = CpuKind_5` on the new point (defeats the CPU path, `:1747`), a real idle kind on the new assist (below).
3. `fp->x618_player_id = team->human_pad_port` on the new point, the CPU's original port on the new assist (`:1748`,
   `:1890`), plus `Player_SetPlayerId` so retail's pause lookup still works (`:1760`, `:1895`; pause scans every port
   against every slot, `gm_DefaultVSGetPauser`, explained `:1749-1759`).

Human + human (Duo) needs none of this: each player keeps their own fighter, tag is a pure label swap (`:1739-1741`).
Hence the team's `is_cpu_team` flag, captured once (`:1646-1704`).

Traps they hit, each cheap to hit again:
- **Double tag.** After repointing, the new fighter's button-edge history (`held_buttons[0..2]`) held stale zeros, so a
  button the human was still holding looked like a fresh press one frame later and the swap cancelled itself. Fix:
  seed all three history slots with the real pad now (`:1762-1782`).
- **`CpuKind_5` is both a real AI profile and the sentinel.** If the CSS gave the CPU kind 5, restoring it verbatim
  defeats `ftCo_IsCpuControlled` and both fighters read one controller. Substituted kind 4 on collision (`:1666-1681`).
- **A stale pad port on the demoted fighter** turns into "both fighters answer one controller" the instant
  `IsCpuControlled` misreads (`:1878-1890`).
- **Results screen softlock.** Swapped slot-types left at match end broke the "wait for Start" gate. Fix: revert in
  `onExitVs` before the end transition and patch the already-snapshotted `MatchEnd.player_standings[].pkind`
  (`gm/gmvsmode.c:321-340`, `tag_assist.c:2709-2766`). A crash came from dereferencing a GObj pointer that was stale by
  match end, so the revert is keyed on cached `player_id`s, never on GObj pointers (`:2717-2739`).
- **Tag input must be read upstream of the fighter's own input.** With a bound X/Y/L/R, `fighter.c` strips that button
  from the fighter input so it stops also being jump/shield (`ft/fighter.c:1868-1928`), so tag detection reads
  `HSD_PadGameStatus` itself with its own edge tracking, one snapshot per frame (`tag_assist.c:261-291`). L/R are
  synthesised from the analog value against `analog_shoulder_deadzone`, since the digital bit needs a full click.

### 2.2 Cancel into control

`TagAssist_TryTag`, `:1913-1996`. The incoming fighter is dropped into a known-good neutral: `ftCo_MS_Wait` if grounded,
`ftCo_Fall_Enter` if airborne (grounded Wait on an airborne fighter "teleports to the ground", commit `6b0d709`,
`:1956-1977`). Skipped when `TagAssist_CantAct` (`:1507-1542`): everything in `IsUncontrollable` plus air dodge (and its
landing lag, tracked with a per-slot "was in EscapeAir" latch because `LandingFallSpecial` is shared with special
fall, `:1511-1532`), plus grabber or any `victim_gobj != NULL`. The fighter then plays that state out, so a tag is never a
free escape. Limits: 3 tags per call (`:326`), 15 frames call-to-first-tag (`:321`), 20 frames between tags (`:331`);
the cameo clock is not restarted by a tag (`:1984-1989`).

### 2.3 The previous point becomes AI/idle

Control writes make the old point a real CPU fighter with `CpuKind_0` (`:1849`), the Training-mode "Standing" dummy:
it never acquires a target or attacks, and only walks toward the floor beneath itself (comment `:1835-1848`). The
first version gave it the real combat AI (`saved_cpu_kind`); playtesting rejected it. `saved_cpu_kind` is still used
when a fighter becomes the sole survivor (`:2088-2093`).

**Important for our companion idea:** `CpuKind_0` does not follow anyone. They have no follow, escort or support AI.
There is no AI work in this repo to learn from.

### 2.4 "Predetermined assist move"

A switch on `FighterKind` to one `_Enter` function per character (Section 1.3), documented in
`docs/tag_assist_roster.csv` and the README table. Not data-driven, no per-call choice (README "Not planned for now").
The move executes on its own once entered; after it ends the fighter idles under `CpuKind_0`. Aerial table is a separate
lookup that currently forwards to the grounded one (`:768-771`).

---

## 3. Teams, stocks, KO, promotion

- **Reused Melee's Team Battle outright**: Red/Blue picker only (Green skipped, `mncharsel.c:2534-2541`), `is_teams`
  forced, team colours for costumes. Team pairing is read from the CSS door colours into `sPortTeamColor[4]` every CSS
  frame (`TagAssist_CssSyncPortTeam`, `tag_assist.c:2380`; call `mncharsel.c:3931`) and frozen when the match starts.
  Start is gated to exactly 2 + 2 (`mncharsel.c:3988-3998`) and a human+CPU team must have the human as point
  (`:4017-4055`).
- **Stocks and percent are per fighter, from the normal player table.** A team therefore has two stock pools. Default
  rules: Stock, 3 lives, items off, 8 min (`TagAssist_ApplyDefaultRules`, `:2352-2359`).
- **Benched assists cannot die** (intangible, Section 1.1), so a team only loses a fighter that was point.
- **Point eliminated** (`Player_GetStocks(point) == 0`, checked every frame from `TagAssist_Tick`, `:2219-2233`,
  `:2682-2687`): promote the assist (`:2011-2116`). It enters riding the angel platform with its current percent kept:
  `fn_8016719C` (primes spawn-platform storage and resets HP), `Player_SetHPByIndex` to restore the percent, then
  `ftCo_800D4FF4` (the retail death chain's own "enter Rebirth"), then clear their bench flags (`:2034-2066`). The camera
  box of the eliminated fighter is set inactive or the camera tightens forever (`:2095-2106`, commit `af12f88`). The check
  is deliberately immediate, not deferred to retail's own "borrow a stock from a teammate" Continue (`fn_8016B918`):
  deferring made the point resurrect as itself by draining the assist's pool (`:2196-2212`). It must live in
  `TagAssist_Tick`, not the per-fighter hook, because retail freezes a 0-stock fighter with the same `x221F_b3` and so
  the hook stops firing (`:2183-2195`). Without promotion the team softlocks: benched assist is intangible, nothing can
  ever take a stock (`:467-483`).
- **Revival**: sole survivor presses the call input to donate one spare stock (`TagAssist_TryReviveFallenPartner`,
  `:2147-2181`), mirroring `fn_8016B918`'s primitives (`Player_LoseStock`, `Player_SetStocks`,
  `gm_GetMatchEndPlayerScore`, `fn_8016719C`), then benched via a forced Wait. Roadmap says this has no on-screen
  indication yet (`ROADMAP.md`, Planned: "HUD and results feedback").
- Match end, sudden death and results use stock team battle unchanged; the only edit is the pkind patch in 2.1.

---

## 4. HUD, nametags, counters

They do not build a new overlay system. They repurpose **Melee's own nametag objects** (the ones that float over a
fighter and follow it, normally name-entry tags), forced to exist for all four ports (`if/ifnametag.c:230-240`
`has_nametag`), and rewrite their text in place:

- Text per slot: point shows `Point: N` (tags left), a called assist shows a live countdown `Assist: 4.2`, `Assist: ...`
  while its bench is waiting out hitstun, `Assist Ready` for a 120-frame badge when a call becomes available
  (`GetNametagText`, `ifnametag.c:358-400`; content key `:416-432`; `TAG_READY_BADGE_FRAMES`, `:287`). Shown only while
  an assist is out or the badge is live (`nametag_should_show`, `:262-266`).
- **Rewrite in place with `HSD_SisLib_803A70A0`, not free-and-recreate.** Recreating each tick leaks the SIS buffer (the
  free half only blanks, it never reclaims bytes) and hit `OSPanic` "Memory Empty" inside a minute; this was the real
  cause of a "crash on Final Destination" report (`:439-452`, commit `da2dcdb`). Only rewrite when a content key changes.
- Characters outside the font's safe set eat the next byte: `(`, `)` silently emitted nothing and swallowed the digit.
  They use `:` and plain letters (`:333-345`).
- Team colour per text via `HSD_SisLib_803A74F0`; a backing bar and arrow triangle drawn in the nametag GObj's own
  render callback with `DrawRectangle`/`GXBegin` (`NameTag_RenderCallback`, `:175-214`).
- "Assist Ready" and "Share Stock?" over the benched fighter's HUD cell: a separate small GObj with its own SIS canvas
  (`ReadyHud_*`, `ifnametag.c:745-790`).
- **Percent and stock HUD for four fighters**: nothing is changed. It is Melee's normal 4-player HUD, which is why they
  needed no HUD work beyond the stranded-percent-digit bug in Section 1.5. (I grepped every `TagAssist_` call site: no
  `ifstatus` edits.) Wide-HUD anchoring comes from upstream.

---

## 5. Menus and CSS

All on top of the decomp's own menu code, gated on `TagAssist_IsTagBattleOn()`:

- **Entry**: a new `SEL_VS_TAG_BATTLE` row in the VS submenu, label "MELEE VS" (`mn/mnonline.c:51-53`, `mnOnline_Label`,
  description `:73-75`). Selecting it opens the existing online submenu with a flag (`sViaTagBattle`) that swaps the
  label/description tables: `LOCAL`, `LAN PLAY`, `DIRECT CONNECT`, `TEAM SELECT`, `MATCHMAKING` (`mnonline.c:25-40`, think
  `:100-190`). Each entry calls `TagAssist_EnterForcedOn` then `TagAssist_ApplyDefaultRules` (`:136-165`). **Every other VS
  entry calls `TagAssist_LeaveTagBattle`** (`mn/mnmain.c:2622-2644`) so a stale flag cannot leak. Labels are free SIS text,
  not new textures (the netcode plan says "v1 labels as SIS text, textures later", upstream `docs/netcode-plan.md` section 2).
- **CSS**: `TagAssist_ConsumeAutoPopulate` is a one-shot true on the first CSS entry after the menu (`tag_assist.c:2373`);
  it opens all four doors paired Red 1+3 / Blue 2+4, Human if a pad is plugged into that port else CPU
  (`mncharsel.c:5729-5780`, online variant uses `pc_net_port_human`, `:5755-5771`). The Green team button is skipped
  (`:2534-2541`). `Z` anywhere on a door's card sets that team's point (`mncharsel.c:3590-3606`,
  `TagAssist_SetExplicitPoint`); default is the lowest port on the team (`tag_assist.c:2392-2416`). The coloured
  **POINT** label is a SIS text object positioned from the door's `team_joint` (`mncharsel.c:3937-3965`). The
  "TEAM BATTLE" banner joint is hidden and a "MeleeVS" title drawn in text (`mncharsel.c:5990-6000`, `sMeleeVsTitle`).
- The one-shot flag matters: it opens the doors once so backing out to rules and returning does not re-stomp choices
  (`tag_assist.h:90-93` doc).

Where this matters for us: this is a template for "a custom CSS variant on the vanilla CSS without new art". We already
have our own "kit" menus (`melee/src/melee/gm/gmfrontend*.c`), so we would not copy their approach.

---

## 6. Rollback and online

### 6.1 How their rollback captures the mod's state: it does not need to

Their rollback is **a whole-memory snapshot** (upstream's, `src/pc/net_snapshot.c:520-600`): the decomp's `.data` and
`.bss` bracketed by a linker script (`src/pc/melee_state.ld`, per-format on PE/ELF/Mach-O), every live `OSAlloc` heap
except the audio heap, plus the RNG seed pointer; a plain `memcpy` per snapshot. The sound machine's TUs are excluded
because the audio thread owns them.

`tag_assist.c` keeps all its state in `static` storage with an `s` prefix (`sTeams`, `sTagBattleOn`, `sFrameCounter`,
`sPortTeamColor`, ..., `:188`, `:527-545`); `CODING_STYLE.md` makes it a rule ("Keep mod state in `static` storage. The
rollback snapshot captures game statics, and a heap allocation would escape it"). Because **GObjs live in the restored
heaps at restored addresses**, the raw `Fighter_GObj*` pointers in `TeamState` stay valid across a restore. That is the
whole reason bench-not-spawn works with rollback: **no spawn or despawn event ever crosses a snapshot.** A savestate
restore simply restores flags, positions, stocks, timers.

### 6.2 What still needed care

- **Determinism inputs.** `CODING_STYLE.md`: gameplay may depend only on synced inputs, synced rules and game state; no
  wall clock, no non-game RNG; never read a local setting live. The Tag Bind setting (which button also calls/tags) is a
  per-port local preference, so it is **pinned into the handshake** (RULES for host, READY for guest) and read from the
  pinned copy, including the remote peer's and each couch partner's (`TagAssist_ExtraBindMask`, `tag_assist.c:190-253`;
  `net_handshake.c:141-170`). A live read caused a real mid-session desync (comment `:141-158`: changing the F1 setting
  took effect locally at once while the peer kept its cached value).
- **Checksum tripwire.** `frame_checksum` folds "who is currently point" and "tags left" per slot
  (`src/pc/net_snapshot.c:290-300`); `CODING_STYLE.md` tells contributors to add any new simulation-affecting mod state
  there. They also log a state ring on desync (`log_state_bits`, `:354-370`). The checksum is a tripwire, not the whole
  state (`:377`, `state_hash` for the full hash).
- **Frame counter.** `sFrameCounter` increments in `TagAssist_Tick` from the scene loop (`gm/gmscene.c:333`), in the
  snapshotted statics, so cooldowns resimulate identically.
- **Pointer lifetime.** `TagAssist_OnReset` clears every cached pointer on reset, match exit and online exit
  (`gmscene.c:421`, `gmvsmode.c:354`, `gmonlinemode.c:500-561`): a `Tick` that dereferenced `team->point` after a scene
  exit crashed in a real run (`gmvsmode.c:342-354`). Statics survive scene changes; the GObjs they point at do not.
- **Spawn/despawn x savestates**: not an issue for the reason in 6.1. The only mod-side lifecycle hazard is new-match
  detection (a changed `port_gobj` pointer means a new match, `:2270-2322`), which a rollback restore does not trigger
  because the pointers are restored too.
- **Sound.** Their tag effect plays a raw AX sound id (`lbAudioAx_80024184(225, ...)`, `:1396-1423`); upstream made sound
  rollback-safe with virtual voice handles (`b1cb7af`, `src/pc/net_sfx.c`). Visual effect spawn (`efLib_Create_Attach_Pos`)
  is just a normal game call inside the sim.

### 6.3 Input delay, prediction, matchmaking, LAN, direct

All inherited from the upstream port (Slippi numbers: delay default 2, window 7, prediction = repeat last input, snapshot
only on predicted frames: `upstream docs/netcode-plan.md` section 1). The mod's additions: 2-machine, 4-fighter
layout; each machine drives its own player on game port `pc_net_game_port(machine, 0)` and an optional **couch partner**
on slot 1 (wire protocol version 10 sends two pads per frame, `src/pc/net.h:30`); the handshake pins the partner and its
bind (`net_handshake.c:158-170`). Matchmaking builds the whole match identically on both machines from the handshake
teams (`gm/gmonlinemode.c:780-830`, ports 1+2 vs 3+4 in matchmaking, 1+3 vs 2+4 in Direct/LAN), with a stage picked from a
shared seed. Matchmaking has its own pool; an owner-run Go **pairing server** (`server/pairing/`) was added beside
upstream's DHT search, with an X25519 session key and UPnP (commits `7411705`, `5515a6f`, `c0edf6c`).
Windows-specific: net.c is built without the game's bitfield layout, so reading `game_speed` hit another field and
"rollback never ran on Windows" until they added a game-side accessor (`204d429`). Two rollback-engine fixes late in
the history (`7666ea6`, `1346c7d`) are about re-running frames and about scene-end handshakes.

Testing: `tools/net_pair_test.py --tag` (full 2v2 two-process harness, requires calls and tags happened, checksums prove
agreement, `--input-delay 1` forces predictions); `MELEE_DEBUG_VS=tag` / `tag2v2` shortcuts skipping the CSS
(`gm/gmvsmode.c:224-259`); `MELEE_NET_SYNCTEST`, record/replay (`net_snapshot.c` header). There are no unit tests for
`tag_assist.c` itself (grep: only `net_pair_test.py`, `test_net_handshake.c`, `test_net_match.c` mention tag).

### 6.4 What this suggests for OUR rollback-safe scripted gameplay

Our rollback is also a snapshot (`melee/pc/platform/gw_snap.c:1-30`: all MEM1, plus game `.data`/`.bss` by walking the
link map, minus an exclusion list; `gw_rollback.c`). The difference is **the Lua VM is not in the snapshot** and "the
engine does not replay their mutations" (`docs/scripting.md:118-135`), so every Lua gameplay write is refused online
(`gs_require_offline`, `melee/pc/platform/gw_script.c:729-734`). Their approach implies:

1. **State that must roll back lives in native statics (or MEM1) of a game-side TU, not in Lua.** TagFighter is exactly
   "gameplay logic as a game-side C module with static state". Our `pc_gameworld_script_game` is already in the snapshot
   list (`gw_snap.c:194-196`), and `gw_script.c` is excluded. A mission/companion/boss runtime written native-side
   (or Lua only issuing **intents** that a native, snapshotted state machine consumes) is the shape that rolls back.
2. **Inputs to gameplay decisions must be synced inputs or pinned rules**, never a live local setting (their desync).
3. **Fold a small hash of the module's state into the per-frame checksum** (point, tags, timer) so a divergence is
   named the frame it happens (`net_snapshot.c:290-300`). We have `gw_RB_GameHash` (`gw_rollback.c`, "the curated
   gameplay hash") as the place to add it.
4. **Avoid spawn and free events in the rollback window** by pre-allocating (bench model). Our `gd.spawn_enemy` creates
   items; items are in the snapshot heaps too, so that is rollback-possible in principle, but the scripting doc says
   enemies are saved with the match while Lua bookkeeping is not (`docs/scripting.md:447-451`).
5. **Clear cached pointers at every scene exit** (their crash twice).

---

## 7. The mod layer as architecture

### 7.1 Hooking

There is a mod directory, but **the "lives almost entirely in `src/melee/mod/`" claim is only true of the logic, not the
footprint.** The mod is 2 files; it is invoked from 14 other game files, each by a one-line call guarded inside the callee:

| Hook | Where (their tree) | Purpose |
|---|---|---|
| per-fighter input frame | `ft/fighter.c:1959` after `Fighter_Spaghetti_8006AD10_Inner1` | call/tag input, benched gating |
| input stripping of the bound button | `ft/fighter.c:1868-1928` | stop X/Y/L/R also being jump/shield |
| per-frame tick | `gm/gmscene.c:333`, after `HSD_GObj_RunProcs` | frame counter, elimination check |
| pointer reset | `gm/gmscene.c:421`, `gm/gmvsmode.c:354`, `gm/gmonlinemode.c:500-561` | stale pointers |
| match-end revert and pkind patch | `gm/gmvsmode.c:321-340`, `gmonlinemode.c:522-550` | results softlock |
| debug entry | `gm/gmvsmode.c:224-259`, `gm/gmboot.c:80-93` | skip CSS |
| menus | `mn/mnmain.c:2622-2644`, `mn/mnonline.c:136-165` | on/off |
| CSS | `mn/mncharsel.c` ~12 sites | auto-populate, Z=point, POINT label, start gate |
| HUD | `if/ifnametag.c` ~20 sites | labels |
| netplay | `pc/net_snapshot.c:290-300`, `pc/net_handshake.c`, `gmonlinemode.c` | checksum, pinned binds, team build |

Plus `configure.py:651-658` adds a `MeleeLib("mod (Tag-team mod)")` with the object marked `Matching` only so the link
includes it ("not Matching in the decomp sense": it deliberately makes `main.dol` differ from retail); the PC CMake build
globs `src/melee/*.c` recursively so it needed no change (commit `1265931`). Hooks were lost once in an upstream merge
because they are line-level edits upstream's history never saw (`1265931`). `CODING_STYLE.md` rules: small hooks only,
logic on the mod side; `TagAssist_` public prefix, `static`/`s` prefix for file state; "Vanilla must stay vanilla": every
hook no-ops when `TagAssist_IsTagBattleOn()` is false.

### 7.2 Keeping vanilla untouched, configuration

The on/off flag `sTagBattleOn` is set only from MeleeVS menu entries and cleared by every other VS entry
(`mnmain.c:2622-2644`); no CSS toggle. Settings: one F1/launcher setting ("Tag Bind", per port). No mod config file; no
data-driven roster.

### 7.3 Testing

As in 6.3: two-process harness with checksum agreement, the debug-VS shortcuts, synctest. No headless logic tests of the
mod. Coding checklist is "build, run `tools/check_style.py`, play a Tag Battle match and a plain match"
(`CODING_STYLE.md`, last section). Most fixes in the history are found by frame-by-frame logging in real matches
(`TagAssist_LogCollisionState` in the early commits), with no harness for the bench logic.

### 7.4 Compared with our approach

| | TagFighter | Ours |
|---|---|---|
| Game code | decomp C compiled **natively** for the host, edited in place (`src/melee/mod/`) | decomp C compiled for **PowerPC then retargeted** to x86 (`melee/pc/tools/gwtool`), memory big-endian; game-side additions in `melee/pc/gameworld/` go through the same retarget |
| Mod unit | C source in the game tree, rebuilt into the exe | Lua scripts (`docs/scripting.md`), Geno profiles and native shims; mods are folders loaded at run time (`_research/vanilla-single-folder-mods-2026-10-03.md`) |
| Added gameplay | hooks into the decomp | Geno engine hooks in `fighter.c` (`Geno_OnFrame` `:1935`, `Geno_FighterReset` `:626`), Lua `gd.*`, LAB |
| Rollback state | statics + heaps, mod uses statics | same (`gw_snap.c`), but Lua is out |

Their mod is a **compile-time fork of the game**; ours is a **run-time extension surface**. So the lessons that transfer
are mechanisms (Sections 1-4) and the rollback discipline (6.4), not the packaging.

---

## 8. Upstream port (999sian/melee-pc) versus ours

Facts from `upstream/docs/architecture.md`, `porting-notes.md`, `README.md` (Status table), `docs/netcode-plan.md`.

| Topic | melee-pc (upstream) | Ours |
|---|---|---|
| Game code | decomp C compiled **natively** with GCC/clang for x86-64/arm64 (`architecture.md` Layers); structs mapping disc data are `DISC_STRUCT` (compiler byte-swaps on access), pointer slots `DISC_PTR` relocated to host addresses; MEM1 mapped at `0x80000000`, exe linked non-PIE with text at `0x10000000` (`architecture.md` Memory map; `porting-notes.md` Data model) | PowerPC-targeted compile, **retargeted** x86 with every memory access byte-swapped, game memory stays big-endian, symbols `gw_`-prefixed (`melee/CLAUDE.md` "The shim boundary") |
| Endianness | disc data big-endian, **runtime structs native little-endian**, with a long list of 64-bit data-model bug classes (8-byte pointers, bitfield order, `bool` clamping) (`porting-notes.md` Bug classes) | one big-endian address space, none of those classes by construction; retarget cost instead |
| Renderer | `extern/aurora` (vendored fork of encounter/aurora): GX command processor to **WebGPU/Dawn** (D3D12, D3D11, Vulkan, Metal), SDL3 window, RmlUi | GX shim to Aurora (`shim_*`, `gw_*`; see `_research/aurora.md`); Windows only |
| Audio | software AX mixer, 5 ms callback, SIMD voice mixer, Master/Music/SFX sliders | shim AX (`shim_ax.c`) |
| Platforms | Windows x86-64/ARM64, Linux, macOS, Android, iOS (partial), browser WebGPU (partial) (README Status) | Windows (Linux for headless/CI, `gw_compat_linux.c`) |
| Launcher / settings | RmlUi launcher (disc pick, SHA-1 Redump verify), F1 overlay with pause, gamepad remap, updater | own launcher (`tools/release/`), console and overlay (`gw_console.cpp`, `gw_overlay.cpp`) |
| Mod loading | **no mod loader**; texture packs (Dolphin format, `tex1_*`), custom music (`.ogg`/`.wav` replaces any streamed track), loose-file overlay in `file_cache.cpp` | `gw_mods.c` mod folders, m-ex runtime, Geno, Lua |
| Netplay | rollback with a whole-memory snapshot, LAN (mDNS), internet direct with friend code, DHT matchmaking, ranked best-of-three with signed records, Slippi `.slp` replay recording (README Status) | rollback and Slippi netcode (`gw_rollback.c`, `gw_slippi_*`, `gw_netplay.c`) |
| Extras we lack | HD texture packs; `.ogg` custom BGM replace; UCF toggle; widescreen with wide-HUD anchoring; PAL disc (experimental); browser build; per-datagram authentication and signed ranked ratings; UPnP; strict-NAT detection; Android/iOS touch | none of these needed except possibly **texture packs** and **custom music** if we want modders to retexture |
| Extras they lack | m-ex, Geno, Lua scripting, LAB, ports, mission system | |

Candidates actually worth having: custom stage music from user files (small, Section 9 row 9), Dolphin-format HD texture
packs (not asked for; skip). Everything else is a platform we do not target.

---

## 9. Ranked takeaways

Sizes: S = under a day, M = a few days, L = a week or more. "Close" = what we already have.

| # | Takeaway | What it would take in our tree | Size | Close to it already | Traps from their history |
|---|---|---|---|---|---|
| 1 | **Reserve (benched) fighters, called and dismissed by script**: pre-launch the mission match with extra slots (CPU), bench them, expose `gd.fighter_bench(port)` / `gd.fighter_call(port, x, y [, move])` | A game-side function in `melee/pc/gameworld/script_game.c` doing the Section 1.1/1.2 sequence (flags, forced `Wait`, floor copy, `mpColl_80043680`, camera box), a Lua binding table entry next to `cpu_mode` in `gw_script.c:5839`, per-frame re-assert of the bench from a hook near `Geno_OnFrame` (`fighter.c:1935`), mission-layer reader in `gw_script_mission.inc` | **M** | `ScriptGame_CpuMode`, `gd.teleport`, `fly_refused`, `MELEE_SCENE` 4-slot launch (`scene-launch.md`) | Clean `Wait` before first freeze (bug #1 in their history); re-assert flags every frame; never write `CollData_X130_Locked`; clear stale input and nudge velocity; camera box `Inactive` or the frame creeps; release grab victims first; slots capped at 4 ports (3 extras) and Ice Climbers use two GObjs; roster fixed at match start |
| 2 | **Fighter enemies and bosses in missions** | Same as 1, plus an "enemy team" and a spawn policy (arena lock, `boss_hold`); deaths: count them (LAB has infinite respawn, `geno_lab_mode.c:127`), promote or end the encounter | **M** (on top of #1) | `gd.boss_hold/release` (`gw_script.c:5843`), `gd.set_damage` ("a boss at zero HP still needs a hit to die", `docs/scripting.md:334`), `gd.cpu_mode`, `gd.cpu_technical` | A benched fighter must be intangible or a stock can be lost frozen; KO/respawn detection by motion-id range, never frame bookkeeping; if the elimination check lives in the per-fighter hook it stops firing when retail freezes a 0-stock fighter |
| 3 | **Companion/ally fighter** (Envoy "companion", co-op ally) | Companion = a CPU fighter on the player's team called/benched by #1 plus a script-driven follow and assist. **Their idle AI does not follow**, so we write follow ourselves: `gd.input(port, spec)` already drives any pad (`docs/scripting.md:315`) and `gd.camera_get`/fighter positions exist | **M** (follow AI is the cost, not the bench) | `gd.input`, `gd.press`, `gd.player()` reads, `gd.cpu_technical` | `CpuKind_5` sentinel collision; a demoted fighter must not read the human's port; dormant Zelda/Sheik and Nana halves are ticked every frame and read real input if their `cpu.kind` allows |
| 4 | **Make scripted gameplay rollback-safe by moving state native** | Put mission, companion and boss state in a snapshotted game-side TU; Lua sends intents; fold a state hash into `gw_RB_GameHash`; pin rule inputs in the handshake. Then lift `gs_require_offline` for those intents only | **L** | `gw_snap.c` already includes `pc_gameworld_script_game`; `gw_RB_GameHash`; hooks skipped during resim (`scripting.md:124`) | Their desync: a local setting read live. Clear pointers on scene exit. Statics survive scene change, GObjs do not |
| 5 | **Fighter-attached label API** (names, counters, "Assist Ready"-style prompts over a fighter) | Two routes. (a) Cheap, pure Lua: project the fighter position through `gd.camera_get` and call `gd.text` (S). (b) Native: reuse the nametag GObjs and rewrite SIS text in place (M), only worthwhile if the HUD must scale and sit exactly like Melee's own | **S** (a) / **M** (b) | `gd.text`, `gd.camera_get`, `gd.hud_visible` | SIS free-and-recreate leaks the buffer and panics within a minute; rewrite in place, only on change; `(` `)` eat the next byte; only a safe character set encodes |
| 6 | **Control hand-off ("tag") between two fighters** | Needed only if the game wants swapping or co-op control. Port-repoint recipe in 2.1 (`x618_player_id`, `Player_SetSlottype`, `cpu.kind`), plus seeding button-edge history | **M** | `gd.input` can already drive a port, so a Lua-only hand-off is possible without touching `x618_player_id`: feed the second fighter's port from the first controller, and zero the one you left (offline only) | Double tag from stale edges; results-screen softlock if slot types are left swapped; pause lookup keys on `player_id`, not `x618_player_id`; do all of it on both halves of Zelda/Sheik and on Nana |
| 7 | **Co-op (two humans, one team)** | Mostly vanilla: Team Battle, two doors, per-fighter stocks, same team colour. The mod's Duo Play is "nothing special" (`tag_assist.c:1739-1741`) | **S-M** mission layer (shared lives, one respawn rule) | `MELEE_SCENE` teams, `gd.player(port)` | Camera with 4 subjects tightens its margin as subjects rise (`af12f88`); inactive boxes for benched or eliminated fighters |
| 8 | **Promotion/revive rule when a lead dies** | Only for team missions: copy the rules, not the code (immediate promotion; stock donation). Not needed for single-player roguelike | **S** | | Promotion must run from an unconditional tick, not a per-fighter hook |
| 9 | Custom-music loader (`.ogg`/`.wav` replacing any streamed track), as a mod feature | New shim reading files into the AX streaming path | **M** | `shim_ax.c` | Upstream decodes whole files to RAM and ignores loop points (README Status) |
| 10 | Their `--tag` two-process checksum harness as a model for ours | Add a "scripted mission run, two processes, hashes equal" CI test to `gw_net_tests.c`/`tools/` once #4 exists | **M** | `gw_net_tests.c`, `MELEE_SYNCTEST` | |

Ordering rationale: 1 is the enabling primitive for 2, 3, 7 and for any "reserve fighter" in a mission. 4 is the
long pole for online play but nothing in the mission plan needs online yet, so it is item 4 even though it is the most
valuable architecturally. 5 is cheap and visible.

---

## 10. Things in their approach that contradict or qualify our plan and spec

1. **"A general spawn / despawn a fighter mid-match" (brief; also implied by Plan section "fighters as enemies/bosses")
   is not what they do, and is not what the evidence supports.** They bench pre-existing slot fighters. They describe an
   earlier mid-match `Fighter_Create` attempt as producing flat/collapsed models. If we want a real spawn we would have
   to do our own load-path work and keep the roster fixed at match start otherwise. The plan's "a boss as a scripted
   fighter" (`docs/PLAN-ENVOY-EDITOR-MISSIONS-2026-10-03.md` around lines 172, 255) is fine only if the boss fighter is
   one of the match's slots.
2. **Slot cap.** The approach caps total fighters at the four ports. Plan line 271 ("solo only for now? ... fighters as
   occasional enemies") and the mission spec's "enemy waves" can use at most three extra fighters, so fighter enemies are
   boss-and-elite-sized, not wave-sized. The seven item-based enemies remain the wave unit.
3. **A companion that "follows" the player (plan section 11, open question) gets nothing from this work.** Their assist is
   a timed cameo, not an escort. `CpuKind_0` is an idle dummy that never follows or attacks.
4. **Benched fighters need to be intangible to avoid stock loss, and must be promoted/handled if the point dies**
   (Section 3). A mission "lives" rule that counts the player's stocks while a companion is benched needs the same
   care: LAB mode's infinite respawn removes the stock problem (`geno_lab_mode.c:127`), but a normal VS-based mission
   would hit the softlock they documented.
5. **"One folder, vanilla disc" (spec) is untouched** by this: nothing in their approach needs different data. But the
   mechanism is C in the game tree, so as a **mod** it would live in our game-side TUs or a Geno native, not a Lua mod.
6. **Online/rollback.** Our statement "Lua gameplay writes are refused online" is the right call given our Lua is out of
   the snapshot; their approach confirms the only safe route is native state. It also shows the cheap alternative:
   **pre-allocated, flag-based** lifecycle (nothing created or freed in the window), which avoids spawn/free rollback
   problems entirely.
7. **No friendly fire or team handling work was needed**; they ride Team Battle. We should check whether our LAB/mission
   launch sets `teams` consistently before relying on it (not verified here).

---

## 11. Not verified (read, not run)

- Nothing was built or executed. No claim here has been observed in a running game, theirs or ours. Their fixes are
  taken from commit messages and in-code comments; whether they hold in practice is their own claim.
- I did not read the decomp's fighter load path, so "all four fighters preload at match start" is inferred from
  "nothing is spawned" plus vanilla behaviour, not read.
- The meaning of `x221E_b1`, `x221E_b2`, `x221F_b1` is not documented by them or the decomp; I do not know which bit
  does what. `x221F_b3` and `x2219_b1` are described in their comments and agree with usage in our `fighter.c`
  (line numbers cited), but I did not read every use in ours.
- I did not check what Melee's team-battle friendly-fire default is in their ruleset, nor the 4-player HUD layout in a
  2v2 (no HUD code was changed; layout is vanilla).
- The CSS art (title text, POINT label) I read as code, not on screen. The roster table's 26 moves were read, not
  exercised.
- Their online layer (net.c, DHT, pairing server in Go, UPnP) I sampled at the places that touch the mod (handshake
  pins, team build, checksum); I did not audit it. `server/pairing` was not read.
- Their open crash (Zelda as both point and assist) is from `ROADMAP.md`; I did not reproduce or locate it.
- The earlier mid-match `Fighter_Create` version is not in the public history I could fetch (the first mod commit I
  could find is `1c468be`/`2240a94` on 2026-09-15, already after the rework); only the code comment records it.
- Upstream comparison used `README.md`, `docs/architecture.md`, `docs/porting-notes.md`, `docs/netcode-plan.md`
  (first 120 lines) only. I did not diff upstream against our tree, nor measure anything.
- Our-side claims (what `gd.input`, `gd.cpu_mode`, `boss_hold` do) are from `docs/scripting.md` and the registration
  tables in `gw_script.c`; I did not run them. Whether `gd.input` can drive a CPU-slot port (not a human pad) is
  **not verified**: `gd.cpu_mode` returns false for a human slot, which suggests the CPU path ignores the pad, so
  takeaway 3 may need a native input route rather than a Lua one.
- Licence reading is mine, from the file text; I am not a lawyer. The repo's top-level `COPYING` is the GPLv3 text; the
  `LICENSE.md` explicitly says it does not apply to `src/melee`.

---

## 12. Credits (owner requirement: always give credit, for ideas as well as code)

No code was copied. Credit is due for ideas, findings and bug history, and must be carried into any doc, release note
or in-game credit that uses them.

| Project | Author / owner | Link | Licence (as stated by them) | What we drew on |
|---|---|---|---|---|
| MeleeVS / melee-pc-TagFighter | Joyastick (GitHub user; repo owner, all 17 PRs) | https://github.com/Joyastick/melee-pc-TagFighter | Three-part `LICENSE.md`: `src/melee`, `src/sysdolphin` (includes the tag mod) not licensed; `src/pc`, `tools`, `platforms`, `cmake`, `.github` GPL-3.0-or-later. Section 0 | The bench/unbench design, bug history, control hand-off, promotion rules, nametag HUD, menu and CSS approach, rollback discipline, pinned-handshake lesson |
| melee-pc | 999sian and "the melee-pc contributors" | https://github.com/999sian/melee-pc | Port code GPL-3.0-or-later; game code unlicensed (same structure) | Whole-memory rollback snapshot design, netcode, architecture comparison (Section 8), SIS and nametag infrastructure the mod builds on |
| doldecomp/melee | the doldecomp contributors | https://github.com/doldecomp/melee | none published | All decomp symbol names and game logic both ports and ours derive from |
| aurora | encounter | https://github.com/encounter/aurora | MIT (per their `LICENSE.md` section 3) | Renderer layer in melee-pc; named only in the comparison |
| Slippi (rollback numbers) | Project Slippi | https://github.com/project-slippi | not checked | Delay 2, window 7, repeat-last-input prediction, as adopted by melee-pc's netcode plan; named only |

Per-takeaway attribution (Section 9 rows):

| # | Idea | Whose work |
|---|---|---|
| 1 | Reserve fighters benched and called, with the bench/unbench recipe and its traps | Joyastick (MeleeVS) |
| 2 | Fighter enemies/bosses via the same bench | Derived by us from Joyastick's mechanism; `boss_hold` etc. are ours |
| 3 | Companion ally; the finding that their idle AI does not follow | Joyastick's `CpuKind_0` idle-cameo finding; follow AI is our own work |
| 4 | Native snapshotted state, pinned inputs, checksum fold | Joyastick for the mod-state discipline; 999sian for the whole-memory snapshot |
| 5 | Fighter-attached labels via SIS in-place rewrite | Joyastick (leak and escape-byte findings) |
| 6 | Control hand-off recipe | Joyastick |
| 7 | Co-op via Team Battle | Joyastick (Duo Play) |
| 8 | Promotion/revive rules | Joyastick |
| 9 | Custom music loader | 999sian |
| 10 | Two-process checksum harness | 999sian and Joyastick (`net_pair_test.py --tag`) |

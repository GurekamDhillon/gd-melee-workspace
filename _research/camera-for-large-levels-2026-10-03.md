# Camera for large levels and mazes (spike, 2026-10-03)

Read-only research plus throwaway probes. Probe mod, data, CSVs and screenshots: `_build/spikes/camera-1p/`
(`mods/cam/scripts/main.lua`, `data/cam_main/rec_*.csv|log_*.txt|*.png`, `an.py`). Game paths are under `melee/src/melee/`.
VERIFIED = read the code or measured it in the game (vanilla disc, port 1 real pad input via `gd.input` unless a row says
"fly cursor"). INFERRED = deduced. Numbers are world units; "eye z" is the camera distance from the z=0 plane.

## 1. Answer in short

1. Adventure's side-scrolling stages use the ordinary STANDARD camera. The stage code does not move the camera: every frame
   it moves the stage "origin" (`Ground_801C38BC`) to the player, and camera bounds and blast zones are stored relative to
   that origin. The camera is then clamped into a small window that travels with the player. The versus camera on a big level
   is the same camera with a fixed window, which is why it swung and looked wrong.
2. Two things made the maze/vertical spike levels look bad, both measured: (a) YAW. Camera yaw/pitch are computed from the
   subject's distance to the origin, clamped at +-17.5 deg yaw. In the maze at the far end the eye was 41 units left of the
   interest (`eye.x - interest.x = -41` at x=470, origin 0). (b) ZOOM follows the subject box with a stage-supplied minimum
   distance; we inherit FD's, so framing is unrelated to chunk size.
3. The Adventure C-stick is the 1P camera zoom (`Camera_8002B0E0`, camera.c:1577), and the same gate (`gm_IsCurrently1PMode_inline`)
   ZEROES the fighter's C-stick (`ft/fighter.c:2241`). It only exists in GM_CLASSIC / GM_ADVENTURE / GM_ALLSTAR. Our modes
   (LAB `0x2F`, VS, Target Test, Training) never enter it: C-stick = attacks, no zoom. Measured both ways.
4. Lua can move the origin and the camera rectangle per frame (`gd.stage_set_origin`, `gd.stage_set_camera_bounds`), which is
   the Adventure technique, and can detach and drive the camera itself. Lua cannot set min/max zoom distance, fov, tilt,
   look-ahead scale, or the fighter camera box. That is a small engine change (section 7).
5. Icicle Mountain uses CAMERA_FIXED (eye (0,51,417), fov 21): the world scrolls past a fixed camera. Data-driven by the stage file.

## 2. The general camera model (VERIFIED, code)

Modes (`cm/forward.h:6`): STANDARD 0, PAUSE 1, TRAINING_MENU 2, CLEAR 3 (stage-clear zoom), FIXED 4, FREE 5, BOSS_INTRO 6,
DEBUG_FOLLOW 7, DEBUG_FREE 8. Per-mode update table `cm_803BCB18` (camera.c:130). The mode is set by
`Ground_EnableMatchCamera` (`gr/ground.c:4006`): `param->x4C_fixed_cam` ? FIXED : STANDARD. Other setters: `Camera_8002F7AC`
(CLEAR, from `gm/gmregclear.c:1073`), `Camera_SetUpPauseCamera` (camera.c:3699), boss intro.

**STANDARD update** (`Camera_8002B3D4`, camera.c:1759), each frame:
1. Subjects (`CmSubject`, `cm/types.h:19`): each fighter owns one "camera box" (`fp->x890_cameraBox`). Box = anchor `pos`
   (fighter pos + Y offset from fighter data `ft_data->x3C`), horizontal extents `ext.h.x` (left) and `ext.h.y` (right), vertical
   `ext.v.x/y`. `ftCamera_UpdateCameraBox` (`ft/ftcamera.c:50`) makes the FORWARD extent `forward * Stage_GetCamFixedZoom()`:
   that is the look-ahead, in the facing direction (not velocity). Extents ease 0.5/frame (`Camera_800293E0`).
   Subjects outside the camera rectangle are dropped (`Camera_8002928C`, camera.c:455; Auto state locks out 600 frames).
2. `Camera_8002958C` (camera.c:577) builds the target rectangle: the min/max of every subject's four box points, each scaled by
   `tracking_weight(n_subjects) * Stage_GetCamTrackRatio()` with weights {1:1.5, 2:1.32, 3:1.16, 4+:1.0} (`cm_803BCB9C`), each
   point clamped into the camera bounds. No subjects: origin +-40.
3. `Camera_80029BC4`/`80029CF8` (camera.c:862/919): distance = max(height/tan(fov), width/(aspect*tan(fov))), clamped to
   `[Stage_GetCamZoomRate(), Stage_GetCamMaxDepth()]` (min and max distance). Pitch/yaw: pitch =
   `-(y_centre_rel_origin + (-30)) * Stage_GetCamInfoX24()` clamped to [-7 deg, +5 deg]; yaw = `-(x_centre_rel_origin) *
   Stage_GetCamInfoX20()` clamped to +-17.5 deg, plus `Stage_GetCamPanAngleRadians()`. (Clamps are `cm_803BCCA0` data read from the
   original DOL: 5, -7, 17.5, -17.5, -30.)
4. Smoothing: interest moves `follow_speed * Stage_GetCamTrackSmooth()` per frame toward target (follow_speed 0.05 for spread
   <120, 0.10 for spread >900); eye moves 0.15 * smooth (camera.c:791-903).
5. `Camera_8002A768` (camera.c:1257) is the clamp. It projects the four frustum corners onto z=0 and shifts position and
   interest so the visible footprint lies inside the CAMERA bounds rectangle (centres on the rectangle if the view is bigger).
   Blast zones are not used (`arg1` is always 0).
6. `Camera_8002B0E0` (camera.c:1577): the 1P zoom (section 5). `Camera_80030AE0(true)` makes the camera ignore P1 when its
   |z|>30 (pipes).

**Stage data** (`GroundParam` -> `stage_info.cam_info`, `Ground_801C0800`, ground.c:814): bounds L/R/T/B (from map markers,
`Ground_801C39C0`), origin `cam_x_offset/cam_y_offset` (`Ground_801C38BC`), tilt x8, pan x14, yaw gain x1C, pitch gain x18
(`Ground_801C38D0`), min distance xC and max depth x10 (`Ground_801C38EC`), track smooth x28, track ratio x20, fixed zoom x24,
pause-camera params, fixed-camera pos/fov/angles x50-x64 and flag x4C. Defaults (`Ground_801BFFB0`, ground.c:418): bounds
+-170 x 120/-60, tilt 30, pan -10, gains 0.2, min dist 82, max depth 1000. Blast zones are separate and also add the origin
(`gr/stage.c:52-130`).

**Pause camera**: `Camera_SetUpPauseCamera`; while paused `Camera_8002C1A8` (camera.c:2114) reads stick, C-stick (orbit), D-pad,
X/Y (zoom) from `HSD_PadCopyStatus`. Runs only while paused, so it cannot conflict with attacks.

## 3. Per-mode table (measured, vanilla disc, Fox via `mode=adventure;p1=fox;step=N;difficulty=0`)

Step N = stage index of Adventure (0 Mushroom Kingdom, 1 Kongo, 2 Underground Maze, 3 Brinstar incl. escape, 7 F-Zero, 9 Icicle).
`fov` is what `gd.camera_get()` reports. Window = camera-bounds rectangle read from `gd.stage_bounds()`.

| Stage (GrKind) | Mode | fov / eye z | Window (w x h), centred on origin | Origin drive | Lead (interest - player x, standing) | Source |
|---|---|---|---|---|---|---|
| Versus FD (LAB) | standard | 30 / 145 at rest, 90-145 moving | 340 x 194, fixed | none | 27 (bounds clip it) | VERIFIED `rec_fd` |
| Mushroom Kingdom (`KinokoRoute` 31) | standard | 25 / 300.0 (never moves) | 249 x 177 (stage markers x 1.5, `grkinokoroute.c:230`) | P1 pos, 10-unit leash, Y clamp [20,250]*scale; 60-frame tween at the Yoshi lock | +-26.4, 5..10 while running | VERIFIED `rec_adv0*` |
| Underground Maze (`ShrineRoute` 32) | standard | 15 / 306.8 | 167 x 97 | P1 pos (`grshrineroute.c:731-750`), hold on hurt/dead, 60-frame tween | +-27, 5 while running | VERIFIED `rec_adv2` |
| Brinstar escape (`ZebesRoute` 33) | standard | 20 / 220 (209-220) | 150 x 180 | x fixed 0, y = max(P1 y, -50) (`grzebesroute.c:187`) | +-27 (x clamps in 150 window) | VERIFIED `rec_adv3` (climb driven with fly cursor) |
| F-Zero GP (`BigBlueRoute` 34) | standard | 15 / 500.0 | 207 x 181 | P1 pos clamped x>=-1140, y in [20,250] (`grbigblueroute.c:1180`) | 27 standing, ~10 at 1.4 u/f | VERIFIED `rec_adv7` |
| Icicle Mountain (`Icemt` 22) | **fixed** | 21 / 417, eye (0,51), interest (0,7.8) | 175 x 154 | stage scrolls its own geometry | none: camera static, fighters can leave view (x to +-134) | VERIFIED `rec_adv9` |
| Brinstar fight (8) | standard | 29 (CLEAR after KO) / 26.6 clear | 227 x 183 | none | - | VERIFIED `rec_adv3` start |
| Target Test (TFox 46) | standard | 10 / 800 | 342 x 355 | none | 19.5 | VERIFIED `rec_tt` |
| Home-Run | standard | - | camera right bound x3 (`grhomerun.c:107`); P1 box `force_inactive` once the bag flies | - | - | code only |
| All-Star rest area (`Heal`) | standard | - | top blast x2 only (`grheal.c:152`) | - | - | code only |
| Events | standard | per stage | per stage | - | - | not looked at |

Adventure framing facts (VERIFIED): the zoom is the stage's MIN distance (z constant while moving: 300.0, 306.8, 500.0, 220),
so all four route stages are telephoto (fov 15-25) at a fixed distance. The window is only ~25-125 units larger than the view, so
the camera is effectively locked to the player; lead is limited by that slack (window half-width minus view half-width) minus the
10-unit origin leash. Turning: interest goes from +27 to -10 over ~45 frames (RunL turn in `rec_adv2`: +35 overshoot while the
player is already moving, then eases). Falling (maze, vy~-4): interest sits 15 above the player. Vertical movement is handled by the
same window: the origin y follows the player, so no special vertical code. Blast zones sit 26-43 (sides/top) and 56-74
(bottom) units outside the camera window at the first section of Mushroom Kingdom; all move with the origin.
Effective on-screen scale: the reported `fov` understates the real vertical field by about 2x in the port at 16:9 (a 100-unit
room at z=186.6, fov 30 filled half the screenshot height); INFERRED, calibrate before using fov for sizing.

## 4. Scripted camera (native) as shipped

`gw_script.c:856-1000`, `cm/camera.c:4442-4720`. VERIFIED by reading:
- `camera_set/move/path/follow/shake/attach/detach/bounds`: detach the camera; the normal camera keeps updating underneath
  (`cm_script_update` writes `transform` from `cm_script.pose`). `camera_follow` is a fixed-offset follow (no look-ahead, no clamp,
  no smoothing). `camera_bounds(true)` only lifts the clamp and extends the far plane.
- `gd.stage_set_origin(x,y,{frames=N})` (`gw_script_arena.inc:41`) and `gd.stage_set_camera_bounds/blast_bounds` (origin-relative,
  `script_arena.inc:137`) feed the same `Stage_Get*Offset` the native stages use. That is the Adventure mechanism. Each call
  runs `gs_rw_branch()` (forks the LAB rewind timeline) and `gw_log` (a log line per call): measured 0.016 ms per origin call,
  318 calls in 228 frames; 208 log lines.
- Nothing writes `stage_info.cam_info` min distance, max depth, fov source, tilt/pan, gains, track ratio/smooth, fixed zoom,
  fixed-cam flag or position. (`grep cam_zoom_rate` in `melee/pc`: no script hook.)

## 5. The C-stick (VERIFIED code and game)

- Camera zoom: `Camera_8002B0E0` (camera.c:1577), called from the STANDARD update. Gate: `gm_IsCurrently1PMode_inline()`
  (`gm/gmvs.c:336`: GM_CLASSIC, GM_ADVENTURE, GM_ALLSTAR) and `x2C0>0` and `!gm_CStickSmashTargetTest` and not m-ex flag
  `enable_c_stick_always_1p_camera`. Reads only P1's C-stick Y (`nml_subStickY`), only when |y| >= 0.85. Effect: `x2BC` scale
  (1.0..0.14) shrinks by 0.02 per frame, pulling interest to the fighter and the eye to 14% of its distance
  (`Camera_8002B1F8`). Measured: z 307 -> 43 in 44 frames; stays there ~1200 frames after release, then relaxes 0.004/frame; C-stick
  down zooms back. It is zoom only; there is no C-stick pan in gameplay.
- Fighter input: `Fighter_Spaghetti_8006AD10` (`ft/fighter.c:2241`): human C-stick is copied to `input.cstick` only when
  `!1P-mode || gm_CStickSmashTargetTest || m-ex flags`; else zeroed. CPU path similar (2206).
- Measured: Adventure (Mushroom, Maze, Brinstar) `cx=127` for 30 frames: no attack action (only idle 14); `cy=127`: zoom. LAB/FD and
  Target Test: `cx=127` -> action 60, up 63, down 64 (smash attacks), eye z unchanged.
- Existing escape hatches inside 1P modes (not wanted for us): hold L+R+START toggles `gm_CStickSmashTargetTest`
  (`fighter.c:2368`); `MELEE_MEX=enable_c_stick_1p` makes `gm_IsCurrently1PMode_inline` false globally.

**Rule for our modes:** never run the level mode under `GM_CLASSIC`, `GM_ADVENTURE` or `GM_ALLSTAR` (the LAB mode `0x2F`, VS,
and Target Test are safe); do not call `Camera_8002B0E0`'s gate true by any other route; if a mode must reuse an Adventure scene,
set `gm_CStickSmashTargetTest = true` for its whole lifetime (and still drop zoom: `x2BC` stays 1.0 with it set). Pause camera
C-stick orbit is paused-only and harmless. Verify in game: with `gd.input(1,{cx=127},3)` per frame expect an attack action
(Falco 60) and a constant `camera_get().eye.z`; with `cy=127` held 100 frames expect no change of eye z.

## 6. Prototypes (maze 4x4 of 120x100; real walking east through the row-0 doors, 228 frames; Lua only)

All numbers `rec_mz*.csv`; screenshots `data/cam_main/maze_*.png` (2560x1440).
| Variant | What it does | Result |
|---|---|---|
| native (control) | whole-maze bounds, FD zoom | eye.x - interest.x = -41 at x=470 (yaw), eye z 142 -> 127; screenshots: perspective-skewed floor, only black void and floor ledges visible, no room framing. |
| `rect` (Adventure technique: origin to room centre with 30-frame tween, camera rect = room 120x100) | per-room native clamp | origin moves per room (rect L0..R120, T100 B0 verified); the view (~105 z) is wider than a 120-wide room so void shows on the left in `maze_rect140.png`; can't tighten because min distance is not settable. The fighter also fell out of the room at one door (probe timing, not camera). |
| `follow` (origin chases player every frame, leash 10, window 250x180) | what Adventure does, from Lua | yaw gone: eye.x - interest.x -4.8 (was -41); eye z 144 -> 105 as view tracks; cost 0.016 ms/call. `maze_follow140.png`: square floor, fighter at the bottom edge of frame and black void below the room because my window (180) is taller than the chunk (100) and the origin y clamp was 90. Needs window = about chunk size and bottom margin. |
| `lua` (detached, `camera_set` per frame: single subject, look-ahead 14 + 10*vx, distance from room height, clamp footprint into room, k 0.10/0.07/0.06) | full control | eye z 144 -> 187 (room-height fit), view centred on the room when wider (int - px -52 at far end); `maze_lua140.png` shows the whole room wall with the fighter at the bottom: the vertical fit was too wide, because the reported fov understates the real field by about 2x (see section 3); room walls then show void below the chunk. Shows the approach works but must be calibrated with real fov/aspect. |
Not obtained: the vertical-storey fly-climb produced no motion (fly target not reached), and the maze shaft phase was contaminated
by fixture falls; do not use those rows. The Brinstar climb was driven by the debug fly cursor (labelled FIXTURE), not walking.

## 7. Recommended design

Common: standard camera, single subject, no custom per-fighter box edits; C-stick untouched (stay out of the 1P modes).

(a) Long scrolling hand-built levels: Adventure model. Origin follows P1 each frame with a 10-unit leash (clamped to the
level's first/last section), camera window about 250 x 180 (view slack ~60 beyond the view each side gives the +-27 look-ahead),
min distance chosen per level (300 at fov 25 is Adventure's), max depth = min distance (fixed zoom), blast bounds relative.
Lua now: `stage_set_origin` per frame + `stage_set_camera_bounds` once (0.016 ms/call; remove the log spam).
Engine: add `gd.camera_params{min_dist, max_depth, fov?, fixed_zoom, track_smooth, track_ratio, tilt, pan, yaw_gain, pitch_gain}`
that writes `stage_info.cam_info` (`gr/ground.c:2689-2740`, S), restoring on unload; set yaw/pitch gains 0 to remove skew.
(b) Enclosed maze chunks: window = chunk rectangle (+ small margin) so walls never show void, origin tweened (30-60 frames) to the
chunk centre on door crossing (the shrine-route pattern), min distance = the distance at which the view equals the chunk. Needs the
same `camera_params` (min_dist/max_depth) because the min distance cannot be set from Lua (S). Alternative with no engine work:
the `lua` prototype, once calibrated for the real fov/aspect (Lua, today, but loses native smoothing/clamp/off-screen handling).
(c) Tall vertical sections: Brinstar-escape pattern: x locked (origin.x fixed), origin.y = player y with the 10-unit leash,
window 150 x 180, min distance 220 (fov 20). Lua today (same two calls); mind `Camera_80030AE0`-like Z gating is only needed for
pipes. Falling look-ahead is automatic (interest +15 above while falling). Fixed-camera Icicle style is an alternative for
auto-scroll sections: `Camera_SetModeToFixed` plus fixed pos/fov (`Stage_80224CAC`), needs an engine hook (M).
Engine sizing: `camera_params` S (ground.c setters exist); expose fixed-camera mode/pos S-M; remove `gw_log` and `gs_rw_branch` per
call for origin/bounds S; true per-chunk rectangles with data-driven tween M; per-fighter camera box size/look-ahead scale M
(`ftCamera_UpdateCameraBox`).

Open: fov reporting vs real field (calibrate); measured constants for `cm_803BCCA0` come from the original DOL (not committed).
Sandboxes: cam-fd2, cam-adv0a, cam-adv0b, cam-adv2a, cam-adv3a, cam-adv3b, cam-adv7a, cam-adv9a, cam-tt1, cam-mzn1, cam-mzr1,
cam-mzl1, cam-vt1, cam-mzf1.

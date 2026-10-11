"""Melee animation rows -> XV2 source clips (damage, down, tech, capture, thrown, items, misc), 2026-10-08.

Each entry: row -> (source clip name, start frame, Melee frames, loop, extra). Frames follow Melee's own row lengths
(Mario/Falcon conventions). 'hold' holds that source frame; 'tf' scales source time; 'note' says why. Nothing here is
a silent placeholder: a reused clip is an explicit choice, recorded in FIDELITY.md (tools/fidelity.py).
"""

# (source, start, frames, loop, extra)
H, B, L = 'CMN_DMG_HEAD', 'CMN_DMG_BODY', 'CMN_DMG_LEG'
ROWS = {
    # hit reactions by hit height (Hi = head, N = body, Lw = legs), severity 1 light / 2 heavy / 3 stagger
    'DamageHi1': (H + '_L_F', 0, 20, False, {}), 'DamageHi2': (H + '_H_F', 0, 26, False, {}),
    'DamageHi3': ('CMN_DMG_YOROKE_HEAD_F', 0, 34, False, {}),
    'DamageN1': (B + '_L_F', 0, 20, False, {}), 'DamageN2': (B + '_H_F', 0, 26, False, {}),
    'DamageN3': ('CMN_DMG_YOROKE_BODY_F', 0, 40, False, {'tf': 1.4}),
    'DamageLw1': (L + '_L_F', 0, 20, False, {}), 'DamageLw2': (L + '_H_F', 0, 26, False, {}),
    'DamageLw3': ('CMN_DMG_YOROKE_LEG_F', 0, 34, False, {}),
    'DamageAir1': ('CMN_DMG_AIR_F', 0, 20, False, {}), 'DamageAir2': ('CMN_DMG_AIR_F_L', 0, 24, False, {}),
    'DamageAir3': ('CMN_DMG_AIR_SPIN_L', 0, 30, False, {}),
    # launched: by launch direction
    'DamageFlyHi': ('CMN_DMG_UP_F', 0, 40, False, {}), 'DamageFlyN': ('CMN_DMG_BLOW_H_F', 0, 36, False, {}),
    'DamageFlyLw': ('CMN_DMG_DIVE_F', 0, 31, False, {}), 'DamageFlyTop': ('CMN_DMG_UP_BODY_F', 0, 40, False, {}),
    'DamageFlyRoll': ('CMN_DMG_BLOW_SPIN', 0, 60, True, {}), 'DamageFall': ('CMN_DMG_TUMBLE_F', 0, 69, True, {}),
    'DamageElec': ('CMN_DMG_ELECTRIC', 0, 31, True, {}),
    'DamageScrew': ('CMN_DMG_BLOW_SPIN', 0, 40, False, {}), 'DamageScrewAir': ('CMN_DMG_BLOW_SPIN', 0, 40, False, {}),
    'DamageSong': ('CMN_DMG_SLEEP', 0, 30, False, {}), 'DamageSongWait': ('CMN_DMG_SLEEP_S', 0, 60, True, {}),
    'DamageSongRv': ('CMN_BAS_RECOVER', 0, 40, False, {}), 'DamageBind': ('CMN_DMG_KANASHIBARI', 0, 60, True, {}),
    'DamageIce': ('CMN_DMG_KANASHIBARI', 0, 2, False, {'hold': 20}), 'DamageIceJump': ('CMN_DMG_KANASHIBARI', 0, 2, False, {'hold': 20}),
    # down (U = face up / AOMUKE, D = face down / UTSUBUSE)
    'DownBoundU': ('CMN_DMG_DOWN_BOUND_AOMUKE', 0, 26, False, {'tf': 2.2}), 'DownBoundD': ('CMN_DMG_DOWN_BOUND_UTSUBUSE', 0, 26, False, {'tf': 2.2}),
    'DownWaitU': ('CMN_BAS_DOWN_AOMUKE', 0, 60, True, {}), 'DownWaitD': ('CMN_BAS_DOWN_UTSUBUSE', 0, 60, True, {}),   # phase 3: the ground variants (no _S sky clips)
    'DownDamageU': ('CMN_DMG_DOWN_BOUND_AOMUKE_H', 0, 20, False, {'tf': 2.5}), 'DownDamageD': ('CMN_DMG_DOWN_BOUND_UTSUBUSE_H', 0, 20, False, {'tf': 2.5}),
    'DownSpotU': ('CMN_DMG_DOWN_BOUND_AOMUKE_H', 0, 20, False, {'tf': 2.5}), 'DownSpotD': ('CMN_DMG_DOWN_BOUND_UTSUBUSE_H', 0, 20, False, {'tf': 2.5}),
    'DownStandU': ('CMN_BAS_DOWN_STAND_AOMUKE', 0, 30, False, {'tf': 1.3}), 'DownStandD': ('CMN_BAS_DOWN_STAND_UTSUBUSE', 0, 30, False, {'tf': 1.3}),
    'DownFowardU': ('CMN_BAS_UKEMI_F', 0, 35, False, {'tf': 1.7}), 'DownFowardD': ('CMN_BAS_UKEMI_F', 0, 35, False, {'tf': 1.7}),
    'DownBackU': ('CMN_BAS_UKEMI_B', 0, 35, False, {'tf': 2.2}), 'DownBackD': ('CMN_BAS_UKEMI_B', 0, 35, False, {'tf': 2.2}),
    'DownAttackU': ('GOK_ATC_012', 0, 50, False, {'tf': .8, 'note': 'AUTHORED: XV2 has no getup attack; the low split sweep from the ground'}),
    'DownAttackD': ('GOK_ATC_012', 0, 50, False, {'tf': .8, 'note': 'AUTHORED: XV2 has no getup attack; the low split sweep from the ground'}),
    'DownReflect': ('CMN_DMG_DOWN_BOUND_AOMUKE', 0, 26, False, {'tf': 2.2}),
    # tech
    'Passive': ('CMN_BAS_UKEMI_N', 0, 26, False, {'tf': 1.4}), 'PassiveStandF': ('CMN_BAS_UKEMI_F', 0, 40, False, {'tf': 1.5}),
    'PassiveStandB': ('CMN_BAS_UKEMI_B', 0, 40, False, {'tf': 2.0}), 'PassiveWall': ('CMN_DMG_WALL_BOUND_F', 0, 20, False, {'tf': 2.3}),
    'PassiveWallJump': ('GOK_BAS_JUMP_BACK_00', 0, 40, False, {'tf': .47}), 'PassiveCeil': ('CMN_BAS_UKEMI_U', 0, 30, False, {'tf': 1.5}),
    # shield break
    'ShieldBreakFly': ('CMN_DMG_UP_F', 0, 40, False, {}), 'ShieldBreakFall': ('CMN_DMG_TUMBLE_F', 0, 69, True, {}),
    'ShieldBreakDownU': ('CMN_DMG_DOWN_BOUND_AOMUKE', 0, 26, False, {'tf': 2.2}), 'ShieldBreakDownD': ('CMN_DMG_DOWN_BOUND_UTSUBUSE', 0, 26, False, {'tf': 2.2}),
    'ShieldBreakStandU': ('CMN_BAS_DOWN_STAND_AOMUKE', 0, 30, False, {'tf': 1.3}), 'ShieldBreakStandD': ('CMN_BAS_DOWN_STAND_UTSUBUSE', 0, 30, False, {'tf': 1.3}),
    'Furafura': ('GOK_BAS_STUN_02', 0, 73, True, {}),
    # being grabbed / thrown: XV2's victim clips (CMN_NAG_*) launch the body far off with root motion, so the held
    # poses are its damage flinches held (HEAD_L_F f6 = choked/held, BLOW_H_F f4 = braced while being thrown)
    'CapturePulledHi': (H + '_L_F', 0, 20, False, {'tf': .35}), 'CapturePulledLw': (H + '_L_F', 0, 20, False, {'tf': .35}),
    'CaptureWaitHi': (H + '_L_F', 0, 30, True, {'hold': 6}), 'CaptureWaitLw': (H + '_L_F', 0, 30, True, {'hold': 6}),
    'CaptureDamageHi': (H + '_H_F', 0, 14, False, {'tf': 1.5}), 'CaptureDamageLw': (H + '_H_F', 0, 14, False, {'tf': 1.5}),
    'CaptureCut': ('CMN_BAS_HAJIKI_B_00', 0, 30, False, {}), 'CaptureJump': ('GOK_BAS_JUMP_FRONT_00', 0, 50, False, {'tf': .38}),
    'ThrownF': ('CMN_DMG_BLOW_H_F', 0, 60, True, {'hold': 4}), 'ThrownB': ('CMN_DMG_BLOW_H_B', 0, 60, True, {'hold': 4}),
    'ThrownHi': ('CMN_DMG_UP_F', 0, 60, True, {'hold': 4}), 'ThrownLw': ('CMN_DMG_DOWN_BOUND_AOMUKE', 0, 60, True, {'hold': 4}),
    'ThrownlwWomen': ('CMN_DMG_DOWN_BOUND_AOMUKE', 0, 60, True, {'hold': 4}),
    'ThrownFF': ('CMN_DMG_BLOW_H_F', 0, 60, True, {'hold': 4}), 'ThrownFB': ('CMN_DMG_BLOW_H_B', 0, 60, True, {'hold': 4}),
    'ThrownFHi': ('CMN_DMG_UP_F', 0, 60, True, {'hold': 4}), 'ThrownFLw': ('CMN_DMG_DOWN_BOUND_AOMUKE', 0, 60, True, {'hold': 4}),
    # his own grab and throws: GOK_NAG_TSUKAMI is the XV2 grab (BAC 600), GNY_NAG_A the XV2 throw (BAC 601)
    'CatchPull': ('GOK_NAG_TSUKAMI', 8, 4, False, {'note': 'source crop: the grab connecting (XV2 BAC 600 f8-11), Melee-short pull'}),
    'CatchAttack': ('GOK_NAG_TSUKAMI', 22, 24, False, {'note': 'source crop: the held grab (f22-45) as the pummel, 24 frames like Mario'}),
    'ThrowF': ('GNY_NAG_A', 16, 30, False, {'note': 'source crop: XV2 throw (BAC 601) lift-and-toss f16-45 while grounded'}),
    'ThrowB': ('GNY_NAG_A', 16, 38, False, {'yaw': -180, 'note': 'source crop + authored turn: the XV2 toss turned 180 to throw behind'}),
    'ThrowHi': ('GOK_ATC_004', 5, 30, False, {'note': 'AUTHORED choice: XV2 has one throw; the uppercut launches up'}),
    'ThrowLw': ('GOK_ATC_012', 0, 30, False, {'note': 'AUTHORED choice: XV2 has one throw; the low split sweep slams down'}),
    'CatchCut': ('CMN_BAS_HAJIKI_B_00', 0, 30, False, {}),
    # misc
    'Ottotto': ('CMN_DMG_YOROKE_BODY_F', 0, 14, False, {'tf': 2.}), 'OttottoWait': ('CMN_DMG_YOROKE_BODY_F', 20, 40, True, {}),
    'MissFoot': ('CMN_DMG_KUZURE', 0, 30, False, {}),
    'Rebound': ('CMN_BAS_HAJIKI_F_00', 0, 38, False, {}), 'ReboundStop': ('CMN_BAS_HAJIKI_F_01', 0, 31, False, {}),
    'StopWall': ('CMN_DMG_WALL_BOUND_F', 0, 20, False, {'tf': 2.3}), 'StopCeil': ('CMN_DMG_WALL_BOUND_B', 0, 6, False, {'tf': 7.}),
    'FlyReflectWall': ('CMN_DMG_WALL_BOUND_B', 0, 20, False, {'tf': 2.3}), 'FlyReflectCeil': ('CMN_DMG_WALL_BOUND_F', 0, 20, False, {'tf': 2.3}),
    'EscapeAir': ('GOK_BAS_STEP_L_S', 0, 30, False, {'tf': 1.5}),
    'DeadUpStar': ('CMN_DMG_BLOW_SPIN', 0, 60, True, {}), 'DeadUpFall': ('CMN_DMG_TUMBLE_F', 0, 69, True, {}),
    'DeadUpFallHitCamera': ('CMN_DMG_BLOW_H_F', 0, 36, False, {}), 'DeadUpFallHitCameraFlat': ('CMN_DMG_BLOW_H_F', 0, 36, False, {}),
    'Sleep': ('GOK_BAS_STAND', 0, 100, True, {'note': 'off screen between stocks'}),
    'Rebirth': ('GOK_BAS_STAND', 0, 100, True, {}), 'RebirthWait': ('GOK_BAS_STAND', 0, 100, True, {}),
    'AppealSR': ('CMN_BAS_HIRAMEKI', 0, 60, False, {'note': 'AUTHORED choice: XV2 lobby gesture as the taunt'}),
    'AppealSL': ('CMN_BAS_HIRAMEKI', 0, 60, False, {'note': 'AUTHORED choice: XV2 lobby gesture as the taunt'}),
    'GuardSetOff': ('GOK_GRD_L', 0, 16, False, {}),
    # Melee items (an XV2 fighter has none): Goku's own motions for the same action
    'LightGet': ('CMN_BAS_ITM', 0, 8, False, {'tf': 2.5}), 'HeavyGet': ('CMN_BAS_ITM', 0, 30, False, {}),
    'LiftWait': ('GOK_GRD_KAMAE', 0, 60, True, {}), 'LiftWalk1': ('GOK_BAS_WALK', 0, 70, True, {}),
    'LiftWalk2': ('GOK_BAS_WALK', 0, 70, True, {}), 'LiftTurn': ('GOK_BAS_STAND', 0, 12, False, {'hold': 0, 'yaw': -180}),
    'ShoulderedWait': ('GNY_NAG_A', 0, 30, True, {'hold': 8}), 'ShoulderedWalkSlow': ('GNY_NAG_A', 0, 30, True, {'hold': 8}),
    'ShoulderedWalkMiddle': ('GNY_NAG_A', 0, 30, True, {'hold': 8}), 'ShoulderedWalkFast': ('GNY_NAG_A', 0, 30, True, {'hold': 8}),
    'ShoulderedTurn': ('GNY_NAG_A', 0, 12, False, {'hold': 8}),
    'ItemParasolOpen': ('GOK_BAS_BUKUU_DOWN', 0, 20, False, {}), 'ItemParasolFall': ('GOK_BAS_BUKUU_DOWN', 0, 50, True, {}),
    'ItemParasolFallSpecial': ('GOK_BAS_BUKUU_DOWN', 0, 50, True, {}), 'ItemParasolDamageFall': ('CMN_DMG_TUMBLE_F', 0, 69, True, {}),
    'BarrelWait': ('GNY_NAG_A', 0, 30, True, {'hold': 8}), 'Barrel': ('CMN_DMG_BLOW_SPIN', 0, 40, False, {}),
    'Bury': ('GOK_BAS_JUMP', 50, 7, False, {}), 'BuryWait': ('GOK_BAS_JUMP', 56, 30, True, {'hold': 56}),
    'BuryJump': ('GOK_BAS_JUMP_FRONT_00', 0, 19, False, {}),
    'WarpStarJump': ('GOK_BAS_JUMP_FRONT_00', 0, 19, False, {}), 'WarpStarFall': ('GOK_BAS_BUKUU_DOWN', 0, 50, True, {}),
    'YoshiEgg': ('GNY_NAG_A', 0, 30, True, {'hold': 8}), 'KirbyYoshiEgg': ('GNY_NAG_A', 0, 30, True, {'hold': 8}),
}
for kind in ('Light', 'Heavy'):
    for d in ('F', 'B', 'Hi', 'Lw'):
        for sfx in ('', '4'):
            ROWS['%sThrow%s%s' % (kind, d, sfx)] = ('GOK_ATC_SHOT_F', 0, 30, False, {'note': 'item throw: the ki-blast throwing arm'})
for d in ('F', 'B', 'Hi', 'Lw'):
    for sfx in ('', '4'):
        ROWS['LightThrowAir%s%s' % (d, sfx)] = ('GOK_ATC_SHOT_F', 0, 30, False, {'note': 'item throw: the ki-blast throwing arm'})
ROWS['LightThrowDash'] = ('GOK_ATC_SHOT_F', 0, 30, False, {'note': 'item throw: the ki-blast throwing arm'})
ROWS['LightThrowDrop'] = ('GOK_ATC_SHOT_N', 0, 20, False, {})
for item, clips in {'Sword': None, 'Bat': None, 'Parasol': None, 'Harisen': None, 'StarRod': None, 'Lipstick': None}.items():
    ROWS[item + 'Swing1'] = ('GOK_ATC_002', 0, 28, False, {'note': 'item swing: his jab arm'})
    ROWS[item + 'Swing3'] = ('GOK_ATC_008', 4, 28, False, {'note': 'item swing: his forward tilt'})
    ROWS[item + 'Swing4'] = ('GOK_ATC_006', 5, 45, False, {'note': 'item swing: his forward smash lunge'})
    ROWS[item + 'SwingDash'] = ('GOK_ATC_011', 13, 36, False, {'note': 'item swing: his dash attack'})
for r in ('LGunShoot', 'LGunShootAir', 'LGunShootEmpty', 'LGunShootAirEmpty', 'FireFlowerShoot', 'FireFlowerShootAir',
          'ItemScrew', 'ItemScrewAir'):
    ROWS[r] = ('GOK_ATC_SHOT_N', 0, 30, False, {'note': 'item fire: his ki-blast pose'})
for ph in ('Start', 'Rapid', 'Fire', 'End'):
    for air in ('', 'Air'):
        for empty in ('', 'Empty'):
            ROWS['ItemScope%s%s%s' % (air, ph, empty)] = ('GOK_ATC_SHOT_N' if ph != 'Rapid' else 'GOK_ATC_SHOT_N_LOOP', 0, (30 if ph == 'Fire' else 15) if ph != 'Rapid' else 7,
                                                           ph == 'Rapid', {'note': 'item fire: his ki-blast pose'})
for r in ('HammerWait', 'HammerWalk', 'HammerTurn', 'HammerKneeBend', 'HammerFall', 'HammerJump', 'HammerLanding'):
    ROWS[r] = ('GOK_ATC_013', 18, 28, r in ('HammerWait', 'HammerWalk', 'HammerFall'), {'note': 'hammer: his rising arm swing'})
for r in ('KinokoGiantStart', 'KinokoGiantStartAir', 'KinokoGiantEnd', 'KinokoGiantEndAir', 'KinokoSmallStart',
          'KinokoSmallStartAir', 'KinokoSmallEnd', 'KinokoSmallEndAir'):
    ROWS[r] = ('CMN_BAS_HIRAMEKI', 0, 40, False, {})
# fighter-specific captures/throws: the generic grabbed/thrown victim poses
for r in ('CaptureNeck', 'CaptureFoot', 'CaptureCaptain', 'CaptureYoshi', 'CaptureKoopa', 'CaptureWaitKoopa', 'CaptureKoopaAir',
          'CaptureWaitKoopaAir', 'CaptureKirby', 'CaptureWaitKirby', 'CaptureMewtwo', 'CaptureMewtwoAir', 'CaptureMasterHand',
          'CaptureWaitMasterHand', 'CaptureKirbyYoshi', 'CaptureLeadead', 'CaptureLikelike', 'CaptureCrazyHand', 'CaptureWaitCrazyHand'):
    ROWS[r] = ('GNY_NAG_A', 0, 30, True, {'hold': 8})
for r in ('CaptureDamageKoopa', 'CaptureDamageKoopaAir', 'CaptureDamageMasterHand', 'CaptureDamageCrazyHand'):
    ROWS[r] = (H + '_L_F', 0, 14, False, {'tf': 1.5})
for r in ('ThrownKoopaF', 'ThrownKoopaB', 'ThrownKoopaAirF', 'ThrownKoopaAirB', 'ThrownKirbyStar', 'ThrownCopyStar', 'ThrownKirby',
          'ThrownMewtwo', 'ThrownMewtwoAir', 'ThrownMasterHand', 'ThrownCrazyHand'):
    ROWS[r] = ('GNY_NAG_A', 8, 60, False, {})
# safe aliases (checklist: the same pose is final art), declared so none is a silent placeholder
ALIASES = {'WalkSlow': 'WalkMiddle', 'WalkFast': 'WalkMiddle', 'FallAerial': 'Fall', 'FallAerialF': 'Fall', 'FallAerialB': 'Fall',
           'FallSpecial': 'Fall', 'FallSpecialF': 'Fall', 'FallSpecialB': 'Fall', 'Pass': 'Fall',
           'LandingFallSpecial': 'Landing', 'LandingAirN': 'Landing', 'LandingAirF': 'Landing', 'LandingAirB': 'Landing',
           'LandingAirHi': 'Landing', 'LandingAirLw': 'Landing'}


def apply(out, clip_by_name, ean_clip):
    """Add the rows to row_specs' `out`: clip_by_name(source name) -> clip id."""
    for row, (src, start, frames, loop, ex) in ROWS.items():
        cid = clip_by_name(src)
        if cid is None:
            continue
        rs = {'clip': cid, 'loop': loop, 'frames': frames, 'start': start,
              'status': (ex.get('note') or ('source: %s from f%d, %d frames%s' % (src, start, frames, (' x%g' % ex['tf']) if ex.get('tf') else '')))}
        if ex.get('tf'):
            rs['time_factor'] = ex['tf']
        if ex.get('hold') is not None:
            rs['hold_source'] = ex['hold']
        if ex.get('yaw'):
            rs['yaw'] = ex['yaw']
        out[row] = rs
    for row, base in ALIASES.items():
        if base in out and row not in out:
            out[row] = {**out[base], 'status': 'safe alias of %s (the same pose is final art)' % base}

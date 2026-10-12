"""Cross-port moves: a retail Melee fighter's action (animation + hitbox script) retargeted onto Goku's rig.

python ports/goku-xv2/tools/cross_port.py            # every entry of tools/cross-port.json (needs GW_ISO_VANILLA; source .env)
python ports/goku-xv2/tools/cross_port.py AttackAirB # one row

Owner decision (2026-10-09): Goku's back air is Melee Luigi's AttackAirB, animation and hitbox structure, because XV2 has no
suitable back attack. For each registry entry this
  1. reads the retail action from the vanilla disc and solves it onto Goku's skeleton by bone role (ports/ir/tools/retarget_melee_anim.py),
     writing the clip to _build/goku-xv2/cross-port/<row>/clip.npz (+ report.json, script.json) -- disc-derived, git-ignored;
  2. writes moves/<move>.genoasm: Luigi's script with every hitbox moved to the Goku bone of the same role, offsets rebuilt along/across the
     bone, size and offsets scaled by the Goku/Luigi size ratio (the script text is in pre-build units: build.py multiplies by its model
     scale), word 0 as @HITW0:<role>:<base>@ so build.py puts in the destination joint; Luigi's damage, angle, KBG/BKB, element, sound bits,
     timing, auto-cancel window (cmd_var) and IASA are kept;
  3. updates gameplay.json for the move (windows, IASA, minimum clip frames, design).
xv2_to_artist.py then bakes the clip (row_specs reads cross-port.json); fidelity.py reports the row as CROSS-PORT.
The generated moves/*.genoasm carry Luigi's numbers (disc data): they are git-ignored here like the rest of ports/goku-xv2.
"""
import json
import os
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_gameplay as SG
ROOT = PORT.parents[1]
REGISTRY = PORT / 'tools/cross-port.json'
OUT = ROOT / '_build/goku-xv2/cross-port'
FIGHTER_JSON = ROOT / '_build/goku-xv2/author-source/fighter.json'
ART_REPORT = ROOT / '_build/goku-xv2/author-source/art-report.json'


def registry(loco=None):
    """tools/cross-port.json plus, when a locomotion set is selected, tools/cross-port-loco-<set>.json (Turn, TurnRun, RunBrake from another fighter).
    The set is GOKU_LOCO_SET (falcon | marth | fox ...); unset is the default build: Goku's own locomotion rows, no overlay."""
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    loco = os.environ.get('GOKU_LOCO_SET', '') if loco is None else loco
    if loco:
        f = REGISTRY.with_name('cross-port-loco-%s.json' % loco)
        if not f.exists():
            raise SystemExit('GOKU_LOCO_SET=%s: %s does not exist' % (loco, f.name))
        reg.update(json.loads(f.read_text(encoding='utf-8')))
    return reg


def clip_path(row):
    return OUT / row / 'clip.npz'


def tool():
    """The retarget tool: this checkout's ports/ir/tools, else $GOKU_RETARGET_DIR (the ws/retarget-tool worktree before it is merged)."""
    for d in (os.environ.get('GOKU_RETARGET_DIR'), str(ROOT / 'ports/ir/tools'), str(ROOT / 'worktrees/ws-retarget-tool/ports/ir/tools')):
        if d and (Path(d) / 'retarget_melee_anim.py').exists():
            sys.path.insert(0, d)
            sys.path.insert(0, str(ROOT))
            import retarget_melee_anim
            return retarget_melee_anim
    raise SystemExit('retarget_melee_anim.py not found: set GOKU_RETARGET_DIR to the folder that holds it')


def markers():
    sys.path.insert(0, str(PORT / 'tools'))
    sys.path.insert(0, str(ROOT))
    import build
    return {role: marker for marker, role in build.ROLE.items()}


def scale_tracks(T, got, res, gain=1.0):
    """Source bone-scale tracks (Luigi's bair thigh stretch: SCAX on both leg joints) mapped to the destination bone of the same role.
    HSD bones point along local X, so a source X scale is a stretch along the bone; it is carried on the destination bone's own axis when that
    axis is a coordinate axis. Returns ({dst bone: {axis, values, src_role}}, [notes])."""
    import numpy as np
    src, clip, dst = got['rig'], got['clip'], res.dst
    _, _, s = clip.sample(src, T.sample_frames(clip))
    out, notes = {}, []
    for role, sj in src.roles.items():
        sv = s[:, sj]
        if role not in dst.roles or np.abs(sv - 1).max() < 0.02:
            continue
        if np.abs(sv[:, 1:] - 1).max() > 0.02:
            notes.append('%s: scale on Y/Z not carried' % role)
            continue
        dj = dst.roles[role]
        d, _ = T.bone_frame(dst, dj)
        ax = int(np.argmax(np.abs(d)))
        if abs(d[ax]) < 0.99:
            notes.append('%s: destination bone axis is not a coordinate axis, not carried' % role)
            continue
        out[dst.names[dj]] = {'axis': ax, 'values': [round(1.0 + gain * float(v - 1.0), 5) for v in sv[:, 0]], 'src_role': role, 'gain': gain}
    return out, notes


def generate(row, entry, out=None):
    """`out` (default _build/goku-xv2/cross-port) is the folder that gets <row>/clip.npz; the previews solve several sets side by side."""
    OUT_ = Path(out) if out else OUT
    T = tool()
    height = json.loads(ART_REPORT.read_text(encoding='utf-8'))['geometry']['height']
    cfg = SG.load()
    build_scale = height / cfg['geometry_reference_height']
    res, report, events, got = T.run(entry['fighter'], entry['action'], str(FIGHTER_JSON), str(OUT_ / row))
    src, dst, ratio = got['rig'], res.dst, report['ratio']
    scales, scale_notes = scale_tracks(T, got, res, entry.get('scale_gain', 1.0))
    (OUT_ / row / 'scale.json').write_text(json.dumps({'bones': scales, 'notes': scale_notes}, indent=1) + chr(10), encoding='utf-8')
    if entry.get('anim_only'):
        # the animation (and the grab anchor's choreography) only: the move's own script stays (ThrowF keeps its ki-blast spawns and damage). 'spawn_from' records where
        # a role sits in the solved pose on the given script frames, for placing an article there (remake_patch.py reads spawn.json).
        import numpy as np
        from scipy.spatial.transform import Rotation as _R
        sp = entry.get('spawn_from')
        if sp:
            wd = T.solved_world(res)
            jd = dst.roles[sp['role']]
            pts = np.array([wd[min(int(f), wd.shape[0] - 1), jd, :3, 3] for f in sp['frames']])
            (OUT_ / row / 'spawn.json').write_text(json.dumps({'role': sp['role'], 'frames': sp['frames'], 'art_units': pts.tolist(), 'build_scale': build_scale,
                                                              'mean_forward_up_script_units': [float(pts[:, 2].mean() / build_scale), float(pts[:, 1].mean() / build_scale)]}, indent=1) + chr(10), encoding='utf-8')
        samples = len(range(int(round(report['source']['frames'])) + 1))
        if entry.get('move'):
            gp = SG.load()
            m = next(x for x in gp['moves'] if x['name'] == entry['move'])
            m['minimum_clip_frames'] = samples
            SG.save(gp)
        summary = {'row': row, 'clip': str(OUT_ / row / 'clip.npz'), 'move_script': None, 'ratio': ratio, 'build_scale': build_scale, 'windows': [], 'iasa': samples, 'samples': samples,
                   'hitboxes': [], 'worst_end_effector_error': max(v['max'] for v in report['end_effector_error'].values())}
        (OUT_ / row / 'cross-port.json').write_text(json.dumps(summary, indent=1) + chr(10), encoding='utf-8')
        return summary
    mk = markers()
    lines, moved = T.script_text(got['words'], src, dst, ratio, scale=1.0 / build_scale,
                                 joint_ref=lambda role, jd, base: '@HITW0:%s:0x%08X@' % (mk[role], base))
    drop = tuple(entry.get('drop', ()))   # commands of the source script that stay behind (Falcon's grab effect and sound)
    if drop:
        lines = [ln for ln in lines if ln.split(None, 1)[0] not in drop]
    who = entry['fighter'].capitalize()
    text = ['# HB-SAMPLE (CROSS-PORT): Melee %s %s (retail data from the vanilla disc), retargeted by bone role; owner choice: %s.'
            % (who, entry['action'], entry['reason']),
            "# Hitbox joint, size and offsets are %s's moved to Goku's bone of the same role (a sphere on the root joint is scaled about it) and scaled by the size ratio %.4f"
            " (script units: build.py multiplies by %.4f; the engine then applies Goku's built size 1.2 to the fighter, model and hitboxes alike). Damage, angle, KBG/BKB, timing,"
            " auto-cancel and IASA are unchanged%s." % (who, ratio, build_scale, ('; left behind: ' + ', '.join(drop)) if drop else ''), 'PUT ANIM_RATE 1.0'] + lines
    hbs = [e for e in events if e['kind'] == 'hitbox']
    clears = [e['frame'] for e in events if e['kind'] == 'hitboxes_clear']
    iasa = next((e['frame'] for e in events if e['kind'] == 'iasa'), None)   # a source action with no IASA (Catch) plays to the end of its animation
    release = next((e['frame'] for e in events if e['kind'] == 'throw_release'), None)
    windows = [[h['frame'], next((c for c in clears if c > h['frame']), h['frame'] + 1) - h['frame']] for h in hbs]
    samples = len(range(int(round(report['source']['frames'])) + 1))
    if iasa is None:
        iasa = samples
    move = None
    if entry.get('move'):   # a row with no move of its own (CatchWait) is the animation only
        move = PORT / 'moves' / (entry['move'] + '.genoasm')
        move.write_text('\n'.join(text) + '\n', encoding='utf-8')
        gp = SG.load()
        m = next(x for x in gp['moves'] if x['name'] == entry['move'])
        roles = [mk.get(x['src_role'], x['src_role']) for x in moved]
        thr = next((e for e in events if e['kind'] == 'throw'), None)
        first = moved[0]['before'] if moved else None
        if first is None and thr is not None:   # a throw with no hitbox: slot 0 of its throw command is the number that matters
            import re
            first = {k: int(v) for k, v in re.findall(r'(damage|angle|kbg|bkb)=(-?\d+)', thr['text'])}
        m['hb'] = 'HB-SAMPLE'
        m['windows'] = windows
        m['iasa'] = iasa
        m['minimum_clip_frames'] = samples
        if release is not None:
            m['release'] = release
        d = dict(m.get('design', {}))
        if first:
            d.update(damage=first['damage'], angle=first['angle'], kbg=first['kbg'], bkb=first['bkb'])
        if moved:
            d.update(radius=round(moved[0]['after']['size'] * build_scale, 4), role=roles[0], window_roles=roles, offset=[0, 0, 0])
        else:
            for k in ('radius', 'role', 'offset', 'window_roles'):
                d.pop(k, None)
        m['design'] = d
        m['timing'] = ('CROSS-PORT from Melee %s %s (%s): %s, IASA f%d, %d clip frames, release %s; %s numbers%s'
                       % (who, entry['action'], entry['reason'], ('hitboxes f%d-%d' % (windows[0][0], windows[0][0] + windows[0][1])) if windows else 'no hitbox', iasa, samples,
                          release, who, (' (damage %d, angle %d, KBG %d, BKB %d), spheres on %s scaled x%.3f'
                                         % (first['damage'], first['angle'], first['kbg'], first['bkb'], '/'.join(roles), ratio)) if first and moved else ''))
        m['pick'] = {'status': 'cross-port', 'source': '%s %s' % (entry['fighter'], entry['action']), 'why': entry['reason'], 'ratio': ratio}
        m['pose_review'] = ("Cross-port clip: %s's %s retargeted by bone role (a bone-scale track is carried when the source has one: clips.scale_bones). "
                            "Pose review in the LAB owed." % (who, entry['action']))
        SG.save(gp)  # full file + regenerated stripped gameplay.json
    summary = {'row': row, 'clip': str(OUT_ / row / 'clip.npz'), 'move_script': str(move), 'ratio': ratio, 'build_scale': build_scale,
               'windows': windows, 'iasa': iasa, 'release': release, 'samples': samples, 'hitboxes': moved,
               'worst_end_effector_error': max(v['max'] for v in report['end_effector_error'].values())}
    (OUT_ / row / 'cross-port.json').write_text(json.dumps(summary, indent=1) + '\n', encoding='utf-8')
    return summary


def main(argv):
    """cross_port.py [--set falcon] [--out DIR] [--rows A,B] [ROW ...]: --set selects the locomotion overlay (default: GOKU_LOCO_SET), --out solves into DIR
    instead of _build/goku-xv2/cross-port, and with --rows only those rows (an overlay set's rows, when --set is given and no ROW is named)."""
    out = None
    loco = None
    argv = list(argv)
    for flag in ('--set', '--out'):
        if flag in argv:
            i = argv.index(flag)
            val = argv[i + 1]
            del argv[i:i + 2]
            if flag == '--set':
                loco = val
            else:
                out = val
    reg = registry(loco)
    if loco and not argv:
        argv = [r for r in json.loads(REGISTRY.with_name('cross-port-loco-%s.json' % loco).read_text(encoding='utf-8'))]
    for row in (argv or reg):
        s = generate(row, reg[row], out)
        print('%s: %d frames, windows %s, IASA %d, ratio %.3f, worst end-effector error %.2f; script %s'
              % (row, s['samples'], s['windows'], s['iasa'], s['ratio'], s['worst_end_effector_error'], s['move_script']))


if __name__ == '__main__':
    main(sys.argv[1:])

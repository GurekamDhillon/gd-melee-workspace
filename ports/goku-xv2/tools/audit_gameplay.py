"""Audit genuine parity-selected BAC candidates against the installed Geno package.

Reuses check_hitbox_positions' native ftcmd/FigaTree readers, never fabricates ACMD.
This is offline destination encoding, native animation pose and hurtbox coverage evidence.
XV2 geometry equivalence, native contact and LAB clock timing remain unverified.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.spatial.transform import Rotation

import build as G
from tools.geno import report, script
import check_hitbox_positions as HP
import figatree
from plan_hurtboxes import coverage, seg_dist

def rest_context(mesh, plan):
    rest = {}
    for joint in mesh['joints']:
        rest[joint['name']] = (np.array(joint['trans']),None,np.array(joint['scale']),np.array(joint['rot']))
    # Artist-generated synthesized joints have real transforms; evaluate those too.
    native_plan = {'joints':[dict(j,synthesized=False) for j in plan['joints']]}
    identity = {'joints':[[] for j in plan['joints']]}
    worlds = HP.pose_matrices(identity,native_plan,rest,0)
    return rest,native_plan,worlds

def mesh_points(mesh):
    seen,points,weights = set(),[],[]
    for obj in mesh['dobjs']:
        for triangle in obj['tris']:
            for vertex in triangle:
                key = tuple(vertex['p'])+tuple(tuple(w) for w in vertex['w'])
                if key in seen:
                    continue
                seen.add(key)
                points.append(vertex['p'])
                weights.append(vertex['w'])
    return np.asarray(points),weights

def fit_hurtboxes(mesh,plan):
    """Adapt plan_hurtboxes' 14-segment PCA/92-percent method to artist-native mesh input."""
    rest,native,worlds = rest_context(mesh,plan)
    points,weights = mesh_points(mesh)
    roles = ['head','chest','spine','hips','upper_arm.L','lower_arm.L','upper_arm.R','lower_arm.R',
             'upper_leg.L','lower_leg.L','upper_leg.R','lower_leg.R','foot.L','foot.R']
    segments = {plan['roles'][r][0]:r for r in roles if r in plan['roles']}
    fallback = plan['roles']['hips'][0]
    parents = {j['index']:j['parent'] for j in plan['joints']}
    owners = []
    for weights_at_vertex in weights:
        joint = max(weights_at_vertex,key=lambda w:w[1])[0]
        while joint not in segments and parents[joint] is not None:
            joint = parents[joint]
        owners.append(joint if joint in segments else fallback)
    lo,hi = np.percentile(points[:,1],[2,98])
    caps = []
    for joint,role in segments.items():
        selected = points[np.array(owners)==joint]
        if len(selected)<4:
            continue
        inv = np.linalg.inv(worlds[joint])
        local = (inv[:3,:3]@selected.T).T+inv[:3,3]
        centre = local.mean(0)
        axis = np.linalg.svd(local-centre,full_matrices=False)[2][0]
        low,high = np.percentile((local-centre)@axis,[3,97])
        a,b = centre+axis*low,centre+axis*high
        radius = max(.15,float(np.percentile(seg_dist(local,a,b),92)))
        pull = min(radius,(high-low)/2)
        a,b = a+axis*pull,b-axis*pull
        radius = max(.15,float(np.percentile(seg_dist(local,a,b),92)))
        if role in ('foot.L','foot.R','lower_leg.L','lower_leg.R'):
            radius += 1.6  # hybrid hover stance (2026-10-09): the hover rows lift him 2 units, so the lower hurtboxes reach back down to the floor
        height = float((worlds[joint]@np.append(centre,1))[1])
        caps.append({'id':'goku_'+role,'joint':joint,'bone':plan['joints'][joint]['name'],
                     'a':a.tolist(),'b':b.tolist(),'radius':radius,
                     'height':'low' if height<lo+(hi-lo)/3 else 'high' if height>lo+2*(hi-lo)/3 else 'mid',
                     'grabbable':True})
    if not 1<=len(caps)<=15:
        raise ValueError('Invalid fitted hurtbox count')
    return caps,dict(zip(('covered','worst_outside'),coverage(caps,worlds,points)))

def audit(package,art_build,fit=False):
    package,art_build = G.generated(package),G.generated(art_build)
    ir = G.load(G.PORT/'ir/goku.xv2.ir.json')
    cfg = G.load(G.SG.path())
    plan_path = package/'files/plan.json'
    plan = G.load(plan_path)
    mesh_path = next(art_build.glob('mesh_*.json'))
    mesh = G.load(mesh_path)
    rest,native,worlds = rest_context(mesh,plan)
    if fit:
        plan['hurtboxes'],fit_stats = fit_hurtboxes(mesh,plan)
        G.write(plan_path,plan)
        G.write(art_build/'plan.json',plan)
    else:
        points,_ = mesh_points(mesh)
        fit_stats = dict(zip(('covered','worst_outside'),coverage(plan['hurtboxes'],worlds,points)))
    bank = (package/'files'/plan['bank']['file']).read_bytes()
    fighter = G.load(package/'geno.json')['fighters'][0]
    overlays = {o['index']:o for o in fighter['subactions']}
    motions = report.motion_subactions()
    frames, positions, problems, posed_hurt, limb_review = [],[],[],[],[]
    points,weights = mesh_points(mesh)
    bind_inv = [np.linalg.inv(w) for w in worlds]
    import remake_samples as RS   # lazy: remake_samples imports this module
    clouds_by_joint = {c['joint']:c for c in RS.limb_clouds(plan,points,weights,worlds).values()}
    for move in cfg['moves']+cfg['special_adaptations']:
        parity,source,source_scripts = G.move_source(ir,move['parity'])
        expected_source = []
        variant = move.get('source_variant',0)
        if source_scripts:
            expected_source = [[e['frame'],e['args']['engine']['xv2.pc']['duration_frames']]
                               for e in source_scripts[min(variant,len(source_scripts)-1)]['events'] if e['op']=='hitbox.create']
        if move.get('hb') != 'HB-NONE' and move.get('timing','').startswith('BAC static candidate') and move.get('windows') != expected_source:
            problems.append(move['name']+': declared candidate windows disagree with parity-selected BAC')
        declared_clip = None
        if 'motions' in move:
            rows = sorted({motions[m][1] for m in move['motions']})
        else:
            sub = next(s['subaction'] for s in cfg['states'] if s['name']==move['name'])
            if isinstance(sub, str):  # 'clip:<name>': a declared own row, 303 + index in fighter.rows
                declared_clip = sub[5:]
                own = json.loads((package/'geno.json').read_text(encoding='utf-8'))['fighters'][0]['fighter']['rows']
                sub = 303 + own.index(declared_clip)
            rows = [sub]
        for row in rows:
            words = script.read_words((package/overlays[row]['file']).read_text())
            static = report.frames(words)
            frames.append({'move':move['name'],'row':row,'source_windows':expected_source,'target':static,
                           'parity_relation':parity['relation'],'clock':'static script frames; not native action_frame'})
            events = HP.hitbox_events(words+[0]) if static['hitboxes'] else []   # HB-NONE (remake): no hitbox to place; scripts with flow ops (Kamehameha charge loop) need no position check
            clip = declared_clip or plan['row_clips'][row]
            record = plan['bank']['clips'][clip]
            _,tree = figatree.parse_archive(bank[record['offset']:record['offset']+record['bytes']])
            sample_frames = {0}
            for box in static['hitboxes']:
                end = box['end'] if box['end'] is not None else tree['frames']+1
                sample_frames.update(range(math.ceil(box['start']),math.ceil(end)))
            sample_frames = sorted(sample_frames)
            for frame in sample_frames:
                pose = HP.pose_matrices(tree,native,rest,min(frame,tree['frames']))
                if row==rows[0] and frame in [w[0] for w in move.get('windows',[])]:
                    chest = pose[plan['roles']['chest'][0]][:3,3]
                    limb_review.append({'move':move['name'],'row':row,'clip':clip,'frame':frame,
                        'placement':move.get('pose_review','authored destination anatomical placement'),
                        'world_positions':{role:pose[plan['roles'][role][0]][:3,3].tolist() for role in G.ROLE.values()},
                        'chest_relative':{role:(pose[plan['roles'][role][0]][:3,3]-chest).tolist() for role in G.ROLE.values()},
                        'chosen_roles':move.get('design',{}).get('window_roles',[])})
                spheres = HP.live_spheres(events,frame)
                if len(spheres)>4:
                    problems.append(move['name']+': more than4 live spheres')
                for words_box in spheres:
                    centre,radius = HP.sphere(words_box,pose)
                    joint = (words_box[0]>>11)&255
                    if not np.isfinite(centre).all() or not radius>0:
                        problems.append(move['name']+': nonfinite or empty sphere')
                    if move.get('hb') == 'HB-SAMPLE' and joint in clouds_by_joint:
                        # remake phase 2: a sample sphere must sit ON its limb: centre within its radius of the limb bone segment in every active frame
                        cl = clouds_by_joint[joint]
                        pa,pb = (pose[joint]@np.append(cl['a'],1))[:3],(pose[joint]@np.append(cl['b'],1))[:3]
                        d = float(seg_dist(np.array([centre]),pa,pb)[0])
                        if d > radius:
                            problems.append('%s: f%d sphere on %s is %.2f from its limb bone segment, radius %.2f (floats off the limb)'%(move['name'],frame,plan['joints'][joint]['name'],d,radius))
                    positions.append({'move':move['name'],'row':row,'clip':clip,'frame':frame,
                                      'joint':joint,'joint_name':plan['joints'][joint]['name'],
                                      'native_bank_world_centre':centre.tolist(),'radius':radius,
                                      'basis':'Native encoded joint-local sphere evaluated through installed FigaTree; no XV2 geometry equivalence claim'})
                if row==rows[0]:
                    skin = [pose[i]@bind_inv[i] for i in range(len(pose))]
                    posed = np.zeros_like(points)
                    for i,ww in enumerate(weights):
                        for joint,weight in ww:
                            posed[i] += weight*(skin[joint][:3,:3]@points[i]+skin[joint][:3,3])
                    cov,worst = coverage(plan['hurtboxes'],pose,posed)
                    capsules = []
                    for cap in plan['hurtboxes']:
                        transform = pose[cap['joint']]
                        capsules.append({'joint':cap['joint'],'bone':cap['bone'],
                                         'a':(transform@np.array([*cap['a'],1]))[:3].tolist(),
                                         'b':(transform@np.array([*cap['b'],1]))[:3].tolist(),
                                         'radius':cap['radius']})
                    posed_hurt.append({'move':move['name'],'row':row,'clip':clip,'frame':frame,
                                       'covered':cov,'worst_outside':worst,'capsules':capsules,
                                       'native_bank_world_capsules':capsules})
    G.write(art_build/'framedata-parity-check.json',{'ok':not problems,'checks':'BAC candidate windows / encoded destination scripts',
        'legacy_cli':'framedata_check.py requires Ultimate ACMD and LAB export; incompatible with XV2',
        'native_lab_timing':'NOT RUN','source_runtime_timing':'UNVERIFIED','moves':frames,'problems':problems})
    G.write(art_build/'hitbox-positions.json',{'ok':not problems,'adapter':'check_hitbox_positions.sphere/pose_matrices/hitbox_events',
        'sampling':'Every integer active script frame of every fighter hitbox plus frame0, evaluated at animation rate1. Article geometry is declared separately; native contact is not tested.',
        'source_geometry_equivalence':'NOT CLAIMED: authored anatomical spheres replace unverified XV2 shape semantics',
        'coordinates':'HSD/author GLB model coordinates X-left,Y-up,Z-forward before runtime fighter facing/world transform. XV2(x,y,z)->model(x,y,-z), winding flipped. Blender import model(x,y,z)->Blender(x,-z,y): Z-up,-Y-forward. Runtime fighter rotation/translation is not simulated.',
        'native_contact_both_facings':'NOT RUN','positions':positions,'problems':problems})
    G.write(art_build/'hurtbox-coverage.json',{'method':'plan_hurtboxes PCA / 92th-percentile fit adapted to artist mesh',
        'rest':fit_stats,'capsules':plan['hurtboxes'],'poses':posed_hurt,
        'sampling':'Every integer fighter-hitbox active frame plus frame0; one animation row per authored move declaration.',
        'limitations':'Coverage values are measurements without a pass threshold. Hair, cloth and extremities may be outside percentile capsules; coverage alone is not gameplay validation.'})
    G.write(art_build/'limb-placement-review.json',{'basis':'Installed FigaTree poses. Model forward=+Z,up=+Y; runtime facing not applied.',
        'placement_prose_reference_height':cfg['geometry_reference_height'],
        'measured_positions':'Numeric world_positions/chest_relative use current built size; historical placement prose numbers use authored reference height.',
        'limitations':'Anatomical strike placement is reviewed, but source candidates are not necessarily canonical Melee attack directions. Lateral 3D motion remains a projection limitation.',
        'samples':limb_review})
    return problems

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package',type=Path,required=True)
    ap.add_argument('--art-build',type=Path,required=True)
    ap.add_argument('--fit-hurtboxes',action='store_true')
    args = ap.parse_args()
    problems = audit(args.package,args.art_build,args.fit_hurtboxes)
    print('Offline gameplay audit:', 'FAIL '+str(problems) if problems else 'PASS (source fidelity and LAB timing unverified)')
    return bool(problems)

if __name__ == '__main__':
    raise SystemExit(main())

"""Checked source IR + explicit parity -> local, lossy Geno artist source.

python ports/goku-xv2/tools/xv2_to_artist.py [--build] [--blend]
Bulk assets are dereferenced exclusively through checksum-checked IR BlobRefs.
This adapter is a prototype, not an XV2 renderer or runtime-faithful exporter.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import os
import json
import shutil
import math
from pathlib import Path
import re
import struct
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation, Slerp

ROOT = Path(__file__).resolve().parents[3]
PORT = ROOT / 'ports/goku-xv2'
def cross_registry():
    """tools/cross-port.json (+ the locomotion overlay GOKU_LOCO_SET=falcon|marth|fox: tools/cross-port-loco-<set>.json; unset = Goku's own Turn/TurnRun/RunBrake)."""
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import cross_port
    return cross_port.registry()
HAND_FILE = Path(os.environ.get('GOKU_HAND', PORT / 'anim/hand.json'))   # hand-authored deltas; NEVER written by this converter
AUTHOR = ROOT / '_build/goku-xv2' / os.environ.get('GOKU_AUTHOR', 'author-source')   # GOKU_AUTHOR=splice-preview: a reduced build that leaves the shipped package alone
sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_gameplay as SG
import splice as SP
sys.path.insert(0, str(ROOT))
from tools.geno.artist import model, spec, pipeline, validate
from tools.geno.artist.blender import hand_layer as HL   # the hand-animation file (ports/goku-xv2/anim/hand.json), applied last

BODY = 'chara/GOK/GOK_000.esk'
EAN = 'chara/GOK/GOK.ean'
BAC = 'chara/GOK/GOK_PLAYER.bac'
BASIS = np.diag([1., 1., -1.])  # source Y-up/-Z forward -> glTF Y-up/+Z forward
ROLES = {'b_C_Base':'translation', 'b_C_Pelvis':'hips', 'b_C_Spine1':'spine',
         'b_C_Chest':'chest','b_C_Neck1':'neck','b_C_Head':'head',
         'item_socket.R':'item_socket.R','grab_anchor':'grab_anchor'}
for side in ('L','R'):
    for bone, role in [('Shoulder','shoulder'),('Arm1','upper_arm'),('Arm2','lower_arm'),
                       ('Hand','hand'),('Leg1','upper_leg'),('Leg2','lower_leg'),('Foot','foot'),('Toe','toe')]:
        ROLES[f'b_{side}_{bone}'] = f'{role}.{side}'
    ROLES[f'h_{side}_Thumb1'] = f'thumb.{side}'
    ROLES[f'h_{side}_Index1'] = f'fingers.{side}'


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')


class Source:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.doc = json.loads(self.path.read_text(encoding='utf-8-sig'))
        if self.doc['subject']['engine'] != 'xv2.pc':
            raise ValueError('Expected XV2 source IR')
        self.parity_rows = self.doc.get('parity', [])
        self.parity = {p['here']:p for p in self.parity_rows if p['here'].startswith('move:')}
        if not self.parity_rows or any(not p.get('differences') for p in self.parity_rows):
            raise ValueError('Explicit source/host parity decisions are required')
        for move in self.doc['behavior']['moves']:
            if move['id'] not in self.parity:
                raise ValueError('Missing move parity: '+move['id'])
        for bone, role in ROLES.items():
            if bone in ('item_socket.R','grab_anchor'):
                continue
            if not any(p['here']=='joint:'+BODY+'/'+bone and f'artist role {role};' in p['differences'] for p in self.parity_rows):
                raise ValueError('Missing anatomical role parity: '+bone)
        self.cache = {}
        self.json_cache = {}
        self.reads = {}
        self.assets = self.doc['assets']
        self.clips = {c['id']:c for c in self.assets['animations']['clips']}
        self.subs = {s['id']:s for s in self.doc['behavior']['subactions']}
        self.scripts = {s['id']:s for s in self.doc['behavior']['scripts']}

    def blob(self, ref, binary=False):
        path = Path(ref['path'])
        key = str(path)
        if key not in self.cache:
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != ref.get('sha256'):
                raise ValueError('IR BlobRef checksum mismatch: '+str(path))
            self.cache[key] = data
            self.reads[key] = ref['sha256']
        if self.reads[key] != ref.get('sha256'):
            raise ValueError('Conflicting BlobRef checksum for '+key)
        if binary:
            return self.cache[key]
        if key not in self.json_cache:
            self.json_cache[key] = json.loads(self.cache[key].decode('utf-8-sig'))
        obj = self.json_cache[key]
        pointer = re.search(r'JSON Pointer ([^;]+)', ref.get('note',''))
        if pointer:
            for bit in pointer.group(1).split('/')[1:]:
                bit = bit.replace('~1','/').replace('~0','~')
                obj = obj[int(bit)] if isinstance(obj,list) else obj[bit]
        return obj

    def rig(self, name):
        s = next(s for s in self.assets['skeletons'] if s['name']==name)
        return self.blob(s['engine']['xv2.pc']['source_data'])['joints']


def trs(j):
    m = np.eye(4)
    m[:3,:3] = Rotation.from_quat(j['rotation']).as_matrix() @ np.diag(j['scale'])
    m[:3,3] = j['translation']
    return m


def world_matrices(joints):
    out=[]
    for j in joints:
        m=trs(j)
        out.append(out[j['parent']] @ m if j['parent'] >= 0 else m)
    return out


def size_basis(height):
    """Metadata-only comparison; source/host physics and source parity stay intact."""
    path=PORT/'ir/host.melee.ir.json'
    host=json.loads(path.read_text())
    joints=host['assets']['skeletons'][0]['joints'];world=[]
    for joint in joints:
        r=joint['rest'];m=np.eye(4)
        m[:3,:3]=Rotation.from_euler('xyz',r['rotation_euler_rad']).as_matrix()@np.diag(r['scale'])
        m[:3,3]=r['translation'];p=joint['parent']
        world.append(world[p]@m if p is not None else m)
    head=next(w for j,w in zip(joints,world) if j.get('role_guess')=='head')
    modelscale=next(a['value'] for a in host['behavior']['attributes']['common'] if a.get('engine_name')=='model_scaling')
    return {'classification':'destination visual size design','bind_height':height,'allowed_bind_height':[8,20],
            'reason':'20-unit default uses the contract ceiling after the 14-unit version appeared too short in the LAB.',
            'previous_bind_height':14,'previous_wait_frame0_mesh_height':11.654000332554418,
            'relative_to_previous':height/14.,'host_ir_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'falcon_rest_head_joint_y':float(head[1,3]),'falcon_rest_highest_joint_y':float(max(w[1,3] for w in world)),
            'falcon_model_scaling':modelscale,
            'comparison_limit':'Host IR has skeleton landmarks but no mesh bounds; a rest head joint is not a posed mesh-height measurement. Source animation stance lowers visible Goku height below bind height.'}


def reduce_weights(names, weights, attach=None):
    combined={}
    for name,w in zip(names,weights):
        if w<=1e-6: continue
        name=attach or ('b_C_Head' if name.startswith('f_') else name)
        combined[name]=combined.get(name,0.)+float(w)
    pairs=sorted(combined.items(), key=lambda x:(-x[1],x[0]))
    if not pairs: raise ValueError('Unweighted source vertex')
    discarded=sum(w for _,w in pairs[2:])/sum(w for _,w in pairs)
    pairs=pairs[:2]
    total=sum(w for _,w in pairs)
    return [(n,w/total) for n,w in pairs], discarded


class GLB:
    def __init__(self):
        self.data=bytearray()
        self.g={'asset':{'version':'2.0','generator':'goku-xv2 IR adapter'},'bufferViews':[], 'accessors':[]}

    def view(self, raw):
        while len(self.data)%4:self.data.append(0)
        n=len(self.g['bufferViews'])
        self.g['bufferViews'].append({'buffer':0,'byteOffset':len(self.data),'byteLength':len(raw)})
        self.data.extend(raw)
        return n

    def accessor(self, data, kind, dtype='<f4', bounds=False):
        a=np.asarray(data,dtype=dtype)
        typ={'<f4':5126,'<u2':5123,'<u4':5125}[dtype]
        d={'bufferView':self.view(a.tobytes()),'componentType':typ,'count':len(a),'type':kind}
        if bounds:
            d['min']=np.min(a,axis=0).reshape(-1).tolist()
            d['max']=np.max(a,axis=0).reshape(-1).tolist()
        n=len(self.g['accessors']);self.g['accessors'].append(d);return n

    def save(self,path):
        while len(self.data)%4:self.data.append(0)
        self.g['buffers']=[{'byteLength':len(self.data)}]
        js=json.dumps(self.g,separators=(',',':')).encode()
        js+=b' '*((-len(js))%4)
        path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(js)+len(self.data))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(self.data),0x004e4942)+self.data)


def material_tile(source, matid, size=192, window=None):
    """Diffuse source texture with explicit provisional DYT tint; no toon shader claim."""
    mat=next(m for m in source.assets['materials'] if m['id']==matid)
    ext=mat['engine']['xv2.pc']
    original=source.blob(ext['source_material'])
    sm=next(m for m in original['Materials'] if m['Name']==mat['name'])
    params={p['Name']:float(p['Value']) for p in sm.get('Parameters',[]) if p['Type'].get('label')=='Float'}
    # Colour construction is deliberately documented as a flat-light approximation.
    container=ext['texture_container']
    index=ext['samplers'][0]['EmbIndex'] if ext.get('samplers') else 0
    key='embedded/'+container+'/'+str(index).zfill(4)+'.dds'
    tex=next(t for t in source.assets['textures'] if t['name']==key)
    im=Image.open(io.BytesIO(source.blob(tex['pixels'],True))).convert('RGBA')
    if mat['name']=='mark':
        # 2026-10-09 (owner #8, the back emblem): `mark` is a decal. Its texture is black ink whose ALPHA holds the ring and kanji (alpha ~184) over
        # crease shading (alpha 45-110); the old path forced alpha opaque and tinted the black RGB skin-coloured, so the emblem was a flat patch.
        # Composite the ink over the gi orange and bake only the mark's own UV window (a quarter of the texture) at the tile's full resolution.
        u0,v0,u1,v1=window  # texture fractions, top-origin
        w,h=im.size;im=im.crop((int(u0*w),int(v0*h),int(np.ceil(u1*w)),int(np.ceil(v1*h)))).resize((size,size),Image.Resampling.LANCZOS)
        a=np.asarray(im)[:,:,3].astype(float)
        ink=np.clip((a-125.)/40.,0.,1.);ink=ink*ink*(3-2*ink)
        base=np.asarray((238,91,12),dtype=float)[None,None,:];dark=np.asarray((16,16,24),dtype=float)[None,None,:]
        rgb=base*(1-ink[:,:,None])+dark*ink[:,:,None]
        out=np.dstack([np.clip(rgb,0,255),np.full((size,size),255.)]).astype('uint8')
        return Image.fromarray(out),{'material':matid,'source_texture':tex['id'],'mode':'decal: black ink masked by the DDS alpha over the gi orange (window baked at full tile resolution)','window':list(window),'alpha':'ink mask baked; tile opaque','source_shader':sm.get('ShaderProgram'),'palette':'DYT toon lookup not reproduced'}
    im=im.resize((size,size),Image.Resampling.LANCZOS)
    pixels=np.asarray(im).copy()
    # Source DDS RGB often contains a monochrome toon mask. Use a named artistic
    # base colour only when chroma is low; preserve actual coloured source pixels.
    name=mat['name'].lower()
    tint=(235,167,119)
    if any(n in name for n in ('hair','eyebrow','line')):tint=(24,23,28)
    elif any(n in name for n in ('pants','dougi','syatu')):tint=(238,91,12)
    if any(n in name for n in ('obi','rist','boots','inner','shirts','listband')):tint=(29,52,114)
    if any(n in name for n in ('eye','tooth','teeth','white')) and 'eyebrow' not in name:tint=(235,236,222)
    rgb=pixels[:,:,:3].astype(float)
    if float(np.mean(np.max(rgb,axis=2)-np.min(rgb,axis=2)))<18:
        luminance=np.mean(rgb,axis=2)/255.
        rgb=np.asarray(tint)[None,None,:]*(.72+.28*luminance[:,:,None])
    pixels[:,:,:3]=np.clip(rgb,0,255).astype('uint8')
    pixels[:,:,3]=255
    return Image.fromarray(pixels), {'material':matid,'source_texture':tex['id'],'mode':'provisional flat diffuse; low-chroma RGB tinted by material name','tint':list(tint),'alpha':'forced opaque','source_shader':sm.get('ShaderProgram'), 'palette':'DYT toon lookup not reproduced'}


def build_mesh(source, height):
    main=source.rig(BODY)
    worlds=world_matrices(main); by={j['name']:worlds[i] for i,j in enumerate(main)}
    p=[];n=[];uv=[];weights=[];indices=[];tiles=[]; material_records=[]; lost=[]
    atlas=Image.new('RGBA',(1024,1024),(20,20,25,255))
    for model_ir in source.assets['models']:
        ext=model_ir['engine']['xv2.pc']; part=ext['part']
        geometry=source.blob(ext['geometry'])
        attach=by[part['attachBone']] if part['attachBone'] else np.eye(4)
        for sm,sm_ir in zip(geometry['submeshes'],model_ir['meshes']):
            matid=sm_ir['material']
            # Bake the complete submesh UV domain. Applying modulo at vertices
            # creates interpolation seams on triangles that cross a wrap edge.
            tiles.append(sm_ir['id']);ti=len(tiles)-1
            srcuv=np.array([v['uv0'] for v in sm['vertices']])
            is_mark=next(m for m in source.assets['materials'] if m['id']==matid)['name']=='mark'
            if is_mark:
                # decal: the tile IS the mark's UV window (u, frac(v) top-origin), no wrapping
                lo=srcuv.min(axis=0);span=np.maximum(srcuv.max(axis=0)-lo,1e-6)
                assert srcuv[:,1].max()<=0. and srcuv[:,1].min()>=-1.,'mark UVs cross a V wrap'
                tile,rec=material_tile(source,matid,window=(lo[0],1+lo[1],lo[0]+span[0],1+lo[1]+span[1]))
            else:
                tile,rec=material_tile(source,matid)
                lo=np.floor(srcuv.min(axis=0));hi=np.ceil(srcuv.max(axis=0));span=np.maximum(hi-lo,1)
                srcpixels=np.array(tile)
                xx=((np.arange(192)/191*span[0]+lo[0])%1*191).astype(int)
                yy=((np.arange(192)/191*span[1]+lo[1])%1*191).astype(int)
                tile=Image.fromarray(srcpixels[yy[:,None],xx[None,:]])
            x,y=(ti%5)*204+6,(ti//5)*204+6
            atlas.paste(tile,(x,y));rec.update(uv_min=lo.tolist(),uv_max=(lo+span).tolist());material_records.append(rec)
            for group in sm['groups']:
                remap={}
                for vi in sorted(set(group['indices'])):
                    v=sm['vertices'][vi];remap[vi]=len(p)
                    pos=attach @ np.r_[v['position'],1.]
                    normal=attach[:3,:3] @ v['normal'];normal/=max(np.linalg.norm(normal),1e-12)
                    p.append(BASIS @ pos[:3]);n.append(BASIS @ normal)
                    # Each source submesh occupies one wrapped tile. Source negative
                    # V convention is kept as frac(V); texture storage origin is top.
                    u,vv=(np.array(v['uv0'])-lo)/span;uv.append([(x+u*191)/1024,(y+vv*191)/1024])
                    names=[group['boneNames'][i] for i in v['paletteIndices']]
                    w,drop=reduce_weights(names,v['weights'],part['attachBone']);weights.append(w);lost.append(drop)
                for i in range(0,len(group['indices']),3):
                    a,b,c=group['indices'][i:i+3];indices.extend([remap[a],remap[c],remap[b]])
    p=np.array(p); n=np.array(n)
    floor=float(p[:,1].min()); factor=height/float(np.ptp(p[:,1]))
    p[:,1]-=floor;p*=factor
    # Drop only redundant exporter root. Keep the anatomy/face hierarchy so every
    # shared source name can be traced; facial weights are collapsed, not hidden.
    bones=[dict(j) for j in main if j['name']!='EXP_GOK_000']
    names=[j['name'] for j in bones]
    globals_=[]; parents=[]
    for j in bones:
        w=by[j['name']].copy();w[:3,:3]=BASIS@w[:3,:3]@BASIS
        w[:3,3]=BASIS@w[:3,3];w[1,3]-=floor;w[:3,3]*=factor
        if j['name']=='b_C_Base':w=np.eye(4)
        globals_.append(w)
        pn=main[j['parent']]['name'] if j['parent']>=0 else None
        parents.append(names.index(pn) if pn in names else None)
    for name,parent,offset in [('item_socket.R','b_R_Hand',[0,0,.04]),('grab_anchor','b_C_Chest',[0,0,.27]),('shield_anchor','b_C_Base',[0,0,0])]:
        names.append(name);parents.append(names.index(parent));w=globals_[parents[-1]].copy();w[:3,3]+=np.array(offset)*factor
        if name=='grab_anchor':
            # 2026-10-08: the held victim sat inside him at (2.33, 0) (Mario holds at (7.64, -1.56)), and under the chest the
            # anchor turned with the grab pose's twist. ThrowN hangs off the root instead, unrotated, 5.3 in front of the
            # chest and 1.5 below it, so the hold point stays in front of him whatever the pose.
            parents[-1]=names.index('b_C_Base');w=np.eye(4);w[:3,3]=globals_[names.index('b_C_Chest')][:3,3]+np.array(offset)*factor+np.array([0.,-1.5,5.3])
        if name=='shield_anchor':
            # 2026-10-11 (owner: the shield bubble sat at his forearms; then, pointed at YRotN, the whole body grew when he shielded). The guard code scales the SHIELD part's joint by the
            # shield size (ftCo_Guard.c:216,338,806,880 HSD_JObjSetScale(parts[x8->x11].joint)), so the part must be a LEAF with no weights. Retail's ThrowN is one: a leaf under YRotN with an
            # identity local. This is the same: hung off the root like grab_anchor, unrotated, at the pelvis height on the body line (the plan puts YRotN at the hip height and gives
            # children of the root a local of identity there), so the bubble is centred on his body and scaling it moves nothing else.
            w=np.eye(4);w[1,3]=globals_[names.index('b_C_Pelvis')][1,3]
        globals_.append(w)
    locals_=[np.linalg.inv(globals_[par])@w if par is not None else w for par,w in zip(parents,globals_)]
    jts=[];wts=[]
    for pairs in weights:
        jts.append([names.index(a) for a,b in pairs]+[0]*(4-len(pairs)))
        wts.append([b for a,b in pairs]+[0.]*(4-len(pairs)))
    return dict(positions=p,normals=n,uv=np.array(uv),joints=jts,weights=wts,indices=indices,
                names=names,parents=parents,locals=locals_,worlds=globals_,factor=factor,floor=floor,atlas=atlas,
                report={'vertices':len(p),'triangles':len(indices)//3,'export_bones':len(names),'estimated_plan_joints':len(names)+3,
                        'weighted_bones':len({a for pairs in weights for a,b in pairs}), 'max_influences':max(map(len,weights)),
                        'source_influences_reduced_vertices':sum(x>1e-8 for x in lost),'max_discarded_weight':max(lost),
                        'mean_discarded_weight':float(np.mean(lost)),'height':height,'source_floor':floor,'scale':factor,
                        'materials':material_records,'facial_weights':'f_* -> b_C_Head','physics':'hair rigid head; belt rigid pelvis',
                        'axis':'glTF (x,y,-z), determinant -1; normals transformed and triangle winding reversed'} )


def sample_track(keys, frames, rotation=False):
    keys=np.asarray(keys,float);times=keys[:,0]
    values=keys[:,1:5] if rotation else keys[:,1:4]*keys[:,4:5]
    if rotation:
        values/=np.linalg.norm(values,axis=1)[:,None]
        if len(keys)==1:return np.repeat(values,len(frames),axis=0)
        return Slerp(times,Rotation.from_quat(values))(np.clip(frames,times[0],times[-1])).as_quat()
    return np.stack([np.interp(frames,times,values[:,i]) for i in range(3)],axis=1)


WAIT_CLIP = 0   # GOK_BAS_STAND: XV2's ground idle (remake phase 3, owner 2026-10-11: no hover; the floating idle GOK_BAS_STAND_S is clip 1)


ROLL_DISTANCE=24.82   # world units a roll travels: Goku's own earlier roll (owner 2026-10-11: 52, Mewtwo's measured reach, was too long); Mario's is 33  # authored 24.82 = 27.3 / SIZE 1.1 (was 22.75 at 1.2): the in-game roll travels 27.3 at the built size (owner 2026-10-11)
REMAKE_REPORT=[]   # filled by row_specs: what remake_apply did to each row


def row_specs(source):
    out={}
    def direct(row,num,loop=False,frames=None,start=0,status='adapted candidate'):
        out[row]={'clip':'clip:'+EAN+'/'+str(num),'loop':loop,'frames':frames,'start':start,'status':status}
    for row,num,loop in [('Wait',WAIT_CLIP,True),('WalkMiddle',2,True),('Run',3,True),('JumpF',5,False),('JumpB',8,False),
                          ('JumpAerialF',6,False),('Fall',12,True),('Guard',30,True),('GuardOn',30,False),
                          ('GuardOff',32,False),('EscapeF',26,False),('EscapeB',27,False),('EscapeN',28,False),
                          ('DamageN1',20,False),('DamageFlyN',22,True),('Furafura',24,True),('EntryStart',87,False)]:direct(row,num,loop)
    direct('CatchWait',81,True,30,24,'authored hold from source catch pose');out['CatchWait']['hold_source']=24
    # 2026-10-08: GuardOn played all 130 frames of GRD_KAMAE, so the shield rose ~2 s late (Mario's bubble is up by f8);
    # Melee lengths: GuardOn 8, GuardOff 16
    out['GuardOn'].update(frames=8,status='source crop: GOK_GRD_KAMAE f0-7 (Melee GuardOn length)')
    out['GuardOff'].update(frames=16,time_factor=1.8,status='source crop: GOK_GRD_L at x1.8 (Melee GuardOff length)')
    # 2026-10-08 length pass (row-lengths.json: Goku vs Mario measured in game). The jump pose must last the rise.
    # 2026-10-10 (ws/goku-jumpf, owner-approved): 55 frames outlasted Goku's 48-frame hop, so he never reached Fall and
    # carried ground momentum through the air (run-jump too long). Same source span (18 source frames), played at x0.5
    # in 36 frames (Falcon's JumpF ends ~35): the whole pose is sped up, nothing is cut.
    out['JumpF'].update(frames=36,time_factor=.5,status='source: GOK_BAS_JUMP_FRONT_00 at x0.5 (36 frames, ends before a hop lands so the fighter enters Fall like Falcon)')
    out['JumpB'].update(frames=36,time_factor=.5,status='source: GOK_BAS_JUMP_BACK_00 at x0.5 (36 frames)')
    out['JumpAerialF'].update(frames=60,time_factor=.27,status='source: GOK_BAS_JUMP_FRONT_01 at x0.27 (60 frames)')
    out['EscapeN'].update(frames=24,time_factor=1.85,status='source: GOK_BAS_STEP_L_S at x1.85: spot dodge at Melee length (Mario 23)')
    out['Furafura']['hold_source']=30
    out['EscapeF']['root_motion']=True;out['EscapeB']['root_motion']=True
    direct('Landing',7,False,20,10);direct('KneeBend',5,False,8)
    # Locomotion pass 2026-10-08 (owner: "no dashback/turn around animation"). XV2 has no turn,
    # crouch or ground-dash clips; these are source crops plus authored yaw/blends (PARITY.md).
    W,RUN,JUMP,BOOST0,BOOST2=WAIT_CLIP,3,4,17,19
    out['Wait']['status']='source: GOK_BAS_STAND (XV2 ground idle), looped; feet planted on the floor (remake phase 3)'
    def ean(n):return 'clip:'+EAN+'/'+str(n)
    direct('Turn',W,False,12,0,'authored: Wait pose, 180-degree yaw ramp');out['Turn'].update(hold_source=0,yaw=-180)
    direct('TurnRun',RUN,False,18,0,'authored: GOK_BAS_RUN crop + 180-degree yaw (grounded; phase 3)');out['TurnRun'].update(yaw=-180)
    direct('Dash',RUN,False,14,0,'source crop: GOK_BAS_RUN f0-13, the start of the run (XV2 has no ground dash; the boost launch is a flight clip; phase 3)')
    direct('RunBrake',W,False,16,0,'source crop: GOK_BAS_STAND (XV2 has no ground skid; the boost brake is a flight clip; phase 3)')
    direct('Squat',JUMP,False,7,50,'source crop: GOK_BAS_JUMP landing crouch f50-56')
    direct('SquatWait',JUMP,True,30,56,'authored hold of the crouch (GOK_BAS_JUMP f56)');out['SquatWait']['hold_source']=56
    direct('SquatRv',JUMP,False,10,56,'source crop: GOK_BAS_JUMP f56-65 rise, eased into Wait');out['SquatRv'].update(blend_to=ean(W),blend_frames=5)
    # 2026-10-09 floating-idle pass (owner #14): rows that leave/enter Wait ease from/to the floating idle pose
    out['Landing'].update(blend_to=ean(W),blend_frames=6);out['GuardOff'].update(blend_to=ean(W),blend_frames=5)
    out['GuardOn'].update(blend_from=dict(clip=ean(W),frame=0,frames=4));out['Dash'].update(blend_from=dict(clip=ean(W),frame=0,frames=3))
    out['Squat'].update(blend_from=dict(clip=ean(W),frame=0,frames=3))
    direct('JumpAerialB',9,False,60,0,'source: GOK_BAS_JUMP_BACK_01 at x0.27 (60 frames, Melee lasts the rise)');out['JumpAerialB']['time_factor']=.27
    # Ledge pass 2026-10-08 (owner: "grabbing ledges doesn't work right"). XV2 has no ledge animations. The hang is
    # GOK_BAS_JUMP_BACK_00 f12 (both arms overhead) leaned 40 degrees so the hands sit 19.25 up and 9.46 forward of
    # the root; TransN = -that puts the hands on the ledge point (Mario's CliffWait TransN is (z -1.88, y -11.76)).
    # Frame counts follow Mario's rows (CliffCatch reaches CliffWait in 7 frames).
    JB,HANG=8,[0.,-19.25,-9.46]
    hang=lambda y=0.:[HANG[0],HANG[1]+y,HANG[2]]
    hold_hang=dict(hold_source=12,pitch=40.,root_motion=True)
    bf=dict(clip=ean(JB),frame=12,pitch=40.,frames=8)
    direct('CliffCatch',JB,False,8,12,'authored: overhead hang pose dropping onto the ledge');out['CliffCatch'].update(hold_hang,root_path=[[0,*hang(3.)],[1,*hang()]])
    direct('CliffWait',JB,True,60,12,'authored: held overhead hang');out['CliffWait'].update(hold_hang,root_path=[[0,*hang()],[1,*hang()]])
    up=[[0,*hang()],[.55,0.,-2.,1.],[1,0.,-1.,6.]]  # ends just below the floor so the climb lands in Wait
    for row,frames,tf in [('CliffClimbQuick',33,.6),('CliffClimbSlow',58,.35)]:
        direct(row,JUMP,False,frames,46,'authored: hang to standing, BAS_JUMP crouch crop, TransN path ledge to stage');out[row].update(time_factor=tf,blend_from=bf,blend_to=ean(W),blend_frames=6,root_motion=True,root_path=up)
    for row,frames,tf in [('CliffAttackQuick',55,.7),('CliffAttackSlow',69,.55)]:
        direct(row,62,False,frames,0,'authored: hang to GOK_ATC_012 low sweep on the stage');out[row].update(time_factor=tf,blend_from=bf,blend_to=ean(W),blend_frames=6,root_motion=True,root_path=[[0,*hang()],[.3,0.,0.,4.],[1,0.,0.,6.]])
    for row,frames,tf in [('CliffEscapeQuick',49,.5),('CliffEscapeSlow',78,.33)]:
        direct(row,26,False,frames,0,'authored: hang to forward roll (BAS_STEP_F_S) onto the stage');out[row].update(time_factor=tf,blend_from=bf,blend_to=ean(W),blend_frames=6,root_motion=True,root_path=[[0,*hang()],[.3,0.,0.,3.],[1,0.,0.,22.]])
    for row,frames in [('CliffJumpQuick1',13),('CliffJumpSlow1',18)]:
        direct(row,JB,False,frames,12,'authored: hang pulling up to the ledge top');out[row].update(hold_hang,root_path=[[0,*hang()],[1,0.,0.,1.]])
    for row in ('CliffJumpQuick2','CliffJumpSlow2'):
        direct(row,5,False,None,0,'source: GOK_BAS_JUMP_FRONT_00 (the ledge jump)')
    moves={m['input']:m for m in source.doc['behavior']['moves']}
    move_rows={'jab':['Attack11','Attack12','Attack13'],'rapid_jab':['Attack100Start','Attack100Loop','Attack100End'],'dash_attack':['AttackDash'],'ftilt':['AttackS3S'],
               'utilt':['AttackHi3'],'dtilt':['AttackLw3'],'fsmash':['AttackS4S'],'usmash':['AttackHi4'],'dsmash':['AttackLw4'],
               'nair':['AttackAirN'],'fair':['AttackAirF'],'bair':['AttackAirB'],'uair':['AttackAirHi'],'dair':['AttackAirLw'],
               'grab':['Catch'],'fthrow':['ThrowF'],'special_n':['KameCharge'],'special_s':['Rush'],'special_hi':['Recovery']}
    for key,rows in move_rows.items():
        move=moves[key];parity=source.parity[move['id']]
        if parity['relation']=='no_counterpart':continue
        for i,row in enumerate(rows):
            sub=source.subs[move['subactions'][min(i,len(move['subactions'])-1)]]
            script=source.scripts[sub['scripts']['main']]
            bindings=[e for e in script['events'] if e['op']=='engine.animation' and e['args'].get('binding',{}).get('clip')
                      and source.clips[e['args']['binding']['clip']]['engine']['xv2.pc'].get('camera') is False
                      and '.fce.' not in e['args']['binding']['clip']]
            hits=[e for e in script['events'] if e['op']=='hitbox.create']
            end=max([e['frame']+e['args']['engine']['xv2.pc']['duration_frames']+12 for e in hits]+[32])
            out[row]={'clip':sub['clip'],'loop':False,'frames':end,'start':0,'status':'parity-selected candidate; runtime unverified',
                      'move':move['id'],'subaction':sub['id'],'events':bindings,'hit_frames':[e['frame'] for e in hits],
                      'parity':parity,'ignored_time_scale':[e for e in script['events'] if e['op']=='timer.set_anim_rate']}
    # 2026-10-08 move review (PARITY.md "Move review"): rows whose parity-selected BAC pose hit the
    # wrong direction or frame are re-cropped from the XV2 clip whose limb actually reaches there.
    for row,c in json.loads((PORT/'tools/move-crops.json').read_text()).items():
        out[row]={'clip':'clip:'+EAN+'/'+str(c['clip']),'loop':False,'frames':c['frames'],'start':c['start'],
                  'status':'move review re-crop: '+c['note'],'move':c['move']}
    # Cross-port rows (tools/cross-port.json, tools/cross_port.py): a retail Melee action retargeted onto this rig; the clip is the solved
    # npz, the XV2 clip below is only a placeholder for the lookups (its channels are replaced in animations()).
    ean_=lambda n:'clip:'+EAN+'/'+str(n)
    def put_cross_ports():
        # applied here and again after the remake / rowmap passes below: those rewrite rows by name (the grab and throw slots), a cross-port row must be the last word
        for row,c in cross_registry().items():
            npz=ROOT/'_build/goku-xv2/cross-port'/row/'clip.npz'
            if not npz.exists():raise SystemExit('cross-port clip missing: run python ports/goku-xv2/tools/cross_port.py (needs GW_ISO_VANILLA)')
            nat=int(np.load(npz)['frames'])
            fit=c.get('fit_frames') if os.environ.get('GOKU_LOCO_LEN','row')!='retail' else None   # locomotion sets: the row keeps Goku's current length unless GOKU_LOCO_LEN=retail
            out[row]={'clip':'clip:'+EAN+'/0','loop':bool(c.get('loop')),'frames':int(fit or nat),'start':0,'move':c['move'],
                      'status':'CROSS-PORT: Melee %s %s (%s)'%(c['fighter'].capitalize(),c['action'],c['reason']),'cross_port':dict(c,npz=str(npz))}
            # locomotion sets (cross-port-loco-<set>.json): a retail Turn / RunBrake starts and ends in that fighter's own stance, not Goku's, so the row
            # eases from the row he comes from and into the row he returns to (the shipped rows do the same: Landing, GuardOff, SquatRv ...)
            clipof={'Wait':WAIT_CLIP,'Run':3}
            if c.get('root_t'):out[row]['root_motion']=True   # ledge rows: the source's TransN path is the row's root motion (the engine places the fighter at ledge + TransN)
            if c.get('ease_from'):out[row]['blend_from']=dict(clip=ean_(clipof[c['ease_from'][0]]),frame=0,frames=int(c['ease_from'][1]))
            if c.get('ease_to'):out[row].update(blend_to=ean_(clipof[c['ease_to'][0]]),blend_frames=int(c['ease_to'][1]))
            if c.get('turn'):out[row]['turn_align']=True   # a 180-degree turn: the pelvis is lined up with the row it comes from and ends on that row's pose TURNED 180 (see turn_align below)
    put_cross_ports()
    # Custom move art deliberately has separate charge/release stages. These are
    # local design crops, not claims about source BAC state-machine equivalence.
    charge=out['KameCharge'];charge.update(frames=135,loop=True,hold_source=40)   # 135: the XV2 charge SE (2.1 s) plays once per loop; the script restarts when the clip wraps
    # Kamehameha (2026-10-08 specials pass): XV2's own charge entry (skill 000_GOK_KMH.bac 12) cups the hands f0-40,
    # holds at f47 and fires f48-120. Charge = f0-40 then hold f40; the three releases fire from f48, longer per tier.
    charge.update(status='PICK provisional (skill KMH BAC 12): cup hands f0-40, held at f40 while charging')
    for row,frames,tf in [('KameTap',30,1.4),('KameMid',45,1.0),('KameFull',60,.8)]:
        out[row]={**charge,'frames':frames,'loop':False,'hold_source':None,'start':48,'time_factor':tf,'events':[],
                  'status':'PICK provisional (skill KMH BAC 12): fire from f48 at x%g, %d frames'%(tf,frames)}
    out['Rush']['frames']=max(66,out['Rush']['frames'])   # remake phase 2: the whole XV2 knockback attack (BOOST_F_00 > STEP_F_S > ATC_013, strike at f40-43), so its sample hitbox lands inside the row
    # Instant Transmission (up B, geno.cape): XV2 evasive skill 001_GOK_KUR. Start = the vanish f0-18 over 26 frames
    # (the cape decides at 26); ITEnd = the reappear (f70-106) over 36 frames.
    kur=None
    for cid,c in source.clips.items():
        if c['name']=='GOK_ESC_KUR_C':kur=cid
    pow_=next((cid for cid,c in source.clips.items() if c['name']=='CMN_BLT_POW_C'),None)
    if kur:
        out['Recovery']={'clip':kur,'loop':False,'frames':26,'start':0,'time_factor':.7,'library':True,
                         'status':'PICK provisional (skill ESC 001_GOK_KUR BAC 0): Instant Transmission vanish f0-18'}
        out['ITEnd']={'clip':kur,'loop':False,'frames':36,'start':70,'library':True,
                      'status':'PICK provisional (skill ESC 001_GOK_KUR BAC 0): Instant Transmission reappear f70-106'}
        # down B tap: the Z-vanish blink (counter window), reappear strike behind = Riposte (his forward kick)
        out['Counter']={'clip':kur,'loop':False,'frames':46,'start':0,'time_factor':.39,'library':True,
                        'status':'PICK provisional (skill ESC 001_GOK_KUR): Z-vanish blink as the counter stance'}
    if pow_:
        out['KiCharge']={'clip':pow_,'loop':True,'frames':60,'start':20,'library':True,
                         'status':'PICK provisional (skill BLT 1080_CMN_POW BAC 11): power-up stance, looped while down B is held'}
    # 2026-10-09 specials pass: Super Kamehameha (skill ULT 000_GOK_CKM: charge f0-30, beam from f70) and the Dragon Rush
    # combo (BAC 427 clip GOK_ATC_023, hit f10, from f4). Library clips bound by declared row (fighter.rows).
    ckm=next((cid for cid,c in source.clips.items() if c['name']=='GOK_ULT_CKM_C'),None)
    atc23=next((cid for cid,c in source.clips.items() if c['name']=='GOK_ATC_023'),None)
    if ckm:
        out['KameSuper']={'clip':ckm,'loop':False,'frames':70,'start':40,'library':True,
                          'status':'PICK provisional (skill ULT 000_GOK_CKM): Super Kamehameha, fire from source f70 (Melee f30)'}
    # KameStore1..4: the charge put away (shield cancel, or the full-chant auto-store), one state per tier so each flash can differ: the cupped-hands pose
    # held at clip frame 40 for 9 frames (the natives' Cancel states last 8)
    for i in range(1,5):
        out['KameStore%d'%i]={**charge,'frames':9,'loop':False,'hold_source':40,'start':40,'library':True,'status':'PICK provisional (skill KMH BAC 12 f40): the charge stored, tier %d flash'%i}
    # the two extra release tiers (thin = tier 1, max = tier 4) use the same fire clip as Tap/Mid/Full, from clip frame 48
    out['KameThin']={**charge,'frames':36,'loop':False,'hold_source':None,'start':48,'time_factor':1.2,'events':[],'library':True,
                     'status':'PICK provisional (skill KMH BAC 12): fire from f48 at x1.2, 36 frames (tier 1)'}
    out['KameMax']={**charge,'frames':75,'loop':False,'hold_source':None,'start':48,'time_factor':0.7,'events':[],'library':True,
                    'status':'PICK provisional (skill KMH BAC 12): fire from f48 at x0.7, 75 frames (tier 4)'}
    if atc23:
        out['RushCombo']={'clip':atc23,'loop':False,'frames':36,'start':4,'library':True,
                          'status':'PICK provisional (BAC 427 clip GOK_ATC_023, hit f10): Dragon Rush follow-up flurry'}
    direct('Riposte',58,False,46,1,'PICK provisional (BAC 475 clip GOK_ATC_008, from f1, 46 frames so the air counter is not shorter than 0.55x Melee): Z-vanish reappear kick')
    out['ThrowF'].update(frames=32,time_factor=5.,events=[],status='authored 5x primary-clip crop: source release 90 -> target18; victim choreography omitted')
    CROSS=set(cross_registry())   # rows whose clip is a cross-port (a retail Melee action retargeted): no placeholder or alias over them
    for row in ['ThrowB','ThrowHi','ThrowLw','CatchAttack']:
        if row in CROSS:continue
        direct(row,81,False,32,24,'authored-needed placeholder: held catch pose');out[row]['hold_source']=24
    for base,aliases in [('AttackS3S',['AttackS3Hi','AttackS3HiS','AttackS3LwS','AttackS3Lw']),
                          ('AttackS4S',['AttackS4Hi','AttackS4HiS','AttackS4LwS','AttackS4Lw']),('Catch',['CatchDash'])]:
        for row in aliases:
            if row in CROSS:continue
            out[row]={**out[base],'status':'explicit prototype reuse of '+base+'; directional pose authored-needed'}
    # 2026-10-08 damage / down / tech / capture / thrown / grab-throw / item rows (tools/rowmap.py; FIDELITY.md)
    import rowmap
    byname={}
    for cid,c in source.clips.items():
        if c['engine']['xv2.pc'].get('camera') is False and '.fce.' not in cid:byname.setdefault(c['name'],cid)
    rowmap.apply(out,byname.get,None)
    for row in rowmap.ROWS:
        if row in out:out[row]['library']=True   # CMN clips may scale bones; tolerated as in the library
    # REMAKE phase 1 (2026-10-11): the owner's picks (remake-picks.json, the LAB picker's file) go on the rows remake-rows.json lists; a row whose
    # clip already is the pick keeps its tuned crop. GAP slots have no pick and change nothing.
    import remake_apply
    REMAKE_REPORT[:]=remake_apply.apply(out,source,byname.get,EAN,rowmap.ALIASES)
    put_cross_ports()
    for r in REMAKE_REPORT:
        if r.get('row') in CROSS:r.update(action='superseded',why='the row is a cross-port (tools/cross-port.json)')
    # Homing dash strike (XV2 BAC 476, Guard+Heavy): BOOST_F_00 f0-19 then ATC_008 from f20, 66 frames (the BAC's own two bindings, played at speed 1).
    # Entered from the shield by a combo route (combo.json Guard>Homing); a row of its own so the clip chain is the one XV2 plays.
    # Flight aerials (phase 4): the aerial rows again, as declared rows of their own, for the Geno states FlightNair..FlightDair (their script and row are the aerial's)
    for new,base in (('FlightNair','AttackAirN'),('FlightFair','AttackAirF'),('FlightBair','AttackAirB'),('FlightUair','AttackAirHi'),('FlightDair','AttackAirLw')):
        if base in out:out[new]={**out[base],'ground_as':base,'status':'flight aerial: the row of '+base}
        if base in out and out[new].get('cross_port'):   # the cross-port report is looked up by row name: give the copy its own folder (the solved clip stays the original's)
            src=ROOT/'_build/goku-xv2/cross-port'/base;dst=ROOT/'_build/goku-xv2/cross-port'/new;dst.mkdir(parents=True,exist_ok=True)
            for f in src.glob('*.json'):shutil.copyfile(f,dst/f.name)
    # Rolls are Instant Transmission teleports (phase 4, owner 2026-10-11, like Mewtwo's): the XV2 vanish pose (ESC_KUR f0-18), a hidden gap, the reappear pose (f70-106).
    # Melee timing from Mewtwo's own roll measured in this engine (tools/lua roll_probe.lua): 37 frames, intangible f5-22, travel 52; the body moves inside the hidden gap.
    kur=byname.get('GOK_ESC_KUR_C')
    if kur:
        def bk(fr,st,en):return {'frame':fr,'args':{'binding':{'clip':kur,'start_frame':st,'end_frame':en,'speed':1}}}
        for row,sign in (('EscapeF',1.),('EscapeB',-1.)):
            out[row]={'clip':kur,'loop':False,'frames':37,'start':0,'events':[bk(0,0,18),bk(5,70,106)],'library':True,'root_motion':True,
                      'root_path':[[0,0.,0.,0.],[.135,0.,0.,0.],[.42,0.,0.,sign*ROLL_DISTANCE],[1,0.,0.,sign*ROLL_DISTANCE]],
                      'status':'PICK (owner 2026-10-11, phase 4): Instant Transmission roll: ESC_KUR vanish f0-18, hidden f5-22 (the body travels %d units inside the gap), reappear f70-106; 37 frames like the Mewtwo roll'%ROLL_DISTANCE}
        out['EscapeN']={'clip':kur,'loop':False,'frames':24,'start':0,'events':[bk(0,0,18),bk(3,70,106)],'library':True,
                        'status':'PICK (owner 2026-10-11, phase 4): Instant Transmission spot dodge: vanish in place, hidden f3-16, reappear'}
    for row,clipname,frames in (('FlightUp','GOK_BAS_BUKUU_UP',50),('FlightF','GOK_BAS_BUKUU_F_S',40),('FlightB','GOK_BAS_BUKUU_B_S',40)):
        if byname.get(clipname):   # Up B flight (phase 3): the XV2 fly clips, looped; the air has no ground contact
            out[row]={'clip':byname[clipname],'loop':True,'frames':frames,'start':0,'status':'PICK (owner 2026-10-11): Up B flight, XV2 %s looped'%clipname}
    b0,a8=byname.get('GOK_BAS_BOOST_F_00'),byname.get('GOK_ATC_008')
    if b0 and a8:
        bind=lambda c,fr:{'frame':fr,'args':{'binding':{'clip':c,'start_frame':0,'end_frame':source.clips[c]['frames']-1,'speed':1}}}
        out['Homing']={'clip':b0,'loop':False,'frames':66,'start':0,'events':[bind(b0,0),bind(a8,20)],
                       'status':'PICK (owner, remake phase 1): XV2 BAC 476 homing dash strike (Guard+Heavy): BOOST_F_00 f0-19, ATC_008 from f20; 66 frames'}
    gameplay_path=SG.path()
    if gameplay_path.exists():
        gameplay=json.loads(gameplay_path.read_text())
        bymotion={r['motion']:r['name'] for r in spec.clip_table()['rows']}
        for move in gameplay['moves']:
            for motion in move['motions']:
                row=bymotion[motion]
                if row in out:
                    out[row]['frames']=max(out[row].get('frames') or 0,move.get('minimum_clip_frames') or 0)
                    out[row]['active_end']=max([out[row].get('active_end') or 0]+[a+l for a,l in move.get('windows',[])])
        for sp in gameplay.get('special_adaptations',[]):
            row=sp.get('state') or sp.get('name')
            if row in out:out[row]['frames']=max(out[row].get('frames') or 0,sp.get('minimum_clip_frames') or 0)
    apply_splices(out,source)
    return out


SPLICE_DROP=('events','hold_source','time_factor','cross_port','blend_from','blend_to','blend_frames','yaw','pitch')   # row keys the baked recipe replaces


def splice_targets(r):
    """Engine rows a recipe targets: its `row`, or the rows of its `move` in gameplay.json (stripped or full)."""
    if r.get('row'):return [r['row']]
    gp=SG.path()
    if not gp.exists():return []
    bymotion={x['motion']:x['name'] for x in spec.clip_table()['rows']}
    mv=next((m for m in json.loads(gp.read_text(encoding='utf-8-sig'))['moves'] if m['name']==r['move']),None)
    return [bymotion[m] for m in (mv or {}).get('motions',[]) if m in bymotion]


def apply_splices(out,source):
    """Splice recipes (splices.json, tools/splice.py) become rows. A recipe with "wired": true REPLACES its target row(s) (the gameplay
    minimum length still pads it); every recipe, wired or not, also gets the CLIPS library row `s<recipe>` so it can be viewed. A preview row
    takes its target row's ground mode (`ground_as`) so it sits on the floor exactly as the wired row would."""
    doc=SP.load()
    byname=clip_by_name(source)
    for rname,r in doc['recipes'].items():
        first=next((byname[sg['clip']] for sg in r['segments'] if sg['clip'] in byname),out['Wait']['clip'])
        targets=[t for t in splice_targets(r) if t in out]
        n=SP.recipe_length(r)
        ref=dict(name=rname,summary=' + '.join(SP.segment_summary(sg) for sg in r['segments']),wired=bool(r.get('wired')),example=bool(r.get('example')))
        if r.get('wired'):
            if not targets:raise SystemExit('splice recipe %s is wired but its target %s has no row'%(rname,r.get('row') or r.get('move')))
            for t in targets:
                for k in SPLICE_DROP:out[t].pop(k,None)
                out[t].update(clip=first,loop=bool(r.get('loop')),start=0,frames=max(out[t].get('frames') or 0,n),splice=ref,
                              status='SPLICED: recipe %s (%s)'%(rname,ref['summary']))
        lib=SP.library_name(rname)
        out[lib]={'clip':first,'loop':bool(r.get('loop')),'frames':n,'start':0,'library':True,'splice':dict(ref,preview_of=targets),'splice_library':True,
                  'ground_as':targets[0] if targets else None,'active_end':(out[targets[0]].get('active_end') if targets else None),
                  'status':'SPLICE %s: %s'%('WIRED' if r.get('wired') else 'preview',ref['summary'])}


def clip_by_name(source):
    byname={}
    for cid,c in source.clips.items():
        if c['engine']['xv2.pc'].get('camera') is False and '.fce.' not in cid:byname.setdefault(c['name'],cid)
    return byname


class XV2Clip:
    """An XV2 clip as a splice source: sampled with the same channel handling as animations() (BASIS conjugation, pelvis/base translation scaled)."""
    def __init__(self,source,mesh,cid):
        c=source.clips[cid];self.length=c['frames']-1;self.name=c['name']
        self.ch={(t['bone'],t['channel']):t['keys'] for t in source.blob(c['keys'])}
        self.bones=set(mesh['names']);self.factor=mesh['factor']
        self.rest_hip=mesh['locals'][mesh['names'].index('b_C_Pelvis')][:3,3]

    def sample(self,tm):
        tm=np.asarray(tm,float);n=len(tm);rot={};hips=np.repeat(self.rest_hip[None],n,axis=0);root=np.zeros((n,3))
        for (bone,kind),keys in self.ch.items():
            if kind=='Rotation' and bone in self.bones:
                r=Rotation.from_quat(sample_track(keys,tm,True)).as_matrix()
                rot[bone]=Rotation.from_matrix(BASIS[None]@r@BASIS[None]).as_quat()
            elif kind=='Position' and bone=='b_C_Pelvis':hips=sample_track(keys,tm)@BASIS*self.factor
            elif kind=='Position' and bone=='b_C_Base':root=sample_track(keys,tm)@BASIS*self.factor
        return SP.Clip(rot,np.asarray(hips,float),np.asarray(root,float))


def cross_npz(ref):
    """The cross-port clip.npz of `melee:<fighter>/<action>`: the registry row that already holds it, else one solved with the retarget tool
    (cross_port.tool(), needs the vanilla disc) and cached under _build/goku-xv2/splice-cross."""
    fighter,_,action=ref[len('melee:'):].partition('/')
    if not (fighter and action):raise SP.SpliceError('cross-port ref must be melee:<fighter>/<action>: '+ref)
    for row,c in cross_registry().items():
        npz=ROOT/'_build/goku-xv2/cross-port'/row/'clip.npz'
        if c['fighter']==fighter and c['action']==action and npz.exists():return npz
    out=ROOT/'_build/goku-xv2/splice-cross'/(fighter+'_'+action)
    if not (out/'clip.npz').exists():
        import cross_port
        if not os.environ.get('GW_ISO_VANILLA'):raise SP.SpliceError('%s needs the vanilla disc: source .env (GW_ISO_VANILLA) first'%ref)
        cross_port.tool().run(fighter,action,str(cross_port.FIGHTER_JSON),str(out))
    return out/'clip.npz'


def splice_context(source,mesh):
    """What tools/splice.py needs from the XV2 adapter: {resolve(ref) -> source, rig, move_rows=(move -> motions, motion -> row)}."""
    rig=SP.Rig(list(mesh['names']),[-1 if p is None else p for p in mesh['parents']],
               np.array([Rotation.from_matrix(m[:3,:3]).as_quat() for m in mesh['locals']]))
    byname=clip_by_name(source);cache={}
    def resolve(ref):
        if ref not in cache:
            if ref.startswith('melee:'):cache[ref]=SP.ArraySource(SP.npz_clip(cross_npz(ref)),ref)
            elif ref in byname:cache[ref]=XV2Clip(source,mesh,byname[ref])
            else:raise SP.SpliceError('unknown XV2 clip '+ref)
        return cache[ref]
    gp=SG.path()
    mm={m['name']:m['motions'] for m in json.loads(gp.read_text(encoding='utf-8-sig'))['moves']} if gp.exists() else {}
    return dict(resolve=resolve,rig=rig,move_rows=(mm,{r['motion']:r['name'] for r in spec.clip_table()['rows']}))


def splice_bake(source,mesh,rows,only=None):
    """{recipe: (Clip, report)} for every recipe a row in `rows` uses (or just `only`). A preview-only recipe that cannot be baked (a cross-port
    clip without the disc) is dropped from `rows` with a warning; a wired one stops the build."""
    doc=SP.load();ctx=splice_context(source,mesh);baked={}
    for name,rs in list(rows.items()):
        ref=rs.get('splice')
        if not ref or ref['name'] in baked or (only and ref['name']!=only):continue
        try:baked[ref['name']]=SP.bake(ref['name'],doc['recipes'][ref['name']],ctx['resolve'],ctx['rig'])
        except (SP.SpliceError,SystemExit,KeyError,OSError) as e:
            if ref['wired']:raise
            print('splice %s: preview skipped (%s)'%(ref['name'],e),file=sys.stderr)
    for name in [n for n,rs in rows.items() if rs.get('splice') and rs['splice']['name'] not in baked]:del rows[name]
    return baked


def splice_preview(recipe,file=None):
    """Reduced build of one recipe: the shipped rows plus the one library row `s<recipe>` (no XV2 clip library), built into
    _build/goku-xv2/splice-preview (GOKU_AUTHOR) so the shipped author-source package is not touched; then prints the LAB CLIPS command."""
    if recipe not in SP.load(file)['recipes']:raise SystemExit('no recipe %s in %s'%(recipe,file or SP.SPLICES))
    if os.environ.get('GOKU_AUTHOR','author-source')=='author-source':
        env=dict(os.environ,GOKU_AUTHOR='splice-preview')
        cmd=[sys.executable,str(Path(__file__).resolve()),'--splice-only',recipe,'--build']+(['--splice-file',str(file)] if file else [])
        rc=subprocess.run(cmd,cwd=ROOT,env=env).returncode
        if rc:return rc
    print("\nView it (PowerShell):  $env:MELEE_MODS_DIR='%s'; ports/goku-xv2/tools/clips.ps1 %s"%(ROOT/'_build/goku-xv2/splice-preview/package/mods',SP.library_name(recipe)))
    return 0


# 2026-10-11 remake phase 3 (owner: no hover; grounded clips, feet on the floor exactly): every standing ground row is PLANTED: on every frame its pelvis track is shifted so the
# lowest skinned vertex sits exactly on the floor (never above, never below). Still anchored (frame-0 anchor, lifted only on frames that would sink): aerial attack rows,
# shield-break flight, the hanging/climbing ledge rows, items and the bury rows. HOVER_Y is gone.
PLANT_ROWS = ('Wait', 'Walk', 'Dash', 'Run', 'Turn', 'Guard', 'KneeBend', 'Landing', 'Appeal', 'Rebirth', 'Entry', 'Sleep', 'KiCharge', 'Counter',
              'Squat', 'Attack', 'Catch', 'Throw', 'Escape', 'Ottotto', 'Kame', 'Riposte', 'Rush', 'Homing', 'Furafura', 'Down', 'Passive',
              'ShieldBreakDown', 'ShieldBreakStand')
ANCHOR_ROWS = ('AttackAir', 'ShieldBreak', 'Bury', 'CliffAttack', 'CliffEscape', 'CliffClimb', 'Item', 'Hammer')
NO_GROUND = ('EscapeAir', 'Thrown', 'Capture', 'CliffWait', 'CliffCatch', 'CliffJump', 'Recovery', 'ITEnd', 'Jump', 'Fall', 'Damage', 'Dead', 'Barrel', 'Warp', 'PassiveWall', 'PassiveCeil', 'Pass')


GROUND_MODES_PATH = Path(__file__).resolve().parent.parent / 'ground_modes.json'   # per-row overrides written by the Geno Workbench (schema ground-modes/1)
GROUND_MODE_NAMES = {'plant': 'plant', 'hover': 'plant', 'anchored': 'anchor', 'anchor': 'anchor', 'none': None}


def ground_overrides():
    """rows from ground_modes.json ({} when the file is absent, so the legacy prefix tables below decide). Raises ValueError on a bad mode."""
    p = Path(GROUND_MODES_PATH)
    if not p.is_file():
        return {}
    rows = json.loads(p.read_text(encoding='utf-8-sig')).get('rows', {})
    for row, spec in rows.items():
        if spec.get('mode') not in GROUND_MODE_NAMES:
            raise ValueError("ground_modes.json: row %s has unknown mode %r (use plant, anchored or none)" % (row, spec.get('mode')))
    return rows


def ground_mode(name):
    """'plant' | 'anchor' | None. An exact-name entry in ground_modes.json wins; otherwise the legacy prefix tables decide."""
    spec = ground_overrides().get(name)
    if spec is not None and os.environ.get('GOKU_GROUND') != '0':
        return GROUND_MODE_NAMES[spec['mode']]
    return _legacy_ground_mode(name)


def _legacy_ground_mode(name):
    """'plant' | 'anchor' | None (aerial, hanging, attached or flying rows keep the frame-0 anchor)."""
    if os.environ.get('GOKU_GROUND') == '0':  # evidence builds only: the pre-fix frame-0 anchor
        return None
    if name.startswith(NO_GROUND):
        return None
    if name.startswith(ANCHOR_ROWS):
        return 'anchor'
    if name.startswith(PLANT_ROWS):
        return 'plant'
    return None


BLEND_FRAMES = 6   # the ramp between the hover stance and the floor anchor at a row's ends
def ground_blend(name):
    """(blend_in, blend_out): an exact-name `blend_in`/`blend_out` pair in ground_modes.json wins, else the legacy answer."""
    spec = ground_overrides().get(name)
    if spec is not None and ('blend_in' in spec or 'blend_out' in spec):
        legacy = _legacy_ground_blend(name)
        return (bool(spec.get('blend_in', legacy[0])), bool(spec.get('blend_out', legacy[1])))
    return _legacy_ground_blend(name)


def _legacy_ground_blend(name):
    """(blend_in, blend_out) for an ANCHOR row. 2026-10-09 owner #1/#3: an anchored row used to start ON the floor and end wherever its pose left the feet, while
    the idle it came from and goes to hovers HOVER_Y up, so every grounded move snapped at its ends. A blended end keeps the lowest point at HOVER_Y on the
    row's first/last frame and ramps (smoothstep, BLEND_FRAMES) to the floor anchor, so the strike frames stay on the floor. Rows that start or end lying,
    hanging, held or in the air (knockdown, ledge, items, aerials, the held-catch loop) keep that end as it was."""
    return (False, False)   # remake phase 3: no hover stance to blend from or to
    if name.startswith(('AttackAir', 'Attack100')):return (False, False)
    if name.startswith('Attack'):return (True, True)
    if name in ('Catch', 'CatchDash'):return (True, False)
    if name in ('CatchCut',) or name.startswith('Throw'):return (False, True)
    if name.startswith('EscapeAir'):return (False, False)
    if name.startswith('Escape'):return (True, True)
    if name == 'Squat':return (True, False)
    if name == 'SquatRv':return (False, True)
    if name.startswith('LandingAir') or name == 'LandingFallSpecial':return (False, True)
    if name.startswith(('DownStand', 'DownFoward', 'DownBack', 'DownSpot', 'DownAttack', 'ShieldBreakStand')):return (False, True)
    return (False, False)


def lift_envelope(need, radius=2):
    """Smooth non-negative lift >= need on every frame: max-filter then box blur, both of the same radius (so the result never undercuts `need`)."""
    need = np.maximum(np.asarray(need, dtype=float), 0.0)
    n = len(need)
    mx = np.array([need[max(0, i - radius):i + radius + 1].max() for i in range(n)])
    return np.array([mx[max(0, i - radius):i + radius + 1].mean() if i - radius >= 0 and i + radius < n else mx[max(0, i - radius):i + radius + 1].mean() for i in range(n)]) if n > 1 else mx



def frame_mins(names, rest, rotations, hip, mesh, count):
    """Lowest skinned vertex height on every frame of a row (model space, the row's pelvis track as given)."""
    pos = np.c_[mesh['positions'], np.ones(len(mesh['positions']))]
    jx, wt = np.array(mesh['joints']), np.array(mesh['weights'])
    inv = [np.linalg.inv(b) for b in mesh['worlds']]
    out = np.zeros(count)
    for f in range(count):
        world = []
        for i, n in enumerate(names):
            m = rest[n].copy()
            m[:3, :3] = Rotation.from_quat(rotations[n][f]).as_matrix()
            if n == 'b_C_Pelvis':
                m[:3, 3] = hip[f]
            par = mesh['parents'][i]
            world.append(world[par] @ m if par is not None else m)
        sk = np.stack([a @ b for a, b in zip(world, inv)])
        y = np.zeros(len(pos))
        for k in range(4):
            y += np.einsum('nj,nj->n', sk[jx[:, k]][:, 1, :], pos) * wt[:, k]
        out[f] = y.min()
    return out



def animations(source,mesh,rows,splices=None):
    names=mesh['names'];rest={n:m for n,m in zip(names,mesh['locals'])};cache={};result={};report={}
    def channels(cid):
        if cid not in cache:cache[cid]={(t['bone'],t['channel']):t['keys'] for t in source.blob(source.clips[cid]['keys'])}
        return cache[cid]
    if splices is None and any(r.get('splice') for r in rows.values()):splices=splice_bake(source,mesh,rows)
    hand=HL.load(HAND_FILE) if HAND_FILE.is_file() else None
    hand_clips=dict(hand['clips']) if hand else {}
    for missing in sorted(set(hand_clips)-set(rows)):print('hand file: no row named %s (clip ignored)'%missing,file=sys.stderr)
    for name,rs in list(rows.items()):
        gname=rs.get('ground_as') or name   # a splice preview row sits on the floor like the row it previews
        cid=rs['clip'];clip=source.clips[cid];count=rs['frames'] or clip['frames'];frames=np.arange(count,dtype=float)
        # Select body-animation bindings on the BAC clock. Unimplemented BAC
        # time-scale operations are retained in reports, never silently applied.
        selected=[(cid,float(rs.get('start',0))+f*rs.get('time_factor',1.)) for f in frames]
        if rs.get('hold_source') is not None:selected=[(cid,float(rs['hold_source']))]*count
        elif rs.get('events'):
            events=sorted(rs['events'],key=lambda e:e['frame'])
            for i,f in enumerate(frames):
                active=[e for e in events if e['frame']<=f]
                if active:
                    e=active[-1];b=e['args']['binding'];end=min(b['end_frame'],source.clips[b['clip']]['frames']-1)
                    selected[i]=(b['clip'],min(end,b['start_frame']+(f-e['frame'])*b['speed']))
        rotations={n:np.repeat(Rotation.from_matrix(rest[n][:3,:3]).as_quat()[None,:],count,axis=0) for n in names}
        hip=np.repeat(rest['b_C_Pelvis'][:3,3][None,:],count,axis=0)
        root=np.zeros((count,3))
        lostscale=set();ignored=set()
        for used in sorted({c for c,f in selected}):
            ix=np.array([i for i,(c,f) in enumerate(selected) if c==used]);tm=np.array([selected[i][1] for i in ix]);ch=channels(used)
            for (bone,kind),keys in ch.items():
                if kind=='Rotation' and bone in rotations:
                    q=sample_track(keys,tm,True);r=Rotation.from_quat(q).as_matrix()
                    rotations[bone][ix]=Rotation.from_matrix(BASIS[None]@r@BASIS[None]).as_quat()
                elif kind=='Position' and bone=='b_C_Pelvis':hip[ix]=sample_track(keys,tm)@BASIS*mesh['factor']
                elif kind=='Position' and bone=='b_C_Base':root[ix]=sample_track(keys,tm)@BASIS*mesh['factor']
                elif kind=='Position' and bone!='b_C_Base':ignored.add(bone)
                elif kind=='Scale' and np.max(np.abs(sample_track(keys,tm)-1.))>1e-5:lostscale.add(bone)
        cp=rs.get('cross_port');scales={};trans={};ledge_root=False
        if cp:
            z=np.load(cp['npz']);have=int(z['frames']);zn=list(z['names'])
            pick=lambda a:np.concatenate([a,np.repeat(a[-1:],count-have,axis=0)]) if count>have else a[:count]
            if cp.get('fit_frames') and count!=have:   # a locomotion set retimed to the row's length: sample the solved clip at count points over its span (slerp for rotations, lerp otherwise)
                def pick(a,_n=count,_h=have):
                    x=np.linspace(0.,_h-1.,_n);i0=np.minimum(x.astype(int),_h-2);w=(x-i0).reshape((-1,)+(1,)*(a.ndim-1))
                    if a.ndim==2 and a.shape[1]==4:
                        out_=np.empty((_n,4))
                        for k in range(_n):out_[k]=Slerp([0,1],Rotation.from_quat([a[i0[k]],a[i0[k]+1]]))(float(w[k,0])).as_quat()
                        return out_
                    return a[i0]*(1-w)+a[i0+1]*w
            for n in names:
                if n in zn:rotations[n]=pick(z['q'][:,zn.index(n)])
            hip=pick(z['hips_t']).copy();root=np.zeros((count,3));lostscale=set()
            if cp.get('drop_root_travel') and 'root_t' in z.files:
                # goku-stage 2026-10-11 (TurnRun pelvis drift, 9.9 units of TransN z folded into the hips): the locomotion rows are played in place (the engine moves the fighter), so the
                # source's TransN travel is taken out of the pelvis and the body stays on its collision; the pelvis keeps its own sway.
                rt_=pick(z['root_t']);hip[:,0]-=rt_[:,0];hip[:,2]-=rt_[:,2]
            if cp.get('root_t') and 'root_t' in z.files:
                # goku-stage 2026-10-11 (ledge hang too high): the source's TransN displacement is the row's TransN track, the pelvis keeps only its motion relative to it. The ledge
                # state puts the fighter at ledge + TransN, so the hands land on the ledge point like retail's; no recentring and no ground plant below (the feet dangle).
                rt=pick(z['root_t']).copy();hip=hip-rt;root=rt;ledge_root=True
            if 'anchor_t' in z.files and 'grab_anchor' in names and rs['cross_port'].get('anchor',True):   # the source's own grab-anchor motion (a throw carries the victim): translation + rotation of the anchor bone
                rotations['grab_anchor']=pick(z['anchor_q']);trans['grab_anchor']=pick(z['anchor_t'])
            # 2026-10-09 (owner #11): the source's bone-scale tracks (Luigi's thigh stretch) ride on the destination bone of the same role
            sj=Path(cp['npz']).with_name('scale.json')
            if sj.exists():
                for bone,sc in json.loads(sj.read_text())['bones'].items():
                    v=np.ones((count,3));v[:,sc['axis']]=pick(np.asarray(sc['values'])[:,None])[:,0];scales[bone]=v
        splice_rep=None
        if rs.get('splice'):
            # Splice recipe (tools/splice.py): the baked clip replaces the sampled channels BEFORE the yaw/blend/ground logic below, padded to the row length
            baked,splice_rep=splices[rs['splice']['name']];baked=SP.pad_to(baked,count)
            for n in names:
                if n in baked.rot:rotations[n]=baked.rot[n][:count].copy()
            hip=baked.hips[:count].copy();root=baked.root[:count].copy();scales={b:v[:count].copy() for b,v in baked.scl.items()};lostscale=set()
        if lostscale and not rs.get('library'):raise ValueError(name+' uses unsupported animated scale on '+','.join(sorted(lostscale)))
        # Authored locomotion (Turn/TurnRun): XV2 has no turn clips. The engine keeps the root at
        # the OLD facing's yaw for the whole Turn motion (Fighter_ChangeMotionState sets it only on
        # entry), so the clip itself must rotate the body 180 degrees and end facing the new way.
        if rs.get('yaw'):
            t=np.linspace(0.,1.,count);s=t*t*(3.-2.*t)
            ry=Rotation.from_euler('y',(np.radians(rs['yaw'])*s)[:,None])
            rotations['b_C_Base']=(ry*Rotation.from_quat(rotations['b_C_Base'])).as_quat()
        if rs.get('pitch'):
            # authored lean (ledge hang): a constant rotation about X on the translation bone
            rp=Rotation.from_euler('x',np.radians(rs['pitch']))
            rotations['b_C_Base']=(rp*Rotation.from_quat(rotations['b_C_Base'])).as_quat()
        turn_yaw=None
        if rs.get('turn_align') and rs.get('blend_to') is not None:
            # goku-stage 2026-10-11 (owner: the Turn spins past the new facing, then pops back): the retail Turn twists the hips ~180 degrees and the engine ends the row by switching to
            # Wait/Run at the NEW facing, so the row must END on that pose TURNED 180 about the vertical. Easing the end toward the plain Wait pose (what every other row does) made the
            # twist a full 360 (past the new facing, back to the old one) and the next row snapped 180. The pelvis is first lined up with the pose the row starts from (a retail stance
            # differs from Goku's by tens of degrees), so the whole twist is monotonic, then the end eases to that pose turned by the twist's sign * 180.
            bone_='b_C_Pelvis';ok_=channels(rs['blend_to']).get((bone_,'Rotation'))
            if ok_ is not None and bone_ in rotations:
                q_=sample_track(ok_,np.zeros(1),True);wt_=Rotation.from_matrix(BASIS@Rotation.from_quat(q_[0]).as_matrix()@BASIS)
                D_=wt_*Rotation.from_quat(rotations[bone_][0]).inv()
                rotations[bone_]=(D_*Rotation.from_quat(rotations[bone_])).as_quat()
                e_=np.unwrap(Rotation.from_quat(rotations[bone_]).as_euler('YXZ')[:,0])
                turn_yaw=180. if e_[-1]>e_[0] else -180.
                rs=dict(rs);rs.pop('blend_from',None)   # lined up already: no ease-in
        if rs.get('blend_from') is not None:
            # Ease the first frames in from another clip's held pose (with its own pitch) so a row starts seamlessly.
            bf=rs['blend_from'];other=channels(bf['clip']);n=min(bf.get('frames',6),count)
            rp=Rotation.from_euler('x',np.radians(bf.get('pitch',0.)))
            for (bone,kind),keys in other.items():
                if kind=='Rotation' and bone in rotations:
                    q=sample_track(keys,np.array([float(bf['frame'])]),True);src_r=Rotation.from_matrix(BASIS@Rotation.from_quat(q[0]).as_matrix()@BASIS)
                    if bone=='b_C_Base':src_r=rp*src_r
                    for k in range(n):
                        w=k/max(n,1);w=w*w*(3-2*w)
                        pair=Rotation.from_quat([src_r.as_quat(),rotations[bone][k]])
                        rotations[bone][k]=Slerp([0,1],pair)(w).as_quat()
        if rs.get('blend_to') is None and ground_mode(gname)=='anchor' and ground_blend(gname)[1] and count>2*BLEND_FRAMES                 and (rs.get('active_end') or 0)+BLEND_FRAMES<count and 'Wait' in rows:
            rs=dict(rs,blend_to=rows['Wait']['clip'],blend_frames=BLEND_FRAMES)   # exit pose eases into the idle it returns to (no pop)
        if rs.get('blend_to') is not None:
            # Ease the last frames toward another clip's frame-0 pose so the next row starts seamlessly.
            other=channels(rs['blend_to'])
            n=min(rs.get('blend_frames',6),count)
            for (bone,kind),keys in other.items():
                if kind=='Rotation' and bone in rotations:
                    q=sample_track(keys,np.zeros(1),True);tgt=Rotation.from_matrix(BASIS@Rotation.from_quat(q[0]).as_matrix()@BASIS)
                    if turn_yaw is not None and bone=='b_C_Pelvis':tgt=Rotation.from_euler('y',np.radians(turn_yaw))*tgt
                    for k in range(n):
                        i=count-n+k;w=(k+1)/n;w=w*w*(3-2*w)
                        pair=Rotation.from_quat([rotations[bone][i],tgt.as_quat()])
                        rotations[bone][i]=Slerp([0,1],pair)(w).as_quat()
        # Keep character centred. Root motion/arena flight is intentionally removed.
        if not ledge_root:
            hip[:,0]-=hip[0,0];hip[:,2]-=hip[0,2]
            root-=root[0]
        if rs.get('root_path'):
            # authored TransN (ledge rows): keyframes (t 0..1, x, y, z), smoothstep between them. The cliff states
            # place the fighter at ledge + TransN (ftCo_CliffCatch_Phys), so this is the hang/climb path.
            keys=rs['root_path'];tt=np.linspace(0.,1.,count)
            for i,t in enumerate(tt):
                for a,b in zip(keys,keys[1:]):
                    if a[0]<=t<=b[0]:
                        u=(t-a[0])/max(b[0]-a[0],1e-6);u=u*u*(3-2*u)
                        root[i]=np.array(a[1:])*(1-u)+np.array(b[1:])*u;break
                else:root[i]=np.array(keys[-1][1:])
        if name in ('JumpF','JumpB','JumpAerialF','Fall','Recovery'):hip[:,1]=np.median(hip[:,1])
        # Derive a per-clip ground placement from the skinned soles at frame zero.
        world=[]
        for i,n in enumerate(names):
            m=rest[n].copy();m[:3,:3]=Rotation.from_quat(rotations[n][0]).as_matrix()
            if n=='b_C_Pelvis':m[:3,3]=hip[0]
            par=mesh['parents'][i];world.append(world[par]@m if par is not None else m)
        sk=np.stack([a@np.linalg.inv(b) for a,b in zip(world,mesh['worlds'])])
        pos=np.c_[mesh['positions'],np.ones(len(mesh['positions']))]
        deformed=np.zeros((len(pos),4))
        for k in range(4):deformed+=np.einsum('nij,nj->ni',sk[np.array(mesh['joints'])[:,k]],pos)*np.array(mesh['weights'])[:,k,None]
        ground=0. if ledge_root else float(deformed[:,1].min());hip[:,1]-=ground
        mode=None if ledge_root else ground_mode(gname)
        if mode:
            # 2026-10-09 ground pass (owner: HYBRID HOVER STANCE). XV2 combat clips are authored in a flight stance, so a frame-0 anchor lets the
            # pelvis sink (or the legs dangle) later in the clip. Measure the lowest skinned vertex on EVERY frame and shift the row's pelvis
            # track by a smooth per-frame lift (never a drop): HOVER rows (idle, walk, run, turn, crouch, shield) keep the lowest point HOVER_Y above the floor so the flight
            # stance never sinks; ANCHOR rows (attacks, grabs, throws, escapes, knockdown, ledge) keep the frame-0 anchor and are lifted only on frames that would sink.
            mins=frame_mins(names,rest,rotations,hip,mesh,count)
            if mode=='plant':shift=-mins                      # remake phase 3: the lowest vertex exactly on the floor, every frame
            else:shift=lift_envelope(0.-mins)                 # anchor: never below the floor, lifted only where it would sink
            hip[:,1]+=shift;ground-=float(shift.max())
            ground_report=dict(ground_mode=mode.upper(),ground_blend=list(ground_blend(gname)) if mode=='anchor' else None,ground_shift=float(shift.max()),ground_shift_frame0=float(shift[0]),ground_lowest_before=float(mins.min()))
        else:ground_report={}
        if rs.get('cross_port'):
            cpr=json.loads((ROOT/'_build/goku-xv2/cross-port'/name/'report.json').read_text())
            cp_info=dict(rs['cross_port'],ratio=cpr['ratio'],end_effector_error_max={k:round(v['max'],2) for k,v in cpr['end_effector_error'].items()},
                         not_carried=cpr['not_carried'],unmatched_dst_roles=cpr['solver']['unmatched_dst_roles'])
        hand_rep=None;hand_root=False
        if name in hand_clips:
            # hand-authored delta (tools/geno/artist/blender/hand_layer.py): the LAST step, so what was authored in Blender is what the game plays
            rest_q={n:Rotation.from_matrix(rest[n][:3,:3]).as_quat() for n in names}
            hip,root_h,hand_rep=HL.apply_clip(hand_clips[name],count=count,rotations=rotations,rest_q=rest_q,hips=hip,root=root if rs.get('root_motion') else None,
                                              hips_bone='b_C_Pelvis',root_bone='b_C_Base',rest_hips=rest['b_C_Pelvis'][:3,3])
            if root_h is not None:root=root_h;hand_root=True
        result[name]={'rotation':rotations,'hips':hip,'root':root if (rs.get('root_motion') or hand_root) else None,'frames':count,'loop':rs['loop'],'scale':scales,'trans':trans}
        report[name]={k:v for k,v in rs.items() if k!='events'}
        report[name].update(ground_report)
        report[name].update(frames=count,source_name=clip['name'],ground_offset=-ground,
                            posed_frame0_mesh_height=float(np.ptp(deformed[:,1])),
                            discarded_nonhip_translation=sorted(ignored),fps=60,fps_basis='LibXenoverse2 EAN exporter convention, not runtime measurement',
                            root_motion=bool(rs.get('root_motion')), root_displacement=root[-1].tolist(),
                            motion_policy='Base translation retained on translation bone for flagged roll rows; otherwise omitted; hips lateral start removed; jump/recovery vertical flattened')
        if hand_rep:report[name]['hand']=hand_rep
        if splice_rep:
            report[name].update(splice=dict(rs['splice'],frames=splice_rep['frames'],ok=splice_rep['ok'],seams=splice_rep['seams'],segments=splice_rep['segments'],
                                            max_step_deg=splice_rep['max_step_deg'],notes=splice_rep['notes']),
                                source_name='Splice '+rs['splice']['name']+': '+rs['splice']['summary'],source_frames=count,start=0)
        if rs.get('cross_port'):
            report[name].update(cross_port=cp_info,source_name='Melee %s %s (retail, retargeted)'%(cp_info['fighter'].capitalize(),cp_info['action']),
                                source_frames=count,start=0)
    return result,report


def emit_glb(mesh,anims,path):
    b=GLB();g=b.g;names=mesh['names'];nodes=[]
    for n,m in zip(names,mesh['locals']):
        nodes.append({'name':n,'translation':m[:3,3].tolist(),'rotation':Rotation.from_matrix(m[:3,:3]).as_quat().tolist(),'scale':[1,1,1]})
    for i,p in enumerate(mesh['parents']):
        if p is not None:nodes[p].setdefault('children',[]).append(i)
    nodes.append({'name':'Goku','mesh':0,'skin':0})
    g['nodes']=nodes;g['scenes']=[{'nodes':[i for i,p in enumerate(mesh['parents']) if p is None]+[len(names)]}];g['scene']=0
    ibm=np.array([np.linalg.inv(w).T.reshape(-1) for w in mesh['worlds']])
    g['skins']=[{'name':'GokuExport','joints':list(range(len(names))),'inverseBindMatrices':b.accessor(ibm,'MAT4')}]
    attrs={k:b.accessor(mesh[field],kind,dtype,bounds) for k,field,kind,dtype,bounds in [
        ('POSITION','positions','VEC3','<f4',True),('NORMAL','normals','VEC3','<f4',False),('TEXCOORD_0','uv','VEC2','<f4',False),
        ('JOINTS_0','joints','VEC4','<u2',False),('WEIGHTS_0','weights','VEC4','<f4',False)]}
    g['meshes']=[{'name':'GokuMerged','primitives':[{'attributes':attrs,'indices':b.accessor(mesh['indices'],'SCALAR','<u4'),'material':0,'mode':4}]}]
    buf=io.BytesIO();mesh['atlas'].save(buf,format='PNG')
    g['images']=[{'bufferView':b.view(buf.getvalue()),'mimeType':'image/png'}];g['textures']=[{'source':0,'sampler':0}]
    g['samplers']=[{'magFilter':9729,'minFilter':9729,'wrapS':33071,'wrapT':33071}]
    g['materials']=[{'name':'GokuBakedDiffuse','pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicFactor':0,'roughnessFactor':1},'alphaMode':'OPAQUE','doubleSided':False}]
    g['animations']=[]
    for name,a in anims.items():
        an={'name':name,'samplers':[],'channels':[]};times=b.accessor(np.arange(a['frames'])/60.,'SCALAR',bounds=True)
        def channel(bone,kind,values,typ):
            idx=len(an['samplers']);an['samplers'].append({'input':times,'output':b.accessor(values,typ),'interpolation':'LINEAR'})
            an['channels'].append({'sampler':idx,'target':{'node':names.index(bone),'path':kind}})
        for bone,q in a['rotation'].items():channel(bone,'rotation',q,'VEC4')
        channel('b_C_Pelvis','translation',a['hips'],'VEC3')
        if a['root'] is not None:channel('b_C_Base','translation',a['root'],'VEC3')
        for bone,v in a.get('scale',{}).items():channel(bone,'scale',v,'VEC3')
        for bone,v in a.get('trans',{}).items():channel(bone,'translation',v,'VEC3')
        g['animations'].append(an)
    b.save(path)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ir',type=Path,default=PORT/'ir/goku.xv2.ir.json')
    ap.add_argument('--out',type=Path,default=AUTHOR);ap.add_argument('--height',type=float,default=20.)
    ap.add_argument('--build',action='store_true');ap.add_argument('--no-library',action='store_true');ap.add_argument('--blend',action='store_true')
    ap.add_argument('--splice-only',metavar='RECIPE',help='reduced build: the shipped rows plus this recipe library row only (use with GOKU_AUTHOR=splice-preview)')
    ap.add_argument('--splice-file',type=Path,help='recipe file (default splices.json)');args=ap.parse_args(argv)
    if args.splice_file:SP.SPLICES=args.splice_file
    out=args.out.resolve()
    if not out.is_relative_to(AUTHOR):ap.error('All generated assets must stay under '+str(AUTHOR))
    if not 8<=args.height<=20:ap.error('Height must be within 8..20 Melee units')
    out.mkdir(parents=True,exist_ok=True);source=Source(args.ir);mesh=build_mesh(source,args.height)
    assert mesh['report']['weighted_bones']<=64 and len(mesh['names'])+3<=128
    rs=row_specs(source)
    write(PORT/'remake-applied.json',{'schema':'goku-remake-applied/1','rows':REMAKE_REPORT})
    # LAB CLIPS library (2026-10-08): every body clip of the source (character, common and skill EANs),
    # unbound to any input. Bank name = 'x' + source name (<= 31 chars); geno.json fighter.rows lists them.
    browse=[]
    if args.splice_only:
        lib_row=SP.library_name(args.splice_only)
        if lib_row not in rs:ap.error('no recipe '+args.splice_only)
        for n in [n for n,r in rs.items() if r.get('splice_library') and n!=lib_row]:del rs[n]
    if not args.no_library and not args.splice_only:
        seen=set()
        for cid,c in source.clips.items():
            e=c['engine']['xv2.pc']
            if e.get('camera') is not False or '.fce.' in cid or c['frames']<2:continue
            name=re.sub(r'[^A-Za-z0-9_]','_','x'+c['name'])[:31]
            while name in seen or name in rs:name=name[:28]+'_%02d'%(len(seen)%100)
            seen.add(name)
            rs[name]={'clip':cid,'loop':False,'frames':min(c['frames'],180),'start':0,'status':'LAB CLIPS library: '+c['file']+' '+c['name'],'library':True}
            browse.append({'name':name,'source':c['name'],'file':c['file'].replace('file:',''),'frames':min(c['frames'],180),'source_frames':c['frames'],'id':cid})
    # splice library rows (CLIPS: s<recipe>) are listed with the XV2 library so they can be viewed; wired recipes are baked into their rows
    for n,r in rs.items():
        if r.get('splice_library'):browse.append({'name':n,'source':'splice '+r['splice']['name'],'file':'splices.json','frames':r['frames'],'source_frames':r['frames'],'id':r['clip']})
    anims,animreport=animations(source,mesh,rs)
    browse=[b for b in browse if b['name'] in anims]   # a preview recipe that could not be baked is dropped
    emit_glb(mesh,anims,out/'goku.glb');mesh['atlas'].save(out/'atlas.png')
    cmap={name:[name] for name in anims if name in spec.clip_table()['by_name']}
    cmap.update({'KameCharge':['SpecialN'],'KameTap':['SpecialAirN'],'Rush':['SpecialS','SpecialAirS'],
                 'Recovery':['SpecialHi','SpecialAirHi'],'Counter':['SpecialLw'],'Riposte':['SpecialAirLw']})
    # KameMid/Full deliberately remain in the bank with CLIP_UNMAPPED warnings:
    # only the gameplay overlay can bind custom rows 297/298. Mapping fictional
    # engine row names here is a validator error; ignoring them would lose clips.
    cfg={'schema':'geno-artist/1','key':'goku-xv2','name':'Goku','art':{'glb':'goku.glb','scale':1,'reduce_influences':False},
         'roles':ROLES,'costumes':[{'name':'default','texture':'atlas.png'}],
         'clips':{'map':cmap,'loop':{n:a['loop'] for n,a in anims.items()},'root_motion':[n for n,a in anims.items() if a['root'] is not None],
                  'scale_bones':{n:sorted(a['scale']) for n,a in anims.items() if a.get('scale')},
                  'translate_bones':{n:sorted(a['trans']) for n,a in anims.items() if a.get('trans')}},'hurtboxes':'auto','output':str(out/'package')}
    write(out/'fighter.json',cfg)
    write(out/'clip-library.json',{'schema':'goku-clip-library/1','clips':browse})
    write(out/'goku.glb.geno.json',{'schema':'geno-fighter-sidecar/1','roles':ROLES,'clips':{n:{'loop':a['loop'],'frames':a['frames'],'root_motion':a['root'] is not None} for n,a in anims.items()}})
    findings,f=validate.validate(str(out/'fighter.json'))
    write(out/'art-report.json',{'source_ir_sha256':hashlib.sha256(args.ir.read_bytes()).hexdigest(), 'source_document':source.doc['document_id'],
        'parity_consumed':source.parity_rows,'checked_blobrefs':source.reads,'geometry':mesh['report'],'size_design':size_basis(args.height),'animations':animreport,
        'limitations':['Prototype art; no XV2 or Melee runtime validation claimed.','Source toon/DYT shader, eye compositing and transparency not reproduced.',
                       'Facial animation weights collapsed to head; hair/belt physics replaced by rigid attachments.',
                       'BAC time-scale operations reported but not simulated; hit-frame pose requires LAB verification.',
                       'Triangle budget warning accepted: source topology preserved.','No deformation-error bound measured for top-two influence reduction.']})
    allrows=[]
    for row in f.rows:
        table=spec.clip_table()['by_name'][row['row']];cn=row['clip']
        allrows.append({**row,'tier':table['tier'],'source':animreport.get(cn),'review_status':'authored-needed' if row['status']=='placeholder' else ('no-animation' if row['status']=='no-animation' else 'prototype candidate; pose review needed')})
    write(PORT/'ANIM-ROWS.json',{'schema':'goku-animation-mapping/0.2','fps':{'value':60,'status':'tool-source convention; not measured'},
                              'rows':allrows,'body_source_inventory':[{'id':c['id'],'name':c['name'],'frames':c['frames']} for c in source.clips.values() if c['file']=='file:'+EAN]})
    losses=[]
    for what,why in [
        ('Source rendering','Toon/DYT ramp lookup, source shader lighting, eye composition, alpha and material animation are not reproduced. Source DDS mask images use provisional material-name colours in a single opaque atlas.'),
        ('Facial deformation','All f_* skin weights collapse to b_C_Head; source facial animation and expressions do not deform the destination skin.'),
        ('Attachment physics','Hair and belt vertices are baked into main-rig rest positions, rigidly weighted to head and pelvis; SCD simulation is omitted.'),
        ('Influence reduction',f"Top two remapped weights are normalized. {mesh['report']['source_influences_reduced_vertices']} vertices lose influence weight; maximum discarded mass {mesh['report']['max_discarded_weight']:.6f}; no pose-space error bound measured."),
        ('Source time base','60 fps is the LibXenoverse EAN export convention; original runtime FPS has not been measured. Sparse keys use linear position and quaternion slerp interpolation.'),
        ('In-place adaptation','Arena root translation is omitted outside EscapeF/B; pelvis initial lateral displacement is removed and jump/recovery vertical translation is flattened. Roll carrier channels preserve decoded Base translation, which may be zero.'),
        ('Unfinished animation rows',f"{sum(r['status']=='placeholder' for r in f.rows)} standard rows remain explicit placeholders. ANIM-ROWS.json lists every row. Attack directions, grabs/throws, ledges and special poses require authoring/review."),
        ('Performance budget','Source topology retains 18,183 triangles and a 1024-square atlas; runtime multi-fighter performance is unmeasured.'),
    ]:losses.append({'move':'art','frame':0,'what':what,'why':why,'source':source.doc['document_id']})
    for name,record in animreport.items():
        if record.get('ignored_time_scale'):
            losses.append({'move':name,'frame':0,'what':'BAC animation time-scale operations','why':'Static BAC animation bindings are sampled; source time-scale operations are not executed. Strike-pose alignment with candidate hit frames needs LAB review.','source':record.get('subaction')})
    write(out/'art-losses.json',{'version':1,'losses':losses})
    write(out/'validation.json',{'ok':findings.ok,'findings':findings.items})
    if not findings.ok:
        print(validate.format_report(findings))
        return 1
    if args.blend:
        subprocess.run([pipeline.blender_exe(),'-b','--python',str(PORT/'tools/artist_blender.py'),'--',str(out)],cwd=ROOT,check=True)
    if args.build:
        # Public rebuilds must restore custom gameplay, fit/audit the colliders,
        # and merge gameplay losses after the generic artist assembler rewrites.
        rc=subprocess.run([sys.executable,str(PORT/'tools/build.py'),'--fighter',str(out/'fighter.json'),
                           '--out',str(out/'package')],cwd=ROOT).returncode
        if rc:return rc
    print(json.dumps({'out':str(out),'geometry':{k:v for k,v in mesh['report'].items() if k!='materials'},'clips':len(anims),'rows':len(allrows)}))
    return 0

if __name__=='__main__':raise SystemExit(main())

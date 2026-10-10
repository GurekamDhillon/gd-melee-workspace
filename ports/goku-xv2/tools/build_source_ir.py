"""Describe the accepted shallow dump using ports/ir, without copying bulk data.

The source package is immutable. File-scoped indices and unknown semantics are
retained. Parity is a reviewed adaptation proposal, never a claim of runtime identity.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, re, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PORT=ROOT/'ports/goku-xv2'
DEFAULT=Path('E:/Torrents/Dragon.Ball.Xenoverse.2.Future.Saga.Chapter.4-RUNE/modding/exports/goku-base-shallow-v0.1')
COMMIT='59242676d1b212df009930e32b46d76f3b9b198b'
BODY='chara/GOK/GOK_000.esk'
BAC='chara/GOK/GOK_PLAYER.bac'
ROLE_MAP={
 'top_n':('EXP_GOK_000','root'), 'trans_n':('b_C_Base','translation'),
 'hip':('b_C_Pelvis','hips'), 'waist':('b_C_Spine1','spine'),
 'chest':('b_C_Chest','chest'), 'neck':('b_C_Neck1','neck'), 'head':('b_C_Head','head'),
 'jaw':('f_C_Jaw',None), 'eye_l':('f_L_EyeIris',None), 'eye_r':('f_R_EyeIris',None),
}
for side,upper in [('l','L'),('r','R')]:
 for role,bone,artist in [('clavicle','Shoulder','shoulder'),('shoulder','Arm1','upper_arm'),('arm','Arm2','lower_arm'),
                         ('hand','Hand','hand'),('leg','Leg1','upper_leg'),('knee','Leg2','lower_leg'),('foot','Foot','foot'),('toe','Toe','toe')]:
  ROLE_MAP[f'{role}_{side}']=(f'b_{upper}_{bone}',f'{artist}.{upper}')
 ROLE_MAP[f'thumb_{side}']=(f'h_{upper}_Thumb1',f'thumb.{upper}')
 ROLE_MAP[f'finger_index_{side}']=(f'h_{upper}_Index1',f'fingers.{upper}')
 # Source anatomical proxies. Destination sockets require newly authored helpers.
 ROLE_MAP[f'hand_item_{side}']=(f'b_{upper}_Hand',f'item_socket.{upper}')
ROLE_MAP['throw_n']=('b_C_Chest','grab_anchor')

# Proposed source candidates, NOT XV2 input equivalences. Each is reviewed in parity.
MOVE_CANDIDATES={
 'jab':[300,301,302], 'rapid_jab':[336], 'dash_attack':[311], 'ftilt':[310],
 'utilt':[330], 'dtilt':[340], 'fsmash':[350], 'usmash':[352], 'dsmash':[360],
 'nair':[312], 'fair':[320], 'bair':[335], 'uair':[370], 'dair':[375],
 'grab':[600], 'fthrow':[601], 'special_s':[475], 'special_hi':[419],
}
OPS={1:'hitbox.create',2:'move.velocity',3:'body.state',4:'timer.set_anim_rate',8:'gfx.spawn',9:'article.spawn',11:'sfx.play',17:'throw.set'}

def uid(ns,path): return ns+':'+re.sub(r'[^A-Za-z0-9_.@/+\-]','_',str(path))
def index(space,value): return dict(space=space,value=int(value),stability='stable')
def prov(conf,*evidence,note=None):
 p=dict(confidence=conf,evidence=list(dict.fromkeys(evidence)))
 if note: p['note']=note
 return p
def ext(**kw): return {'xv2.pc':kw}
def label(x): return x.get('label') if isinstance(x,dict) else x
def enumval(x): return x.get('value') if isinstance(x,dict) else x
def quat_euler(q):
 x,y,z,w=q
 return [math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),math.asin(max(-1,min(1,2*(w*y-z*x)))),math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))]

class Builder:
 def __init__(self,source,host):
  self.source=source.resolve(); self.host=host
  self.m=self.read('manifest.json'); self.assets={a['file']:a for a in self.m['assets']}
  self.by_kind=collections.defaultdict(list)
  for a in self.m['assets']: self.by_kind[a['kind']].append(a)
  self.checks={}
  for line in (source/'package-files.sha256').read_text().splitlines():
   digest,path=line.split('  ',1); self.checks[path]=digest
  self.cache={}; self.joints={}; self.clip_lookup={}; self.subids=set(); self.parity=[]
  self.doc=dict(ir_version='0.1.0',document_id='goku.xv2',subject=dict(character='Goku (base form)',game='other',engine='xv2.pc',distribution=dict(name='Dragon Ball Xenoverse 2 PC',version='1.25.02.0',kind='retail'),analysed_with=[dict(tool='Xv2CoreLib',revision=COMMIT)],notes='Shallow source description. XV2 never ran successfully. No observed facts; source and destination behavior differ.'),evidence=[],identity={},resources=dict(files=[],shared_dependencies=[]),assets={},behavior=dict(attributes=dict(common=[]),actions=[],subactions=[],scripts=[],moves=[],articles=[]),issues=[],coverage={},parity=self.parity)
 def read(self,path): return json.loads((self.source/path).read_text(encoding='utf-8-sig'))
 def ev(self,source): return uid('ev','raw/'+source)
 def blob(self,path,pointer=None):
  d=dict(kind='sidecar',path=(self.source/path).as_posix(),format='json' if path.endswith('.json') else Path(path).suffix.lstrip('.'),sha256=self.checks[path])
  if pointer is not None:d['note']='JSON Pointer '+pointer+'; checksum covers the entire sidecar.'
  return d
 def decoded(self,source):
  return next((a['file'] for a in self.m['assets'] if a['source']==source and a['kind'] not in ('raw','embeddedRaw','texture','rig')),None)
 def source_prov(self,source,verified=False,note=None): return prov('verified' if verified else 'inferred',self.ev(source),'ev:parser',*(['ev:validation'] if verified else []),note=note)
 def issue(self,key,title,detail,ev='ev:manifest',severity='wrong_behavior',layer='ir'):
  ident=uid('issue',key)
  self.doc['issues'].append(dict(id=ident,title=title,layer=layer,severity=severity,status='open',description=detail,provenance=prov('inferred',ev)))
  return ident
 def evidence_resources(self):
  d=self.doc
  for path,kind,note in [('sources.json','tool_output','Xv2CoreLib parser commit and resolved CPK origins.'),('validation.json','tool_output','Integrity, skeleton hierarchy, palette references, weight sums, triangle ranges, ordered keyframes. Does not prove decoded values independently or behavior.'),('manifest.json','analysis_report','Accepted v0.1 scope and gaps.')]:
   eid={'sources.json':'ev:parser','validation.json':'ev:validation','manifest.json':'ev:manifest'}[path]
   d['evidence'].append(dict(id=eid,kind=kind,path=(self.source/path).as_posix(),sha256=self.checks[path],revision=COMMIT if path=='sources.json' else 'v0.1',note=note))
  d['evidence'] += [dict(id='ev:enum_labels',kind='community_knowledge',path='https://github.com/LazyBone152/XV2-Tools',revision=COMMIT,note='Parser enum and BAC type labels. Inferred, not observed runtime semantics.'),dict(id='ev:role_map',kind='documentation',path='ports/goku-xv2/ROLE-MAP.md',note='Single schema/artist/source role vocabulary mapping; socket and throw anchors are destination design decisions.'),dict(id='ev:parity_design',kind='analysis_report',path='ports/goku-xv2/PARITY.md',note='Proposed adaptation decisions and evidence limits. No user review or in-game approval claimed.'),dict(id='ev:schema',kind='documentation',path='ports/ir/schema/engines/xv2.md',note='File-scoped numbering and extension semantics.')]
  origins={f['path']:f['archive'] for f in self.read('sources.json')['files']}
  roles={'esk':'costume_model','emd':'costume_model','emm':'costume_model','emb':'costume_textures','ean':'animation_bank','bac':'fighter_data','bcm':'fighter_data','bdm':'fighter_data','bsa':'article_data','eepk':'effect_bank','acb':'sound_bank'}
  for a in self.by_kind['raw']:
   p=a['file']; s=a['source']; actual=hashlib.sha256((self.source/p).read_bytes()).hexdigest()
   if actual!=self.checks[p] or actual!=a['sha256']:raise ValueError('Source hash mismatch: '+p)
   d['evidence'].append(dict(id=self.ev(s),kind='file_bytes',path=(self.source/p).as_posix(),length=a['bytes'],sha256=self.checks[p]))
   details=dict(archive=origins[s],raw=self.blob(p))
   dec=self.decoded(s)
   if dec:details['decoded']=self.blob(dec)
   d['resources']['files'].append(dict(id=uid('file',s),name=s,local_path=(self.source/p).as_posix(),disc_path=origins[s]+'/data/'+s,role=roles.get(Path(s).suffix[1:],'other'),size=a['bytes'],sha256=actual,container=dict(format=Path(s).suffix[1:].upper()),engine=ext(**details),provenance=self.source_prov(s,True,note='Raw hash cross-checked with package-files.sha256 and export manifest.')))
  d['identity']=dict(names=dict(display={'en':'Goku'},internal=['GOK'],series='Dragon Ball'),indices=[dict(**index('xv2.cms_id',0),provenance=self.source_prov('system/char_model_spec.cms'))],behavior_host=dict(mode='self',binding='authored'),index_mappings=[dict(from_=a,to=b,rule=c,partial=True,provenance=prov('inferred','ev:parser','ev:schema')) for a,b,c in []],provenance=self.source_prov('system/char_model_spec.cms'))
  for a,b,c in [('xv2.cms_id','xv2.bcs.partset','CMS BcsPath selects a BCS; costume/model-preset selects a file-local partset.'),('xv2.bac.entry','xv2.ean.clip','BAC Animation clipId + sourceScope + owning BAC/skill directory select an EAN file and its clip ID. Common/Character/Skill namespaces never collapse.'),('xv2.bcm.node','xv2.bac.entry','BCM primary/airborne/charge/connect fields address the BAC in the same character or skill namespace; sentinel values are not entries.'),('xv2.bac.entry','xv2.bdm.entry','Hitbox reactionScope plus BdmEntryID select a BDM; common and character damage tables differ.'),('xv2.bac.entry','xv2.eepk.effect','Effect scope and skill ID select a bank, then EffectID selects an EEPK entry; unresolved scopes remain unresolved.'),('xv2.emb.index','xv2.emb.index','EMD material sampler EmbIndex indexes the part-selected EMB; DYT palette selection uses a separate EMB.'),('xv2.cus.skill_id','xv2.bac.entry','CUS ID1 includes skill category; ID2 plus CMS owner and short code constructs the skill directory. BAC entries are local to that folder.')]:
   d['identity']['index_mappings'].append({'from':a,'to':b,'rule':c,'partial':True,'provenance':prov('inferred','ev:parser','ev:schema')})
 def skeletons(self):
  skels=[]; roles=[]; physical={p['rig']:p for p in self.m['parts']}
  for a in self.by_kind['rig']:
   source=a['source']; data=self.read(a['file']); skelid=uid('skel',source); render=source in physical
   self.joints[source]={j['name']:j['id'] for j in data['joints']}
   js=[]
   for j in data['joints']:
    js.append(dict(id=uid('joint',source+'/'+j['name']),index=j['id'],name=j['name'],parent=j['parent'] if j['parent']>=0 else None,rest=dict(translation=j['translation'],rotation_euler_rad=quat_euler(j['rotation']),scale=j['scale']),traits=['skeleton_root'] if j['parent']<0 else [],provenance=self.source_prov(source,note='Topology cross-checked by v0.1; TRS parsing and quaternion-to-Euler conversion inferred. Raw XYZW kept in source BlobRef.')))
   extra=dict(purpose='render' if render else 'animation_reference',index_space='xv2.esk.joint',source_file=source,source_data=self.blob(a['file']),joint_indices=[index('xv2.esk.joint',j['id']) for j in data['joints']])
   if render and physical[source]['attachBone']:
    extra['attachment']=dict(skeleton=uid('skel',BODY),joint=uid('joint',BODY+'/'+physical[source]['attachBone']),role='head' if physical[source]['role']=='Hair' else 'hip',simulation='untranslated SCD; destination rigid bake is a design loss')
   skels.append(dict(id=skelid,name=source,file=uid('file',source),joint_count=len(js),order='file_order',joints=js,engine=ext(**extra),provenance=self.source_prov(source)))
  body=self.joints[BODY]
  for role,(bone,artist) in ROLE_MAP.items():
   note=f'Name-based anatomical mapping; artist role {artist or "unmapped"}.'
   if role.startswith('hand_item') or role=='throw_n':note+=' Anatomical proxy only; source has no verified equivalent socket/throw anchor. Destination must synthesize a helper.'
   roles.append(dict(role=role,joint=body[bone],skeleton=uid('skel',BODY),engine_index=index('xv2.esk.joint',body[bone]),provenance=prov('inferred','ev:role_map',self.ev(BODY),note=note)))
  self.doc['assets'].update(skeletons=skels,bone_roles=roles)
 def models(self):
  assets=self.doc['assets']; models=[]; mats=[]; textures=[]; meshindex=0; mat_seen=set()
  # Material and pixel records cover only model-part containers, with all other banks
  # still resolvable as resource BlobRefs. This is intentionally representative.
  containers={p[k] for p in self.m['parts'] for k in ['texture','palette'] if p[k]}
  for a in self.by_kind['texture']:
   if a['source'] not in containers:continue
   raw=(self.source/a['file']).read_bytes(); h,w=struct.unpack_from('<II',raw,12)
   fmt=raw[84:88].decode('ascii',errors='replace').rstrip('\0') or 'DDS uncompressed'
   textures.append(dict(id=uid('tex',a['file']),name=a['file'],width=w,height=h,format=fmt,pixels=self.blob(a['file']),semantic='DYT toon palette' if '.dyt.' in a['source'] else 'source sampler texture',provenance=self.source_prov(a['source'],note='DDS dimensions and source format parsed from header; no color-space or shader interpretation asserted.')))
  for p in self.m['parts']:
   data=self.read('decoded/'+p['model']+'.json'); meshes=[]
   for i,s in enumerate(data['submeshes']):
    mid=uid('mat',p['material']+'/'+s['material'])
    if mid not in mat_seen:
     mat_seen.add(mid); mats.append(dict(id=mid,name=s['material'],shading=dict(lighting='unknown',alpha='unknown',cull='unknown'),engine=ext(source_material=self.blob('decoded/'+p['material']+'.json'),texture_container=p['texture'],palette_container=p['palette'],samplers=s['samplers']),provenance=self.source_prov(p['material'])))
    meshes.append(dict(id=uid('mesh',p['model']+'/'+s['id']),index=meshindex,name=s['material'],material=mid,vertices=len(s['vertices']),faces=sum(len(g['indices'])//3 for g in s['groups']),primitive_groups=[dict(skinning='envelope' if s['hasSkin'] else 'rigid',max_influences=4 if s['hasSkin'] else 0,display_list=self.blob('decoded/'+p['model']+'.json',f'/submeshes/{i}/groups/{n}')) for n,g in enumerate(s['groups'])],engine=ext(index_space='xv2.emd.mesh',mesh_index=index('xv2.emd.mesh',meshindex),source_submesh=s['id'],geometry=self.blob('decoded/'+p['model']+'.json',f'/submeshes/{i}')),provenance=self.source_prov(p['model'],True,note='v0.1 checked vertex/index bounds, weight sums and group-local palette membership; shader semantics unverified.')))
    meshindex+=1
   models.append(dict(id=uid('model',p['model']),name=p['role'],role='body',skeleton=uid('skel',p['rig']),meshes=meshes,stats=dict(meshes=len(meshes)),engine=ext(part=p,geometry=self.blob('decoded/'+p['model']+'.json')),provenance=self.source_prov(p['model'])))
  assets.update(models=models,materials=mats,textures=textures)
  bcs=self.read('character-source.json')['bcs']; costumes=[]; groups=collections.defaultdict(list)
  for i,s in enumerate(bcs['PartSets']):
   n=int(s['Index']); signature=[]
   for role in ['FaceBase','FaceEye','FaceForehead','FaceNose','FaceEar','Hair','Bust','Pants','Rist','Boots']:
    part=s.get(role)
    if part:signature.append([role,part.get('CharaCode'),part.get('Model'),part.get('EmdPath'),[(x.get('CharaCode'),x.get('EmdPath')) for x in part.get('PhysicsParts') or []]])
   sig=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()[:16]; cid=uid('costume',n); groups[sig].append(cid)
   costumes.append(dict(id=cid,index=index('xv2.bcs.partset',n),name='GOK partset '+str(n),kind='base' if n==0 else 'mixed',files=[uid('file','chara/GOK/GOK.bcs')],set=uid('costumeset',sig),engine=ext(selection=self.blob('character-source.json',f'/bcs/PartSets/{i}'),model_parts=[m['id'] for m in models] if n==0 else [],geometry_exported=n==0),provenance=self.source_prov('chara/GOK/GOK.bcs',note='Only partset 0 geometry is exported; other partsets are metadata, not base-form assertions.')))
  assets['costumes']=costumes
  assets['costume_sets']=[dict(id=uid('costumeset',sig),name='BCS geometry signature '+sig,costumes=cs,within_set_variation='Grouped by declared model paths/physics attachment geometry; nonzero partsets not extracted for byte comparison.',provenance=self.source_prov('chara/GOK/GOK.bcs')) for sig,cs in groups.items()]
  face_meshes=[s['index'] for m in models if m['name'] in ('FaceBase','FaceEye') for s in m['meshes']]
  assets['material_animations']=[dict(id='matanim:face_eye',name='Face/eye source expression channels',targets=face_meshes,driver='unknown',purpose='Face/eye expression and palette swaps: source FCE channels retained; no texture-swap schedule asserted.',engine=ext(source_data=self.blob('decoded/chara/GOK/GOK.fce.ean.json'),status='unresolved material-versus-skeletal expression interpretation'),provenance=prov('inferred',self.ev('chara/GOK/GOK.fce.ean'),'ev:manifest'))]
  assets['part_visibility']=[dict(id='vis:base',driver='script',parts=[dict(part=i,semantic=m['name'],states=[dict(state=0,meshes=[s['index'] for s in m['meshes']],semantic='selected partset 0 geometry; runtime visibility not measured')]) for i,m in enumerate(models)],hazards=['BAC part visibility and face swaps have not been executed. Mesh numbering is xv2.emd.mesh document-global stable traversal.'],provenance=self.source_prov('chara/GOK/GOK.bcs'))]
 def animations(self):
  clips=[]
  for a in self.by_kind['animation']:
   d=self.read(a['file']); source=a['source']
   for i,c in enumerate(d['clips']):
    cid=uid('clip',source+'/'+str(c['id']));self.clip_lookup[(source,c['id'])]=cid
    clips.append(dict(id=cid,name=c['name'],file=uid('file',source),frames=c['frameCount'],authored_for=dict(skeleton=uid('skel',source),joint_count=len(self.joints[source])),tracks=dict(per_channel=dict(collections.Counter(t['channel'] for t in c['tracks']))),keys=self.blob(a['file'],f'/clips/{i}/tracks'),engine=ext(clip_index=index('xv2.ean.clip',c['id']),scope=source,camera=d['isCamera'],fps=None,source_pointer=f'/clips/{i}'),provenance=self.source_prov(source,note='Frame ordering/finiteness cross-checked by v0.1; values and interpolation only parser-inferred. Camera channels are not skeletal quaternion channels.')))
  self.doc['assets']['animations']=dict(indexing='(EAN resource path, xv2.ean.clip) tuple; body, FCE, camera and each skill are separate namespaces.',clips=clips,stats=dict(clips=len(clips)))
 def resolve_clip(self,source,payload):
  scope=payload['sourceScope']; i=payload['clipId']
  if scope=='Character': path='chara/GOK/GOK.ean'
  elif scope=='Common': path='chara/CMN/CMN.ean'
  elif scope=='Skill': path=source.removesuffix('_PLAYER.bac').removesuffix('.bac')+'.ean'
  else:return None
  return self.clip_lookup.get((path,i))
 def behavior(self):
  b=self.doc['behavior']; labels={}; bodyj=self.joints[BODY]; role_by_bone={bone:role for role,(bone,artist) in ROLE_MAP.items() if role not in ('throw_n','hand_item_r','hand_item_l')}
  for a in self.by_kind['moves']:
   source=a['source']; data=self.read(a['file'])
   for n,entry in enumerate(data['entries']):
    sid=uid('subaction',source+'/'+str(entry['id']));scriptid=uid('script',source+'/'+str(entry['id']));self.subids.add(sid)
    events=[]; animation_bindings=[]
    for ei,e in enumerate(entry['events']):
     t=e['typeId']; labels[t]=e['kind']; fields=e['sourceFields']; opname=OPS.get(t,'engine.'+re.sub('[^a-z0-9]+','_',e['kind'].lower()).strip('_'))
     raw_ext=dict(source_file=uid('file',source),decoded_pointer=f'/entries/{n}/events/{ei}',duration_frames=e['durationFrames'],encoding=dict(endianness='little',note='BAC typed command record; raw bytes in source resource; decoded fields at pointer.'))
     event=dict(op=opname,frame=e['startFrame'],args=dict(engine=ext(**raw_ext)),raw=dict(opcode=t,engine_name=e['kind']))
     if t==0:
      payload=e['payload']; clip=self.resolve_clip(source,payload)
      bind=dict(index=index('xv2.ean.clip',payload['clipId']),source_scope=payload['sourceScope'],clip=clip,start_frame=payload['clipStartFrame'],end_frame=payload['clipEndFrame'],speed=payload['speed'])
      animation_bindings.append(bind); event['args'].update(binding=bind)
     elif t==1:
      h=e['payload']; bone=h['bone']; hit=dict(damage=h['damage'],size=h['sourceSize'],offset=h['offset'],angle_kind='other',element='other',engine=ext(shape=h['sourceShape'],min=h['sourceMin'],max=h['sourceMax'],reaction=index('xv2.bdm.entry',h['reactionId']),reaction_scope=h['reactionScope'],unknown_fields=['angle','knockback_growth','base_knockback','element'],size_semantics='source Size scalar; sphere equivalence unverified',source_bone=bone))
      if bone in bodyj:hit.update(joint=bodyj[bone],joint_role=role_by_bone.get(bone,bone));hit['engine']['xv2.pc']['joint_index']=index('xv2.esk.joint',bodyj[bone])
      event['hitbox']=hit
     elif t==4:event['args']['rate']=fields.get('TimeScale')
     events.append(event)
    b['scripts'].append(dict(id=scriptid,language='xv2.bac',location=dict(file=uid('file',source)),role='subaction_main',events=events,provenance=prov('inferred',self.ev(source),'ev:enum_labels','ev:parser',note='Static start times; durations, branching, collision and simultaneous-event precedence not executed. Raw form retained through resource BlobRefs.')))
    primary=next((x['clip'] for x in animation_bindings if x['clip']),None)
    b['subactions'].append(dict(id=sid,index=index('xv2.bac.entry',entry['id']),name=f'{Path(source).name}:{entry["id"]}',clip=primary,empty=not entry['events'],scripts=dict(main=scriptid),engine=ext(scope=source,animation_bindings=animation_bindings,primary_clip_rule='First resolved animation event for browsing only; full bindings remain authoritative.',source_flags=entry['sourceFlags']),provenance=self.source_prov(source)))
  b['script_languages']=[dict(id='xv2.bac',unit='command_record',opcode_field='BAC type ID, with source-frame start and duration fields',decoder=dict(path='Xv2CoreLib/BAC/BAC_File.cs',note=COMMIT),opcodes=[dict(opcode=i,engine_name=name,op=OPS.get(i,'engine.'+re.sub('[^a-z0-9]+','_',name.lower()).strip('_'))) for i,name in sorted(labels.items())])]
  for a in self.by_kind['inputGraph']:
   source=a['source']; data=self.read(a['file']); nodes=data['nodes']; bacpath=source.removesuffix('.bcm')+'.bac'
   # Character uses GOK_PLAYER.bac; skills use *_PLAYER.bcm but unsuffixed BAC.
   if not any(s.startswith(uid('subaction',bacpath)+'/') for s in self.subids):
    alternative=source.removesuffix('_PLAYER.bcm')+'.bac'
    if any(s.startswith(uid('subaction',alternative)+'/') for s in self.subids):bacpath=alternative
   children=collections.defaultdict(list)
   for node in nodes:
    if node['parent'] is not None:children[node['parent']].append(uid('action',source+'/'+node['id']))
   by_source={node['sourceId']:uid('action',source+'/'+node['id']) for node in nodes}
   for i,node in enumerate(nodes):
    f=node['sourceFields']; sid=uid('subaction',bacpath+'/'+str(f.get('BacEntryPrimary')))
    transitions=children[node['id']][:]
    for key in ('LoopAsChild','LoopAsSibling'):
     if f.get(key) in by_source:transitions.append(by_source[f[key]])
    actor=dict(id=uid('action',source+'/'+node['id']),index=index('xv2.bcm.node',int(node['sourceId'])),name=node['inputLabels'],source='content',category='misc',enters=list(dict.fromkeys(transitions)),summary='Inferred condition-tree branch; child/loop candidates are not confirmed runtime transitions.',engine=ext(scope=source,source_file=uid('file',source),decoded_pointer=f'/nodes/{i}',input_mask=node['inputMask'],parent=uid('action',source+'/'+node['parent']) if node['parent'] else None,condition_status='not executed'),provenance=self.source_prov(source))
    actor['engine']['xv2.pc']['bac_scope']=bacpath
    actor['engine']['xv2.pc']['bac_bindings']={}
    for field in ('BacEntryPrimary','BacEntryAirborne','BacEntryCharge','BacEntryUserConnect','BacEntryVictimConnect','BacEntryTargetingOverride'):
     value=f.get(field)
     if isinstance(value,int) and value>=0 and value!=65535:
      ref=uid('subaction',bacpath+'/'+str(value))
      actor['engine']['xv2.pc']['bac_bindings'][field]=dict(index=index('xv2.bac.entry',value),subaction=ref if ref in self.subids else None,note='Static field reference; zero can be a default and activation conditions remain unexecuted.')
    if sid in self.subids:actor['subaction']=sid
    b['actions'].append(actor)
  for a in self.by_kind['projectiles']:
   for i,x in enumerate(self.read(a['file'])['BSA_Entries']):
    b['articles'].append(dict(id=uid('article',a['source']+'/'+x['Index']),global_index=index('xv2.bsa.entry',int(x['Index'])),name=Path(a['source']).name+':'+x['Index'],kind='projectile',status='unknown',descriptor=a['source'],engine=ext(scope=a['source'],source=self.blob(a['file'],f'/BSA_Entries/{i}')),provenance=self.source_prov(a['source'])))
  b['body']=dict(dynamics=dict(chains=[dict(skeleton=uid('skel',p['rig']),attachment=uid('joint',BODY+'/'+p['attachBone']),source=p['physics']) for p in self.m['parts'] if p['attachBone']],note='SCD dynamics are present as raw source only; target rigid bake is an explicit conversion loss.'),provenance=prov('inferred','ev:manifest'))
 def effects_audio(self):
  banks=[]
  for a in self.by_kind['effects']:
   d=self.read(a['file']); effects=[index('xv2.eepk.effect',int(e.get('Index',e.get('IndexNum',0)))) for e in d['Effects']]
   banks.append(dict(id=uid('fxbank',a['source']),file=uid('file',a['source']),owner='shared' if '/cmn/' in a['source'] else 'self',id_scheme='(source EEPK file, xv2.eepk.effect); event scope chooses bank',engine=ext(effect_indices=effects,source_data=self.blob(a['file'])),provenance=self.source_prov(a['source'])))
  self.doc['assets']['effects']=banks
  # These are unresolved ACB references, not invented bank contents.
  sounds=['sound/SE/Battle/Common/CAR_BTL_CMN.acb','sound/SE/Battle/Chara/CAR_BTL_GOK.acb']
  self.doc['assets']['audio']=[]
  for i,path in enumerate(sounds):
   fid=uid('file',path)
   self.doc['resources']['files'].append(dict(id=fid,name=path,role='sound_bank',container=dict(format='ACB'),provenance=prov('assumed','ev:manifest',note='Unresolved expected naming reference; not extracted and filename not confirmed by CSO.')))
   self.doc['assets']['audio'].append(dict(id=uid('sfxbank',path),file=fid,id_scheme='Unresolved ACB cue IDs; no waveform or cue table decoded.',provenance=prov('unknown','ev:manifest')))
 def parity_moves(self):
  b=self.doc['behavior']; h=self.host; hostmoves={m['input']:m for m in h['behavior']['moves']}; prefix=h['document_id']+'#'
  subs={s['id']:s for s in b['subactions']}; scripts={s['id']:s for s in b['scripts']}
  inputs=json.loads((ROOT/'ports/ir/schema/behavior.schema.json').read_text())['$defs']['Move']['properties']['input']['enum']
  for key in inputs:
   candidates=[uid('subaction',BAC+'/'+str(i)) for i in MOVE_CANDIDATES.get(key,[])];candidates=[s for s in candidates if s in self.subids]
   if key=='special_n':candidates=[s['id'] for s in b['subactions'] if 'skill/SPA/000_GOK_KMH/' in s['id'] and not s['empty']][:1]
   relation='analogous' if candidates else 'no_counterpart'
   if key in ('grab','fthrow','special_n','special_hi'):relation='partial' if candidates else relation
   desc=('Proposed destination adaptation candidate selected from decoded BAC animation/hit events; source input semantics and strike direction are unverified. ' if candidates else 'No verified source counterpart in this pass; destination action must be authored or explicitly disabled. ')
   desc+='Goku uses arena combat and health damage; Falcon uses platform movement, percentage damage and knockback. This row is not executable behavior or approved tuning.'
   evidence=['ev:parity_design']
   for candidate in candidates:
    s=subs[candidate]; evidence.append(self.ev(s['engine']['xv2.pc']['scope']))
    hits=[e['frame'] for e in scripts[s['scripts']['main']]['events'] if e['op']=='hitbox.create']
    animations=[f"{a['source_scope']}:{a['index']['value']}[{a['start_frame']}:{a['end_frame']}]" for a in s['engine']['xv2.pc']['animation_bindings'] if a['source_scope'] not in ('FaceBase','FaceForehead')]
    desc+=f" Candidate {candidate}: animation selections {', '.join(animations) or 'unresolved'}, source hit starts {hits}."
   if not candidates:evidence.append('ev:manifest')
   evidence=list(dict.fromkeys(evidence))
   m=dict(id='move:'+key,input=key,name='Goku '+key,subactions=candidates,description=desc,provenance=prov('inferred' if candidates else 'unknown',*evidence))
   b['moves'].append(m)
   target=hostmoves.get(key,{}).get('id','file:plca')
   self.parity.append(dict(here=m['id'],there=prefix+target,relation=relation,differences=desc+' Evidence: '+', '.join(evidence)+'.'))
  hostroles={r['role']:r for r in h['assets']['bone_roles']}
  hostskels={s['id']:s for s in h['assets']['skeletons']}
  for r in self.doc['assets']['bone_roles']:
   role=r['role'];bone,artist=ROLE_MAP[role];hr=hostroles.get(role)
   target='file:plcanr'
   if hr:target=hostskels[hr['skeleton']]['joints'][hr['joint']]['id']
   missing=role.startswith('hand_item') or role=='throw_n' or not hr
   diff=f'Role {role}; artist role {artist or "unmapped"}; XV2 {bone}. '+('No matching semantic source helper; destination socket/anchor must be authored from this anatomical proxy.' if role.startswith('hand_item') or role=='throw_n' else 'Topology, bind axes and local translations differ; retarget by role and reconcile bind poses.')
   self.parity.append(dict(here=uid('joint',BODY+'/'+bone),there=prefix+target,relation='no_counterpart' if missing else 'analogous',differences=diff+' Evidence: ev:role_map.'))
  for a in h['behavior']['attributes']['common']:
   key=a['key']; issue=self.issue('attribute/'+key,'XV2 attribute unavailable: '+key,'v0.1 did not extract stats. Host comparison value '+json.dumps(a.get('value'))+' is not an XV2 measurement. A destination design value must be labelled separately.',severity='info')
   b['attributes']['common'].append(dict(key=key,engine_name=a.get('engine_name',key),meaning='Source value absent; do not substitute the host number as source data.',provenance=prov('unknown','ev:manifest')))
   self.parity.append(dict(here=issue,there=prefix+'file:plca',relation='no_counterpart',differences=f'Attribute {key} (host field {a.get("engine_name",key)}): XV2 value not extracted; Falcon value {json.dumps(a.get("value"))}. Target tuning is a design choice, not numerical conversion. Evidence: ev:manifest; host evidence on behavior.attributes.common.'))
 def finish(self):
  d=self.doc
  for g in self.m['gaps']:self.issue('v0.1/'+g['category'],g['category'],g.get('detail',str(g)))
  self.issue('schema_addressability','Schema role/attribute fields have no IDs','Role parity points to its joint and names the role in differences. Attribute parity points from a missing-source Issue to host file:plca and names the exact attribute key. Native schema integer joint/mesh positions remain scoped by their enclosing skeleton/model; source numbering also appears as IndexSpace records.','ev:schema','info')
  self.issue('fps_unmeasured','Source frame rate has not been measured','No timebase in shallow data. LibXenoverse2 exports at 60 fps, a tool convention only. Destination 60 Hz is a design convention, not an observed XV2 clock.','ev:manifest','info')
  cov={k:dict(status='absent') for k in json.loads((ROOT/'ports/ir/schema/character.schema.json').read_text())['properties']['coverage']['propertyNames']['enum']}
  for k in ['identity','resources','assets','assets.skeletons','assets.models','assets.textures','assets.costumes','assets.animations','assets.effects','behavior','behavior.body','behavior.actions','behavior.subactions','behavior.scripts','behavior.moves','behavior.articles','issues']:
   cov[k]=dict(status='representative' if k in ('assets.models','assets.textures','behavior.moves') else 'summary',note='Coverage bounded by accepted v0.1 dump; no runtime observation or full dependency closure.')
  cov['behavior.attributes']=dict(status='absent',note='Keys mirrored for comparison; no XV2 stat values extracted.')
  cov['assets.audio']=dict(status='absent',note='Unresolved ACB references only; no cue tables or waveforms.')
  d['coverage']=cov
  d['integration']=dict(hosts=[dict(engine='xv2.pc',revision='1.25.02.0',engine_detail=ext(source_package=str(self.source),parity_policy='Read root parity before using source entities for destination conversion.',raw_part_manifest=self.blob('manifest.json','/parts'),role_map='ports/goku-xv2/ROLE-MAP.md',skill_bindings=self.blob('skills.json')),provenance=prov('inferred','ev:manifest','ev:schema'))])
  return d
 def build(self):
  for method in [self.evidence_resources,self.skeletons,self.models,self.animations,self.behavior,self.effects_audio,self.parity_moves]:method()
  return self.finish()

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=DEFAULT);p.add_argument('--host',type=Path,default=PORT/'ir/host.melee.ir.json');p.add_argument('--out',type=Path,default=PORT/'ir/goku.xv2.ir.json');a=p.parse_args()
 d=Builder(a.source,json.loads(a.host.read_text())).build();a.out.parent.mkdir(parents=True,exist_ok=True)
 temp=a.out.with_suffix(a.out.suffix+'.tmp');temp.write_text(json.dumps(d,indent=1,ensure_ascii=False),encoding='utf-8');temp.replace(a.out)
 print(json.dumps(dict(output=str(a.out),bytes=a.out.stat().st_size,actions=len(d['behavior']['actions']),subactions=len(d['behavior']['subactions']),scripts=len(d['behavior']['scripts']),parity=len(d['parity']))))
if __name__=='__main__':main()

"""Original parametric recipes. No game/disc/imported assets are used."""
from pathlib import Path
import copy
import json
import math
import hashlib
import shutil

VERSION = 2
ASSET_ROOT = Path(__file__).resolve().parents[2] / "menu/out_effects_study"
ROLES = ('charge', 'core', 'flow', 'ring', 'fragments', 'aftermath', 'distortion')
PACKAGES = ('SolarEruption', 'GlacialShatter', 'ThermalBlend', 'ThermalShock')

def asset_catalog():
    """Pin installation to the reviewed artwork, before writing runtime packages."""
    manifest = json.loads((ASSET_ROOT / 'manifest.json').read_text())
    assets = {a['name']: a for a in manifest['assets']}
    for asset in assets.values():
        path = ASSET_ROOT / asset['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError(f"Reviewed asset checksum mismatch: {path}")
    return assets

def curve(points): return {'kind':'keys','keys':points}
def emitter(name, texture, color, start, duration, rate, life, scale, speed=0, shader='sprite', burst=False, blend='add'):
    mat={'shader':{'type':shader,'color':'modulate'},'blend':blend,'depth_test':True}
    samplers=[{'texture':texture,'wrap':['Clamp','Clamp']}]
    if shader!='sprite':
        samplers.append({'texture':'flow_curl' if shader=='distortion' else 'noise_soft','wrap':['Repeat','Repeat'],'uv':{'scroll_add':[.007,.011]}})
        mat['shader'].update(offset=1,strength=[.013,.009] if shader=='distortion' else [.05,.04],color_textures=[] if shader=='distortion' else [0],alpha_textures=[0],offset_targets=[0])
    if blend=='add': mat['bloom']={'threshold':.7,'intensity':.3}
    return {'name':name,'kind':'particle','follow':'none','emission':{'start':start,'duration':duration,'rate':rate,'interval':1,
        'one_time':bool(burst),'fade':{'on_stop':1,'alpha_frames':12}},
        'shape':{'type':'sphere_fill','radius':[3,4,2]},
        'particle':{'life':life,'life_random_pct':15,'shape':'billboard','velocity':{'all_direction':speed,'direction':[0,1,0],'direction_scale':speed*.25,'random_pct':20},
          'forces':{'air_resistance':.97,'gravity_dir':[0,-1,0],'gravity':.001 if speed else 0,'gravity_world':1},
          'rotation':{'init_random':[0,0,math.tau],'add_random':[0,0,.02]},
          'scale':{'base':list(scale)+[1],'random_pct':[15,15,0],'keys':[[.35,.35,1,0],[1,1,1,.2],[1.5,1.5,1,1]]}},
        'material':mat,'samplers':samplers,
        'color':{'color0':curve([[*color,0],[*color,.35],[*[c*.4 for c in color],1]]),
          'alpha0':curve([[0,0,0,0],[.85,0,0,.12],[.55,0,0,.65],[0,0,0,1]]),'scale':1,
          'param':{'kind':'constant','value':1}}}

def founder(ice=False):
    prefix='ice' if ice else 'fire'
    c=[.32,.75,1] if ice else [1,.24,.018]
    bright=[.8,.95,1] if ice else [1,.8,.28]
    es=[emitter(prefix+'_charge','frost_branch' if ice else 'ember_shard',c,0,36,1.0,24,(1.5,1.5),-.12),
      emitter(prefix+'_core','ice_cleaver' if ice else 'flame_lance',bright,30,1,6,30,(7,9),0,'warp',True),
      emitter(prefix+'_flow','ice_needle' if ice else 'flame_hook',c,28,22,2.0,30,(2.3,4.8) if ice else (3.4,7.5),.27 if ice else .38),
      emitter(prefix+'_ring','ring_broken' if ice else 'ring_clean',bright,36,1,2,28,(15,15),0,'warp',True),
      emitter(prefix+'_fragments','ice_chip' if ice else 'streak_taper',bright,37,1,70,36,(1.2,1.2) if ice else (1.8,.55),.72,'sprite',True),
      emitter(prefix+'_aftermath','steam_wisp' if ice else 'smoke_billow', [.38,.65,.78] if ice else [.25,.15,.10],46,32,.7,42,(4.5,4.5),.08,'sprite',False,'alpha'),
      emitter(prefix+'_distortion','smoke_billow' if ice else 'steam_wisp',[1,1,1],30,1,2,44,(16,16),0,'distortion',True,'alpha')]
    # The gathering layer travels inward from a shell; its silhouette builds toward release.
    es[0]['shape']={'type':'sphere','radius':[7,9,3]}
    for k in (1,3,6): es[k]['shape']={'type':'point'};es[k]['follow']='srt';es[k]['particle']['rotation']={}
    es[3]['particle']['scale']['keys']=[[.2,.2,1,0],[1,1,1,.45],[1.65,1.65,1,1]]
    if ice: es[2]['particle']['shape']='directional_polygon'
    else:
        es[2]['emission'].update(rate=3.0,interval=1)
        es[2]['particle']['life']=34
        es[2]['shape']={'type':'sphere','radius':[5,5,2]}
        es[2]['particle']['rotation']={'init_random':[0,0,1.2],'add_random':[0,0,.03]}
    return es

def package(name, emitters, assets):
    kinds=sorted({s['texture'] for e in emitters for s in e['samplers']})
    return {'geno_fx':1,'name':name,'source':{'format':'original procedural effects lab','recipe_version':VERSION,'phases':[0,36,78,128],
            'asset_set':'effects-study-01','asset_sha256':{k:assets[k]['sha256'] for k in kinds},
            'sprite_pivot':'center (asset anchors are authoring hints, not runtime pivots)'},
        'textures':[{'name':k,'file':'tex/'+k+'.png','w':assets[k]['size'][0],'h':assets[k]['size'][1],'swizzle':assets[k].get('gfx_texture_swizzle','rgba')} for k in kinds], 'emitters':emitters}

def recipes():
    assets=asset_catalog()
    fire, ice=founder(), founder(True)
    # Matching role pairs crossfade in one package. Midpoint retains both silhouettes,
    # with a cool shell around the hot core and fragment emission sharing a budget.
    blend=copy.deepcopy(fire+ice)
    shock=copy.deepcopy(ice)
    for e in shock: e['emission']['start']=max(0,e['emission']['start']-28)
    shock[0]['emission'].update(duration=8,rate=2)
    shock[1]['samplers'][0]['texture']='impact_flash'
    shock[1]['particle']['life']=8
    shock[4]['color']['color0']=curve([[.65,.95,1,0],[1,.4,.04,.3],[.3,.06,.01,1]])
    shock[4]['emission']['rate']=95
    shock[5]['emission'].update(start=12,duration=38,rate=1.2)
    shock[5]['color']['color0']={'kind':'constant','value':[.7,.8,.82]}
    shock[5]['particle']['scale']['base']=[5.5,5.5,1]
    hot=copy.deepcopy(fire[1]);hot['name']='shock_hot_crown';hot['samplers'][0]['texture']='flame_fork'
    hot['emission'].update(start=6,rate=3);hot['particle']['life']=20;shock.append(hot)
    return [package('SolarEruption',fire,assets),package('GlacialShatter',ice,assets),package('ThermalBlend',blend,assets),package('ThermalShock',shock,assets)]

def build(mod):
    for data in recipes():
        path=mod/'fx'/data['name'];path.mkdir(parents=True,exist_ok=True)
        (path/'tex').mkdir(exist_ok=True)
        for tex in data['textures']:
            shutil.copyfile(ASSET_ROOT/'rgba'/(tex['name']+'.png'),path/tex['file'])
        (path/(data['name']+'.gfx.json')).write_text(json.dumps(data,indent=2)+'\n')

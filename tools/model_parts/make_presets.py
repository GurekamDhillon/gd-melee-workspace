"""Original procedural textures/presets for the existing sprite, warp and distortion shaders."""
from pathlib import Path
import copy
import json
import math
import struct
import zlib

PRESETS = ('GoldEmbers','FrostDrift','ElectricSparks','CrimsonSpiral','EmeraldRings','HeatShimmer','ShadowPulse')

def png(path, fn, n=96):
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    raw=bytearray()
    for y in range(n):
        raw.append(0)
        for x in range(n): raw.extend(round(max(0,min(1,c))*255) for c in fn((x+.5)/n,(y+.5)/n))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

def texture(kind,u,v):
    x,y=(u-.5)*2,(v-.5)*2;r=math.hypot(x,y)
    if kind=='noise': return (.5+.3*math.sin(u*math.tau*4+math.sin(v*math.tau*3)),.5,1,.5+.3*math.cos(v*math.tau*4+math.sin(u*math.tau*2)))
    if kind=='bolt':
        # Piecewise-linear lightning, with a thin branch; no imported textures.
        points=[(-.95,.05),(-.5,-.28),(-.1,.13),(.15,-.12),(.5,.25),(.95,-.05)]
        distance=10
        for (y0,x0),(y1,x1) in zip(points,points[1:]):
            if y0<=y<=y1:
                center=x0+(x1-x0)*(y-y0)/(y1-y0)
                distance=min(distance,abs(x-center))
        if -.1<=y<=.5:distance=min(distance,abs(x-(.13+(y+.1)*.75)))
        a=math.exp(-(distance/.034)**2)*max(0,1-abs(y))**.25
        return (1,1,1,a)
    if kind=='ring': a=math.exp(-((r-.64)/.065)**2)*(.6+.4*math.sin(math.atan2(y,x)*9+r*10)**2)
    elif kind=='flake': a=max(0,1-r)**2+math.exp(-abs(x)*35-abs(y)*5)*.6+math.exp(-abs(y)*35-abs(x)*5)*.6
    else: a=max(0,1-r*r)**2
    return (1,1,1,a)

def build(mod):
    settings=[('GoldEmbers','sprite',[1,.3,.025],2.0,'add'),('FrostDrift','sprite',[.65,.9,1],2.8,'alpha'),
      ('ElectricSparks','sprite',[.08,.5,1],2.2,'add'),('CrimsonSpiral','warp',[1,.035,.07],14,'add'),
      ('EmeraldRings','warp',[.08,1,.3],15,'screen'),('HeatShimmer','distortion',[1,1,1],14,'alpha'),
      ('ShadowPulse','warp',[.3,.07,.55],16,'sub')]
    for name,shader,color,scale,blend in settings:
        path=mod/'fx'/name; kinds=[('bolt' if name=='ElectricSparks' else 'flake') if name in ('FrostDrift','ElectricSparks') else 'soft'] if shader=='sprite' else ['ring' if shader=='warp' else 'soft','noise']
        for kind in kinds:png(path/'tex'/(kind+'.png'),lambda u,v,k=kind:texture(k,u,v))
        particle={'life':48,'shape':'billboard','scale':{'base':[scale,scale,1]},'forces':{'air_resistance':.98}}
        emission={'rate':.8 if shader=='sprite' else 1,'interval':0 if shader=='sprite' else 36,'duration':0,'one_time':0,'fade':{'on_stop':1,'alpha_frames':8}}
        shape={'type':'sphere','radius':[6,8,4]} if shader=='sprite' else {'type':'point'}
        if shader=='sprite':particle['velocity']={'direction':[0,1 if name=='GoldEmbers' else -.4,0],'direction_scale':.13,'all_direction':.035}
        else:particle['rotation']={'add':[0,0,.025 if name=='CrimsonSpiral' else -.012]}
        material={'shader':{'type':shader,'color':'modulate'},'blend':blend,'depth_test':1}
        if shader!='sprite':material['shader'].update({'offset':1,'strength':[.012,.01] if shader=='distortion' else [.11,.08], 'color_textures':[] if shader=='distortion' else [0],'alpha_textures':[0],'offset_targets':[0]})
        if name in ('GoldEmbers','ElectricSparks','CrimsonSpiral'):material['bloom']={'threshold':.4,'intensity':.6}
        samplers=[{'texture':k,'wrap':['Repeat','Repeat'] if k=='noise' else ['Clamp','Clamp']} for k in kinds]
        if len(samplers)>1:samplers[1]['uv']={'scroll_add':[.005,.003]}
        em={'name':name,'kind':'particle','follow':'none' if shader=='sprite' else 'srt','emission':emission,'shape':shape,'particle':particle,
          'material':material,'samplers':samplers,'color':{'color0':{'kind':'constant','value':color},'alpha0':{'kind':'keys','keys':[[0,0,0,0],[.8,0,0,.2],[0,0,0,1]]},'scale':1}}
        emitters=[em]
        if name=='ElectricSparks':
            particle['life']=14
            particle['scale']['base']=[2.8,7,1]
            particle['rotation']={'init_random':[0,0,math.tau]}
            particle['velocity']={'all_direction':.02}
            emission['rate']=1.2
            em['color']['color0']['value']=[.35,.75,1]
            em['color']['alpha0']['keys']=[[0,0,0,0],[1,0,0,.08],[.85,0,0,.7],[0,0,0,1]]
        elif name=='ShadowPulse':
            # Subtraction alone disappears against FD's dark background. Keep
            # the dark layer but add an independently fading violet boundary.
            rim=copy.deepcopy(em);rim['name']='ShadowPulseRim'
            rim['material']['blend']='add'
            rim['material']['shader']['strength']=[.04,.025]
            rim['color']['color0']['value']=[.6,.12,1]
            rim['color']['alpha0']['keys']=[[0,0,0,0],[.85,0,0,.2],[.5,0,0,.7],[0,0,0,1]]
            rim['particle']['scale']['keys']=[[.6,.6,1,0],[1,1,1,.4],[1.3,1.3,1,1]]
            emitters.append(rim)
        data={'geno_fx':1,'name':name,'source':{'format':'original procedural showcase','note':'Preset for existing '+shader+' shader; no new shader algorithm'},
          'textures':[{'name':k,'file':'tex/'+k+'.png','w':96,'h':96,'swizzle':'rgba'} for k in kinds],'emitters':emitters}
        (path/(name+'.gfx.json')).write_text(json.dumps(data,indent=2)+'\n')

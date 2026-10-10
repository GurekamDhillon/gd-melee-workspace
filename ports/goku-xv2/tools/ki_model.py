"""Original cyan beam proxy for the charged Ki article; no XV2 FX bytes are used."""
import base64
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.geno.artist.convert import fighterbuild_dll

def build(package,art_build,scale=1.0):
    package,art_build = Path(package).resolve(),Path(art_build).resolve()
    for p in (package,art_build):
        if not p.is_relative_to((ROOT/'_build').resolve()):
            raise ValueError('Article output must remain under _build')
    def vertex(ring,column):
        a = math.pi*ring/8
        b = math.tau*column/16
        p = [math.sin(a)*math.cos(b),math.cos(a),math.sin(a)*math.sin(b)]
        # Native item forward is model +Z, rotated to world +/-X by item facing.
        return {'p':[v*scale for v in (2.5*p[0],2.5*p[1],7.5*p[2]-4.5)],'n':p,'uv':[column/16,ring/8],'w':[[1,1.0]]}
    triangles = []
    for ring in range(8):
        for column in range(16):
            a,b,c,d = vertex(ring,column),vertex(ring,column+1),vertex(ring+1,column),vertex(ring+1,column+1)
            if ring: triangles.append([a,c,b])
            if ring<7: triangles.append([b,c,d])
    mesh = {'joints':[{'name':name,'parent':parent,'scale':[1,1,1],'rot':[0,0,0],'trans':[0,0,0],
                        'ibm':[1,0,0,0,0,1,0,0,0,0,1,0]} for name,parent in [('TopN',-1),('Ki',0)]],
            'textures':[{'name':'ki','w':4,'h':4,'fmt':'RGBA8','rgba':base64.b64encode(bytes([65,215,255,255])*16).decode()}],
            'dobjs':[{'object':'Ki','subindex':0,'group':None,'textures':['ki'],'wrap':[['ClampToEdge','ClampToEdge']],
                       'cull':'Cull_None','xlu':False,'lit':False,'tris':triangles}]}
    art_build.mkdir(parents=True,exist_ok=True)
    path = art_build/'ki-model.json'
    path.write_text(json.dumps(mesh),encoding='utf-8')
    dest = package/'files/GnGokuKi.dat'
    dest.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['dotnet',fighterbuild_dll(),'build',str(path),'-',str(dest),'goku_ki_joint','goku_ki_matanim',
                    str(art_build/'ki-model-report.json'),'--pc-palette','64'],check=True,cwd=ROOT)
    return dest

if __name__ == '__main__':
    build(sys.argv[1],sys.argv[2])

#!/usr/bin/env python3
"""Original fire/ice study assets, authored as SVG and deterministic data textures.

Build: python3 menu/pipeline/effects_assets.py
Requires NumPy, rsvg-convert and ImageMagick. Outputs review-only art under
menu/out_effects_study; does not install mods or change any effect recipes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import numpy as np

MENU = Path(__file__).resolve().parents[1]
OUT = MENU / 'out_effects_study'
SIZE = 256
FIRE = '#ffb85c'
ICE = '#88dafa'
SHARED = '#e0cdff'
ASSETS = []


def asset(name, title, group, role, body, tint, anchor=(.5, .5), notes=''):
    ASSETS.append(dict(name=name, title=title, group=group, role=role, body=body,
                       tint=tint, anchor=list(anchor), notes=notes, kind='mask'))


DEFS = '''<defs>
<linearGradient id="flame" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
 <stop offset="0" stop-color="white" stop-opacity=".15"/>
 <stop offset=".28" stop-color="white" stop-opacity=".92"/>
 <stop offset=".72" stop-color="white" stop-opacity=".65"/>
 <stop offset="1" stop-color="white" stop-opacity="0"/>
</linearGradient>
<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="white" stop-opacity="0"/>
 <stop offset=".75" stop-color="white" stop-opacity=".8"/>
 <stop offset="1" stop-color="white" stop-opacity="1"/>
</linearGradient>
<radialGradient id="puff"><stop stop-color="white" stop-opacity=".8"/>
 <stop offset=".48" stop-color="white" stop-opacity=".48"/>
 <stop offset=".8" stop-color="white" stop-opacity=".13"/>
 <stop offset="1" stop-color="white" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%" color-interpolation-filters="sRGB">
 <feGaussianBlur stdDeviation="2.1"/></filter>
<filter id="billow" x="-25%" y="-25%" width="150%" height="150%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency=".055" numOctaves="3" seed="41" result="noise"/>
 <feDisplacementMap in="SourceGraphic" in2="noise" scale="10" xChannelSelector="R" yChannelSelector="G"/>
</filter>
</defs>'''


asset('flame_lance', 'Flame / lance', 'Fire', 'Upward core and sharp release', '''
<path fill="url(#flame)" d="M45 92 C24 78 33 61 42 49 C49 39 49 22 59 8 C54 28 70 31 69 46 C80 39 84 26 83 20 C97 47 82 62 74 76 C70 87 74 97 68 113 L43 116 Z"/>
<path fill="white" opacity=".58" d="M53 103 C39 83 47 74 52 64 C59 54 59 45 58 34 C69 48 64 57 60 67 C56 78 67 86 60 101 Z"/>''', FIRE, (.48,.82), 'Narrow upright silhouette with an internal hot tongue.')
asset('flame_hook', 'Flame / hook', 'Fire', 'Curling outer flame', '''
<path fill="url(#flame)" d="M41 111 C39 89 22 83 24 60 C27 34 55 18 78 26 C93 30 99 43 95 57 C93 69 81 72 73 65 C89 67 91 49 78 44 C62 37 46 49 45 65 C44 83 67 89 59 113 Z"/>
<path fill="white" opacity=".7" d="M46 97 C43 83 34 73 36 60 C38 44 53 34 68 35 C51 40 43 48 43 63 C42 78 56 84 50 100 Z"/>''', FIRE, (.4,.82), 'A clear hook profile; mirror and rotate around the core.')
asset('flame_fork', 'Flame / fork', 'Fire', 'Broken flame crown', '''
<path fill="url(#flame)" d="M42 112 C32 95 22 82 28 68 C33 56 32 45 27 38 C43 47 43 67 50 70 C57 57 45 40 57 26 C62 20 65 13 65 8 C80 27 65 43 71 57 C79 51 80 37 91 30 C87 48 101 65 90 80 C79 92 83 103 77 115 Z"/>
<path fill="white" opacity=".6" d="M58 106 C51 96 44 90 47 81 C50 74 56 66 56 59 C64 69 61 79 67 82 C74 77 74 68 76 64 C82 79 72 91 69 108 Z"/>''', FIRE, (.48,.84), 'Three unequal tips, intended for brief bursts rather than wallpaper.')

asset('ice_needle', 'Ice / needle', 'Ice', 'Long outward shard', '''
<path fill="white" opacity=".32" d="M64 8 L80 45 L74 100 L59 119 L49 76 L52 31 Z"/>
<path fill="white" opacity=".88" d="M64 8 L65 53 L59 119 L49 76 L52 31 Z"/>
<path fill="white" opacity=".48" d="M65 53 L80 45 L74 100 L59 119 Z"/>
<path fill="none" stroke="white" stroke-width="1.15" d="M64 8 L80 45 L74 100 L59 119 L49 76 L52 31 Z M64 8 L65 53 L59 119 M52 31 L65 53 L80 45"/>''', ICE, (.5,.65), 'Facets are alpha values, so the whole shard remains tintable.')
asset('ice_cleaver', 'Ice / cleaver', 'Ice', 'Broad shell fragment', '''
<path fill="white" opacity=".35" d="M78 10 L98 51 L83 92 L49 117 L31 82 L40 37 Z"/>
<path fill="white" opacity=".82" d="M78 10 L69 63 L31 82 L40 37 Z"/>
<path fill="white" opacity=".4" d="M69 63 L98 51 L83 92 L49 117 Z"/>
<path fill="none" stroke="white" stroke-width="1.2" d="M78 10 L98 51 L83 92 L49 117 L31 82 L40 37 Z M78 10 L69 63 L49 117 M31 82 L69 63 L98 51"/>''', ICE, (.5,.58), 'Broad asymmetric wedge to vary the breakup silhouette.')
asset('ice_chip', 'Ice / chip', 'Ice', 'Small tumbling fragment', '''
<path fill="white" opacity=".35" d="M39 26 L83 37 L102 76 L70 104 L28 89 L21 55 Z"/>
<path fill="white" opacity=".85" d="M39 26 L67 61 L21 55 Z"/>
<path fill="white" opacity=".52" d="M67 61 L83 37 L102 76 L70 104 Z"/>
<path fill="none" stroke="white" stroke-width="1.5" d="M39 26 L83 37 L102 76 L70 104 L28 89 L21 55 Z M39 26 L67 61 L70 104 M21 55 L67 61 L102 76"/>''', ICE, notes='A squat fragment; distinct from the long and broad shards.')
asset('frost_branch', 'Frost / branch', 'Ice', 'Growing frost and fracture detail', '''
<g fill="none" stroke="white" stroke-linecap="round" stroke-linejoin="round">
<path stroke-width="2.6" d="M24 112 L48 84 L64 57 L84 25 L91 12"/>
<path stroke-width="1.8" d="M48 84 L24 75 L16 55 M48 84 L70 90 L94 84 M64 57 L41 44 L38 25 M64 57 L90 58 L111 42 M84 25 L67 20 L60 10"/>
<path stroke-width="1.1" d="M28 77 L25 62 M40 81 L36 66 M76 88 L83 73 M90 57 L97 43 M48 48 L48 33 M73 39 L91 37 M39 102 L53 103"/>
</g>''', ICE, (.19,.88), 'A branching fragment, not a full snowflake stamped everywhere.')

asset('ring_clean', 'Ring / clean', 'Impact', 'Charge halo and expanding wave', '''
<circle cx="64" cy="64" r="43" fill="none" stroke="white" stroke-width="2.2"/>
<circle cx="64" cy="64" r="40.6" fill="none" stroke="white" stroke-width=".7" opacity=".35"/>
''', SHARED, notes='A thin continuous ring with room to expand inside the texture.')
asset('ring_broken', 'Ring / fractured', 'Impact', 'Shatter and interrupted shockwave', '''
<g fill="none" stroke="white" stroke-linecap="butt">
<path stroke-width="2.7" d="M24 42 A45 45 0 0 1 68 19 M80 22 A45 45 0 0 1 108 61 M107 76 A45 45 0 0 1 86 103 M70 108 A45 45 0 0 1 25 88 M19 69 A45 45 0 0 1 20 54"/>
<path stroke-width="1" opacity=".55" d="M31 46 A38 38 0 0 1 54 27 M92 39 L106 31 M80 102 L85 116 M25 82 L12 90"/>
</g>''', SHARED, notes='Unequal arcs and radial splinters make the break direction readable.')
asset('impact_flash', 'Flash / release', 'Impact', 'One brief impact accent', '''
<path fill="white" d="M61 10 L66 49 L84 34 L73 54 L117 64 L76 69 L94 92 L69 76 L62 119 L57 76 L35 91 L47 70 L11 63 L49 57 L32 34 L56 49 Z"/>
<circle cx="62" cy="64" r="22" fill="url(#puff)"/>
''', SHARED, notes='A sharp asymmetric star, intended for only a few game frames.')
asset('streak_taper', 'Streak / taper', 'Impact', 'Fast fragments and swept accents', '''
<path fill="url(#fade)" d="M10 69 C44 59 78 57 111 63 C88 72 49 73 10 69 Z"/>
<path fill="white" opacity=".85" d="M45 66 L111 63 L76 68 Z"/>
''', SHARED, (.85,.5), 'The anchor is near the bright leading tip; the tail points left.')
asset('ember_shard', 'Ember / splinter', 'Fire', 'Small hot debris', '''
<path fill="white" opacity=".75" d="M44 26 L69 42 L84 72 L68 99 L51 76 L40 48 Z"/>
<path fill="white" d="M44 26 L62 52 L68 99 L51 76 L40 48 Z"/>
''', FIRE, notes='An angular hot fragment, rather than another round sparkle.')

asset('smoke_billow', 'Smoke / billow', 'Atmosphere', 'Soft, irregular aftermath', '''
<g filter="url(#billow)">
<ellipse cx="43" cy="68" rx="30" ry="25" fill="url(#puff)"/>
<ellipse cx="66" cy="52" rx="29" ry="35" fill="url(#puff)"/>
<ellipse cx="87" cy="67" rx="25" ry="29" fill="url(#puff)"/>
<ellipse cx="67" cy="83" rx="32" ry="25" fill="url(#puff)"/>
<ellipse cx="44" cy="42" rx="20" ry="18" fill="url(#puff)"/>
</g>''', '#bcc8dd', notes='Soft alpha with an irregular edge; tint dark for smoke or pale for mist.')
asset('steam_wisp', 'Steam / wisp', 'Atmosphere', 'Rising thermal-shock steam', '''
<path filter="url(#soft)" fill="url(#flame)" d="M46 112 C60 95 71 87 62 73 C50 56 46 43 61 30 C69 23 73 17 72 9 C86 26 71 37 65 45 C57 57 84 69 79 86 C75 101 61 109 57 117 Z"/>
<path filter="url(#soft)" fill="url(#flame)" opacity=".45" d="M30 106 C43 88 34 79 30 64 C25 44 43 37 43 22 C58 43 37 48 43 65 C53 83 47 101 38 113 Z"/>
''', '#c9eaf6', (.4,.85), 'Two unequal curls leave empty space between wisps.')


def png_bytes(pixels):
    h,w,c=pixels.shape
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b''.join(b'\0'+row.tobytes() for row in pixels)
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6 if c==4 else 2,0,0,0))+
            chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))


def uri(pixels):
    return 'data:image/png;base64,'+base64.b64encode(png_bytes(pixels)).decode()


def tinted(pixels,color):
    p=pixels.copy();p[:,:,:3]=[int(color[i:i+2],16) for i in (1,3,5)];return p


def data_textures():
    y,x=np.mgrid[:SIZE,:SIZE].astype(float)*math.tau/SIZE
    rng=np.random.default_rng(91473)
    field=np.zeros_like(x);dx=np.zeros_like(x);dy=np.zeros_like(x)
    for kx,ky in [(1,1),(2,-1),(1,3),(3,2),(4,-3),(5,1),(2,6),(7,-4)]:
        phase=rng.uniform(0,math.tau);amp=1/(kx*kx+ky*ky)
        theta=kx*x+ky*y+phase
        field+=amp*np.sin(theta);dx+=amp*kx*np.cos(theta);dy+=amp*ky*np.cos(theta)
    n=(field-field.min())/np.ptp(field)
    gray=np.round(n*255).astype(np.uint8)
    noise=np.stack([gray,gray,gray,np.full_like(gray,255)],axis=2)
    bound=max(np.max(np.abs(dx)),np.max(np.abs(dy)))
    flow=np.empty_like(noise);flow[:,:,0]=np.round(127.5+110*dy/bound)
    flow[:,:,1]=np.round(127.5-110*dx/bound);flow[:,:,2]=128;flow[:,:,3]=255
    return [('noise_soft','Noise / soft','Scalar modulation and distortion',noise,
             'Seamless grayscale data; scroll and remap it, not a visible particle.'),
            ('flow_curl','Flow / curl','Directional heat/refraction offsets',flow,
             'Seamless R/G vector field; 0.5 means zero offset. Use texture swizzle rgbg with the current warp/distortion shaders (G feeds alpha).')]


def write_sheet(out,assets,pixels):
    width,height=1600,1770
    body=['<rect width="1600" height="1770" fill="#101725"/>',
      '<path d="M40 38 H420 L406 46 H40Z" fill="#f0b429"/>',
      '<text x="40" y="93" font-size="38" font-weight="bold" fill="#f6eddc">FIRE / ICE — ASSET STUDY 01</text>',
      '<text x="42" y="124" font-size="17" fill="#aabace">16 original building blocks · review art only · no runtime integration</text>',
      '<text x="42" y="153" font-size="15" fill="#aabace">Warm / cool tints are previews. Production masks are white + alpha. Last two tiles are data maps.</text>']
    for i,a in enumerate(assets):
        x=40+(i%4)*390;y=182+(i//4)*385
        body.append(f'<rect x="{x}" y="{y}" width="370" height="365" rx="5" fill="#1d293a"/>')
        body.append(f'<text x="{x+16}" y="{y+30}" font-size="20" font-weight="bold" fill="#f6eddc">{i+1:02d} / {html.escape(a["title"])}</text>')
        body.append(f'<text x="{x+16}" y="{y+54}" font-size="13" fill="#aabace">{html.escape(a["group"].upper())} · {"RG DATA" if a["name"]=="flow_curl" else "LUMA DATA" if a["kind"]=="data" else "TINTABLE ALPHA"}</text>')
        preview=pixels[a['name']] if a['kind']=='data' else tinted(pixels[a['name']],a['tint'])
        u=uri(preview)
        for j,bg in enumerate(('#070c16','#e8edf3')):
            bx=x+14+j*174
            body.append(f'<rect x="{bx}" y="{y+72}" width="168" height="207" fill="{bg}"/>')
            body.append(f'<image href="{u}" x="{bx+4}" y="{y+92}" width="160" height="160"/>')
            body.append(f'<text x="{bx+10}" y="{y+270}" font-size="11" fill="{"#8293ab" if j==0 else "#52647b"}">{"DARK" if j==0 else "LIGHT"}</text>')
        body.append(f'<image href="{u}" x="{x+17}" y="{y+295}" width="32" height="32"/>')
        body.append(f'<text x="{x+64}" y="{y+308}" font-size="13" fill="#c5d2e4">{html.escape(a["role"])}</text>')
        body.append(f'<text x="{x+64}" y="{y+331}" font-size="12" fill="#8395ae">32 px check · 256 × 256 source</text>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1770" style="font-family:Liberation Sans,sans-serif">'+''.join(body)+'</svg>'
    (out/'preview/contact-sheet.svg').write_text(svg)
    subprocess.run(['rsvg-convert',str(out/'preview/contact-sheet.svg'),'-o',str(out/'preview/contact-sheet.png')],check=True)


def write_review(out,assets):
    cards=[]
    for i,a in enumerate(assets):
        n=a['name'];kind=a['kind'];cls='data' if kind=='data' else 'mask'
        # Embed previews so local-file browser CORS rules cannot hide CSS masks.
        encoded='data:image/png;base64,'+base64.b64encode((out/'rgba'/f'{n}.png').read_bytes()).decode()
        art=f'<img src="{encoded}" alt="{a["title"]}">' if kind=='data' else f'<div class="art mask" style="--mask:url(\'{encoded}\')"></div>'
        cards.append(f'''<article style="--tint:{a['tint']}"><div class="meta">{i+1:02d} / {a['group']} · {'DATA MAP' if kind=='data' else 'ALPHA MASK'}</div>
<h2>{a['title']}</h2><p class="role">{a['role']}</p>
<div class="pair"><div class="well dark">{art}<span>DARK</span></div><div class="well light">{art}<span>LIGHT</span></div></div>
<p class="notes">{a['notes']}</p><footer><a href="rgba/{n}.png" download>PNG ↗</a>{f'<a href="svg/{n}.svg" download>SVG ↗</a>' if kind=='mask' else '<span>Seed 91473</span>'}<span>256 × 256</span></footer></article>''')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fire / Ice — Asset Study 01</title><style>
@font-face{font-family:Kit;src:url('../SourceSans3/SourceSans3-Semibold.otf')}
*{box-sizing:border-box}body{margin:0;background:#101725;color:#f6eddc;font:17px Kit,system-ui,sans-serif;--size:160px;--opacity:1}
main{max-width:1580px;margin:auto;padding:42px 30px}header{border-top:5px solid #f0b429;padding-top:18px}
.eyebrow,.meta{color:#93a7c2;letter-spacing:.1em;font-size:12px;text-transform:uppercase}h1{font-size:clamp(30px,4vw,54px);margin:10px 0;font-style:italic}header p{max-width:850px;color:#b2c3d9;line-height:1.5}
.toolbar{display:flex;gap:25px;align-items:center;flex-wrap:wrap;padding:18px 22px;background:#23344c;margin:26px 0}
label{display:flex;gap:9px;align-items:center;font-size:15px}input[type=range]{accent-color:#f0b429;width:135px}button,a{color:#f0b429}button{padding:8px 12px;background:#101725;border:1px solid #6b809b;font:inherit;cursor:pointer}input[type=color]{width:36px;border:0;background:none}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}article{background:#1d293a;padding:18px;min-width:0}h2{margin:9px 0;font-size:23px}.role{font-size:14px;color:#b2c3d9;height:34px;margin:0 0 14px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.well{height:205px;position:relative;display:grid;place-items:center;overflow:hidden}.dark{background:#070c16}.light{background:#e8edf3}.well>span{position:absolute;bottom:7px;left:9px;font-size:10px;letter-spacing:.1em;color:#7f91aa}.light>span{color:#506076}
.art,.well img{width:var(--size);height:var(--size);object-fit:contain;opacity:var(--opacity)}.mask{background:var(--override,var(--tint));mask:var(--mask) center/contain no-repeat;-webkit-mask:var(--mask) center/contain no-repeat}
.notes{font-size:14px;line-height:1.45;min-height:62px;color:#b7c5d8}footer{border-top:1px solid #35465f;padding-top:12px;display:flex;gap:14px;font-size:12px}footer span:last-child{margin-left:auto;color:#93a7c2}a{text-decoration:none}a:hover{text-decoration:underline}
.explain{color:#b2c3d9;line-height:1.55;max-width:970px;margin-top:30px}
@media(max-width:1150px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:880px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:570px){.grid{grid-template-columns:1fr}main{padding:24px 16px}}
</style><main><header><div class="eyebrow">GD / Effects library · authoring review</div><h1>Fire / Ice — Asset Study 01</h1><p>Sixteen original building blocks for Solar Eruption, Glacial Shatter and Thermal Shock. Review the shapes, softness and small-size readability before we compose the effects in-game.</p></header>
<div class="toolbar"><label>Size <input id="size" type="range" min="32" max="192" value="160"><output id="sizeValue">160 px</output></label><label>Opacity <input id="alpha" type="range" min="10" max="100" value="100"></label><label>Test tint <input id="tint" type="color" value="#ffb85c"></label><button id="white">White masks</button><button id="reset">Reset</button><a href="preview/contact-sheet.png">Full preview sheet ↗</a></div>
<section class="grid">'''+''.join(cards)+'''</section><p class="explain"><strong>Review only.</strong> These assets are not installed in the game. Masks export as white RGB with straight alpha; preview colours are runtime-tint suggestions. Noise and flow tiles are opaque data textures, not visible particles. Flow needs explicit channel mapping when integrated. Shards here are 2D sprites; three-dimensional shell and shard meshes are a separate authoring step.</p></main>
<script>
const root=document.body, size=document.getElementById('size'), alpha=document.getElementById('alpha'), tint=document.getElementById('tint');
size.oninput=()=>{root.style.setProperty('--size',size.value+'px');document.getElementById('sizeValue').value=size.value+' px'};
alpha.oninput=()=>root.style.setProperty('--opacity',alpha.value/100);
tint.oninput=()=>root.style.setProperty('--override',tint.value);
document.getElementById('white').onclick=()=>root.style.setProperty('--override','#ffffff');
document.getElementById('reset').onclick=()=>{root.style.removeProperty('--override');size.value=160;alpha.value=100;size.oninput();alpha.oninput()};
</script></html>'''
    font=base64.b64encode((MENU/'SourceSans3/SourceSans3-Semibold.otf').read_bytes()).decode()
    page=page.replace("url('../SourceSans3/SourceSans3-Semibold.otf')", "url('data:font/otf;base64,"+font+"')")
    (out/'index.html').write_text(page)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    out=parser.parse_args().out.resolve()
    for tool in ('rsvg-convert','magick'):
        if not shutil.which(tool):parser.error(tool+' is required')
    for directory in ('svg','rgba','preview'):(out/directory).mkdir(parents=True,exist_ok=True)
    pixels={};records=[]
    for a in ASSETS:
        n=a['name'];svg='<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 128 128">'+DEFS+a['body']+'</svg>'
        (out/'svg'/f'{n}.svg').write_text(svg)
        raw=subprocess.run(['rsvg-convert','-w','512','-h','512',str(out/'svg'/f'{n}.svg')],check=True,capture_output=True).stdout
        alpha=subprocess.run(['magick','png:-','-resize','256x256','-alpha','extract','-depth','8','gray:-'],input=raw,check=True,capture_output=True).stdout
        p=np.full((SIZE,SIZE,4),255,dtype=np.uint8);p[:,:,3]=np.frombuffer(alpha,dtype=np.uint8).reshape(SIZE,SIZE)
        pixels[n]=p;records.append({k:v for k,v in a.items() if k!='body'})
    for name,title,role,p,note in data_textures():
        pixels[name]=p;records.append(dict(name=name,title=title,group='Distortion',role=role,
            tint='#ffffff',anchor=[.5,.5],notes=note,kind='data'))
    for a in records:
        p=pixels[a['name']];data=png_bytes(p);path=out/'rgba'/(a['name']+'.png');path.write_bytes(data)
        a.update(file='rgba/'+path.name,size=[SIZE,SIZE],format='RGBA8',alpha='straight',
                 wrap='repeat' if a['kind']=='data' else 'clamp',sha256=hashlib.sha256(data).hexdigest())
        if a['kind']=='mask':
            alpha=p[:,:,3]
            assert alpha.max()>100 and np.count_nonzero(alpha)>100,a['name']+' empty'
            edge=np.concatenate([alpha[0],alpha[-1],alpha[:,0],alpha[:,-1]])
            assert edge.max()<=3,a['name']+' clips the canvas'
            assert np.unique(alpha).size>=16,a['name']+' lacks alpha levels'
            assert np.all(p[:,:,:3]==255)
        else:
            a['colour_space']='linear data; do not apply sRGB decoding'
            a['gfx_texture_swizzle']='rgbg' if a['name']=='flow_curl' else 'rrrr'
            a['sampling_note']='The current FX offset shader reads R/A. Keep this sampler out of alpha_textures; data alpha is not particle opacity.'
    (out/'manifest.json').write_text(json.dumps(dict(schema=1,review_only=True,seed=91473,
       provenance='Original SVG paths, gradients and deterministic analytic fields in menu/pipeline/effects_assets.py; no game or disc references.',
       assets=records),indent=2)+'\n')
    write_sheet(out,records,pixels);write_review(out,records)
    print(f'Built {len(records)} assets; alpha, canvas bounds and dimensions validated.')
    print(out/'preview/contact-sheet.png');print(out/'index.html')


if __name__=='__main__':main()

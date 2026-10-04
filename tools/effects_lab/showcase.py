#!/usr/bin/env python3
"""Build an evidence-labelled tour of installed native recipes and original art."""
import argparse
import csv
import html
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(os.environ.get('GW_BUILD_ROOT', ROOT/'_build')).expanduser().resolve()
OUT = ROOT / '_build/effects-showcase'
CAPTURES = ROOT / '_build/effects-tour-profile/data/effects_tour_main'

CATALOGUE = [
 ('GoldEmbers','Gold Embers','Attachment preset','Warm orange motes rise gently around the body.','Quiet fire charge / hot ancestry; concentrate near hands for Assault.'),
 ('FrostDrift','Frost Drift','Attachment preset','Pale flakes drift down with a soft, broad silhouette.','Cold ancestry / persistent Guard field; localise near torso or defensive equipment.'),
 ('ElectricSparks','Electric Sparks','Attachment preset','Short blue-white angular bolts blink and disappear.','Electrical ready state / high-energy mutation; hands or weapon tip. This is not the planned Thunder Crown founder.'),
 ('CrimsonSpiral','Crimson Spiral','Attachment preset','A red ring ripples and rotates through a moving offset texture.','Aggressive pulse / hot readiness; torso or hand. There is no physical vortex simulation.'),
 ('EmeraldRings','Emerald Rings','Attachment preset','Green warped rings give a distinct circular boundary.','Guard boundary / recovery identity; chest or shield. Ring colour alone does not create a new gameplay ability.'),
 ('HeatShimmer','Heat Shimmer','Attachment preset','A transparent offset field is intended to bend the background. The black-background still does not visibly establish temporal heat distortion.','Heat accumulation / high-energy state; keep subtle near a core or heated equipment. Emission and renderer execution were observed; this still needs a textured-background motion review.'),
 ('ShadowPulse','Shadow Pulse','Attachment preset','A dark subtractive ring carries an independently fading violet rim.','Void-flavoured Guard / charged shell; torso. It is not the planned Astral Vortex founder.'),
 ('SolarEruption','Solar Eruption','Founder prototype','Gathering embers release curling flame silhouettes, a ring, streak fragments and smoke.','Fire founder identity; low charge at hands, bright ready accents, full burst on release.'),
 ('GlacialShatter','Glacial Shatter','Founder prototype','Frost gathers before needles, fractured rings, chips and mist scatter.','Ice founder identity; torso/Guard or cold equipment, with a bounded release burst.'),
 ('ThermalBlend','Thermal Blend · 50/50','Authored founder blend','A shared-budget hot core and cool shell retain both texture families.','Fire/ice mixed ancestry; colour, density, size and timing express the build. This preview applies the authored midpoint weights.'),
 ('ThermalShock','Thermal Shock','Scripted reaction','A brief fracture/flash gives way to steam and hot fragments.','Fire + ice reaction after activation; an event sequence, separate from persistent genome appearance.'),
 ('RogueCinderRelease','Cinder · immediate release','Gameplay release variant','Solar’s release begins immediately, without replaying the lab charge-up.','Current Cinder Assault release package. This isolated preview proves appearance; gameplay hit/charge evidence belongs to the roguelite acceptance run.'),
 ('RogueRimeRelease','Rime · immediate release','Gameplay release variant','Glacial’s core, ring and shards appear immediately on the release event.','Current Rime Assault release package. This isolated preview proves appearance; it does not prove a new Guard or Traversal ability.'),
]

TEMPLATE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TBD · Effects walkthrough</title><style>
@font-face{font-family:Kit;src:url(font.otf)}*{box-sizing:border-box}body{margin:0;background:#080d17;color:#f2efe4;font:17px Kit,Arial,sans-serif}button,a{font:inherit;color:inherit}button{cursor:pointer;border:1px solid #33476d;background:#14243c;padding:9px 13px}button:hover,button[aria-pressed=true]{background:#f0b429;color:#080d17}button:focus-visible,a:focus-visible{outline:3px solid #36c9d8;outline-offset:3px}header{padding:22px 28px;border-bottom:2px solid #f0b429;display:flex;align-items:center;justify-content:space-between;gap:16px}.eyebrow{letter-spacing:3px;font-size:12px;color:#f0b429}h1{margin:5px 0;font-size:31px;font-style:italic}header p{margin:0;color:#a8b7ce;font-size:14px}nav{display:flex;gap:7px;flex-wrap:wrap}main{padding:20px 28px}.viewer{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:20px}.stage{background:black;min-width:0;display:flex;align-items:center;justify-content:center;height:calc(100dvh - 230px);min-height:380px}.stage img{width:100%;height:100%;object-fit:contain}aside{padding:8px 0}h2{font-size:27px;margin:10px 0}h3{font-size:20px;margin:20px 0 7px}.badge{font-size:11px;color:#f0b429;letter-spacing:2px}p{color:#b8c2dc;font-size:15px;line-height:1.5}.meta{background:#11203a;padding:12px;font-size:13px;line-height:1.6;color:#b8c2dc}.controls{display:flex;gap:6px;margin:13px 0;flex-wrap:wrap}.track{height:3px;background:#24365b}.track span{display:block;background:#f0b429;height:100%;width:0}.strip{display:flex;gap:8px;overflow-x:auto;padding:14px 0}.strip button{flex-shrink:0;font-size:12px}section[hidden]{display:none}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}.card{border:1px solid #293c5e;background:#101c30;padding:14px}.card img{width:100%;max-height:230px;object-fit:contain;background:repeating-conic-gradient(#101928 0% 25%,#172236 0% 50%) 50% / 20px 20px}.card h3{margin:10px 0 5px}.card p{font-size:13px;margin:6px 0}.body-layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(290px,1fr);gap:24px}.body-layout img{width:100%}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #2a3c5d}th{color:#f0b429}small{color:#889ab6;font-size:12px}.future{background:#12223b;padding:18px;margin-top:20px}.future p{margin:6px 0}a{color:#36c9d8}@media(max-width:900px){header{flex-wrap:wrap}.viewer,.body-layout{grid-template-columns:1fr}.stage{height:55dvh;min-height:280px}main{padding:14px}h1{font-size:26px}}
</style><header><div><div class="eyebrow">TBD / VISUAL VOCABULARY</div><h1>Effects, materials, and build expression.</h1><p>13 installed recipes · 3 particle shader modes · 16 approved original textures</p></div><nav><button data-tab="native" aria-pressed="true">Native tour</button><button data-tab="textures">Texture library</button><button data-tab="body">Body + equipment</button></nav></header><main>
<section id="native"><div class="viewer"><div class="stage"><img id="frame" alt=""></div><aside><div class="badge" id="kind"></div><h2 id="name"></h2><p id="appearance"></p><h3>Build expression</h3><p id="expression"></p><div class="meta" id="meta"></div><div class="controls"><button id="previous">←</button><button id="play">Play tour</button><button id="next">→</button><button id="full">Fullscreen</button></div><div class="track"><span></span></div><p><small>← → browse · Space pauses · F fullscreen<br>__STATUS__<br>Captures are genuine native frames. All are cosmetic, fixed-seed attachment fixtures; attachment placement suggestions are design direction.</small></p><a href="evidence.tsv">Emission / cleanup evidence</a></aside></div><div class="strip" aria-label="Effect recipes"></div></section>
<section id="textures" hidden><div class="badge">ORIGINAL ASSET PREVIEW / STATIC PNGS</div><h2>The shapes behind the recipes.</h2><p>These are source textures; the runtime applies the effect colour. They are not simulated particles. Flame, ice, rings, impacts, smoke and flow fields give each recipe its silhouette; the runtime combines them through sprite, warp and distortion materials.</p><div class="grid">__TEXTURES__</div></section>
<section id="body" hidden><div class="badge">CURRENT CAPABILITY + PROPOSED PRESENTATION</div><h2>A gene should read on the fighter.</h2><div class="body-layout"><div><img src="build-study.png" alt="Illustrative build art with Assault hands/equipment, Guard torso and Traversal feet"><p><small>INTERACTIVE ART STUDY: placement diagram and balance numbers are illustrative. This is not a native body shader capture.</small></p></div><div><h3>Available today</h3><p>Measured fighter model parts accept texture-preserving tint. The native character-parts lab can attach effects to selected joints, recolour parts, restore materials, and inspect equipment. The roguelite binds reviewed body draws to Assault, Guard and Traversal, with explicit coverage diagnostics.</p><h3>Attachment choices</h3><p>Assault can express through hands and reviewed held equipment. Guard can express through torso and defensive pieces. Traversal can express through feet and movement pieces. Those placements share three logical slots; extra meshes do not grant extra slots.</p><p>Current roguelite binding conservatively leaves unreviewed transient equipment and secondary climbers untinted. Joint attachment capability does not mean every weapon has been authored and validated.</p><h3>Genetic states to author next</h3><p>Dormant: quiet material identity. Charging: sparse local motes. Ready: a readable accent. Release: the finite founder burst. Exhausted: short decay. Upgrade or fusion: a transition that follows the deterministic build change.</p><p>Those full state compositions, five polished founders, breeding controls and ten pairwise blends remain planned work.</p></div></div><h3>Recipes use shared renderer treatments</h3><p>Earlier Cyan Sparks, Violet Warp and Heat Haze demos are archived examples of the same three particle shader modes, outside this installed 13-package catalogue.</p><table><thead><tr><th>Treatment</th><th>Visible job</th><th>Existing examples</th></tr></thead><tbody><tr><td>Sprite</td><td>Sample particle textures, colour them, then alpha/add blend.</td><td>Gold Embers, Frost Drift, Electric Sparks, founder fragments/mist</td></tr><tr><td>Warp</td><td>An offset texture moves the coordinates used to sample the visible effect.</td><td>Crimson Spiral, Emerald Rings, Shadow Pulse, founder cores/rings</td></tr><tr><td>Distortion</td><td>An offset field displaces a captured background.</td><td>Heat Shimmer, founder heat/refraction layers</td></tr><tr><td>Texture-preserving part tint</td><td>Keep the fighter's existing texture detail while applying reviewed material colour.</td><td>Current per-body-role roguelite expression; separate from particle recipes</td></tr></tbody></table><div class="future"><div class="badge">CATALOGUE STILL TO COME</div><p>Thunder Crown · branching charge and strikes. Astral Vortex · rotating/inward energy bands. Comet Crescent · luminous sweep and fragmented trail.</p><p>These three founders and the remaining nine distinct founder-pair blends are proposals; Electric Sparks and Shadow Pulse are smaller current presets. Fire/ice is the one authored founder-pair prototype.</p></div></section></main>
<script>const slides=__SLIDES__;const q=s=>document.querySelector(s);let index=0,playing=false,elapsed=0;
slides.forEach((s,i)=>{const b=document.createElement('button');b.textContent=String(i+1).padStart(2,'0')+' '+s.name;b.onclick=()=>{setPlay(false);show(i)};q('.strip').append(b)});
function show(i){index=(i+slides.length)%slides.length;elapsed=0;const s=slides[index];q('#frame').src=s.image;q('#frame').alt=s.name+' — native cosmetic attachment preview';q('#kind').textContent='NATIVE CAPTURE / '+s.kind;q('#name').textContent=s.name;q('#appearance').textContent=s.appearance;q('#expression').textContent=s.expression;q('#meta').textContent=s.shaders+' · '+s.blends+' blending | '+s.emitters+' authored emitters | peak '+s.peak+' particles | seed 17029';Array.from(q('.strip').children).forEach((b,j)=>b.setAttribute('aria-pressed',j===index));q('.track span').style.width='0%'}
function setPlay(on){playing=on;q('#play').textContent=on?'Pause':'Play tour'}function advance(n){setPlay(false);show(index+n)}function fullscreen(){if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>{})}
q('#previous').onclick=()=>advance(-1);q('#next').onclick=()=>advance(1);q('#play').onclick=()=>setPlay(!playing);q('#full').onclick=fullscreen;
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{setPlay(false);document.querySelectorAll('main>section').forEach(s=>s.hidden=s.id!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(x=>x.setAttribute('aria-pressed',x===b))});
document.addEventListener('keydown',e=>{if(e.target.closest('button,a'))return;if(e.key==='ArrowLeft'){e.preventDefault();advance(-1)}else if(e.key==='ArrowRight'){e.preventDefault();advance(1)}else if(e.code==='Space'){e.preventDefault();setPlay(!playing)}else if(e.key.toLowerCase()==='f')fullscreen()});setInterval(()=>{if(playing&&!document.hidden){elapsed+=100;if(elapsed>=12000)show(index+1);q('.track span').style.width=elapsed/120+'%'}},100);show(0);</script></html>'''

def build(reviewed=False):
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'menu/SourceSans3/SourceSans3-Black.otf', OUT/'font.otf')
    shutil.copy2(ROOT/'menu/SourceSans3/LICENSE.md', OUT/'font-LICENSE.md')
    shutil.copy2(ROOT/'menu/out_roguelite/preview/build.png', OUT/'build-study.png')
    raw=(CAPTURES/'evidence.tsv').read_text()
    evidence={r['package']:r for r in csv.DictReader(raw.splitlines(),delimiter='\t')}
    shutil.copy2(CAPTURES/'evidence.tsv',OUT/'evidence.tsv')
    slides=[]
    for package,name,kind,appearance,expression in CATALOGUE:
        shutil.copy2(CAPTURES/(package+'.png'),OUT/(package+'.png'))
        paths=list((BUILD/'mods').glob('*/fx/'+package+'/'+package+'.gfx.json'))
        if not paths:
            raise FileNotFoundError('Installed effect package missing: '+package)
        data=json.loads(paths[0].read_text())
        shaders=sorted({e['material']['shader']['type'] for e in data['emitters']})
        blends=sorted({e['material']['blend'] for e in data['emitters']})
        slides.append(dict(package=package,name=name,kind=kind,appearance=appearance,expression=expression,image=package+'.png',shaders=' / '.join(shaders),blends=' / '.join(blends),emitters=len(data['emitters']),peak=evidence[package]['peak_particles']))
    art=ROOT/'menu/out_effects_study';manifest=json.loads((art/'manifest.json').read_text())
    cards=[]
    for a in manifest['assets']:
        target='texture-'+a['name']+'.png';shutil.copy2(art/a['file'],OUT/target)
        tint=''
        cards.append('<article class="card"><img src="'+target+'" alt="'+html.escape(a['title'])+'" '+tint+'><h3>'+html.escape(a['title'])+'</h3><p>'+html.escape(a['role'])+'</p><p>'+html.escape(a['notes'])+'</p><small>'+html.escape(a['kind'])+' / '+str(a['size'][0])+' × '+str(a['size'][1])+'</small></article>')
    status='Corrected fixed-position captures; framing reviewed. Heat Shimmer appearance still needs a motion review.' if reviewed else 'Visual framing review pending: later frames require recapture; emission/lifecycle evidence only.'
    page=TEMPLATE.replace('__SLIDES__',json.dumps(slides)).replace('__TEXTURES__',''.join(cards)).replace('__STATUS__',status)
    (OUT/'index.html').write_text(page)
    (OUT/'catalogue.json').write_text(json.dumps(dict(visual_reviewed=reviewed,slides=slides),indent=2))
    if shutil.which('magick'):
        subprocess.run(['magick','montage','-font',str(OUT/'font.otf'),'-pointsize','18',
                        '-fill','#f0b429','-background','#080d17','-set','label','%t',
                        *[str(OUT/s['image']) for s in slides],'-geometry','392x294+4+12',
                        '-tile','4x',str(OUT/'contact-sheet.png')],check=True)
    print(OUT/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reviewed',action='store_true');build(parser.parse_args().reviewed)

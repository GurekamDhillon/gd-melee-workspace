#!/usr/bin/env python3
"""Original roguelite UI art: shared kit colours/type, SVG masks, interactive review.

No game/disc images, fonts or model references. Run from any directory; librsvg
renders original vector masks, while the review embeds Source Sans 3 (OFL).
"""
from pathlib import Path
import base64
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out_roguelite'

# Symbols use a 64-unit canvas and deliberately different silhouettes at 24 px.
ICONS = {
    'cinder': '<path d="M35 5C39 20 19 21 24 35C15 32 13 27 15 22C-1 40 13 59 32 59C53 59 63 40 46 21C47 34 39 37 36 29C31 22 43 17 35 5Z"/><path d="M33 35C31 43 21 45 27 53C40 59 46 45 33 35Z" fill="black"/>',
    'rime': '<path d="M31 4L46 15L53 42L34 60L13 46L10 23Z"/><path d="M31 11L31 52M15 26L31 34L46 19M31 34L47 43" fill="none" stroke="black" stroke-width="4"/>',
    'magic': '<path d="M33 4L40 22L58 29L40 36L33 55L26 36L8 29L26 22Z"/><path d="M53 4L55 10L62 12L55 15L53 22L50 15L44 12L50 10Z"/>',
    'item': '<path d="M24 7H42V14H39V23L52 44Q58 57 43 59H22Q7 57 13 44L26 23V14H24ZM28 28L21 39H44L37 28Z"/>',
    'special': '<path d="M36 3L9 36H29L24 61L56 24H36Z"/>',
    'assault': '<path d="M47 5L58 6L57 17L32 42L38 49L32 55L22 45L10 58L6 54L18 41L9 32L15 26L22 33Z"/><path d="M48 12L27 36" fill="none" stroke="black" stroke-width="3"/>',
    'traversal': '<path d="M24 6H42L39 34L54 42L59 53L56 58H9L7 49L19 36Z"/><path d="M12 49H48M25 19H39M22 28H37" fill="none" stroke="black" stroke-width="4"/>',
    'guard': '<path d="M32 5L55 13V31Q53 48 32 60Q11 48 9 31V13Z"/><path d="M32 14V50Q46 40 46 27V20Z" fill="black"/>',
    'focus': '<path d="M32 6L39 20L55 21L44 33L47 51L32 43L17 51L20 33L9 21L25 20Z"/><circle cx="32" cy="29" r="7" fill="black"/>',
    'gene': '<path d="M16 5C16 27 48 35 48 59M48 5C48 27 16 35 16 59M18 11H46M22 22H42M22 42H42M18 53H46" fill="none" stroke="white" stroke-width="6"/>',
    'fusion': '<path d="M12 8L28 24L23 29L7 13ZM52 8L57 13L41 29L36 24ZM32 24L47 39L32 60L17 39Z"/><path d="M26 39H38L32 48Z" fill="black"/>',
    'route': '<path d="M29 59V38L11 25V8H17V22L32 32L47 22V8H53V25L35 38V59Z"/><circle cx="14" cy="9" r="8"/><circle cx="50" cy="9" r="8"/>',
    'elite': '<path d="M9 15L23 26L32 8L41 26L55 15L49 46H15ZM17 52H47V59H17Z"/>',
    'check': '<path d="M7 32L23 48L58 14L51 7L23 35L14 25Z"/>',
    'left': '<path d="M9 32L31 10V24H57V40H31V54Z"/>',
    'right': '<path d="M55 32L33 10V24H7V40H33V54Z"/>',
    'down': '<path d="M32 55L10 33H24V7H40V33H54Z"/>',
    'up': '<path d="M32 9L10 31H24V57H40V31H54Z"/>',
}

def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="128" height="128"><defs><mask id="shape"><g fill="white">{body}</g></mask></defs><path fill="white" mask="url(#shape)" d="M0 0H64V64H0Z"/></svg>'

def build():
    for folder in ('svg', 'rgba', 'preview'):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    records=[]
    for name, body in ICONS.items():
        src=OUT/'svg'/f'ico_rogue_{name}.svg'
        src.write_text(svg(body))
        dst=OUT/'rgba'/f'ico_rogue_{name}.png'
        subprocess.run(['rsvg-convert', '-o', str(dst), str(src)],check=True)
        records.append({'name':f'ico_rogue_{name}','file':f'rgba/{dst.name}',
            'file_1x':f'out_roguelite/rgba/{dst.name}',
            'file_2x':f'out_roguelite/rgba/{dst.name}', 'format':'IA4',
            'size_1x':[32,32], 'size':[128,128], 'recommended_format':'ia4',
            'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
    kit=json.loads((ROOT/'out_kit/kit.json').read_text())
    manifest={'schema':1,'provenance':'Original vector paths in menu/pipeline/roguelite_art.py',
        'palette':kit['palette'],'shear':.25,'textures':records,
        'font':'Source Sans 3 / SIL OFL 1.1',
        'controls':{'left':'branch 1','right':'branch 2','down':'branch 3','up':'parent; taunt only at root'}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    font=base64.b64encode((ROOT/'SourceSans3/SourceSans3-Black.otf').read_bytes()).decode()
    symbols=''.join(f'<symbol id="i-{k}" viewBox="0 0 64 64"><mask id="mask-{k}"><g fill="white">{v}</g></mask><path fill="currentColor" mask="url(#mask-{k})" d="M0 0H64V64H0Z"/></symbol>' for k,v in ICONS.items())
    html=HTML.replace('__FONT__',font).replace('__SYMBOLS__',symbols)
    (OUT/'index.html').write_text(html)
    (OUT/'font-LICENSE.md').write_text((ROOT/'SourceSans3/LICENSE.md').read_text())
    (OUT/'README.md').write_text('''# Roguelite UI art study

Original Astra-authored SVG masks and interactive menu-kit art review. No game
images or fonts. Open index.html; click branch buttons or use arrow keys. Up backs
out within the tree; at root it signals taunt without running a game.

Rebuild: `python3 menu/pipeline/roguelite_art.py` (requires rsvg-convert).
Build/placement study: `python3 menu/pipeline/roguelite_build_art.py`, then open
`build.html`. Its abstract mannequin is original vector art, not a fighter mesh.
Feedback/motion study: `python3 menu/pipeline/roguelite_feedback_art.py`, then open
`feedback.html` and click Replay Feedback. These HTML studies are proposals, not
captures of completed game screens.

Convert the masks with a Python environment containing Pillow:
`python melee/worktrees/linux/pc/tools/png2gx.py --layout menu/out_roguelite/manifest.json --outdir menu/out_roguelite/gx`.
The roguelite installer copies these GX textures and supplies their kit metadata.

The preview is an art study, not a screenshot of implemented gameplay. Names and
numbers illustrate the proposed commands. 18 masks are exported as 128px PNG/SVG;
manifest records original source, hashes and recommended GX mask format.
''')
    print(OUT/'index.html')

HTML=r'''<!doctype html><html><head><meta charset="utf-8"><title>TBD · command tree art</title>
<style>
@font-face{font-family:Kit;src:url(data:font/otf;base64,__FONT__)}
:root{--ink:#0a0e18;--bone:#f2efe4;--muted:#b8c2dc;--gold:#f0b429;--blue:#1e3a8c;--fire:#ff8050;--ice:#8fdef6}
*{box-sizing:border-box}body{margin:0;background:var(--ink);color:var(--bone);font:18px Kit, sans-serif}main{max-width:1520px;margin:auto;padding:46px 52px 36px}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid var(--gold);padding-bottom:24px}.eyebrow{font-size:14px;color:var(--gold);letter-spacing:3px}.big{font-size:64px;line-height:1;transform:skewX(-14deg);transform-origin:left;margin:12px 0}.muted{color:var(--muted)}.hint{font-size:16px;line-height:1.6;text-align:right}.hint b{color:var(--gold)}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:34px}.step{padding:0 17px 22px;background:#101a2c;border-top:4px solid #304a78;position:relative}.step h2{font-size:19px;letter-spacing:1px;margin:20px 0 5px}.step h2 span{color:var(--gold);padding-right:8px}.path{font-size:13px;color:var(--muted);height:30px}
.fork{display:grid;grid-template-columns:1fr 1fr;gap:42px 16px;position:relative;margin-top:58px}.fork:before{content:"";position:absolute;left:25%;right:25%;height:24px;top:-30px;border-top:2px solid #5873a3;border-left:2px solid #5873a3;border-right:2px solid #5873a3}.fork:after{content:"";position:absolute;left:50%;height:55px;top:-64px;border-left:2px solid #5873a3}.node{position:relative;background:var(--blue);border:0;color:var(--bone);font:20px Kit;padding:18px 10px 14px;text-align:center;box-shadow:5px 6px 0 #030712;cursor:pointer;min-height:90px}.node:hover{filter:brightness(1.17)}.node.selected{background:var(--gold);color:var(--ink);box-shadow:5px 6px 0 #8b621b}.node.disabled{background:#242e43;color:#8793ac}.node .key{position:absolute;top:-14px;left:8px;background:var(--bone);color:var(--ink);height:28px;width:28px;padding:5px;box-shadow:2px 2px 0 #05070b}.node.selected .key{background:var(--gold)}.node .icon{display:block;width:34px;height:34px;margin:0 auto 5px}.node .small{font-size:12px;display:block;margin-top:5px}.node.bottom{grid-column:1/3;margin:0 24%;min-width:52%}.node.bottom:before{content:"";position:absolute;height:33px;left:50%;top:-42px;border-left:2px solid #5873a3}.step .status{margin-top:23px;display:flex;align-items:center;gap:8px;font-size:14px;color:var(--muted)}svg{width:24px;height:24px;flex-shrink:0}.status svg{color:var(--gold)}
.lower{display:grid;grid-template-columns:1.12fr 1fr;gap:24px;margin-top:32px}.section-title{font-size:15px;letter-spacing:2px;margin:0 0 16px;color:var(--muted)}.demo{background:#111f38;border:1px solid #2a4673;padding:22px}.demo-bar{display:flex;justify-content:space-between;align-items:center;gap:8px}.demo-bar strong{font-size:25px;font-style:italic}.breadcrumbs{color:var(--gold);font-size:13px;margin-top:5px}.live-buttons{display:flex;gap:12px;margin-top:28px}.live-buttons .node{flex:1;font-size:17px;min-width:0;padding-top:19px}.demo-footer{display:flex;justify-content:space-between;margin-top:22px;font-size:14px}.toast-stack{display:grid;gap:14px}.toast{background:#17243b;border-left:5px solid var(--gold);display:flex;gap:15px;align-items:center;min-height:96px;padding:15px 20px;box-shadow:5px 5px 0 #030712}.toast>svg{height:45px;width:45px;color:var(--gold)}.toast h3{font-size:20px;margin:0 0 4px}.toast p{margin:0;font-size:15px;color:var(--muted)}.toast.elite{border-color:#ff8050}.toast.elite>svg{color:#ff8050}.tag{font-size:11px;letter-spacing:2px;color:var(--gold);margin-bottom:5px}.elite .tag{color:#ff8050}.strip{border-top:1px solid #30415c;margin-top:34px;padding-top:24px;display:flex;align-items:center;gap:25px}.strip .symbols{display:flex;gap:20px;flex-wrap:wrap}.strip .symbols svg{width:31px;height:31px}.strip p{font-size:13px;max-width:195px;margin:0;color:var(--muted)}.fire{color:var(--fire)}.ice{color:var(--ice)}button:focus-visible{outline:3px solid white;outline-offset:6px}footer{margin-top:25px;font-size:12px;letter-spacing:1px;color:#7d88a6;display:flex;justify-content:space-between}@media(max-width:1050px){.steps{grid-template-columns:1fr}.lower{grid-template-columns:1fr}.hint{display:none}.big{font-size:40px}main{padding:30px}.strip{flex-wrap:wrap}}
</style></head><body><svg style="position:absolute;width:0;height:0" aria-hidden="true"><defs>__SYMBOLS__</defs></svg><main>
<header><div><div class="eyebrow">TBD / ROGUELITE · ART STUDY 01</div><div class="big">POWER AT YOUR THUMBS.</div><div class="muted">Three directions. A branching command tree.</div></div><div class="hint"><b>← → ↓</b> CHOOSE A BRANCH<br><b>↑</b> BACK ONE LEVEL<br>AT ROOT, <b>↑</b> TAUNTS</div></header>
<div class="steps">
<section class="step"><h2><span>01</span> COMMAND ROOT</h2><div class="path">Combat stays in your hands.</div><div class="fork"><button class="node selected" data-go="magic"><svg class="key"><use href="#i-left"/></svg><svg class="icon"><use href="#i-magic"/></svg>MAGIC</button><button class="node" data-go="item"><svg class="key"><use href="#i-right"/></svg><svg class="icon"><use href="#i-item"/></svg>ITEM</button><button class="node bottom" data-go="special"><svg class="key"><use href="#i-down"/></svg><svg class="icon"><use href="#i-special"/></svg>SPECIAL</button></div><div class="status"><svg><use href="#i-up"/></svg>Taunt available at the root.</div></section>
<section class="step"><h2><span>02</span> PICK A FAMILY</h2><div class="path">COMMAND → MAGIC</div><div class="fork"><button class="node selected" data-go="fire"><svg class="key"><use href="#i-left"/></svg><svg class="icon"><use href="#i-cinder"/></svg>FIRE</button><button class="node" data-go="ice"><svg class="key"><use href="#i-right"/></svg><svg class="icon"><use href="#i-rime"/></svg>ICE</button><button class="node bottom" data-go="fusion"><svg class="key"><use href="#i-down"/></svg><svg class="icon"><use href="#i-fusion"/></svg>REACTION</button></div><div class="status"><svg><use href="#i-up"/></svg>Back to COMMAND. No taunt.</div></section>
<section class="step"><h2><span>03</span> MAKE YOUR MOVE</h2><div class="path">COMMAND → MAGIC → FIRE</div><div class="fork"><button class="node selected" data-action="CINDER STRIKE"><svg class="key"><use href="#i-left"/></svg><svg class="icon"><use href="#i-assault"/></svg>CINDER STRIKE<span class="small">HANDS / READY</span></button><button class="node disabled" data-action="CINDER STEP"><svg class="key"><use href="#i-right"/></svg><svg class="icon"><use href="#i-traversal"/></svg>CINDER STEP<span class="small">FEET / UNEQUIPPED</span></button><button class="node bottom disabled" data-action="HEAT GUARD"><svg class="key"><use href="#i-down"/></svg><svg class="icon"><use href="#i-guard"/></svg>HEAT GUARD<span class="small">TORSO / UNEQUIPPED</span></button></div><div class="status"><svg><use href="#i-up"/></svg>Back to MAGIC. No taunt.</div></section>
</div>
<div class="lower"><section><h2 class="section-title">TRY THE TREE / ARROW KEYS OR CLICK</h2><div class="demo"><div class="demo-bar"><strong id="live-title">COMMAND</strong><svg style="color:var(--gold)"><use href="#i-gene"/></svg></div><div class="breadcrumbs" id="crumb">ROOT · ↑ TAUNT</div><div class="live-buttons" id="buttons"></div><div class="demo-footer"><span id="feedback">Choose a direction.</span><button id="reset" style="background:none;border:0;color:var(--gold);font:14px Kit;cursor:pointer">RESET ↶</button></div></div></section>
<section><h2 class="section-title">NOTICE THE MOMENT / NOT EVERY HIT</h2><div class="toast-stack"><div class="toast"><svg><use href="#i-cinder"/></svg><div><div class="tag">GENE UPGRADED · HANDS</div><h3>Cinder has evolved.</h3><p>Stronger release. Longer recharge.</p></div></div><div class="toast elite"><svg><use href="#i-elite"/></svg><div><div class="tag">ENEMY MUTATION</div><h3>Frostbound guard</h3><p>Blocking builds frost. Watch for the counter.</p></div></div></div></section></div>
<div class="strip"><p>ORIGINAL GLYPHS<br>One family across commands,<br>placements and notifications.</p><div class="symbols" id="symbols"></div></div>
<footer><span>ORIGINAL VECTOR ART · SOURCE SANS 3 · EXISTING KIT PALETTE + SHEAR</span><span>ART PREVIEW · EXAMPLE ABILITIES · NOT A GAME CAPTURE</span></footer>
</main><script>
const nodes={root:{title:'COMMAND',children:[['MAGIC','magic','magic'],['ITEM','item','item'],['SPECIAL','special','special']]},magic:{title:'MAGIC',parent:'root',children:[['FIRE','cinder','fire'],['ICE','rime','ice'],['REACTION','fusion','fusion']]},fire:{title:'FIRE',parent:'magic',children:[['CINDER STRIKE','assault',null],['CINDER STEP','traversal',null,'UNEQUIPPED'],['HEAT GUARD','guard',null,'UNEQUIPPED']]},ice:{title:'ICE',parent:'magic',children:[['RIME BURST','rime',null],['FROST GUARD','guard',null],['BACK','up','magic']]},fusion:{title:'REACTION',parent:'magic',children:[['THERMAL SHOCK','fusion',null],['BACK','up','magic']]},item:{title:'ITEM',parent:'root',children:[['RESTORE','item',null],['CLEANSING','magic',null],['BACK','up','root']]},special:{title:'SPECIAL',parent:'root',children:[['RELEASE','special',null],['GENE SHIFT','gene',null],['BACK','up','root']]}};
let current='root',held=new Set();const icon=n=>`<svg class="icon"><use href="#i-${n}"/></svg>`;function render(){let n=nodes[current];document.querySelector('#live-title').textContent=n.title;let names=[],p=current;while(p){names.unshift(nodes[p].title);p=nodes[p].parent}document.querySelector('#crumb').textContent=names.join(' → ')+(current==='root'?' · ↑ TAUNT':' · ↑ BACK');document.querySelector('#buttons').innerHTML=n.children.map((c,i)=>`<button class="node ${c[3]?'disabled':''}" data-index="${i}"><svg class="key"><use href="#i-${['left','right','down'][i]}"/></svg>${icon(c[1])}${c[0]}${c[3]?`<span class="small">${c[3]}</span>`:''}</button>`).join('')}
function choose(i){let c=nodes[current].children[i];if(!c)return;if(c[3]){document.querySelector('#feedback').textContent='Equip this placement first.';return}if(c[2])current=c[2];else{document.querySelector('#feedback').textContent=c[0]+' · activated';current='root'}render()}
function back(){if(nodes[current].parent){current=nodes[current].parent;document.querySelector('#feedback').textContent='Back one level.'}else document.querySelector('#feedback').textContent='TAUNT · root only';render()}
document.addEventListener('keydown',e=>{if(!e.key.startsWith('Arrow'))return;e.preventDefault();if(held.has(e.key)||e.repeat)return;held.add(e.key);if(e.key==='ArrowUp')back();else choose({ArrowLeft:0,ArrowRight:1,ArrowDown:2}[e.key])});document.addEventListener('keyup',e=>held.delete(e.key));window.addEventListener('blur',()=>held.clear());document.querySelector('#buttons').addEventListener('click',e=>{let b=e.target.closest('button');if(b)choose(+b.dataset.index)});document.querySelector('#reset').onclick=()=>{current='root';document.querySelector('#feedback').textContent='Choose a direction.';render()};document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>{current=b.dataset.go;render()});document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>{current='fire';render();document.querySelector('#feedback').textContent=b.classList.contains('disabled')?'Equip this placement first.':'CINDER STRIKE · activated'});document.querySelector('#symbols').innerHTML=['cinder','rime','magic','item','special','assault','traversal','guard','focus','gene','fusion','route','elite','check'].map(n=>icon(n)).join('');render();
</script></body></html>'''

if __name__ == '__main__':
    build()

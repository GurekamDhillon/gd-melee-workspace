#!/usr/bin/env python3
"""Assemble existing original art and separately labelled gameplay evidence."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'menu/out_roguelite'
OUT = ROOT / '_build/roguelite-showcase'

HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TBD · Showcase</title><style>
@font-face{font-family:Kit;src:url(font.otf)}
*{box-sizing:border-box}body{margin:0;background:#080d17;color:#f2efe4;font:16px Kit,Arial,sans-serif}
main{height:100dvh;display:grid;grid-template-rows:auto minmax(0,1fr) auto;padding:22px 28px;gap:15px}
header{display:flex;justify-content:space-between;gap:20px;align-items:center;border-bottom:2px solid #f0b429;padding-bottom:14px}
.tag{color:#f0b429;font-size:11px;letter-spacing:3px}h1{font-size:27px;font-style:italic;margin:4px 0 0}
nav{display:flex;gap:8px;flex-wrap:wrap}button,a{font:inherit;color:inherit;background:#1e3a8c;border:0;padding:10px 15px;text-decoration:none;cursor:pointer}
button[aria-pressed=true],#play{color:#080d17;background:#f0b429}button:focus-visible,a:focus-visible{outline:3px solid #f2efe4;outline-offset:3px}
.stage{min-height:0;display:flex;align-items:center;justify-content:center;background:#0a0e18;position:relative}
img,video{max-height:100%;max-width:100%;object-fit:contain;display:block}video[hidden],img[hidden]{display:none}
footer{display:flex;align-items:center;justify-content:space-between;gap:20px}.copy{max-width:880px}p{margin:5px 0;color:#b8c2dc;font-size:14px}.controls{display:flex;gap:8px;flex-shrink:0}.progress{height:3px;background:#28395b;margin-top:9px}.progress span{display:block;background:#f0b429;height:100%;width:0}small{color:#8e9ab5;font-size:11px}#kind{font-size:11px;color:#f0b429;letter-spacing:2px}
@media(max-width:900px){main{padding:14px;gap:9px}header{align-items:flex-start}h1{font-size:21px}nav{max-width:180px}nav button{padding:8px 10px}footer{flex-wrap:wrap}.controls{width:100%}p{font-size:12px}}
</style><main><header><div><div class="tag">TBD / ROGUELITE</div><h1 id="title"></h1></div><nav aria-label="Showcase chapters"></nav></header>
<div class="stage"><img id="art" alt=""><video id="video" hidden controls loop muted playsinline></video></div>
<footer><div class="copy"><div id="kind"></div><p id="caption"></p><small>← → browse · Space pauses · F fullscreen</small><div class="progress"><span></span></div></div><div class="controls"><button id="previous" aria-label="Previous chapter">←</button><button id="play">Pause</button><button id="next" aria-label="Next chapter">→</button><a id="open" target="_blank" rel="noopener">Try this screen ↗</a><button id="full" aria-label="Fullscreen">⛶</button></div></footer></main>
<script>
const slides=__SLIDES__;let index=0,elapsed=0,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches;
const q=s=>document.querySelector(s),nav=q('nav'),video=q('#video');
slides.forEach((slide,i)=>{let b=document.createElement('button');b.textContent=slide.short;b.onclick=()=>{setPlay(false);show(i)};nav.append(b)});
function show(i){index=(i+slides.length)%slides.length;elapsed=0;let s=slides[index];q('#title').textContent=s.title;q('#kind').textContent=s.kind;q('#caption').textContent=s.caption;q('#art').src=s.image;q('#art').alt=s.title+' — '+s.kind;q('#open').href=s.link;q('#open').textContent=s.kind==='GAMEPLAY CAPTURE'?'Open capture ↗':'Try this screen ↗';video.pause();video.hidden=!s.video;q('#art').hidden=!!s.video;if(s.video){video.src=s.video;video.poster=s.image;video.play().catch(()=>{})}Array.from(nav.children).forEach((b,j)=>b.setAttribute('aria-pressed',j===index));q('.progress span').style.width='0%'}
function setPlay(on){playing=on;q('#play').textContent=on?'Pause':'Play tour';q('#play').setAttribute('aria-pressed',on)}
function advance(n){setPlay(false);show(index+n)}
function fullscreen(){if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>{})}
q('#previous').onclick=()=>advance(-1);q('#next').onclick=()=>advance(1);q('#play').onclick=()=>setPlay(!playing);q('#full').onclick=fullscreen;q('.stage').onpointerdown=()=>setPlay(false);q('#open').onclick=()=>setPlay(false);
document.addEventListener('keydown',e=>{if(e.target.closest('button,a,video'))return;if(e.key==='ArrowLeft'){e.preventDefault();advance(-1)}else if(e.key==='ArrowRight'){e.preventDefault();advance(1)}else if(e.code==='Space'){e.preventDefault();setPlay(!playing)}else if(e.key.toLowerCase()==='f')fullscreen()});
setInterval(()=>{if(playing&&!document.hidden){elapsed+=100;if(elapsed>=14000)show(index+1);q('.progress span').style.width=(elapsed/140)+'%'}},100);show(0);setPlay(playing);
</script></html>'''


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'menu/SourceSans3/SourceSans3-Black.otf', OUT / 'font.otf')
    shutil.copy2(ROOT / 'menu/SourceSans3/LICENSE.md', OUT / 'font-LICENSE.md')
    slides = []
    for short, title, name, page, caption in [
        ('01 Commands', 'Power at your thumbs.', 'command-tree', 'index',
         'Left, right and down follow the command tree. Up backs out; at the root, Up taunts.'),
        ('02 Build', 'Build a fighting style.', 'build', 'build',
         'Body and equipment placements, gene identity, and readable tradeoffs. Illustrative balance values.'),
        ('03 Feedback', 'Feel the build change.', 'feedback', 'feedback',
         'Charge, ready, upgrade and clear states. Open the screen and hit Replay Feedback to try the motion.'),
    ]:
        shutil.copy2(ART / 'preview' / (name + '.png'), OUT / (name + '.png'))
        slides.append(dict(short=short, title=title, image=name+'.png',
                           link=(ART / (page+'.html')).as_uri(), kind='INTERACTIVE ART STUDY', caption=caption))
    capture = Path('/tmp/roguelite-cinder-live.png')
    if capture.exists():
        shutil.copy2(capture, OUT / 'cinder.png')
        slide = dict(short='04 In game', title='Cinder, in the actual game.', image='cinder.png',
                     link='cinder.png', kind='GAMEPLAY CAPTURE',
                     caption='Three ordinary hits earn charge. Left → Left → Left releases Cinder for 10 damage. Target positioning is a demonstration fixture; the HUD and room are prototypes.')
        if (OUT / 'cinder.mp4').exists():
            slide.update(video='cinder.mp4', link='cinder.mp4')
        slides.append(slide)
    (OUT / 'index.html').write_text(HTML.replace('__SLIDES__', json.dumps(slides)))
    print(OUT / 'index.html')


if __name__ == '__main__':
    build()

#!/usr/bin/env python3
"""Validate the art export and capture its browser motion reference.

This checks art files and browser controls, not native gameplay or frame rate.
Uses installed Chromium via Playwright; never launches or modifies the game.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import subprocess
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

MENU=Path(__file__).resolve().parents[1]
ROOT=MENU.parent
OUT=MENU/'out_roguelite_expansion'
PRE=OUT/'preview'


def sheet(items,path,cols=3,w=384,h=310):
    result=Image.new('RGB',(cols*w,math.ceil(len(items)/cols)*h),'#0a0e18')
    draw=ImageDraw.Draw(result)
    font=ImageFont.truetype(str(OUT/'font.otf'),16)
    for i,(title,im) in enumerate(items):
        im=im.convert('RGB');im.thumbnail((w-12,h-42))
        x=(i%cols)*w;y=(i//cols)*h
        result.paste(im,(x+(w-im.width)//2,y))
        title_font=font
        for size in range(16,8,-1):
            title_font=ImageFont.truetype(str(OUT/'font.otf'),size)
            if draw.textlength(title,font=title_font)<=w-24:break
        draw.text((x+12,y+h-31),title,font=title_font,fill='#f0b429')
    result.save(path)


def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    direction=json.loads((OUT/'direction.json').read_text())
    layout=json.loads((OUT/'layout.json').read_text())
    spec=importlib.util.spec_from_file_location('gx',ROOT/'melee/worktrees/linux/pc/tools/png2gx.py')
    gx=importlib.util.module_from_spec(spec);spec.loader.exec_module(gx)
    names=set();errors=[];ui_bytes=0;max_alpha_delta=0;group_counts={}
    for a in manifest['textures']:
        assert a['name'] not in names;names.add(a['name'])
        png=OUT/a['file'];assert hashlib.sha256(png.read_bytes()).hexdigest()==a['sha256']
        im=Image.open(png).convert('RGBA');assert list(im.size)==a['size']
        assert all(v>0 and v&(v-1)==0 and v<=1024 for v in im.size)
        assert im.getchannel('A').getextrema()[1]>0, a['name']+' empty'
        assert all(0<=v<=1 for v in a['anchor'])
        back=gx.decode_gxtex(str(OUT/a['gx'])).convert('RGBA');assert back.size==im.size
        error=ImageChops.difference(im.getchannel('A'),back.getchannel('A')).getextrema()[1]
        assert error<=(17 if a['format']=='IA4' else 0),(a['name'],error)
        max_alpha_delta=max(max_alpha_delta,error)
        group_counts[a['group']]=group_counts.get(a['group'],0)+1
        if a['group'] in ('shared','wayfinding','ui','family','equipment','reward','tell'):ui_bytes+=a['gx_bytes']
    assert ui_bytes<direction['budget']['ui_resident_bytes_max']
    assert manifest['gx_total_bytes']<direction['budget']['full_pack_bytes_max']
    assert len(direction['blends'])==10
    for b in direction['blends']:
        assert b['parents'][0]!=b['parents'][1]
        assert b['weights']==[0,.25,.5,.75,1]
    for f in direction['families'].values():
        for field in ('icon','trail','halo','orbit','surface'):
            assert not f[field] or f[field] in names
    for f in direction['founders'].values():
        for field in ('core','ring','detail'):assert f[field] in names
    for r in direction['reactions'].values():assert all(k in direction['founders'] for k in r['parents'])
    assert layout['doors']['upper_socket_origin']==[39,26]
    assert layout['combat']['coverage_4_3']['open_primary_panels']<.09
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(OUT.as_uri()+'/index.html');page.wait_for_function('window.review && review.ready')
        page.evaluate('review.setTime(1100)')
        # Exercise actual pointer/keyboard tree behavior, including parent and root taunt.
        page.locator('[data-dir=left]').click();assert page.evaluate('review.getNode()')=='magic'
        page.locator('[data-dir=left]').click();assert page.evaluate('review.getNode()')=='cinder'
        page.locator('[data-dir=up]').click();assert page.evaluate('review.getNode()')=='magic'
        page.locator('[data-dir=up]').click();assert page.evaluate('review.getNode()')=='root'
        page.locator('[data-dir=up]').click();assert page.evaluate('review.getNode()')=='root'
        page.evaluate("toast=''; toastUntil=0")
        screen=lambda:Image.open(BytesIO(page.locator('#scene').screenshot())).copy()
        def tab(name):page.locator(f'[data-tab={name}]').click();page.evaluate('review.setTime(1100)')
        def set_(id,value):page.locator('#'+id).select_option(value);page.evaluate('review.draw()')
        captures=[]
        for aspect in ('wide','four'):
            set_('aspect',aspect)
            for opened in (False,True):
                if opened:page.locator('[data-dir=left]').click()
                label=f'Combat {aspect} / '+('open' if opened else 'closed')
                im=screen()
                im.save(PRE/f'combat-{aspect}-{"open" if opened else "closed"}.png');captures.append((label,im))
                if opened:page.locator('[data-dir=up]').click()
        sheet(captures,PRE/'combat-sheet.png',2,640,390)
        set_('aspect','wide');page.screenshot(path=str(PRE/'01-combat.png'),full_page=True)
        tab('identity');families=[]
        for family in direction['families']:
            set_('family',family);im=screen();families.append((direction['families'][family]['name'],im))
        sheet(families,PRE/'family-sheet.png')
        set_('family','fire');page.screenshot(path=str(PRE/'02-identity.png'),full_page=True)
        # Color/reduced options must execute without hiding semantic glyphs.
        for vision in ('gray','protan','deutan','normal'):set_('vision',vision);screen()
        page.locator('#reduced').check();screen().save(PRE/'reduced-motion.png');page.locator('#reduced').uncheck()
        page.locator('#opponent').uncheck()
        states=[]
        for family in ('fire','frost'):
            set_('family',family)
            for state in direction['states']:
                set_('state',state);states.append((family+' / '+state,screen()))
        sheet(states,PRE/'state-sheet.png',5,320,266)
        set_('state','ready');set_('family','fire');page.locator('#opponent').check()
        tab('founders');founders=[]
        page.evaluate('review.setTime(2200)')
        for key in direction['founders']:
            set_('parentA',key);founders.append((direction['founders'][key]['title'],screen()))
        sheet(founders,PRE/'founder-sheet.png',3,426,350)
        set_('parentA','ThunderCrown');page.screenshot(path=str(PRE/'03-thunder.png'),full_page=True)
        # Compare effect region at exact blend endpoints against solo parents.
        set_('mode','blend');set_('parentA','SolarEruption');set_('parentB','GlacialShatter')
        def region():return screen().crop((0,130,1028,655)).convert('RGB')
        set_('mode','single');soloA=region();set_('parentA','GlacialShatter');soloB=region();set_('parentA','SolarEruption')
        set_('mode','blend')
        for value,reference in ((0,soloA),(100,soloB)):
            page.locator('#mix').fill(str(value));page.locator('#mix').dispatch_event('input')
            assert ImageChops.difference(region(),reference).getbbox() is None, 'blend endpoint drift'
        blends=[]
        for b in direction['blends']:
            set_('parentA',b['parents'][0]);set_('parentB',b['parents'][1])
            for weight in (0,25,50,75,100):
                page.locator('#mix').fill(str(weight));page.locator('#mix').dispatch_event('input')
                blends.append((b['parents'][0]+' + '+b['parents'][1]+f' / {weight}%',screen()))
        sheet(blends,PRE/'blend-sheet.png',5,320,266)
        set_('mode','reaction');reactions=[]
        for key,r in direction['reactions'].items():set_('reaction',key);reactions.append((r['title'],screen()))
        sheet(reactions,PRE/'reaction-sheet.png')
        tab('world');worlds=[]
        for presentation in ('reward','fusion','victory','failure','transition','tells'):
            set_('presentation',presentation);page.evaluate('review.setTime(1900)');worlds.append((presentation,screen()))
        sheet(worlds,PRE/'world-sheet.png',2,640,390)
        set_('presentation','reward');page.screenshot(path=str(PRE/'04-world.png'),full_page=True)
        # Deterministic motion strip exported as a GIF, explicitly an art reference.
        tab('identity');set_('family','fire');set_('state','ready');set_('placement','assault')
        frames=[]
        for i in range(40):
            page.evaluate(f'review.setTime({i*100})')
            im=screen();im.thumbnail((640,480));frames.append(im.convert('RGB'))
        frames[0].save(PRE/'continuous-motion.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
        tab('library');assert page.locator('.asset').count()==len(names)
        set_('group','wayfinding');assert page.locator('.asset').count()==group_counts['wayfinding']
        page.screenshot(path=str(PRE/'05-wayfinding.png'),full_page=True)
        # Smaller desktop/mobile widths must not cause horizontal document overflow.
        for width in (960,640):
            page.set_viewport_size({'width':width,'height':900});tab('combat')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        browser.close()
    assert not errors,errors
    report={'status':'art asset and browser validation passed','native_acceptance':'pending',
      'textures':len(names),'groups':group_counts,'ui_gx_bytes':ui_bytes,'total_gx_bytes':manifest['gx_total_bytes'],
      'max_alpha_roundtrip_delta':max_alpha_delta,'browser_errors':errors,
      'checked':['GX decode and dimensions','nonempty alpha','hashes','reference coverage','texture budgets',
                 'D-pad parent/root behavior','4:3 and 16:9 closed/open HUD','six families and five states',
                 'color inspection and reduced motion controls','five founders','ten blends at five weights',
                 'exact sampled blend endpoints','six reactions','six presentation screens','responsive overflow'],
      'limitations':['No native afterimage/ribbon/surface support claimed','No integrated branch-room capture',
                     'Browser color simulation is an approximation; human readability review pending',
                     'Native GPU timing, model bindings, physics and controller acceptance pending']}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

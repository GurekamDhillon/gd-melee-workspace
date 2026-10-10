"""XV2 move map: Goku's BCM (input/condition tree) -> BAC entries -> their timelines, as a browsable page.

python ports/goku-xv2/tools/movemap.py
  -> _build/goku-xv2/movemap/index.html   (open in a browser: graph + per-move timeline, searchable)
  -> _build/goku-xv2/movemap/movemap.json (everything, for tools)
  -> <package>/mods/geno-lab/missions/moves-goku.txt (keyed by the fighter's name) (the LAB CLIPS page's MOVES category)
Source-derived names: local output only, never committed. Timing is the BAC's static frames at the
exporter's 60 fps convention: nothing here is observed in the running game.
"""
from __future__ import annotations
import collections
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PORT = ROOT / 'ports/goku-xv2'
OUT = ROOT / '_build/goku-xv2/movemap'
AUTHOR = ROOT / '_build/goku-xv2' / os.environ.get('GOKU_AUTHOR', 'author-source')   # splice-preview builds keep their own
LIB = AUTHOR / 'clip-library.json'
LABDATA = AUTHOR / 'package/mods/geno-lab/missions'  # gd.mod_read reads missions/ only
CAVEAT = ('Unverified timing: static BAC frames at the LibXenoverse 60 fps export convention; BCM conditions are '
          'decoded, not executed; nothing here is observed in XV2 or in the game. Hitbox and cancel windows are '
          'source reference only, not Melee hitboxes.')
SLOTS = ('BacEntryPrimary', 'BacEntryAirborne', 'BacEntryCharge', 'BacEntryUserConnect', 'BacEntryVictimConnect')


def scope_kind(scope):
    if scope.startswith('chara/GOK/'):
        return 'goku'
    if scope.startswith('chara/CMN/'):
        return 'shared'
    if '_GOK_' in scope:
        return 'goku-skill'
    return 'borrowed'


def label(v):
    return v.get('label') if isinstance(v, dict) else v


def main():
    ir = json.loads((PORT / 'ir/goku.xv2.ir.json').read_text(encoding='utf-8'))
    beh = ir['behavior']
    files = {f['id']: f for f in ir['resources']['files']}
    clips = {c['id']: c for c in ir['assets']['animations']['clips']}
    subs = {s['id']: s for s in beh['subactions']}
    scripts = {s['id']: s for s in beh['scripts']}
    libname = {}
    if LIB.exists():
        for c in json.loads(LIB.read_text(encoding='utf-8'))['clips']:
            libname[c['id']] = c['name']

    # ---- BAC entries: their ordered timelines
    def timeline(sub):
        sc = scripts.get(sub['scripts']['main'])
        out = {'anim': [], 'hit': [], 'cancel': [], 'move': [], 'gfx': [], 'sfx': [], 'rate': [], 'other': collections.Counter()}
        if not sc:
            return out
        for e in sc['events']:
            eng = e['args'].get('engine', {}).get('xv2.pc', {})
            f, dur = e['frame'], eng.get('duration_frames', 1)
            op = e['op']
            if op == 'engine.animation':
                b = e['args'].get('binding', {})
                cid = b.get('clip')
                if not cid or cid not in clips or '.fce.' in cid or clips[cid]['engine']['xv2.pc'].get('camera') is not False:
                    continue
                c = clips[cid]
                end = b.get('end_frame', 65535)
                out['anim'].append({'frame': f, 'dur': dur, 'clip': cid, 'clip_name': c['name'], 'lib': libname.get(cid),
                                    'start': b.get('start_frame', 0), 'end': min(end, c['frames'] - 1),
                                    'speed': b.get('speed', 1), 'frames': c['frames']})
            elif op == 'hitbox.create':
                out['hit'].append({'frame': f, 'dur': dur, 'damage': e['args'].get('damage', e['args'].get('engine', {}).get('xv2.pc', {}).get('damage'))})
            elif op == 'engine.bcm_callback':
                out['cancel'].append({'frame': f, 'dur': dur})
            elif op == 'move.velocity':
                out['move'].append({'frame': f, 'dur': dur})
            elif op == 'gfx.spawn':
                out['gfx'].append({'frame': f, 'dur': dur})
            elif op == 'sfx.play':
                out['sfx'].append({'frame': f})
            elif op == 'timer.set_anim_rate':
                out['rate'].append({'frame': f, 'dur': dur})
            else:
                out['other'][op] += 1
        out['other'] = dict(out['other'])
        out['anim'].sort(key=lambda a: a['frame'])
        # an animation event of duration <= 1 plays its clip range at its speed (until the next one)
        for k, a in enumerate(out['anim']):
            span = int(round((a['end'] - a['start'] + 1) / max(abs(a['speed']) or 1, 0.01))) if a['dur'] <= 1 else a['dur']
            nxt = out['anim'][k + 1]['frame'] if k + 1 < len(out['anim']) else None
            a['play'] = max(1, min(span, nxt - a['frame']) if nxt is not None and nxt > a['frame'] else span)
        return out

    # ---- BCM nodes: input/conditions -> BAC entries
    bcm_nodes = {}
    referenced = collections.defaultdict(list)
    for fid, f in files.items():
        if not f['name'].endswith('_PLAYER.bcm'):
            continue
        dec = f['engine']['xv2.pc'].get('decoded')
        if not dec or not Path(dec['path']).exists():
            continue
        bcm = json.loads(Path(dec['path']).read_text(encoding='utf-8-sig'))
        scope = f['name']
        bac_scope = scope.replace('_PLAYER.bcm', '.bac') if 'skill/' in scope else scope.replace('.bcm', '.bac')
        names = {}
        for n in bcm['nodes']:
            sf = n.get('sourceFields', {})
            key = scope + '#' + n['id']
            node = {'key': key, 'id': n['id'], 'scope': scope, 'parent': (scope + '#' + n['parent']) if n.get('parent') else None,
                    'input': n.get('inputLabels') or label(sf.get('ButtonInput')) or '', 'dir': label(sf.get('DirectionalInput')),
                    'cond': label(sf.get('PrimaryActivatorConditions')), 'state': label(sf.get('ActivatorState')),
                    'ki': sf.get('KiRequired'), 'stamina': sf.get('StaminaCost'), 'health': sf.get('HealthRequired'),
                    'loop': [sf.get('MinimumLoopDuration'), sf.get('MaximumLoopDuration')], 'bac': {}}
            for slot in SLOTS:
                v = sf.get(slot)
                if isinstance(v, int) and 0 <= v < 65535 and not (slot != 'BacEntryPrimary' and v == 0):
                    sid = 'subaction:' + bac_scope + '/' + str(v)
                    if sid in subs:
                        node['bac'][slot] = sid
                        referenced[sid].append(key)
            bcm_nodes[key] = node
        for n in bcm['nodes']:
            p = n.get('parent')
            if p:
                bcm_nodes.setdefault(scope + '#' + p, {'children': []})
        for k, n in bcm_nodes.items():
            if n.get('parent') and n['parent'] in bcm_nodes:
                bcm_nodes[n['parent']].setdefault('children', []).append(k)

    # ---- the moves: Goku's own BAC entries with animation, every skill entry, and shared entries his BCM reaches
    moves = []
    for sid, sub in subs.items():
        scope = sub['engine']['xv2.pc']['scope']
        kind = scope_kind(scope)
        if sub.get('empty'):
            continue
        tl = timeline(sub)
        if not tl['anim']:
            continue
        if kind == 'shared' and sid not in referenced:
            continue
        nodes = referenced.get(sid, [])
        inputs = sorted({(bcm_nodes[k]['input'] or '-') + ('/' + str(bcm_nodes[k]['dir']) if bcm_nodes[k].get('dir') not in (None, '0', 0) else '')
                         for k in nodes})
        first = tl['anim'][0]
        moves.append({'id': sid, 'bac': scope + ':' + str(sub['index']['value']), 'scope': scope, 'kind': kind,
                      'name': '%s %s' % (scope.split('/')[-1].replace('.bac', ''), sub['index']['value']),
                      'clip': first['clip_name'], 'inputs': inputs, 'nodes': nodes, 'timeline': tl,
                      'length': max([a['frame'] + a['play'] for a in tl['anim']] + [h['frame'] + h['dur'] for h in tl['hit']] + [1])})
    order = {'goku': 0, 'goku-skill': 1, 'borrowed': 2, 'shared': 3}
    moves.sort(key=lambda m: (order[m['kind']], m['scope'], int(m['id'].rsplit('/', 1)[1])))
    OUT.mkdir(parents=True, exist_ok=True)
    need = set()
    for m in moves:
        m['node_count'] = len(m['nodes'])
        m['nodes'] = m['nodes'][:40]
        for k in m['nodes']:
            c, g = k, 0
            while c and c in bcm_nodes and g < 16 and c not in need:
                need.add(c); c = bcm_nodes[c].get('parent'); g += 1
        if m['nodes']:
            for ch in bcm_nodes.get(m['nodes'][0], {}).get('children', [])[:40]:
                need.add(ch)
    keep_nodes = {k: bcm_nodes[k] for k in need if 'id' in bcm_nodes[k]}
    doc = {'schema': 'goku-xv2-movemap/1', 'caveat': CAVEAT, 'moves': moves, 'bcm': keep_nodes}
    (OUT / 'movemap.json').write_text(json.dumps(doc, indent=1), encoding='utf-8')

    # ---- the LAB table: one line per record, tab separated (the Lab's Lua reads it with gd.mod_read)
    lines = ['# goku-xv2 BAC moves for the LAB CLIPS page. ' + CAVEAT]
    for m in moves:
        lines.append('\t'.join(['M', m['bac'], m['kind'], m['clip'], ','.join(m['inputs'])[:60], str(m['length'])]))
        for a in m['timeline']['anim']:
            if a['lib']:
                lines.append('\t'.join(['C', str(a['frame']), str(a['play']), a['lib'], str(a['start']), str(a['end']), '%g' % a['speed']]))
        for h in m['timeline']['hit']:
            lines.append('\t'.join(['H', str(h['frame']), str(max(1, h['dur']))]))
        for c in m['timeline']['cancel']:
            lines.append('\t'.join(['X', str(c['frame']), str(max(1, c['dur']))]))
    LABDATA.mkdir(parents=True, exist_ok=True)
    (LABDATA / 'moves-goku.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # ---- the page
    page = PAGE.replace('/*DATA*/', json.dumps({'caveat': CAVEAT, 'moves': moves, 'bcm': keep_nodes}))
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    print(json.dumps({'moves': len(moves), 'bcm_nodes_kept': len(keep_nodes), 'by_kind': collections.Counter(m['kind'] for m in moves),
                      'page': str(OUT / 'index.html'), 'lab': str(LABDATA / 'moves-goku.txt')}, default=dict))


PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Goku XV2 Move Map</title><style>
:root{--bg:#10131a;--panel:#191e29;--ink:#e8e4d8;--mut:#9aa3b8;--gold:#e7b84a;--hit:#e5483b;--cancel:#2f9cf0;--anim:#7bc47f;--move:#c77dff}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,sans-serif}
header{padding:12px 16px;border-bottom:1px solid #2a3142}header p{margin:4px 0;color:var(--mut);font-size:12px}
main{display:grid;grid-template-columns:minmax(260px,360px) 1fr;height:calc(100vh - 92px)}
#list{overflow:auto;border-right:1px solid #2a3142}#list div{padding:5px 12px;cursor:pointer;border-bottom:1px solid #1d2331}
#list div:hover,#list div.on{background:#232a3a}.k{font-size:11px;color:var(--mut)}.goku{color:var(--gold)}.goku-skill{color:#ffd27a}.borrowed{color:#c9a0ff}.shared{color:var(--mut)}
#detail{overflow:auto;padding:16px}input{width:100%;box-sizing:border-box;padding:8px;background:#0c0f15;color:var(--ink);border:1px solid #2a3142}
table{border-collapse:collapse;font-size:12px;margin:8px 0}td,th{padding:3px 8px;border-bottom:1px solid #232a3a;text-align:left}
.bar{position:relative;height:16px;background:#0c0f15;margin:2px 0}.bar span{position:absolute;top:0;height:100%;opacity:.85}
a{color:var(--cancel);cursor:pointer}@media(max-width:700px){main{grid-template-columns:1fr;height:auto}}
</style></head><body><header><b>Goku XV2 move map</b><p id="cav"></p><input id="q" placeholder="search: name, clip, input (e.g. kamehameha, ATC_009, Jump)"></header>
<main><div id="list"></div><div id="detail">Pick a move.</div></main><script>
const D=/*DATA*/;document.getElementById('cav').textContent=D.caveat;
const L=document.getElementById('list'),Q=document.getElementById('q'),R=document.getElementById('detail');
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function draw(){const q=Q.value.toLowerCase();L.innerHTML='';D.moves.forEach((m,i)=>{const t=(m.name+' '+m.clip+' '+m.inputs.join(' ')+' '+m.timeline.anim.map(a=>a.clip_name).join(' ')).toLowerCase();
if(q&&!t.includes(q))return;const d=document.createElement('div');d.innerHTML=`<span class="${m.kind}">${esc(m.name)}</span> ${esc(m.clip)}<div class="k">${esc(m.kind)} · ${esc(m.inputs.join(', ')||'no BCM input')} · ${m.length}f</div>`;d.onclick=()=>show(i,d);L.appendChild(d)})}
function bars(m){const n=Math.max(m.length,1),row=(list,col,lab)=>`<div class="k">${lab}</div><div class="bar">`+list.map(e=>`<span style="left:${e.frame/n*100}%;width:${Math.max(e.play||e.dur||1,1)/n*100}%;background:${col}" title="f${e.frame}+${e.dur||1}"></span>`).join('')+'</div>';
return row(m.timeline.anim,'var(--anim)','animation events')+row(m.timeline.hit,'var(--hit)','hitbox windows (source)')+row(m.timeline.cancel,'var(--cancel)','BCM callback / cancel windows (source)')+row(m.timeline.move,'var(--move)','movement')}
function node(k){const n=D.bcm[k];if(!n)return esc(k);return `${esc(n.input||'-')}${n.dir&&n.dir!='0'?' / '+esc(n.dir):''} <span class="k">[${esc(n.cond)} · state ${esc(n.state)} · ki ${n.ki} · stamina ${n.stamina} · loop ${esc(n.loop)}]</span>`}
function chain(k){const out=[];let c=k,g=0;while(c&&D.bcm[c]&&g++<12){out.unshift(node(c));c=D.bcm[c].parent}return out.join(' &rarr; ')}
function show(i,el){[...L.children].forEach(c=>c.classList.remove('on'));el&&el.classList.add('on');const m=D.moves[i],t=m.timeline;
R.innerHTML=`<h2>${esc(m.name)} <span class="k ${m.kind}">${esc(m.kind)}</span></h2><div class="k">${esc(m.id)} · length ${m.length} frames (static)</div>${bars(m)}
<h3>Animation (play order)</h3><table><tr><th>frame</th><th>clip</th><th>LAB clip</th><th>clip frames</th><th>speed</th></tr>${t.anim.map(a=>`<tr><td>${a.frame} (+${a.dur})</td><td>${esc(a.clip_name)}</td><td>${esc(a.lib||'-')}</td><td>${a.start}..${a.end} of ${a.frames}</td><td>${a.speed}</td></tr>`).join('')}</table>
<h3>Source hitboxes</h3>${t.hit.length?t.hit.map(h=>`f${h.frame} for ${h.dur}`).join(', '):'none'}
<h3>Cancel / BCM callback windows</h3>${t.cancel.length?t.cancel.map(h=>`f${h.frame} for ${h.dur}`).join(', '):'none'}
<h3>Other events</h3>movement ${t.move.length}, effects ${t.gfx.length}, sounds ${t.sfx.length}, anim-rate changes ${t.rate.length} ${esc(JSON.stringify(t.other))}
<h3>BCM routes into it (${m.node_count})</h3>${m.nodes.slice(0,40).map(k=>`<div>${chain(k)}</div>`).join('')||'none (reached by another skill or engine)'}
${m.node_count>40?`<div class="k">+${m.node_count-40} more</div>`:''}
<h3>Children of its first BCM node</h3>${(D.bcm[m.nodes[0]]?.children||[]).filter(c=>D.bcm[c]).slice(0,40).map(c=>`<div>${node(c)} &rarr; ${esc(Object.values(D.bcm[c].bac||{}).join(', '))}</div>`).join('')||'none'}`}
Q.oninput=draw;draw();</script></body></html>'''

if __name__ == '__main__':
    main()

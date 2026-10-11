"""Idempotent: add the chant-tier release states (KameThin, KameMax), the four tiered stored-charge flash states (KameStore1..4, replacing KameStore) and their
move-script adaptations to gameplay.json and (if present) gameplay.full.json.  python ports/goku-xv2/tools/patch_kame_tiers.py"""
import copy, json
from pathlib import Path
P = Path(__file__).resolve().parents[1]
for fn in ('gameplay.json', 'gameplay.full.json'):
    p = P / fn
    if not p.exists():
        continue
    g = json.loads(p.read_text(encoding='utf-8'))
    states = g['states']
    names = [s['name'] for s in states]
    sup = next(s for s in states if s['name'] == 'KameSuper')
    old_store = next((s for s in states if s['name'] == 'KameStore'), None)
    for key, name in (('thin', 'KameThin'), ('max', 'KameMax')):
        if name not in names:
            st = copy.deepcopy(sup)
            st.update(name=name, subaction='clip:' + name, lua={'enter': key + '_enter', 'frame': key + '_frame'})
            states.insert(names.index('KameSuper'), st)
            names.insert(names.index('KameSuper'), name)
    store_tpl = old_store or next((s for s in states if s['name'] == 'KameStore1'))
    for i in range(1, 5):
        nm = 'KameStore%d' % i
        if nm not in names:
            st = copy.deepcopy(store_tpl)
            st.update(name=nm, subaction='clip:' + nm)
            states.insert(names.index('KameSuper'), st)
            names.insert(names.index('KameSuper'), nm)
    if old_store:
        states.remove(old_store)
    ad = g['special_adaptations']
    have = {a['name'] for a in ad}
    sa_sup = next(a for a in ad if a['name'] == 'KameSuper')
    for key, name in (('thin', 'KameThin'), ('max', 'KameMax')):
        if name not in have:
            a = copy.deepcopy(sa_sup)
            a.update(name=name, script='moves/kame_%s.genoasm' % key)
            ad.append(a)
    p.write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding='utf-8')
    print('patched', fn, [n for n in names if n.startswith('Kame')])

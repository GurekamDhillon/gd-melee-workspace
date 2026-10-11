"""Print a compact view of an Xv2Fx `emp` JSON dump (local XV2 data, nothing committed):  python -I emp_view.py file.emp.json"""
import json, sys


def kv(o):
    """Collapse a KeyframedValue/KeyframedVector into a short string."""
    if not isinstance(o, dict) or 'Keyframes' not in o:
        return o
    c = o.get('Constant')
    if isinstance(c, dict):
        c = [round(x, 4) for x in c.get('Values', [])]
    elif isinstance(c, float):
        c = round(c, 4)
    s = 'c=%s' % (c,)
    if o.get('IsAnimated') or len(o.get('Keyframes', [])) > 1:
        ks = []
        for k in o['Keyframes']:
            v = k['Value']
            if isinstance(v, dict):
                v = [round(x, 3) for x in v.get('Values', [])]
            elif isinstance(v, float):
                v = round(v, 3)
            ks.append('%s@%s' % (v, k['Time']))
        s += ' anim%s%s[%s]' % ('L' if o.get('Loop') else '', 'I' if o.get('Interpolate') else '', ' '.join(ks))
    return s


def nm(x):
    return x.get('name') if isinstance(x, dict) else x


def show(n, dep=0):
    p = ' ' * dep
    print(p + '%s [%s/%s] flags=%s/%s start=%s+-%s life=%s+-%s burst=%s+-%s freq=%s max=%s' % (
        n['Name'], nm(n['NodeType']), nm(n['NodeSpecificType']), nm(n['NodeFlags']), nm(n['NodeFlags2']), n['StartTime'], n['StartTime_Variance'],
        n['Lifetime'], n['Lifetime_Variance'], n['Burst'], n['Burst_Variance'], n['BurstFrequency'], n['MaxInstances']))
    print(p + '  pos=%s rot=%s posVar=%s' % (kv(n['Position']), kv(n['Rotation']), n['Position_Variance'].get('Values')))
    e = n['EmitterNode']
    if n['IsEmitter']:
        print(p + '  EMITTER shape=%s area=%s pos=%s+-%s vel=%s+-%s size=%s+-%s size2=%s+-%s angle=%s+-%s edge=%s' % (
            nm(e['Shape']), e['EmitFromArea'], kv(e['Position']), e['Position_Variance'], kv(e['Velocity']), e['Velocity_Variance'], kv(e['Size']), e['Size_Variance'],
            kv(e['Size2']), e['Size2_Variance'], kv(e['Angle']), e['Angle_Variance'], e['EdgeIncrement']))
    m = n['EmissionNode']
    if n['IsEmission']:
        t = m['Texture']
        print(p + '  EMISSION type=%s bb=%s billboard=%s velori=%s startrot=%s+-%s activerot=%s+-%s axis=%s' % (
            nm(m['EmissionType']), nm(m['BillboardType']), m['BillboardEnabled'], m['VelocityOriented'], m['StartRotation'], m['StartRotation_Variance'],
            kv(m['ActiveRotation']), m['ActiveRotation_Variance'], m['RotationAxis'].get('Values')))
        refs = []
        for r in (t.get('TextureEntryRef') or []):
            r = r.get('TextureRef') or {}
            ss = r.get('ScrollState') or {}
            ks = ss.get('Keyframes') or []
            refs.append('emb%s %s rep=%s/%s scroll=%s(%s,%s) keys=%d%s' % (r.get('EmbIndex'), nm(r.get('KeyframeType')), nm(r.get('RepetitionU')), nm(r.get('RepetitionV')), nm(ss.get('ScrollType')), ss.get('ScrollSpeed_U'), ss.get('ScrollSpeed_V'), len(ks), (' k0=%s' % [ks[0].get(x) for x in ('Time', 'ScrollU', 'ScrollV', 'ScaleU', 'ScaleV')]) if ks else ''))
        print(p + '   TEX matID=%s depth=%s refs=%s' % (t['MaterialID'], t['RenderDepth'], refs))
        print(p + '   color1=%s color2=%s var=%s a1=%s a2=%s' % (kv(t['Color1']), kv(t['Color2']), kv(t['Color_Variance']), kv(t['Color1_Transparency']), kv(t['Color2_Transparency'])))
        print(p + '   scaleBase=%s+-%s scaleXY=%s+-%s' % (kv(t['ScaleBase']), t['ScaleBase_Variance'], kv(t['ScaleXY']), t['ScaleXY_Variance']))
        if m['Mesh'].get('EmgFile') or m['Mesh'].get('EmgBytes'):
            print(p + '   MESH', str(m['Mesh'])[:100])
        cx = m.get('ConeExtrude', {})
        if cx.get('Duration'):
            print(p + '   CONE', cx)
    for k in n.get('KeyframedValues', []):
        print(p + '  KV', json.dumps(k)[:200])
    for k in n.get('Modifiers', []):
        print(p + '  MOD', k.get('TypeStr'), [(v.get('Parameter'), v.get('Component'), [kk['Value'] for kk in v.get('Keyframes', [])][:4]) for v in k.get('KeyframedValues', [])])
    for c in n.get('ChildParticleNodes', []):
        show(c, dep + 4)


d = json.load(open(sys.argv[1]))
print('textures:', [(t.get('Name') or t) if isinstance(t, dict) else t for t in d.get('Textures', [])][:20])
for n in d['ParticleNodes']:
    show(n)

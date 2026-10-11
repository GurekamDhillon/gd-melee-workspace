"""Collect the asset-side parameters the engine FX lane needs from the local XV2 dumps (ribbon width/alpha curves, scroll speeds, colours, glare layers, camera events)
into _build/xv2-kame/fx/lane_params.json (local; not committed).   python ports/goku-xv2/tools/xv2_lane_params.py"""
import json
from pathlib import Path
import numpy as np

WT = Path(__file__).resolve().parents[3]
FX = WT / '_build/xv2-kame/fx'
EXP = Path('E:/Torrents/Dragon.Ball.Xenoverse.2.Future.Saga.Chapter.4-RUNE/modding/exports/goku-base-shallow-v0.1/decoded/skill')
SK = {'KMH': ('SPA', '000_GOK_KMH', 'Kmh'), 'CKM': ('ULT', '000_GOK_CKM', 'Ckm')}


def kv(o):
    c = o['Constant']
    c = c.get('Values', c) if isinstance(c, dict) else c
    ks = [[k['Time'], (k['Value'].get('Values') if isinstance(k['Value'], dict) else k['Value'])] for k in o['Keyframes']]
    return {'const': c, 'keys': ks if (o.get('IsAnimated') or len(ks) > 1) else []}


def params(key):
    kind, code, px = SK[key]
    out = {'skill': code, 'ribbons': [], 'glare_materials': [], 'camera_events': [], 'camera_ean': None}
    trc = {m['Index']: m for m in json.loads((EXP / kind / code / (code + '.trc.emm.json')).read_text())['Materials']}
    emb = json.loads((FX / code / (code + '.trc.emb/index.json')).read_text())
    for etr in sorted((FX / code / (code + '.tbind.emb')).glob('*.etr.json')):
        for n in json.loads(etr.read_text())['Nodes']:
            t = n['TextureEntryRef'][0]['TextureRef']
            m = trc.get(n['MaterialID'], {})
            out['ribbons'].append({
                'file': etr.name, 'texture': emb[t['EmbIndex']]['name'], 'material': m.get('Name'), 'shader': m.get('ShaderProgram'),
                'blend': {0: 'alpha', 1: 'add', 2: 'sub'}.get(int(next((p['Value'] for p in m.get('Parameters', []) if p['Name'] == 'AlphaBlendType'), 0)), '?'),
                'width_m': kv(n['Scale']), 'color1': kv(n['Color1']), 'alpha1': kv(n['Color1_Transparency']), 'color2': kv(n['Color2']), 'alpha2': kv(n['Color2_Transparency']),
                'scroll_u_per_frame': t['ScrollState']['ScrollSpeed_U'], 'scroll_v_per_frame': t['ScrollState']['ScrollSpeed_V'],
                'extrude_frames': n['ExtrudeDuration'], 'hold_frames': n['HoldDuration'], 'segment_frame_size': n['SegementFrameSize'], 'flags': n['Flags']['name'],
                'attach_bone': n['AttachBone'], 'uv_repeat': [t['RepetitionU']['name'], t['RepetitionV']['name']]})
    for emo in sorted(FX.glob(f'{code}/{px}_*.emo.json')) + sorted(FX.glob(f'{px}_*.emo.json')):
        pass
    for mf in sorted((EXP / kind / code).glob(f'{px}_*.emm.json')):
        for m in json.loads(mf.read_text())['Materials']:
            P = {p['Name']: p['Value'] for p in m['Parameters']}
            out['glare_materials'].append({'file': mf.name, 'material': m['Name'], 'shader': m['ShaderProgram'], 'glare': P.get('Glare') == '1',
                                           'glare_rgba': [float(P.get('GlareCol' + c, 1)) for c in 'RGBA'], 'blend_type': P.get('AlphaBlendType'),
                                           'matcol0': [float(P.get('MatCol0' + c, 1)) for c in 'RGBA'], 'tex_scroll_uv_per_s': [float(P.get('TexScrl0U', 0)), float(P.get('TexScrl0V', 0))]})
    bac = json.loads((EXP / kind / code / (code + '.bac.json')).read_text())
    e0 = bac['entries'][0]
    for ev in e0['events']:
        if ev['kind'] == 'Camera':
            sf = ev['sourceFields']
            out['camera_events'].append({'start_frame': ev['startFrame'], 'duration': ev['durationFrames'], 'bone': sf['BoneLink']['label'], 'ean_type': sf['EanType']['label'],
                                         'ean_index': sf['EanIndex']})
    cam = EXP / kind / code / (code + '.cam.ean.json')
    if cam.exists():
        for cl in json.loads(cam.read_text())['clips']:
            tr = {}
            for t in cl['tracks']:
                k = np.array([x[1:4] for x in t['keys']])
                tr[t['channel']] = {'frames': [t['keys'][0][0], t['keys'][-1][0]], 'range_xyz': np.round(k.max(0) - k.min(0), 3).tolist()}
            out['camera_ean'] = {'clip': cl['name'], 'frame_count': cl['frameCount'], 'tracks': tr}
    out['bac_time_scale'] = [[ev['startFrame'], ev['durationFrames'], ev['sourceFields'].get('TimeScale')] for ev in e0['events'] if ev['kind'] == 'Time Scale']
    return out


if __name__ == '__main__':
    d = {k: params(k) for k in SK}
    (FX / 'lane_params.json').write_text(json.dumps(d, indent=1), encoding='utf-8')
    for k, v in d.items():
        print(k, 'ribbons', len(v['ribbons']), 'materials', len(v['glare_materials']), 'camera events', v['camera_events'], 'cam ean', v['camera_ean'] and v['camera_ean']['clip'])

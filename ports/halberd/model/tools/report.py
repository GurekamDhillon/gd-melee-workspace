"""Converter report for Meta Knight Phases 2 + 3 -> ports/halberd/model/converter_report.json
(clips converted / failed / skipped, joint count, parts table, visibility groups, TransN decisions, files, checks)."""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL = os.path.dirname(HERE); MK = os.path.dirname(MODEL)
ANIM = os.path.join(MK, 'anim')
sys.path.insert(0, HERE)
import install_mk


def main():
    sk = json.load(open(os.path.join(MODEL, 'work', 'skeleton.json')))
    J = sk['joints']
    mr = json.load(open(os.path.join(ANIM, 'out', 'motion_rows.json')))
    tr = json.load(open(os.path.join(ANIM, 'transn_report.json')))
    vis = json.load(open(os.path.join(ANIM, 'vis_events.json')))
    mrep = json.load(open(os.path.join(MODEL, 'model_report.json')))
    j2p, p2j = install_mk.parts_table(J)
    used = collections.Counter()
    for c in mr['clips'] + mr['extras']:
        for n in c['brawl_clip'].split('+'):
            if not n.startswith('pose:'): used[n] += 1
    cat = lambda n: 'glide' if n.startswith('Glide') else 'jump' if n.startswith('JumpAerialF') else 'special' if n.startswith('Special') else 'common'
    dec = collections.Counter()
    for c in tr['clips']:
        for ax, v in c['axes'].items():
            if v['decision'] != 'none': dec['%s by %s' % (v['decision'], c['rule_source'])] += 1
    rep = {
        'files': {
            'costumes': {cc: v['file'] for cc, v in mrep['costumes'].items()},
            'costume_source': mrep['mapping'],
            'animations': 'anim/out/PlBmAJ.dat (%d bytes, %d sub-archives)' % (mr['aj_size'], len(mr['clips']) + len(mr['extras'])),
            'install': 'model/tools/install_mk.py <mod dir> (fighter data x8/x1C/x20/x30/x34/x38/x44/x54/x58/x5C, motion table, '
                       'scripts bone remap + ModelVis, PlCo parts table, MxDt costumes/anim file)',
        },
        'skeleton': {'joint_count': sk['joint_count'], 'max_depth': sk['max_depth'], 'order': sk['order'],
                     'fk_vs_brawllib_bind_max_err': sk['fk_vs_brawllib_bind_max_err'],
                     'joints': [(i, j['name'], j['parent_index'], j['src']) for i, j in enumerate(J)]},
        'parts_table': {'parts_num': len(J), 'insert_slots_table5': None,
                        'role_to_joint': {install_mk.ROLES[i]: (p2j[i], J[p2j[i]]['name'] if p2j[i] != 255 else None) for i in range(len(p2j))},
                        'joint_to_role': {J[i]['name']: install_mk.ROLES[v] for i, v in enumerate(j2p) if v != 255}},
        'model': {'dobjs': [{k: d[k] for k in ('dobj', 'obj', 'group', 'material', 'texture', 'fmt', 'cull', 'xlu', 'tris', 'pobjs')}
                            for d in mrep['build']['dobjs']],
                  'visibility': {'model 0 (cape, Brawl BoneSwitch2)': {'0': 'closed cape: DObj 10', '1': 'wings: DObjs 11, 12',
                                                                       '2': 'merged cape article: DObj 13'},
                                 'model 1 (body, Brawl BoneSwitch1)': {'0': 'body: DObjs 0-6', '1': 'mantle ball: DObj 9'},
                                 'always drawn': 'sword DObjs 7, 8',
                                 'metal': 'no metal twin meshes: Melee swaps every MObj for its metal material; the table\'s '
                                          'metal-main column = the normal lists, the metal-parts column is empty'},
                  'checks': {cc: {'verify': v['verify'], 'ok': v['verify_ok'], 'cos_py': v['check']} for cc, v in mrep['costumes'].items()},
                  'mesh_stats': mrep['mesh_stats']},
        'animations': {
            'brawl_clips': 331, 'brawl_clips_converted': len(used),
            'converted_by_kind': dict(collections.Counter(cat(n) for n in used)),
            'sub_archives': len(mr['clips']) + len(mr['extras']), 'rows_pointed': sum(len(c['rows']) for c in mr['clips']),
            'rows_on_fallback_pose': sum(len(c['rows']) for c in mr['clips'] if c['brawl_clip'].startswith('pose:')),
            'rows_without_animation': len(mr['rows_without_animation']),
            'failed': mr['failed'], 'skipped': [e['clip'] for e in mr['skipped_brawl_clips']],
            'skipped_why': mr['skipped_brawl_clips'][0]['why'] if mr['skipped_brawl_clips'] else None,
            'max_track_error': max(max(c['max_err'].values()) for c in mr['clips'] + mr['extras']),
            'dense_tracks': sum(c['dense_tracks'] for c in mr['clips'] + mr['extras']),
            'largest_tree_bytes': max(c['size'] for c in mr['clips'] + mr['extras']),
            'trees_over_retail_0x8000': [c['brawl_clip'] for c in mr['clips'] + mr['extras'] if c['size'] > 0x8000],
            'row_map': [{'rows': c['rows'], 'clip': c['brawl_clip'], 'frames': c['frames'], 'kirby_frames': c['vanilla_frames'],
                         'note': c['note']} for c in mr['clips']],
            'extras': [{'clip': c['brawl_clip'], 'symbol': c['symbol'], 'offset': c['offset_hex'], 'size': c['size_hex'],
                        'frames': c['frames'], 'note': c['note']} for c in mr['extras']],
        },
        'transn': {'policy': 'anim/transn_policy.json', 'axis_decisions': dict(dec),
                   'clips': [{'clip': c['brawl_clip'], 'rows': c['rows'], 'rule': c['rule_source'],
                              'axes': {ax: (v['decision'], v['brawl_min'], v['brawl_max'], v['melee_min'], v['melee_max'])
                                       for ax, v in c['axes'].items() if v['decision'] != 'none'}} for c in tr['clips']]},
        'vis_events': {'file': 'anim/vis_events.json', 'clips_with_modelvis': sum(1 for c in vis['clips'] if c['melee_modelvis_suggested'])},
    }
    json.dump(rep, open(os.path.join(MODEL, 'converter_report.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep['animations'].items() if k not in ('row_map', 'extras', 'skipped')}, indent=1))
    print(rep['transn']['axis_decisions'])


if __name__ == '__main__':
    main()

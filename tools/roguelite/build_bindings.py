#!/usr/bin/env python3
"""Build bounded tint selectors from measured parts, never export model geometry.

Policy: visible supported draws, >=80% coherent non-head body roles; hand-mounted
attachment candidates share Assault. Head/face/mixed surfaces are excluded.
Three Pikachu c1 attached head draws were individually reviewed in the original
lab's measured preview images; only that exact signature/costume allows them.
Live transparent MObj draws require gd.dobjs evidence and are filtered at runtime.
Measurements do not prove exhaustive pose/costume/equipment coverage.
"""
from pathlib import Path
import argparse
import json
import re
import game_source

ROOT = Path(__file__).resolve().parents[2]
SOURCE = game_source.ROGUELITE
REPORTS = ROOT / '_build/agents/linux/scripts-data/character_parts_lab_main'
# Alias, costume table code, native internal FighterKind; primary IC only.
STOCK = {
 'captain':('Ca',2), 'donkey':('Dk',3), 'fox':('Fx',1), 'gamewatch':('Gw',24),
 'kirby':('Kb',4), 'bowser':('Kp',5), 'link':('Lk',6), 'luigi':('Lg',17),
 'mario':('Mr',0), 'marth':('Ms',18), 'mewtwo':('Mt',16), 'ness':('Ns',8),
 'peach':('Pe',9), 'pikachu':('Pk',12), 'popo':('Pp',10), 'jigglypuff':('Pr',15),
 'samus':('Ss',13), 'yoshi':('Ys',14), 'zelda':('Zd',19), 'sheik':('Sk',7),
 'falco':('Fc',22), 'younglink':('Cl',20), 'drmario':('Dr',21), 'roy':('Fe',26),
 'pichu':('Pc',23), 'ganondorf':('Gn',25),
}
REVIEWED_ATTACHMENTS = {('pikachu',1,'555363dceb4f68d4'):{22,23,24}}


def stock_counts(checkout=game_source.GAME):
    result = {}
    for source in sorted((checkout / 'src/melee/ft/kinds').glob('*/*.c')):
        text = source.read_text()
        for code, body in re.findall(r'Fighter_CostumeStrings\s+ft(\w+)_Init_CostumeStrings\[\]\s*=\s*\{(.*?)\n\};', text, re.S):
            result[code] = len(re.findall(r'\{\s*\w+\s*,', body))
    return {alias:result[code] for alias,(code,_) in STOCK.items()}


def selectors(report):
    character = re.sub(r'-c\d+$', '', report['character'])
    accessory = REVIEWED_ATTACHMENTS.get((character, report['costume'], report['geometry_signature']), set())
    groups = {name:[] for name in ('assault','guard','traversal')}
    evidence = {}
    for p in sorted(report['parts'], key=lambda p:p['index']):
        if p.get('source') != 0 or p.get('status') != 0:
            continue  # transient item IDs and unsupported geometry never persist
        if p.get('max_coverage',0) < .015 and p.get('mean_coverage',0) < .003:
            continue
        region = p.get('regions',{})
        if p['index'] in accessory:
            role,confidence='assault',region.get('head',0)
            reason='individually_reviewed_head_attachment'
        else:
            if region.get('head',0) > .05:
                continue
            scores = {
                'assault':sum(region.get(k,0) for k in ('left_hand','right_hand','left_arm','right_arm')),
                'guard':region.get('torso',0),
                'traversal':sum(region.get(k,0) for k in ('left_foot','right_foot','left_leg','right_leg')),
            }
            role,confidence=max(scores.items(),key=lambda item:item[1])
            if confidence < .8:
                continue
            # Attachment classification is joint evidence, not a garment label.
            if p.get('equipment_candidate') and role != 'assault':
                continue
            reason='hand_attachment_candidate' if p.get('equipment_candidate') else 'coherent_common_body_roles'
        groups[role].append(p['index'])
        evidence[str(p['index'])]={'role':role,'confidence':round(confidence,6),
          'coverage':round(p.get('mean_coverage',0),6),'reason':reason,'joint':p['joint'],
          'path':p['path'],'source':0}
    return groups,evidence


def catalogue(reports):
    result = {}
    for path in sorted(Path(reports).glob('*-analysis.json')):
        report=json.loads(path.read_text())
        alias=re.sub(r'-c\d+$','',report['character'])
        if alias not in STOCK:
            continue
        if report.get('schema') != 1 or report.get('failures') or report.get('cancelled'):
            raise ValueError(f'Incomplete/failed report: {path.name}')
        if report.get('sample_count') != report.get('requested_sample_count') or report.get('sample_count',0) < 4:
            raise ValueError(f'Incomplete report samples: {path.name}')
        if not re.fullmatch('[0-9a-f]{16}',report.get('geometry_signature','')):
            raise ValueError(f'Invalid geometry signature: {path.name}')
        count=stock_counts()[alias];costume=report['costume']
        if not isinstance(costume,int) or not 0<=costume<count:
            raise ValueError(f'Invalid stock costume: {path.name}')
        groups,evidence=selectors(report)
        key=f'{alias}/c{costume}'
        if key in result:
            raise ValueError(f'Duplicate binding: {key}')
        result[key]={'id':alias,'costume':costume,'kind':STOCK[alias][1],
          'signature':report['geometry_signature'],'asset_sha256':report['asset_sha256'],
          'samples':report['sample_count'],'coverage':('full36' if report['sample_count']>=36 else 'smoke4'),
          'slots':groups,'evidence':evidence,'partner_bound':False}
    if not result:
        raise ValueError('No complete measured reports; existing bindings must be retained')
    return result


def lua(v):
    if isinstance(v,bool):return 'true' if v else 'false'
    if isinstance(v,str):return json.dumps(v,ensure_ascii=True)
    if isinstance(v,(int,float)):return str(v)
    if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
    return '{'+','.join('['+lua(k)+']='+lua(x) for k,x in sorted(v.items()))+'}'


def render(records):
    return '-- Generated by tools/roguelite/build_bindings.py; selectors and evidence only.\nlocal B={}\nlocal catalogue='+lua(records)+'\n'+RUNTIME


RUNTIME = r'''
local slots={'assault','guard','traversal'}
local function clone(t) if type(t)~='table' then return t end local r={} for k,v in pairs(t) do r[k]=clone(v) end return r end
function B.coverage(choice)
 local key=type(choice)=='table' and (choice.id..'/c'..choice.costume) or choice
 local entry=catalogue[key]
 if not entry then return nil,'No measured tint binding; gene actions remain available' end
 local label=entry.coverage=='full36' and (entry.samples..' measured pose / angle pairs') or (entry.samples..' smoke pairs; broader pose review pending')
 local missing={} for _,slot in ipairs(slots) do if #entry.slots[slot]==0 then missing[#missing+1]=slot end end
 if #missing>0 then label=label..'; no isolated '..table.concat(missing,' / ')..' draws' end
 if entry.id=='popo' then label=label..'; primary climber only, partner unbound' end
 return clone(entry),label
end
-- Pass a fresh gd.parts snapshot, actual gd.player and gd.dobjs render evidence.
-- Missing render evidence is conservatively refused; unknown costumes get no tint.
function B.resolve(parts,player,draws)
 if not parts or not player then return nil,'Fighter model unavailable' end
 if type(draws)~='table' then return nil,'Live render flags unavailable; no tint applied' end
 local entry
 for _,candidate in pairs(catalogue) do
  if player.kind==candidate.kind and player.costume==candidate.costume and parts.geometry_signature==candidate.signature then entry=candidate;break end
 end
 if not entry then return nil,'Unmeasured model / costume; no tint applied' end
 local live,render={},{}
 for _,p in ipairs(parts) do live[p.index]=p end
 for _,d in ipairs(draws) do render[d.index]=d end
 local result={assault={},guard={},traversal={},key=entry.id..'/c'..entry.costume..':'..entry.signature,coverage=entry.coverage,samples=entry.samples,equipment_bound=false,partner_bound=false}
 local skipped=0
 for _,slot in ipairs(slots) do for _,id in ipairs(entry.slots[slot]) do
  local p,d,expected=live[id],render[id],entry.evidence[tostring(id)]
  -- render XLU / NO_ZUPDATE are native MObj flags at bits 30 / 29.
  local translucent=d and type(d.render)=='number' and (d.render & 0x60000000)~=0
  if p and d and p.source==0 and p.status==0 and p.path==expected.path and p.joint==expected.joint and not translucent then result[slot][#result[slot]+1]=id
  else skipped=skipped+1 end
 end end
 local count=#result.assault+#result.guard+#result.traversal
 local diagnostic='Measured '..entry.samples..'-pair '..(entry.coverage=='full36' and 'binding' or 'smoke binding')..' / '..count..' draws'
 if skipped>0 then diagnostic=diagnostic..' / '..skipped..' unavailable or transparent' end
 if entry.id=='popo' then diagnostic=diagnostic..' / partner unbound' end
 return result,diagnostic
end
-- Fingerprint includes current items even though unreviewed transient items are untinted.
-- Recompute after respawn/model swap and when this key changes; never persist item IDs.
function B.topology(parts,player)
 if not parts or not player then return 'missing' end
 local a={tostring(player.kind),tostring(player.costume),tostring(parts.geometry_signature)}
 for _,p in ipairs(parts) do a[#a+1]=table.concat({p.index,p.source,p.item_kind or -1,p.item_ordinal or -1,p.path,p.joint,p.status},':') end
 return table.concat(a,'|')
end
return B
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',type=Path,default=REPORTS)
    parser.add_argument('--out',type=Path,default=SOURCE/'bindings.lua')
    args=parser.parse_args();records=catalogue(args.reports)
    args.out.write_text(render(records))
    print(f'{len(records)} measured costume bindings -> {args.out}')

if __name__=='__main__':main()

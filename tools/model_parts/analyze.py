#!/usr/bin/env python3
"""Measure paired in-game ID captures, rank parts, and generate a local review page.

Requires NumPy. ImageMagick or Pillow accelerates PNG loading; a built-in decoder
supports noninterlaced 8-bit RGB/RGBA captures when neither is available.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import html
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib
import numpy as np

LABELS={'unclassified':'Unclassified surface','head':'Head region','torso':'Torso region',
 'left_arm':'Left arm','right_arm':'Right arm','left_hand':'Left hand region','right_hand':'Right hand region',
 'left_leg':'Left leg','right_leg':'Right leg','left_foot':'Left foot','right_foot':'Right foot','equipment':'Owned equipment'}
LABELS.update({'arms':'Arm regions','hands':'Hand regions','legs':'Leg regions','feet':'Foot regions'})

def palette(count):
    n=np.arange(1,count+1,dtype=np.int32)
    return np.stack((16+(n&7)*32,16+((n>>3)&7)*32,16+((n>>6)&7)*32),axis=1).astype(np.uint8)

def png_write(path,pixels):
    a=np.asarray(pixels,dtype=np.uint8);h,w,c=a.shape
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b''.join(b'\0'+row.tobytes() for row in a)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6 if c==4 else 2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

def png_read_builtin(path):
    data=path.read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Not PNG')
    at=8;compressed=[];header=None
    while at+12<=len(data):
        size,=struct.unpack_from('>I',data,at);tag=data[at+4:at+8];body=data[at+8:at+8+size]
        if at+size+12>len(data):raise ValueError('Truncated PNG')
        crc,=struct.unpack_from('>I',data,at+8+size)
        if zlib.crc32(tag+body)&0xffffffff!=crc:raise ValueError('PNG CRC mismatch')
        if tag==b'IHDR':header=struct.unpack('>IIBBBBB',body)
        if tag==b'IDAT':compressed.append(body)
        at+=size+12
    if header is None:raise ValueError('Missing IHDR')
    w,h,depth,kind,compression,filtering,interlace=header
    if depth!=8 or kind not in (2,6) or interlace or compression or filtering:raise ValueError('Expected noninterlaced 8-bit RGB/RGBA PNG')
    c=4 if kind==6 else 3;stride=w*c;raw=zlib.decompress(b''.join(compressed))
    if len(raw)!=(stride+1)*h:raise ValueError('PNG raster size mismatch')
    rows=np.frombuffer(raw,dtype=np.uint8).reshape(h,stride+1);out=np.zeros((h,stride),dtype=np.uint8)
    for y,row in enumerate(rows):
        f=int(row[0]);r=row[1:].copy();prev=out[y-1] if y else np.zeros(stride,dtype=np.uint8)
        if f==1:
            for k in range(c):r[k::c]=np.cumsum(r[k::c],dtype=np.uint32).astype(np.uint8)
        elif f==2:r=r+prev
        elif f in (3,4):
            for x in range(stride):
                left=int(r[x-c]) if x>=c else 0;up=int(prev[x]);corner=int(prev[x-c]) if x>=c else 0
                if f==3:p=(left+up)//2
                else:
                    p0=left+up-corner;a,b,d=abs(p0-left),abs(p0-up),abs(p0-corner)
                    p=left if a<=b and a<=d else up if b<=d else corner
                r[x]=(int(r[x])+p)&255
        elif f!=0:raise ValueError('Unknown PNG filter')
        out[y]=r
    return out.reshape(h,w,c)

def png_read(path):
    try:
        from PIL import Image
        with Image.open(path) as im:return np.asarray(im.convert('RGBA'))
    except ImportError:pass
    magick=shutil.which('magick')
    if magick:
        header=path.read_bytes()[:33];w,h=struct.unpack_from('>II',header,16)
        raw=subprocess.run([magick,str(path),'-depth','8','rgba:-'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
        return np.frombuffer(raw,dtype=np.uint8).reshape(h,w,4)
    return png_read_builtin(path)

def decode_pair(a,b,count,tolerance=2):
    if a.shape[:2]!=b.shape[:2]:raise ValueError('Capture dimensions differ')
    if not 0<count<=512:raise ValueError('ID count outside supported range')
    x=a[:,:,:3].astype(np.int16);y=b[:,:,:3].astype(np.int16)
    lanes=np.clip((x-16+16)//32,0,7)
    encoded=lanes[:,:,0]+lanes[:,:,1]*8+lanes[:,:,2]*64
    indices=(encoded-1)%512
    expected=16+lanes*32
    valid=(np.abs(x-expected).max(axis=2)<=tolerance)&(np.abs(y-(255-expected)).max(axis=2)<=tolerance)&(indices<count)
    ids=np.where(valid,indices,-1).astype(np.int16)
    pixels=int(valid.sum())
    if not pixels:raise ValueError('No validated ID pixels: frozen pose/camera or palette failed')
    yy,xx=np.nonzero(valid);clipped=bool(xx.min()<=1 or yy.min()<=1 or xx.max()>=a.shape[1]-2 or yy.max()>=a.shape[0]-2)
    counts=np.bincount(ids[valid],minlength=count)
    return ids,counts,clipped

def part_key(part):
    if part['source']==0:return 'd'+str(part['index'])
    return 'item-'+str(part['item_kind'])+'-'+str(part['item_ordinal'])+'-'+str(part['path'])

def classify(part):
    weights=part.get('regions',{})
    region,confidence=max(weights.items(),key=lambda p:p[1]) if weights else ('unclassified',0)
    # A single mesh can legitimately cover both sides. Do not pretend one boot or hand dominates.
    if confidence<.7:
        for name in ('arm','hand','leg','foot'):
            combined=weights.get('left_'+name,0)+weights.get('right_'+name,0)
            if combined>=.8:
                region,confidence={'arm':'arms','hand':'hands','leg':'legs','foot':'feet'}[name],combined
                break
    bounds=part.get('bounds',[0]*6);ext=sorted(max(0,bounds[i+3]-bounds[i]) for i in range(3))
    attachment=part.get('body_joint',1)==0 and part.get('joint',0)>0
    candidate=part.get('source',0)==1 or attachment or (region in ('left_hand','right_hand','unclassified') and ext[2]>4*max(.01,ext[1]) and part.get('triangles',0)>4)
    if part.get('status',0)&3:confidence=min(confidence,.49)
    if part.get('source',0)==1:return 'equipment',min(1,confidence),'Owned equipment '+str(part['item_kind']),True
    if attachment:return region,min(confidence,.6),'Attachment candidate',True
    if candidate:return region,min(confidence,.6),'Equipment candidate',True
    if confidence<.7:return region,confidence,'Mixed body regions' if confidence>0 else 'Unclassified surface',False
    return region,confidence,LABELS.get(region,region),False

def make_groups(parts):
    """Conservative suggestions: preserve small/head details and equipment; raw entries always remain."""
    buckets=defaultdict(list)
    for p in parts:
        region,confidence,label,candidate=classify(p);p.update(region=region,confidence=confidence,suggested_name=label,equipment_candidate=candidate)
        # Only coherent same-joint body surfaces are linked automatically. Head details stay separate.
        link=not candidate and confidence>=.8 and region not in ('head','unclassified','left_hand','right_hand','hands') and p.get('mean_coverage',0)>=.015
        key=('region',region,p['joint'],p.get('visibility_model',-1)) if link else ('part',p['key'])
        buckets[key].append(p)
    groups=[]
    for members in buckets.values():
        p=members[0];keys=sorted(x['key'] for x in members)
        groups.append({'id':hashlib.sha256('|'.join(keys).encode()).hexdigest()[:12],
          'suggested_name':p['suggested_name']+(' surfaces' if len(members)>1 else ' #'+str(p['index'])),
          'label':p['suggested_name']+(' surfaces' if len(members)>1 else ' #'+str(p['index'])),
          'confidence':min(x['confidence'] for x in members),'members':keys,'equipment_candidate':any(x['equipment_candidate'] for x in members),
          'grouping':'same_joint_region_suggestion' if len(members)>1 else 'individual_draw',
          'mean_coverage':0,'max_coverage':0,'visible_fraction':0,'reviewed':False})
    return groups

def alternatives(parts):
    out=[]
    for i,a in enumerate(parts):
        for b in parts[i+1:]:
            model=a.get('visibility_model',-1);ma=a.get('visibility_state',-1);mb=b.get('visibility_state',-1)
            if model>=0 and model==b.get('visibility_model') and ma>0 and mb>0 and not ma&mb and a['source']==b['source']==0:
                out.append({'members':[a['key'],b['key']],'evidence':'disjoint_state_masks_in_same_visibility_model','model':model})
    return out

def apply_reviews(report,review):
    if review.get('fingerprint')!=report['fingerprint']:return False
    labels={c['id']:c['label'] for c in review.get('controls',[])}
    for group in report['controls']:
        if group['id'] in labels:
            label=labels[group['id']]
            if not isinstance(label,str) or not label.strip() or len(label)>100:raise ValueError('Reviewed labels must contain 1-100 characters')
            group['label']=label.strip();group['reviewed']=True
    return True

def analyze_manifest(manifest_path,reviews=None):
    folder=manifest_path.parent;manifest=json.loads(manifest_path.read_text());records=[];failures=list(manifest.get('failures') or [])
    if manifest.get('cancelled'):failures.append('Scan was cancelled; coverage is incomplete')
    for filename in manifest.get('samples') or []:
        try:
            record=json.loads((folder/filename).read_text());parts=record['parts']
            ids,counts,clipped=decode_pair(png_read(folder/record['a']),png_read(folder/record['b']),len(parts))
            if clipped:raise ValueError('Silhouette clipped at image edge')
            record.update(ids=ids,counts=counts,total=int(counts.sum()),metadata=filename)
            records.append(record)
        except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as e:failures.append(filename+': '+str(e))
    if not records:raise ValueError('No valid captures: '+ '; '.join(failures[:3]))
    signatures={r['geometry_signature'] for r in records}
    costumes={r['costume'] for r in records}
    if len(signatures)!=1 or len(costumes)!=1:raise ValueError('Model changed within scan: separate assets/costumes must be scanned independently')
    signature=next(iter(signatures));costume=next(iter(costumes))
    asset=manifest.get('asset_sha256')
    fingerprint=hashlib.sha256(json.dumps([1,asset,signature,costume],separators=(',',':')).encode()).hexdigest()
    rows={};coverage=defaultdict(list);shared=[]
    for r in records:
        by_material=defaultdict(list);by_data=defaultdict(list)
        seen={}
        for p,count in zip(r['parts'],r['counts']):
            key=part_key(p);seen[key]=int(count)/r['total']
            if key not in rows or p['area']>rows[key]['area']:rows[key]=dict(p,key=key)
            by_material[p['material']].append(key);by_data[p['material_data']].append(key)
        for key in set(rows)|set(seen):coverage[key].append(seen.get(key,0))
        for kind,buckets in [('MObj',by_material),('material_data',by_data)]:
            for members in buckets.values():
                if len(members)>1:shared.append({'kind':kind,'members':sorted(members),'coupled_by_current_api':False})
    parts=list(rows.values())
    for p in parts:
        values=coverage[p['key']];values=[0]*(len(records)-len(values))+values
        p.update(mean_coverage=sum(values)/len(records),max_coverage=max(values),visible_fraction=sum(v>0 for v in values)/len(records))
    groups=make_groups(parts)
    for group in groups:
        values=[];best=None
        for r in records:
            mapping={part_key(p):p['index'] for p in r['parts']}
            members=[mapping[k] for k in group['members'] if k in mapping]
            count=sum(int(r['counts'][i]) for i in members)
            value=count/r['total'];values.append(value)
            if best is None or value>best[0]:best=(value,r,members)
        group.update(mean_coverage=sum(values)/len(values),max_coverage=max(values),visible_fraction=sum(v>0 for v in values)/len(values))
        _,record,members=best
        mask=np.isin(record['ids'],members);silhouette=record['ids']>=0
        rgb=np.zeros((*mask.shape,3),dtype=np.uint8);rgb[silhouette]=(75,86,107);rgb[mask]=(255,214,62)
        yy,xx=np.nonzero(silhouette);crop=rgb[max(0,yy.min()-6):yy.max()+7,max(0,xx.min()-6):xx.max()+7]
        step=max(1,int(max(crop.shape[:2])/200));thumb=crop[::step,::step]
        image_name=manifest['character']+'-'+group['id']+'.png';png_write(folder/image_name,thumb)
        group.update(preview=image_name,representative_sample=record['metadata'])
    groups.sort(key=lambda g:(-g['mean_coverage'],g['id']))
    for group in groups:
        group['priority']='primary' if group['mean_coverage']>=.015 or (group['equipment_candidate'] and group['max_coverage']>0) else ('detail' if group['max_coverage']>0 else 'unseen')
    report={'schema':1,'character':manifest['character'],'costume':costume,'asset_sha256':asset,'run_id':manifest.get('run_id'),
      'geometry_signature':signature,'fingerprint':fingerprint,'mapping_strength':'asset_and_geometry' if asset else 'geometry_only',
      'sample_count':len(records),'requested_sample_count':len(manifest.get('samples') or []),'cancelled':manifest.get('cancelled',False),
      'parts':sorted(parts,key=lambda p:-p['mean_coverage']),'controls':groups,'alternate_geometry':alternatives(parts),
      'shared_materials':list({json.dumps(s,sort_keys=True):s for s in shared}.values()),'failures':failures,
      'limitations':manifest.get('limitations',[]),
      'sample_summary':[{k:r[k] for k in ('pose','view','requested_frame','actual_frame','motion','pose_execution','total')} for r in records]}
    if reviews:report['reviews_applied']=apply_reviews(report,reviews)
    return report

def write_outputs(folder,report):
    character=report['character'];(folder/(character+'-analysis.json')).write_text(json.dumps(report,indent=2)+'\n')
    rows=['signature\t'+report['geometry_signature'],
          'asset_sha256\t'+(report['asset_sha256'] or ''),'costume\t'+str(report['costume'])]
    for c in report['controls']:
        # Only live fighter entries are reusable by numeric index; transient equipment has lifetime-specific IDs.
        ids=[int(k[1:]) for k in c['members'] if k.startswith('d')]
        if ids and c['priority']=='primary':rows.append(c['label'].replace('\t',' ').replace('\n',' ')+'\t'+str(c['confidence'])+'\t'+str(c['mean_coverage'])+'\t'+','.join(map(str,ids)))
    (folder/(character+'-controls.tsv')).write_text('\n'.join(rows)+'\n')
    data=json.dumps(report).replace('<','\\u003c')
    cards=[]
    for c in report['controls']:
        cards.append('<article><img src="'+html.escape(c['preview'],quote=True)+'"><div><input data-id="'+c['id']+'" value="'+html.escape(c['label'],quote=True)+'"><p>'+f'{c["mean_coverage"]:.1%} average coverage · {c["max_coverage"]:.1%} maximum · {c["confidence"]:.0%} classification confidence'+'</p><p>'+html.escape(', '.join(c['members']))+'</p><details><summary>Evidence</summary><pre>'+html.escape(json.dumps(c,indent=2))+'</pre></details></div></article>')
    body='''<!doctype html><meta charset="utf-8"><title>Character part review</title><style>body{background:#111824;color:#e4e8ef;font:16px system-ui;margin:30px auto;max-width:1000px;padding:0 20px}article{display:flex;gap:24px;background:#1c2837;padding:20px;margin:16px 0;border-radius:10px}img{width:180px;height:180px;object-fit:contain;image-rendering:pixelated}input{background:#101722;color:#ffe29b;border:1px solid #667;font-size:20px;padding:8px;width:90%}button{padding:12px;font-size:16px}pre{white-space:pre-wrap}p{color:#b2c0d2}</style>'''
    body+='<h1>'+html.escape(character)+' — suggested recolor controls</h1><p>'+str(report['sample_count'])+' valid paired captures. Yellow marks the selected surfaces. Body labels are inferred; equipment candidates need review.</p><p>'+html.escape(' '.join(report['limitations']))+'</p><button id="save">Download reviewed names</button>'+''.join(cards)
    body+='<script>const report='+data+''';document.getElementById('save').onclick=()=>{const controls=[...document.querySelectorAll('input[data-id]')].map(x=>({id:x.dataset.id,label:x.value}));const text=JSON.stringify({schema:1,fingerprint:report.fingerprint,controls},null,2);const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'application/json'}));a.download=report.character+'-reviews.json';a.click();URL.revokeObjectURL(a.href)};</script>'''
    (folder/(character+'-review.html')).write_text(body)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--reviews',type=Path);p.add_argument('--character')
    args=p.parse_args();review=json.loads(args.reviews.read_text()) if args.reviews else None
    manifests=sorted(args.folder.glob((args.character or '*')+'-manifest.json'));summary=[]
    if not manifests:p.error('No completed scan manifests found')
    for manifest in manifests:
        try:
            report=analyze_manifest(manifest,review);write_outputs(args.folder,report)
            print(f'{report["character"]}: {report["sample_count"]} captures, {len(report["parts"])} raw parts, {len(report["controls"])} controls, {len(report["failures"])} failures')
            summary.append({'character':report['character'],'run_id':report['run_id'],'ok':not report['failures'],'captures':report['sample_count'],'failures':report['failures']})
        except (ValueError,OSError,KeyError) as e:
            print(f'{manifest.name}: FAILED: {e}');summary.append({'manifest':manifest.name,'ok':False,'error':str(e)})
    # A focused recheck must not replace the complete roster summary.
    summary_name=(args.character+'-analysis-summary.json') if args.character else 'analysis-summary.json'
    (args.folder/summary_name).write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if all(s['ok'] and not s['failures'] for s in summary) else 2
if __name__=='__main__':raise SystemExit(main())

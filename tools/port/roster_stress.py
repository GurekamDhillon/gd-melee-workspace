#!/usr/bin/env python3
"""Build a local ACE roster stress overlay. Never distributes disc-derived data.

Run with --native-registry --count 100 for native rows, or --fill-limit for
legacy table clones (63 clones on ACE 2.0). The disc is read
privately from GW_ISO_ACE in the environment/.env; there is no disc-path CLI.
Existing external ids stay fixed. Internal rows are inserted BEFORE the six
bosses, preserving the runtime's boss-at-end convention. Clones share assets,
but have separate rows, callbacks, port kinds, names and CSS icons.

Layout consulted: the existing dump_mxdt.py reader and mxdt_clone.py writer;
m-ex (https://github.com/akaneia/m-ex), fighter tables, behaviour only.
"""
import argparse
import bisect
import json
import os
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / '_build/local-assets/roster-stress'
sys.path.insert(0, str(ROOT / 'tools/mex_port'))
sys.path.insert(0, str(ROOT / 'experiment/brawl-kirby/tools'))
import mex_hsd
from dump_mxdt import FIGHTER_FIELDS

# Explicit index spaces/strides. Spans are checked, never guessed for a write.
_SPACES = ('e','k','e','e','e','k','k','k','k','k','e','e','e','e',
           'e','k','k','k','e','k','e','e','e','e','e','e','e','e',
           'e','e','e','e','e')
_STRIDES = (4,8,1,3,4,4,4,4,8,1,4,4,4,4,16,8,8,1,8,8,2,4,
            4,4,4,4,4,4,4,2,2,2,4)
FIGHTER_TABLES = tuple((i*4,n,_SPACES[i],_STRIDES[i])
                       for i,n in enumerate(FIGHTER_FIELDS))


def roster_hash(data):
    value=14695981039346656037
    for byte in data:
        value=((value^byte)*1099511628211)&0xFFFFFFFFFFFFFFFF
    return value


def native_manifest(name, internal, external, count, table, fighter, animation):
    """GDRSTR01: original byte ids stay unchanged; native identities are separate."""
    if not 0<count<=65407 or not 0<=internal<128 or not 0<=external<128:
        raise ValueError('native manifest ids/count exceed version 1 bounds')
    if not name or any(ord(c)<32 or ord(c)>126 for c in name):
        raise ValueError('native display names must be printable ASCII')
    rows=[]
    for i in range(count):
        key=f'clone-{i+1:05d}'.encode('ascii')
        label=f'{name} {i+1:03d}'.encode('ascii')
        if len(label)>=48:raise ValueError('native display name exceeds 47 bytes')
        rows.append(struct.pack('>HHI40s48s',internal,external,0,key,label))
    return struct.pack('>8sIQQQ',b'GDRSTR01',count,roster_hash(table),
                       roster_hash(fighter),roster_hash(animation))+b''.join(rows)


def read_native_manifest(raw):
    if len(raw)<36:raise ValueError('native manifest header truncated')
    magic,count,_,_,_=struct.unpack_from('>8sIQQQ',raw)
    if magic!=b'GDRSTR01' or not 0<count<=65407 or len(raw)!=36+count*96:
        raise ValueError('native manifest version/count/length mismatch')
    rows=[];keys=set()
    for i in range(count):
        k,e,flags,key,name=struct.unpack_from('>HHI40s48s',raw,36+i*96)
        if k>=128 or e>=128 or flags or b'\0' not in key or b'\0' not in name:
            raise ValueError('invalid native row')
        key_head,key_tail=key.split(b'\0',1);name_head,name_tail=name.split(b'\0',1)
        if any(key_tail) or any(name_tail) or any(x<32 or x>126 for x in key_head+name_head):
            raise ValueError('native strings are not canonical printable ASCII')
        key=key_head.decode('ascii');name=name_head.decode('ascii')
        if not key or not name or key in keys:raise ValueError('empty/duplicate native key')
        keys.add(key);rows.append({'internal':k,'external':e,'key':key,'name':name})
    return rows


def generate_native(args, g, raw, a, ft, sk, se, dest):
    count=args.count
    source_pl=a.cstr(a.u32(a.u32(ft+4)+sk*8))
    source_aj=a.cstr(a.u32(a.u32(ft+28)+sk*4))
    manifest=native_manifest(args.source,sk,se,count,raw,g.read(source_pl),g.read(source_aj))
    read_native_manifest(manifest)
    # Native rows do not replace or enlarge MxDt/PlCo/menu/HUD archives.
    # ACE supplies shared assets, avoiding a second mutable table namespace.
    dest.mkdir(parents=True)
    (dest/'files').mkdir()  # Prevent legacy whole-folder mounting of the manifest.
    (dest/'roster.gwr').write_bytes(manifest)
    (dest/'mod.json').write_text(json.dumps({'id':args.name,'name':f'Native roster: {count} {args.source} clones',
        'version':'1.0.0','kind':'fighter','pack':'ace',
        'description':'Local native roster manifest; requires registry integration'},indent=2)+'\n')
    (dest/'INSTALL.json').write_text(json.dumps({'schema':'GDRSTR01','count':count,
        'source_internal':sk,'source_external':se,'source_name':args.source,
        'row_id_first':128,'row_id_last':127+count,
        'requires':'same ACE content, native roster frontend/match/snapshot integration',
        'engine_integration':'catalogue available; gameplay hooks still required',
        'no_table_growth':True},indent=2)+'\n')
    print(f'Created {count} native roster rows; ids 128..{127+count}; '
          f'local folder _build/local-assets/roster-stress/{args.name}')


def check_capacity(nk, ne, icons, slots, count):
    # Guest internal ids are signed bytes too; boss rows count toward 128.
    largest = min(94-slots, 128-nk, 128-ne, 128-icons)
    if count <= 0:
        raise ValueError('N must be positive')
    if largest < 0 or count > largest:
        raise ValueError(f'current signed-id engine / m-ex tables or icon capacity exceeded; '
                         f'largest admissible N is {max(0,largest)} '
                         f'({slots}/94 added slots, {nk} internal rows, {ne} external rows, '
                         f'{icons}/128 icons already present)')
    return largest


class Writer:
    def __init__(self, raw):
        self.ar = mex_hsd.Archive(raw)
        self.data = bytearray(self.ar.data)
        self.rel = set(self.ar.reloc_offsets)
        self.targets = sorted({self.u(r) for r in self.rel
                               if self.u(r) < len(self.data)} | {len(self.data)})

    def u(self,o):
        return struct.unpack_from('>I',self.data,o)[0]

    def put(self,o,v):
        struct.pack_into('>I',self.data,o,v)

    def append(self,b,align=4):
        self.data.extend(bytes((-len(self.data)) % align))
        at=len(self.data); self.data.extend(b)
        return at

    def span(self,p):
        if p <= 0 or p >= len(self.ar.data):
            raise ValueError('invalid table pointer')
        return self.targets[bisect.bisect_right(self.targets,p)]-p

    def extend(self,field,n,stride,source,count,insert=None):
        p=self.u(field)
        if not p:
            return None
        if field not in self.rel or self.span(p) < n*stride:
            raise ValueError(f'table at field +0x{field:X} is shorter than its declared rows')
        # Allow alignment padding but refuse an unrecognised stride/layout.
        if self.span(p) > n*stride+3:
            raise ValueError(f'unrecognised table stride at field +0x{field:X}')
        insert=n if insert is None else insert
        order=list(range(insert))+[source]*count+list(range(insert,n))
        at=self.append(b''.join(self.data[p+i*stride:p+(i+1)*stride] for i in order))
        for j,i in enumerate(order):
            for r in self.ar.reloc_offsets:
                if p+i*stride <= r < p+(i+1)*stride:
                    self.rel.add(at+j*stride+r-(p+i*stride))
        self.put(field,at)
        return at

    def finish(self):
        self.data.extend(bytes((-len(self.data))%4))
        body=bytes(self.data)+b''.join(struct.pack('>I',r) for r in sorted(self.rel))
        body+=self.ar.raw[self.ar.o_public:]
        header=struct.pack('>5I',32+len(body),len(self.data),len(self.rel),
                           self.ar.nb_public,self.ar.nb_extern)+self.ar.raw[20:32]
        return header+body


def clone_mxdt(raw,source_k,source_e,count,existing_slots,display_name='Sonic'):
    w=Writer(raw); b=w.ar.public('mexData'); meta=w.u(b); ft=w.u(b+8)
    nk,ne,icons=(w.u(meta+o) for o in (4,8,12))
    check_capacity(nk,ne,icons,existing_slots,count)
    if not (27 <= source_k < nk-6 and 0 <= source_e < ne):
        raise ValueError('source must be an added playable fighter, not a boss')
    if w.data[w.u(ft+12)+source_e*3] != source_k:
        raise ValueError('source internal/external mapping disagrees')
    for p,known in [(ft,33),(w.u(b+12),46),(w.u(b+32),10),(w.u(b+36),9)]:
        if p and any(w.data[p+known*4:p+w.span(p)]):
            raise ValueError('nonzero unrecognised fighter/function fields; layout needs review')
    report={'source_internal':source_k,'source_external':source_e,'count':count,
            'slots_after':existing_slots+count,'tables':[],
            'clone_internal_first':nk-6,'clone_external_first':ne}
    for off,name,space,stride in FIGHTER_TABLES:
        ptr=w.extend(ft+off,nk if space=='k' else ne,stride,
                     source_k if space=='k' else source_e,count,nk-6 if space=='k' else ne)
        report['tables'].append({'name':name,'space':space,'stride':stride,'present':ptr is not None})
    for root,n,layout in [(3,46,None),(8,10,(8,4,4,4,1,4,4,4,4,4)),(9,9,None)]:
        p=w.u(b+root*4)
        if not p: continue
        if w.span(p)<n*4:raise ValueError('incomplete function/Kirby table layout')
        for i in range(n):
            stride=layout[i] if layout else (8 if root==3 and i in (29,30) else 4)
            ptr=w.extend(p+4*i,nk,stride,source_k,count,nk-6)
            report['tables'].append({'name':f'root{root}[{i}]','space':'k','stride':stride,'present':ptr is not None})
    desc=w.u(ft+12)
    for e in range(ne):
        for j in (0,1):
            o=desc+e*3+j
            if nk-6 <= w.data[o] < nk: w.data[o]+=count
    names=w.u(ft)
    for c in range(count):
        w.data[desc+(ne+c)*3:desc+(ne+c)*3+3]=bytes([nk-6+c,255,0])
        at=w.append(f'{display_name} {c+1:03d}'.encode('shift_jis')+b'\0')
        w.put(names+(ne+c)*4,at);w.rel.add(names+(ne+c)*4)
    menu=w.u(b+4);css=w.u(menu+4);size=0xDC+icons*28
    if w.span(css)<size:raise ValueError('CSS block is truncated')
    rows=bytes(w.data[css:css+size])
    matches=[i for i in range(icons) if rows[0xDC+i*28+1]==source_e]
    if len(matches)!=1:raise ValueError('source must have exactly one CSS icon')
    src=rows[0xDC+matches[0]*28:0xDC+(matches[0]+1)*28]
    extra=[]
    for c in range(count):
        row=bytearray(src);row[1]=ne+c;extra.append(row)
    at=w.append(rows+b''.join(extra)+bytes(28),32)
    w.put(menu+4,at)
    for o,v in [(4,nk+count),(8,ne+count),(12,icons+count)]:w.put(meta+o,v)
    return w.finish(),report


def extend_plco(raw,nk,source,count):
    w=Writer(raw);b=w.ar.public('ftLoadCommonData')
    for i in (4,5):
        # ACE has four extra remap/sentinel rows after its 65 fighter rows.
        # Keep these at the end instead of discarding them or treating them as bosses.
        span=w.span(w.u(b+4*i))
        if span%4 or not nk <= span//4 <= nk+4:
            raise ValueError('unexpected PlCo kind-table length')
        w.extend(b+4*i,span//4,4,source,count,nk-6)
    return w.finish()


def remap_texanim(w,tex,pairs,end):
    """Rebuild constant texture keys from an immutable snapshot (no cascading copies)."""
    global texanim_keys
    import texanim_keys
    aobj=w.u(tex+8);f=w.u(aobj+8)
    while f:
        keys=texanim_keys._decode(w.data,f)
        if any(k[1]!=1 for k in keys):raise ValueError('atlas is not constant-key animation')
        ts=[k[0] for k in keys]
        body=bytearray()
        for i,(dst,src) in enumerate(pairs):
            if src < ts[0]:raise ValueError('atlas source frame has no key')
            value=keys[bisect.bisect_right(ts,src)-1][2]
            body.append(1);body+=value
            if i+1<len(pairs):body+=texanim_keys._varint(pairs[i+1][0]-dst)
        pos=w.append(body);w.put(f+4,len(body));w.put(f+16,pos);w.rel.add(f+16)
        f=w.u(f)
    struct.pack_into('>f',w.data,aobj+4,float(end))


def extend_atlas(raw,kind,nk,ne,source_k,source_e,count):
    w=Writer(raw)
    if kind=='css':
        b=w.ar.public('mexSelectChr');stride=w.u(b+16);tex=w.u(w.u(b+12)+8)
        if stride!=ne:raise ValueError('unexpected CSP stride')
        new=ne+count
        end=int(struct.unpack_from('>f',w.data,w.u(tex+8)+4)[0])
        costumes=(end+stride)//stride
        pairs=[(c*new+e,min(end,c*stride+(e if e<ne else source_e)))
               for c in range(costumes) for e in range(new)]
        w.put(b+16,new);remap_texanim(w,tex,pairs,costumes*new)
    else:
        b=w.ar.public('Stc_icns');reserved,stride=struct.unpack_from('>HH',w.data,b)
        if stride!=nk:raise ValueError('unexpected stock stride')
        tex=w.u(w.u(w.u(b+4)+8)+8);new=nk+count
        end=int(struct.unpack_from('>f',w.data,w.u(tex+8)+4)[0])
        costumes=(end-reserved+stride)//stride
        pairs=[(i,i) for i in range(reserved)]
        for c in range(costumes):
            for k in range(new):
                old=k if k<nk-6 else (source_k if k<nk-6+count else k-count)
                pairs.append((reserved+c*new+k,min(end,reserved+c*stride+old)))
        struct.pack_into('>H',w.data,b+2,new);remap_texanim(w,tex,pairs,reserved+costumes*new)
    return w.finish()


def output_folder(name):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*',name):
        raise ValueError('name must contain only letters, numbers, underscores or hyphens')
    dest=LOCAL/name
    if not dest.resolve().is_relative_to((ROOT/'_build').resolve()):
        raise ValueError('output escapes the ignored build root')
    if dest.resolve()!=dest.absolute():raise ValueError('output may not traverse a junction/symlink')
    return dest


def private_disc():
    value=os.environ.get('GW_ISO_ACE')
    if not value:
        for line in (ROOT/'.env').read_text().splitlines():
            match=re.match(r'\s*(?:export\s+)?GW_ISO_ACE\s*=\s*(.*?)\s*$',line)
            if match:value=match[1].strip('\"').strip("'")
    if not value:raise ValueError('GW_ISO_ACE is not configured')
    return mex_hsd.Gcm(value)


def generate(args):
    dest=output_folder(args.name)
    if dest.exists():raise ValueError('output already exists; choose a fresh name')
    g=private_disc();raw=g.read('MxDt.dat');a=mex_hsd.Archive(raw)
    b=a.public('mexData');meta=a.u32(b);ft=a.u32(b+8)
    nk,ne,icons=(a.u32(meta+o) for o in (4,8,12))
    names=a.u32(ft);desc=a.u32(ft+12);pl=a.u32(ft+4)
    hits=[e for e in range(ne) if a.cstr(a.u32(names+4*e)).casefold()==args.source.casefold()]
    if len(hits)!=1:raise ValueError('source name is absent or ambiguous')
    se=hits[0];sk=a.data[desc+se*3]
    if getattr(args,'native_registry',False):
        if args.fill_limit:raise ValueError('--fill-limit is only for legacy table clones')
        generate_native(args,g,raw,a,ft,sk,se,dest)
        return
    basenames={p.rsplit('/',1)[-1].casefold() for p in g.files}
    slots=sum(1 for k in range(27,nk-6) if a.u32(pl+8*k) and
              a.cstr(a.u32(pl+8*k)).casefold() in basenames)
    largest=min(94-slots,128-nk,128-ne,128-icons)
    count=largest if args.fill_limit else args.count
    check_capacity(nk,ne,icons,slots,count)
    mx,info=clone_mxdt(raw,sk,se,count,slots,args.source)
    payload={'MxDt.dat':mx,'PlCo.dat':extend_plco(g.read('PlCo.dat'),nk,sk,count),
             'MnSlChr.usd':extend_atlas(g.read('MnSlChr.usd'),'css',nk,ne,sk,se,count),
             'IfAll.usd':extend_atlas(g.read('IfAll.usd'),'stock',nk,ne,sk,se,count)}
    # Clone assets live once: all slots deliberately share these original bytes.
    # Copy every source fighter/costume/AJ/vi/result archive; ACE supplies shared banks/items.
    source_pl=a.cstr(a.u32(pl+8*sk));stem=source_pl[:-4]
    needed={source_pl,a.cstr(a.u32(a.u32(ft+28)+4*sk)),
            a.cstr(a.u32(a.u32(ft+40)+4*se))}
    for path in g.files:
        base=path.rsplit('/',1)[-1]
        if base.startswith(stem) or base in needed:
            if Path(path).is_absolute() or '..' in Path(path).parts:
                raise ValueError('unsafe disc file name')
            payload[path]=g.read(path)
    info.update({'source_name':args.source,'largest_admissible_N':largest,
                 'internal_rows_after':nk+count,'external_rows_after':ne+count,
                 'icons_after':icons+count,'asset_files':sorted(payload),
                 'base':'ACE (same disc used for generation)',
                 'costumes':'shared source costumes; no automatic tint',
                 'netplay':'offline stress only: clone content identities are equal',
                 'table_rows':'internal clones inserted before bosses; external clones appended'})
    # Validate ALL inputs before creating the output; never overwrite a prior run.
    dest.mkdir(parents=True)
    for path,content in payload.items():
        target=dest/'files'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    (dest/'mod.json').write_text(json.dumps({'id':args.name,'name':f'Roster stress: {count} Sonics',
        'version':'0.1.0','kind':'base','pack':'ace','description':'Local-only offline roster stress'},indent=2)+'\n')
    (dest/'INSTALL.json').write_text(json.dumps(info,indent=2)+'\n')
    print(f'Created {count} clones: {slots+count}/94 added slots, {icons+count}/128 icons; '
          f'local folder _build/local-assets/roster-stress/{args.name}')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--name',default='sonic-limit')
    ap.add_argument('--source',default='Sonic')
    ap.add_argument('--native-registry',action='store_true',
                    help='write wide native rows instead of growing m-ex byte tables')
    group=ap.add_mutually_exclusive_group();group.add_argument('--count',type=int,default=100)
    group.add_argument('--fill-limit',action='store_true')
    args=ap.parse_args()
    try:generate(args)
    except (OSError,KeyError,ValueError,struct.error,AssertionError):
        # Underlying readers include the private disc location in their errors.
        # Only our validated ValueErrors are safe to present.
        exc=sys.exc_info()[1]
        message=str(exc) if isinstance(exc,ValueError) else 'disc/asset read or layout validation failed'
        print('roster_stress: '+message,file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())

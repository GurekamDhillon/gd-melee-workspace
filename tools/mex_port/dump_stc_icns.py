#!/usr/bin/env python3
"""Decode m-ex's IfAll `Stc_icns` stock-icon symbol and check m-ex's GetStockFrame formula.

Read-only. See _research/mex-stock-icons.md.

  python dump_stc_icns.py --iso C:/iso/Akaneia.iso --retail-iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
  python dump_stc_icns.py --iso C:/iso/Akaneia.iso --png-dir OUT --internal 31 --costumes 7

Prints the Stc_icns header, the TexAnim, the frame -> image mapping for one internal id, and
(with --retail-iso) compares every vanilla fighter/costume: retail gm_80168B34 frame on retail
IfAll Stc_scemdls vs GetStockFrame(internal, costume) on Stc_icns, by image+palette hash.
"""
import argparse
import os
import sys, struct, hashlib, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mex_hsd import Gcm, Archive
BPP={0:4,1:8,2:8,3:16,4:16,5:16,6:32,8:4,9:8,10:16,14:4}
BLK={0:(8,8),1:(8,4),2:(8,4),3:(4,4),4:(4,4),5:(4,4),6:(4,4),8:(8,8),9:(8,4),10:(4,4),14:(8,8)}
def pf(a,p,frac):
    fmt=frac&0xE0; sc=1<<(frac&0x1F)
    if fmt==0: return struct.unpack('>f',a.data[p:p+4])[0],p+4
    if fmt==0x20: return struct.unpack('>h',a.data[p:p+2])[0]/sc,p+2
    if fmt==0x40: return struct.unpack('>H',a.data[p:p+2])[0]/sc,p+2
    if fmt==0x60: return struct.unpack('>b',a.data[p:p+1])[0]/sc,p+1
    return a.data[p]/sc,p+1
def fobj_keys(a,f):
    ln=a.u32(f+4); st=struct.unpack('>f',a.data[f+8:f+12])[0]; typ=a.u8(f+12); fv=a.u8(f+13); fs=a.u8(f+14); ad=a.u32(f+16)
    p=ad; end=ad+ln; t=st; keys=[]
    while p<end:
        op=a.data[p]&0xF; d=a.data[p]; p+=1; n=((d>>4)&7)+1; sh=3
        while d&0x80:
            d=a.data[p]; p+=1; n+=(d&0x7F)<<sh; sh+=7
        for _ in range(n):
            if op in (1,2,3,6): v,p=pf(a,p,fv)
            elif op==4: v,p=pf(a,p,fv); _,p=pf(a,p,fs)
            elif op==5: _,p=pf(a,p,fs); continue
            keys.append((t,v))
            w=0;sh=0
            while True:
                d=a.data[p]; p+=1; w|=(d&0x7F)<<sh; sh+=7
                if not d&0x80: break
            t+=w
    return typ,keys
class TexAnim:
    def __init__(s,a,t):
        s.a=a; s.t=t
        s.nimg=a.u16(t+20); s.imgtbl=a.u32(t+12); s.tluttbl=a.u32(t+16); s.ntlut=a.u16(t+22)
        aod=a.u32(t+8); s.end=struct.unpack('>f',a.data[aod+4:aod+8])[0]
        s.tracks={}
        f=a.u32(aod+8)
        while f:
            typ,k=fobj_keys(a,f); s.tracks[typ]=k; f=a.u32(f)
    def idx(s,typ,fr):
        v=None
        for t,val in s.tracks.get(typ,[]):
            if t<=fr+1e-6: v=val
        return None if v is None else int(v)
    def hash(s,fr):
        a=s.a; i=s.idx(1,fr)
        if i is None or i>=s.nimg: return None
        im=a.u32(s.imgtbl+4*i); ptr=a.u32(im); w,h=a.u16(im+4),a.u16(im+6); fmt=a.u32(im+8)
        bw,bh=BLK[fmt]; W=(w+bw-1)//bw*bw; H=(h+bh-1)//bh*bh
        hh=hashlib.md5(a.data[ptr:ptr+W*H*BPP[fmt]//8])
        j=s.idx(10,fr)
        if j is not None and s.ntlut and j<s.ntlut:
            tl=a.u32(s.tluttbl+4*j); tp=a.u32(tl); n=a.u16(tl+12)
            hh.update(a.data[tp:tp+2*n])
        return (w,h,fmt,hh.hexdigest()[:10])
def rgb5a3(v):
    if v&0x8000: return (((v>>10)&31)*255//31,((v>>5)&31)*255//31,(v&31)*255//31,255)
    return (((v>>8)&15)*17,((v>>4)&15)*17,(v&15)*17,((v>>12)&7)*255//7)
def rgb565(v): return (((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31,255)
def ia8(v): return (v&255,v&255,v&255,v>>8)
def decode(T, fr):
    i=T.idx(1,fr); im=T.a.u32(T.imgtbl+4*i); ptr=T.a.u32(im); w,h,fmt=T.a.u16(im+4),T.a.u16(im+6),T.a.u32(im+8)
    j=T.idx(10,fr); tl=T.a.u32(T.tluttbl+4*j); tp=T.a.u32(tl); tf=T.a.u32(tl+4); n=T.a.u16(tl+12)
    pal=[struct.unpack('>H',T.a.data[tp+2*k:tp+2*k+2])[0] for k in range(n)]
    conv={0:ia8,1:rgb565,2:rgb5a3}[tf]
    px=[[(0,0,0,0)]*w for _ in range(h)]
    assert fmt in (8,9)
    bw,bh=(8,8) if fmt==8 else (8,4)
    p=ptr
    for by in range(0,h,bh):
        for bx in range(0,w,bw):
            for y in range(bh):
                for x in range(bw):
                    if fmt==9: v=T.a.data[p]; p+=1
                    else:
                        b=T.a.data[p+((y*bw+x)>>1)]; v=(b>>4) if x%2==0 else b&15
                        if y==bh-1 and x==bw-1: p+=bw*bh//2
                    if by+y<h and bx+x<w: px[by+y][bx+x]=conv(pal[v])
    return px
def png(path,imgs,scale=4):
    W=sum(len(im[0]) for im in imgs)+4*len(imgs); H=max(len(im) for im in imgs)
    canvas=[[(40,40,40,255)]*W for _ in range(H)]
    ox=0
    for im in imgs:
        for y,row in enumerate(im):
            for x,c in enumerate(row):
                a=c[3]/255; canvas[y][ox+x]=tuple(int(c[k]*a+40*(1-a)) for k in range(3))+(255,)
        ox+=len(im[0])+4
    raw=b''.join(b'\0'+bytes([ch for c in row for xx in range(scale) for ch in c[:3]])*1 for row in canvas for _ in range(scale))
    # rebuild properly: each scaled row
    rows=[]
    for row in canvas:
        line=b'\0'+bytes(ch for c in row for _ in range(scale) for ch in c[:3])
        rows+= [line]*scale
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W*scale,H*scale,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))

# ---------------------------------------------------------------- m-ex / retail formulas
SPECIAL = [3, 2, 1, 1, 5, 6]  # MH, CH, Boy, Girl, Giga, Sandbag: the LAST six internal ids


def mex_frame(res, stride, n_internal, internal, costume):
    """m-ex GetStockFrame (Akaneia codes.gct C2 @0x803D7060)."""
    if n_internal - 6 <= internal <= n_internal - 1:
        return SPECIAL[internal - (n_internal - 6)]
    return res + costume * stride + internal


def retail_frame(ck, arg1, c):
    """Retail gm_80168B34 (gm/gm_1601.c)."""
    if ck == 0x1D: return 58
    if ck in (0x1B, 0x1C): return 26
    if ck == 0x1A: return 28
    if ck == 0x1E: return 27
    if ck == 0x1F: return 59
    if ck in (0x12, 0x13): base = 0x19 if arg1 == 7 else 0x12
    elif ck == 0x20: base = 0xE
    elif ck > 0x13: base = ck - 1
    else: base = ck
    return base + c * 30


NAMES = "CF DK Fox GW Kirby Bowser Link Luigi Mario Marth Mewtwo Ness Peach Pikachu IC Puff Samus Yoshi Zelda Sheik Falco YL Doc Roy Pichu Ganon".split()
CK2INT = [2, 3, 1, 24, 4, 5, 6, 17, 0, 18, 16, 8, 9, 12, 10, 15, 13, 14, 19, 7, 22, 20, 21, 26, 23, 25]
RETAIL_COSTUMES = [6, 5, 4, 4, 6, 4, 5, 4, 5, 5, 4, 4, 5, 4, 4, 5, 5, 6, 5, 5, 4, 4, 5, 5, 4, 5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True, help="m-ex disc (Akaneia)")
    ap.add_argument("--ifall", default="IfAll.usd")
    ap.add_argument("--retail-iso")
    ap.add_argument("--n-internal", type=int, default=41, help="mexData metadata internal_id_count")
    ap.add_argument("--internal", type=int, default=31)
    ap.add_argument("--costumes", type=int, default=7)
    ap.add_argument("--png-dir")
    a = ap.parse_args()
    A = Archive(Gcm(a.iso).read(a.ifall))
    s = A.public("Stc_icns")
    res, stride = A.u16(s), A.u16(s + 2)
    maj = A.u32(s + 4)
    ST = TexAnim(A, A.u32(A.u32(maj + 8) + 8))
    print(f"Stc_icns @data+0x{s:X}: reserved={res} stride={stride} matanim_joint=data+0x{maj:X} "
          f"egg_num={A.u32(s + 8)} eggs=data+0x{A.u32(s + 0xC):X}")
    print(f"  TexAnim: {ST.nimg} images, {ST.ntlut} tluts, end frame {ST.end}, "
          f"{len(ST.tracks.get(1, []))} TIMG keys")
    for c in range(a.costumes):
        f = mex_frame(res, stride, a.n_internal, a.internal, c)
        print(f"  internal {a.internal} costume {c}: frame {f} -> image {ST.idx(1, f)} {ST.hash(f)}")
    if a.png_dir:
        os.makedirs(a.png_dir, exist_ok=True)
        png(os.path.join(a.png_dir, f"stc_icns_int{a.internal}.png"),
            [decode(ST, mex_frame(res, stride, a.n_internal, a.internal, c)) for c in range(a.costumes)])
        png(os.path.join(a.png_dir, "stc_icns_reserved.png"), [decode(ST, f) for f in range(res)])
    if a.retail_iso:
        R = Archive(Gcm(a.retail_iso).read("IfAll.usd"))
        rs = R.public("Stc_scemdls")
        sms = R.u32(rs)
        rmaj = R.u32(R.u32(sms + 8))          # matanim joint tree of the first model set
        child = R.u32(rmaj)                    # root -> first child = stock icon joint 1
        RT = TexAnim(R, R.u32(R.u32(child + 8) + 8))
        ok = bad = 0
        for ck, nm in enumerate(NAMES):
            i = CK2INT[ck]
            for c in range(RETAIL_COSTUMES[ck]):
                rf, mf = retail_frame(ck, i, c), mex_frame(res, stride, a.n_internal, i, c)
                same = RT.hash(rf) is not None and RT.hash(rf) == ST.hash(mf)
                ok += same
                bad += not same
                if not same:
                    print(f"  DIFF {nm} costume {c}: retail frame {rf} vs m-ex frame {mf}")
        print(f"vanilla fighter/costume pairs: {ok} identical, {bad} different")


if __name__ == "__main__":
    main()

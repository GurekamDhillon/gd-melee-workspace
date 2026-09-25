"""Melee FigaTree read/write/evaluate (sysdolphin fobj.c semantics).

FigaTree  { int type; u32 flags; f32 frames; s8* nodes; FigaTrack* tracks; }            (0x14)
FigaTrack { u16 length; u16 startframe; u8 obj_type; u8 frac_value; u8 frac_slope; pad; u8* ad } (0xC)
Key stream: [op|count] byte (op low 4 bits: 1 CON 2 LIN 3 SPL0 4 SPL 5 SLP 6 KEY; bits 4-6 count-1,
bit 7 -> 7-bit varint continuation), per key value (+slope for SPL, only slope for SLP), then a
varint wait (not for SLP). Multi-byte values are LITTLE-endian. frac byte: top 3 bits type
(0 f32, 1 s16, 2 u16, 3 s8, 4 u8), low 5 bits = shift.
"""
import struct, math

TT = {1: 'ROTX', 2: 'ROTY', 3: 'ROTZ', 4: 'PATH', 5: 'TRAX', 6: 'TRAY', 7: 'TRAZ', 8: 'SCAX', 9: 'SCAY', 10: 'SCAZ'}
CON, LIN, SPL0, SPL, SLP, KEY = 1, 2, 3, 4, 5, 6


# ------------------------------------------------------------------ decode
def _pf(b, p, frac):
    t = frac >> 5; sh = frac & 0x1F; d = float(1 << sh)
    if t == 0: return struct.unpack_from('<f', b, p)[0], p + 4
    if t == 1: return struct.unpack_from('<h', b, p)[0] / d, p + 2
    if t == 2: return struct.unpack_from('<H', b, p)[0] / d, p + 2
    if t == 3: return struct.unpack_from('<b', b, p)[0] / d, p + 1
    if t == 4: return b[p] / d, p + 1
    raise ValueError('frac type %d' % t)


def decode_keys(b, p, length, fv, fs):
    """-> list of (op, value, slope, wait) ; wait None if omitted."""
    end = p + length; out = []
    while p < end:
        d = b[p]; p += 1; op = d & 0xF; n = ((d >> 4) & 7) + 1
        if d & 0x80:
            sh = 3
            while True:
                d = b[p]; p += 1; n += (d & 0x7F) << sh; sh += 7
                if not d & 0x80: break
        for _ in range(n):
            v = s = None
            if op in (CON, LIN, SPL0, KEY): v, p = _pf(b, p, fv)
            elif op == SPL: v, p = _pf(b, p, fv); s, p = _pf(b, p, fs)
            elif op == SLP: s, p = _pf(b, p, fs)
            else: raise ValueError('op %d' % op)
            w = None
            if op != SLP and p < end:
                w = 0; sh = 0
                while True:
                    d = b[p]; p += 1; w |= (d & 0x7F) << sh; sh += 7
                    if not d & 0x80: break
            out.append((op, v, s, w))
    if p != end: raise ValueError('key stream overrun %d' % (p - end))
    return out


def parse_archive(raw):
    """Standalone HSD sub-archive -> (symbol, tree dict)."""
    fsz, dsz, nrel, npub, next_ = struct.unpack_from('>5I', raw, 0)
    data = raw[0x20:0x20 + dsz]
    po = 0x20 + dsz + nrel * 4
    doff, soff = struct.unpack_from('>2I', raw, po)
    so = po + npub * 8 + next_ * 8 + soff
    sym = raw[so:raw.index(b'\0', so)].decode()
    return sym, parse_tree(data, doff)


def parse_tree(data, off):
    typ, flags, frames, nodes, tracks = struct.unpack_from('>IIfII', data, off)
    counts = []; p = nodes
    while data[p] != 0xFF: counts.append(data[p]); p += 1
    joints = []; ti = 0
    for c in counts:
        tr = []
        for _ in range(c):
            e = tracks + ti * 12; ti += 1
            ln, sf, ty, fv, fs, ad = struct.unpack_from('>HHBBBxI', data, e)
            tr.append(dict(type=ty, start=sf, fv=fv, fs=fs, keys=decode_keys(data, ad, ln, fv, fs), length=ln))
        joints.append(tr)
    return dict(type=typ, flags=flags, frames=frames, joints=joints)


# ------------------------------------------------------------------ evaluate (fobj.c)
def hermite(T, t, p0, p1, d0, d1):
    ft = 1.0 / T; t2 = t * t; ft2 = ft * ft
    t2_T = t2 * ft; t3_T2 = ft2 * t2 * t
    _2t3_T3 = 2.0 * t3_T2 * ft; _3t2_T2 = 3.0 * t2 * ft2
    return d1 * (t3_T2 - t2_T) + d0 * (t + (t3_T2 - t2_T) - t2_T) + p0 * (1 + _2t3_T3 - _3t2_T2) + p1 * (-_2t3_T3 + _3t2_T2)


def segments(keys):
    """Expand a key list into segments (f0, f1, op, p0, p1, d0, d1). Mirrors FObj state machine."""
    segs = []; f = 0; p0 = p1 = d0 = d1 = 0.0; first = True
    for op, v, s, w in keys:
        if op == SLP:
            d0, d1 = d1, s; continue
        if op in (CON, LIN, SPL0):
            p0, p1 = p1, v; d0, d1 = d1, 0.0
        elif op == SPL:
            p0, p1 = p1, v; d0, d1 = d1, s
        elif op == KEY:
            p0 = p1 = v
        if first:
            p0 = p1; first = False
        segs.append([f, op, p0, p1, d0, d1])
        f += (w or 0)
    return segs


def evaluate(keys, frame):
    """Value of a track at an integer/float frame (approximation of FObj stepping at 1.0 rate)."""
    # Build list of key points: (frame, value, slope_out, op)
    pts = []; f = 0; dcur = 0.0
    for op, v, s, w in keys:
        if op == SLP:
            if pts: pts[-1][2] = s
            continue
        slope = s if op == SPL else 0.0
        pts.append([f, v, slope, op])
        f += (w or 0)
    if not pts: return 0.0
    if frame <= pts[0][0]: return pts[0][1]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if a[0] <= frame < b[0] or (b[0] == a[0] and frame == a[0]):
            T = b[0] - a[0]
            if T == 0: return b[1]
            t = frame - a[0]; op = a[3]   # fobj: op_intrp = op of the key the segment leaves
            if op == CON: return a[1]
            if op == LIN: return a[1] + (b[1] - a[1]) * t / T
            if op == KEY: return a[1]
            return hermite(T, t, a[1], b[1], a[2], b[2] if b[3] == SPL else 0.0)
    return pts[-1][1]


# ------------------------------------------------------------------ encode
def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)


def choose_frac(vals, force_f32=False):
    """s16 fixed point with the largest shift that fits; f32 when range is too big."""
    m = max((abs(v) for v in vals), default=0.0)
    if force_f32: return 0x00
    if m == 0: return (1 << 5) | 15
    for sh in range(15, -1, -1):
        if m * (1 << sh) <= 32767: return (1 << 5) | sh
    return 0x00


def _enc(v, frac):
    t = frac >> 5; sh = frac & 0x1F
    if t == 0: return struct.pack('<f', v)
    q = int(round(v * (1 << sh)))
    if t == 1: return struct.pack('<h', max(-32768, min(32767, q)))
    raise ValueError


def quant(v, frac):
    t = frac >> 5; sh = frac & 0x1F
    if t == 0: return struct.unpack('<f', struct.pack('<f', v))[0]
    return max(-32768, min(32767, int(round(v * (1 << sh))))) / float(1 << sh)


def encode_spline(pts, frac_v=None, frac_s=None):
    """pts: list of (frame:int, value, slope) sorted, frames strictly increasing.
    Emits SPL keys (value+slope), wait = gap to next key; the last key has no wait.
    Returns (bytes, fv, fs, quantised key list)."""
    fv = frac_v if frac_v is not None else choose_frac([p[1] for p in pts])
    fs = frac_s if frac_s is not None else choose_frac([p[2] for p in pts])
    body = bytearray(); keys = []
    n = len(pts)
    # one header for all keys (count varint)
    cnt = n - 1
    hdr = SPL | ((cnt & 7) << 4)
    if cnt > 7:
        body.append(hdr | 0x80); body += _varint(cnt >> 3)
    else:
        body.append(hdr)
    for i, (f, v, s) in enumerate(pts):
        body += _enc(v, fv) + _enc(s, fs)
        w = None
        if i + 1 < n:
            w = pts[i + 1][0] - f; body += _varint(w)
        keys.append((SPL, quant(v, fv), quant(s, fs), w))
    return bytes(body), fv, fs, keys


def encode_const(v, frac_v=None):
    fv = frac_v if frac_v is not None else choose_frac([v])
    body = bytes([CON]) + _enc(v, fv)
    return body, fv, 0, [(CON, quant(v, fv), None, None)]


def build_tree_archive(symbol, frames, joints, tree_type=1, flags=0):
    """joints: list (DFS order) of lists of (obj_type, bytes, fv, fs). -> HSD archive bytes."""
    data = bytearray(); relocs = []
    def align(n):
        while len(data) % n: data.append(0)
    # key streams first
    ads = []
    for tr in joints:
        for (ty, body, fv, fs) in tr:
            ads.append(len(data)); data += body
    align(4)
    tracks_off = len(data); i = 0
    for tr in joints:
        for (ty, body, fv, fs) in tr:
            data += struct.pack('>HHBBBxI', len(body), 0, ty, fv, fs, ads[i])
            relocs.append(tracks_off + i * 12 + 8); i += 1
    nodes_off = len(data)
    data += bytes(len(tr) for tr in joints) + b'\xff'
    align(4)
    tree_off = len(data)
    data += struct.pack('>IIfII', tree_type, flags, float(frames), nodes_off, tracks_off)
    relocs += [tree_off + 12, tree_off + 16]
    align(0x20) if False else align(4)
    dsz = len(data)
    rel = b''.join(struct.pack('>I', r) for r in relocs)
    pub = struct.pack('>II', tree_off, 0)
    strs = symbol.encode() + b'\0'
    body = bytes(data) + rel + pub + strs
    fsz = 0x20 + len(body)
    hdr = struct.pack('>8I', fsz, dsz, len(relocs), 1, 0, 0, 0, 0)
    return hdr + body


def walk_aj(raw):
    """Sub-archives of an AJ file: list of (offset, size)."""
    off = 0; subs = []
    while off + 0x20 <= len(raw):
        fs = struct.unpack_from('>I', raw, off)[0]
        if fs == 0 or fs == 0xFFFFFFFF or off + fs > len(raw): break
        subs.append((off, fs)); off = (off + fs + 0x1F) & ~0x1F
    return subs

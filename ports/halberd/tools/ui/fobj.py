"""HSD FObj key streams: full decode / encode (ops CON 1, LIN 2, SPL0 3, SPL 4, SLP 5, KEY 6), values little-endian
as HSD stores them (fobj.c / HSDRaw). Used to add image keys to constant-key TexAnims (CSP, stock, name strips)."""
import struct

def _u32(d, o): return struct.unpack(">I", d[o:o+4])[0]
VLEN = {0: 4, 0x20: 2, 0x40: 2, 0x60: 1, 0x80: 1}

def _val(b, fv):
    t = fv & 0xE0; sc = float(1 << (fv & 0x1F))
    if t == 0: return struct.unpack("<f", b)[0]
    if t == 0x20: return struct.unpack("<h", b)[0] / sc
    if t == 0x40: return struct.unpack("<H", b)[0] / sc
    if t == 0x60: return struct.unpack("<b", b)[0] / sc
    return b[0] / sc

def enc_val(v, fv):
    t = fv & 0xE0; sc = 1 << (fv & 0x1F)
    if t == 0: return struct.pack("<f", v)
    iv = int(round(v * sc))
    return struct.pack({0x20: "<h", 0x40: "<H", 0x60: "<b", 0x80: "<B"}[t], iv)

def _packed(d, p):
    v = 0; sh = 0
    while True:
        b = d[p]; p += 1; v |= (b & 0x7F) << sh; sh += 7
        if not b & 0x80: return v, p

def _varint(n):
    o = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: o.append(b | 0x80)
        else: o.append(b); return bytes(o)

def decode(d, f):
    """-> list of keys [frame, op, value_bytes, slope_bytes|None, wait] (frame = start of the key)."""
    ln, fv, fs, ad = _u32(d, f+4), d[f+13], d[f+14], _u32(d, f+16)
    start = struct.unpack(">f", d[f+8:f+12])[0]
    p, end, t, keys = ad, ad + ln, start, []
    while p < end:
        b = d[p]; p += 1; op = b & 0xF; n = ((b >> 4) & 7) + 1; sh = 3
        while b & 0x80: b = d[p]; p += 1; n += (b & 0x7F) << sh; sh += 7
        for _ in range(n):
            vl, sl = VLEN[fv & 0xE0], VLEN[fs & 0xE0]
            v = s = None; w = 0
            if op in (1, 2, 3):
                v = bytes(d[p:p+vl]); p += vl; w, p = _packed(d, p)
            elif op == 4:
                v = bytes(d[p:p+vl]); p += vl; s = bytes(d[p:p+sl]); p += sl; w, p = _packed(d, p)
            elif op == 5:
                s = bytes(d[p:p+sl]); p += sl
            elif op == 6:
                v = bytes(d[p:p+vl]); p += vl
            else:
                raise ValueError("FObj op %d" % op)
            keys.append([t, op, v, s, w]); t += w
    return keys

def value_at(d, f, frame):
    """Constant-key track: the value of the last valued key at or before `frame`."""
    fv = d[f+13]; last = None
    for t, op, v, s, w in decode(d, f):
        if v is not None and t <= frame: last = _val(v, fv)
    return last

def has_key_at(d, f, frame):
    return any(int(k[0]) == frame and k[2] is not None for k in decode(d, f))

def set_constant(data, f, frame_values):
    """Give a CON-keyed (op 1) track exact values on single frames {frame: value}; the frame after keeps its old value.
    Only for tracks whose keys are all op 1/6 (constant, as m-ex's atlases are). The new key stream is appended to
    `data` (a bytearray) and the FObj's length / pointer are updated (the pointer is already relocated)."""
    fv = data[f+13]
    keys = decode(data, f)
    assert all(k[1] in (1, 6) for k in keys), "set_constant: non-constant track"
    tl = [[int(k[0]), k[2]] for k in keys]
    old_of = lambda fr: [k for k in tl if k[0] <= fr][-1][1]
    for fr, val in sorted(frame_values.items()):
        old = old_of(fr); nv = enc_val(val, fv)
        if not any(k[0] == fr + 1 for k in tl): tl.append([fr + 1, old])
        hit = [k for k in tl if k[0] == fr]
        if hit: hit[0][1] = nv
        else: tl.append([fr, nv])
        tl.sort(key=lambda k: k[0])
    body = bytearray()
    for i, (t, v) in enumerate(tl):
        body.append(0x01); body += v
        body += _varint(tl[i+1][0] - t if i + 1 < len(tl) else 0)
    start = struct.unpack(">f", data[f+8:f+12])[0]
    assert start == 0.0
    while len(data) % 4: data.append(0)
    pos = len(data); data += body
    struct.pack_into(">I", data, f + 4, len(body)); struct.pack_into(">I", data, f + 16, pos)
    return pos


def set_inplace(data, f, frame_values):
    """Rewrite the value of the key that sits exactly on each frame, in place (same stream length, nothing appended).
    Returns False (and changes nothing) when a frame has no key of its own or the track is not constant-keyed."""
    ln, fv, ad = _u32(data, f+4), data[f+13], _u32(data, f+16)
    p, end, t, pos = ad, ad + ln, 0.0, {}
    vl = VLEN[fv & 0xE0]
    while p < end:
        b = data[p]; p += 1; op = b & 0xF; n = ((b >> 4) & 7) + 1; sh = 3
        while b & 0x80: b = data[p]; p += 1; n += (b & 0x7F) << sh; sh += 7
        for _ in range(n):
            if op not in (1, 6): return False
            vp = p; p += vl; w = 0
            if op == 1: w, p = _packed(data, p)
            pos[int(t)] = vp; t += w
    if any(fr not in pos for fr in frame_values): return False
    for fr, v in frame_values.items():
        data[pos[fr]:pos[fr] + vl] = enc_val(v, fv)
    return True


def encode_constant(keys, fv):
    """[(frame, value)] (frames ascending, first 0) -> a compact CON key stream: one header per run of keys
    (count in the header's 3 bits + 7-bit extension bytes, as fobj.c reads it), value, wait to the next key."""
    out = bytearray(); i = 0
    while i < len(keys):
        n = min(len(keys) - i, 1 << 10)
        c = n - 1; b = 0x01 | ((c & 7) << 4); c >>= 3
        ext = []
        while c: ext.append(c & 0x7F); c >>= 7
        if ext: b |= 0x80
        out.append(b)
        for j, e in enumerate(ext): out.append(e | (0x80 if j + 1 < len(ext) else 0))
        for k in range(i, i + n):
            t, v = keys[k]
            out += enc_val(v, fv)
            out += _varint(keys[k + 1][0] - t if k + 1 < len(keys) else 0)
        i += n
    return bytes(out)


def constant_keys(data, f):
    """[(frame, value)] of a constant-keyed track, redundant keys (same value as the previous) dropped"""
    fv = data[f+13]; out = []
    for t, op, v, s, w in decode(data, f):
        assert op in (1, 6) and v is not None
        val = _val(v, fv)
        if not out or out[-1][1] != val: out.append((int(t), val))
    return out

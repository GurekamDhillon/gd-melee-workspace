"""Read helpers for constant-key TexAnims (m-ex CSP / stock atlases): which image + TLUT a frame shows, decoded."""
import os, struct, sys
sys.path.insert(0, r"C:/Users/Gurek/Desktop/GD's Melee/experiment/brawl-kirby/tools")
import texanim_keys
import gxcodec as G

def u32(d, o): return struct.unpack(">I", d[o:o+4])[0]

def frame_value(d, ta, frame, typ):
    f = u32(d, u32(d, ta + 8) + 8)
    while f:
        if d[f+12] == typ:
            keys = texanim_keys._decode(d, f)
            k = [k for k in keys if k[0] <= frame][-1]
            v = k[2]; fv = d[f+13]
            if fv & 0xE0 == 0: return int(struct.unpack("<f", v)[0])
            val = int.from_bytes(v, "little", signed=(fv & 0xE0) in (0x20, 0x60))
            return int(val / (1 << (fv & 0x1F)))
        f = u32(d, f)
    return None

def image_at(d, desc):
    ptr = u32(d, desc); w, h = struct.unpack(">HH", d[desc+4:desc+8]); fmt = u32(d, desc+8)
    return ptr, w, h, fmt

def tlut_at(d, t):
    return u32(d, t), u32(d, t+4), struct.unpack(">H", d[t+0xC:t+0xE])[0]

def decode_frame(d, ta, frame):
    """-> (PIL image, info dict) of the image + TLUT a constant-key TexAnim selects at `frame`."""
    ii = frame_value(d, ta, frame, 1); ti = frame_value(d, ta, frame, 10)
    ptr, w, h, fmt = image_at(d, u32(d, u32(d, ta + 0xC) + 4 * ii))
    tl = None
    if ti is not None and fmt in (8, 9):
        tp, tf, n = tlut_at(d, u32(d, u32(d, ta + 0x10) + 4 * ti)); tl = bytes(d[tp:tp + 2 * n])
    return G.decode(bytes(d[ptr:ptr + G.size_of(fmt, w, h)]), fmt, w, h, tl), {"image": ii, "tlut": ti, "w": w, "h": h, "fmt": fmt, "ptr": ptr}

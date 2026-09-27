#!/usr/bin/env python3
"""Install local Ultimate UI textures into an already-created m-ex slot.

mk_slot_files.py first makes the destination row and its private CSS joint.
This tool replaces that joint's portrait and the row's CSP/stock frame art.
The replaced row's unused image buffers are reused where possible, especially
in IfAll.usd, which has little match-time heap headroom. No source textures or
converted art are written to tracked paths.
"""
import argparse
import bisect
import json
import os
import struct
import sys
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "tools", "mex_port"),
                os.path.join(ROOT, "ports", "halberd", "tools", "ui")]
import mex_hsd  # noqa: E402
import fobj  # noqa: E402
import gxcodec as G  # noqa: E402
from ultimate_vfx_geno import decode_bntx  # noqa: E402

ISO_ACE = "C:/iso/SSBM ACE Build v2.0.0.iso"
UI_ROOT = os.path.join(os.environ.get("GW_ULTIMATE_ROOT", os.path.join(ROOT, "experiment", "tooling", "ultimate")),
                       "workspace", "extracted", "ui", "replace_patch", "chara")
FORMAT = {G.GX_TF_C4: "CI4", G.GX_TF_C8: "CI8"}


def source_paths(root, fighter):
    """The costume atlas uses Ultimate's 00..07 order; ch0 is the CSS close-up."""
    return {kind: [os.path.join(root, f"chara_{kind}", f"chara_{kind}_{fighter}_{c:02}.bntx")
                   for c in (range(1) if kind == 0 else range(8))]
            for kind in (0, 1, 2)}


def missing_sources(root, fighter):
    return [p for paths in source_paths(root, fighter).values() for p in paths if not os.path.isfile(p)]


def load_bntx(path):
    _, image, _, selectors = decode_bntx(path)
    if selectors == [2, 3, 4, 5]:
        return image.convert("RGBA")
    bands = image.convert("RGBA").split()
    zero = Image.new("L", image.size, 0)
    one = Image.new("L", image.size, 255)
    choices = [zero, one, *bands]
    if any(s >= len(choices) for s in selectors):
        raise ValueError(f"unknown BNTX component selector {selectors} in {path}")
    return Image.merge("RGBA", tuple(choices[s] for s in selectors))


def fit_art(image, size, inset=0):
    """Crop transparent padding, then contain in `size` with premultiplied alpha."""
    image = image.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty Ultimate UI texture")
    image = image.crop(bbox)
    target = (size[0] - 2 * inset, size[1] - 2 * inset)
    if min(target) <= 0:
        raise ValueError(f"invalid art size/inset: {size}, {inset}")
    scale = min(target[0] / image.width, target[1] / image.height)
    wh = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.convert("RGBa").resize(wh, Image.Resampling.LANCZOS).convert("RGBA")
    out = Image.new("RGBA", size)
    out.paste(image, ((size[0] - wh[0]) // 2, (size[1] - wh[1]) // 2))
    return out


def portrait_art(image, size):
    """Ultimate chara_1 is a square bust; fill Melee's taller CSP viewport."""
    image = image.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty Ultimate CSP")
    return ImageOps.fit(image.crop(bbox).convert("RGBa"), size, Image.Resampling.LANCZOS,
                        centering=(0.5, 0.35)).convert("RGBA")


def icon_art(image, template, label):
    """Keep the Melee icon border, replace the face and the host name band."""
    out = template.convert("RGBA").copy()
    face = ImageOps.fit(image.convert("RGBa"), (60, 39), Image.Resampling.LANCZOS,
                        centering=(0.5, 0.42)).convert("RGBA")
    out.paste(face, (2, 2))
    draw = ImageDraw.Draw(out)
    draw.rectangle((3, 42, 60, 52), fill=(22, 15, 24, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 9)
    except OSError:
        font = ImageFont.load_default()
    text = label.upper()
    while draw.textbbox((0, 0), text, font=font)[2] > 56 and len(text) > 1:
        text = text[:-1]
    box = draw.textbbox((0, 0), text, font=font)
    x = (64 - (box[2] - box[0])) // 2 - box[0]
    y = 43 - box[1]
    draw.text((x, y), text, font=font, fill=(250, 226, 211, 255))
    return out


def encode_art(image, fmt):
    if fmt not in FORMAT:
        raise ValueError(f"unsupported GX UI format {fmt}")
    return G.encode_ci(image, fmt)


def encode_csp_costumes(images):
    # Ultimate costumes can change pose and silhouette, so they need separate
    # pixel maps. A shared Melee-style index map visibly corrupts those poses.
    return [(pixels, palette) for pixels, palette, _ in
            (encode_art(im, G.GX_TF_C8) for im in images)]


class ArchiveEdit:
    """Append-only HSD editor, preserving the original symbol table and relocations."""
    def __init__(self, raw):
        self.raw = raw
        self.archive = mex_hsd.Archive(raw)
        self.data = bytearray(self.archive.data)
        self.relocs = set(self.archive.reloc_offsets)
        self.remap = lambda offset: offset

    def u32(self, o):
        return struct.unpack_from(">I", self.data, o)[0]

    def u16(self, o):
        return struct.unpack_from(">H", self.data, o)[0]

    def put(self, o, value):
        struct.pack_into(">I", self.data, o, value)

    def ptr(self, o, value):
        self.put(o, value)
        (self.relocs.add if value else self.relocs.discard)(o)

    def append(self, raw, alignment=0x20):
        self.data.extend(b"\0" * (-len(self.data) % alignment))
        at = len(self.data)
        self.data.extend(raw)
        return at

    def clone(self, o, length):
        at = self.append(self.data[o:o + length], 4)
        for delta in range(0, length, 4):
            if o + delta in self.relocs:
                self.relocs.add(at + delta)
        return at

    def image(self, like, pixels):
        fmt = self.u32(like + 8)
        w, h = struct.unpack_from(">HH", self.data, like + 4)
        if len(pixels) != G.size_of(fmt, w, h):
            raise ValueError(f"GX image length for {w}x{h} {fmt}: {len(pixels)}")
        desc = self.clone(like, 0x18)
        self.ptr(desc, self.append(pixels))
        return desc

    def tlut(self, like, palette):
        if len(palette) != 2 * self.u16(like + 0xC):
            raise ValueError("GX TLUT length differs from copied entry")
        desc = self.clone(like, 0x10)
        self.ptr(desc, self.append(palette))
        return desc

    def grow_table(self, table, old_count, extra):
        at = self.append(bytes(4 * (old_count + len(extra))), 4)
        for i in range(old_count):
            self.ptr(at + 4 * i, self.u32(table + 4 * i))
        for i, p in enumerate(extra, old_count):
            self.ptr(at + 4 * i, p)
        return at

    def add_to_texanim(self, ta, images, tluts):
        old_i, old_t = self.u16(ta + 0x14), self.u16(ta + 0x16)
        if images:
            self.ptr(ta + 0xC, self.grow_table(self.u32(ta + 0xC), old_i, images))
            struct.pack_into(">H", self.data, ta + 0x14, old_i + len(images))
        if tluts:
            self.ptr(ta + 0x10, self.grow_table(self.u32(ta + 0x10), old_t, tluts))
            struct.pack_into(">H", self.data, ta + 0x16, old_t + len(tluts))
        return old_i, old_t

    def compact_unreferenced_tables(self, tables):
        """Remove aligned interiors of old pointer tables after TexAnim repointing.

        Removing entire 32-byte blocks preserves the GX alignment of every
        later image and TLUT. The old table's own relocations are discarded;
        every surviving pointer and public symbol is then remapped.
        """
        blocks = []
        for start, count in tables:
            if self.refs(start):
                raise ValueError(f"old UI table at {start:#x} is still referenced")
            lo = (start + 31) & ~31
            hi = (start + 4 * count) & ~31
            if hi > lo:
                blocks.append((lo, hi))
        blocks.sort()
        for (_, end), (start, _) in zip(blocks, blocks[1:]):
            if end > start:
                raise ValueError("old UI table ranges overlap")
        inside = lambda o: any(lo <= o < hi for lo, hi in blocks)
        surviving = [o for o in self.relocs if not inside(o)]
        if any(inside(self.u32(o)) for o in surviving):
            raise ValueError("surviving HSD pointer reaches old UI table")
        starts = [lo for lo, _ in blocks]
        removed = []
        total = 0
        for lo, hi in blocks:
            total += hi - lo
            removed.append(total)
        def shift(o):
            i = bisect.bisect_right(starts, o) - 1
            return o - (removed[i] if i >= 0 else 0)
        new_data = bytearray()
        cursor = 0
        for lo, hi in blocks:
            new_data += self.data[cursor:lo]
            cursor = hi
        new_data += self.data[cursor:]
        self.relocs = set()
        for o in surviving:
            struct.pack_into(">I", new_data, shift(o), shift(self.u32(o)))
            self.relocs.add(shift(o))
        previous = self.remap
        self.remap = lambda o, previous=previous, shift=shift: shift(previous(o))
        self.data = new_data
        return total

    def refs(self, target):
        return sum(self.u32(o) == target for o in self.relocs)

    def save(self, path):
        self.data.extend(b"\0" * (-len(self.data) % 4))
        rel = sorted(self.relocs)
        tail = bytearray(self.raw[self.archive.o_public:])
        for i in range(self.archive.nb_public + self.archive.nb_extern):
            original = struct.unpack_from(">I", tail, 8 * i)[0]
            struct.pack_into(">I", tail, 8 * i, self.remap(original))
        body = bytes(self.data) + b"".join(struct.pack(">I", r) for r in rel) + tail
        header = struct.pack(">5I", 0x20 + len(body), len(self.data), len(rel),
                             self.archive.nb_public, self.archive.nb_extern)
        with open(path, "wb") as stream:
            stream.write(header + self.raw[0x14:0x20] + body)


def desc_at(ar, ta, index):
    return ar.u32(ar.u32(ta + 0xC) + 4 * index)


def tlut_at(ar, ta, index):
    return ar.u32(ar.u32(ta + 0x10) + 4 * index)


def entry(ar, ta, frame):
    tracks = tracks_of(ar, ta)
    indices = [fobj.value_at(ar.data, tracks[t], frame) for t in (1, 10)]
    if any(v is None for v in indices):
        raise ValueError(f"missing UI image/TLUT at frame {frame}")
    return tuple(int(v) for v in indices)


def tracks_of(ar, ta):
    result = {}
    f = ar.u32(ar.u32(ta + 8) + 8)
    while f:
        result[ar.data[f + 12]] = f
        f = ar.u32(f)
    if 1 not in result or 10 not in result:
        raise ValueError("UI TexAnim has no image/TLUT tracks")
    return result


def used_indices(ar, ta, typ):
    return {int(v) for _, v in fobj.constant_keys(ar.data, tracks_of(ar, ta)[typ])}


def check_entry(ar, desc, tlut, expected_fmt=None):
    w, h, fmt = struct.unpack_from(">HHI", ar.data, desc + 4)
    palette_fmt = ar.u32(tlut + 4)
    count = ar.u16(tlut + 0xC)
    if fmt not in FORMAT or (expected_fmt is not None and fmt != expected_fmt):
        raise ValueError(f"unsupported copied GX image format {fmt} ({w}x{h})")
    if palette_fmt != G.GX_TL_RGB5A3 or count != (16 if fmt == G.GX_TF_C4 else 256):
        raise ValueError(f"unsupported copied GX TLUT format/count {palette_fmt}/{count}")
    return w, h, fmt


def write_tlut(ar, tlut, palette):
    dest = ar.u32(tlut)
    if ar.refs(dest) == 1:
        ar.data[dest:dest + len(palette)] = palette
    else:
        ar.ptr(tlut, ar.append(palette))


def set_frames(ar, ta, mapping):
    """mapping: frame -> (image index, TLUT index)."""
    tracks = tracks_of(ar, ta)
    for typ, col in ((1, 0), (10, 1)):
        values = {frame: pair[col] for frame, pair in mapping.items()}
        if not fobj.set_inplace(ar.data, tracks[typ], values):
            fobj.set_constant(ar.data, tracks[typ], values)


def csp_texanim(ar):
    return ar.u32(ar.u32(ar.archive.public("mexSelectChr") + 0xC) + 8)


def stock_texanim(ar):
    s = ar.archive.public("Stc_icns")
    return ar.u32(ar.u32(ar.u32(s + 4) + 8) + 8)


def write_csp(current, original, external, sources):
    ta, old_ta = csp_texanim(current), csp_texanim(original)
    stride = current.u32(current.archive.public("mexSelectChr") + 0x10)
    frames = [external + c * stride for c in range(8)]
    old = [entry(original, old_ta, f) for f in frames]
    used_i, used_t = used_indices(current, ta, 1), used_indices(current, ta, 10)
    descriptors = [desc_at(current, ta, i) for i, _ in old]
    tluts = [tlut_at(current, ta, t) for _, t in old]
    sizes = {check_entry(current, d, t, G.GX_TF_C8) for d, t in zip(descriptors, tluts)}
    if len(sizes) != 1:
        raise ValueError(f"inconsistent copied CSP entries: {sizes}")
    w, h, _ = sizes.pop()
    arts = [portrait_art(im, (w, h)) for im in sources]
    encoded = encode_csp_costumes(arts)
    reusable = {c for c, (i, t) in enumerate(old) if i not in used_i and t not in used_t
                and sum(other_i == i for other_i, _ in old) == 1
                and sum(other_t == t for _, other_t in old) == 1}
    groups = defaultdict(list)
    for c in reusable:
        groups[current.u32(descriptors[c])].append(c)
    for buffer, group in groups.items():
        if current.refs(buffer) != len({descriptors[c] for c in group}):
            reusable.difference_update(group)
    new_images, new_tluts = [], []
    mapping = {}
    claimed_buffers = set()
    new_buffers = 0
    for c, frame in enumerate(frames):
        pixels, palette = encoded[c]
        if c in reusable:
            ii, ti = old[c]
            desc = descriptors[c]
            buffer = current.u32(desc)
            if buffer in claimed_buffers:
                current.ptr(desc, current.append(pixels))
                new_buffers += 1
            else:
                current.data[buffer:buffer + len(pixels)] = pixels
                claimed_buffers.add(buffer)
            write_tlut(current, tluts[c], palette)
        else:
            ii = current.u16(ta + 0x14) + len(new_images)
            ti = current.u16(ta + 0x16) + len(new_tluts)
            new_images.append(current.image(descriptors[c], pixels))
            new_tluts.append(current.tlut(tluts[c], palette))
        mapping[frame] = (ii, ti)
    old_tables = []
    if new_images:
        old_tables.append((current.u32(ta + 0xC), current.u16(ta + 0x14)))
    if new_tluts:
        old_tables.append((current.u32(ta + 0x10), current.u16(ta + 0x16)))
    current.add_to_texanim(ta, new_images, new_tluts)
    set_frames(current, ta, mapping)
    removed = current.compact_unreferenced_tables(old_tables)
    return {"size": [w, h], "format": "CI8/RGB5A3", "frames": mapping,
            "source": "chara_1", "reused": len(reusable), "new_images": len(new_images),
            "new_pixel_buffers": new_buffers,
            "old_table_bytes_removed": removed}


def write_stocks(current, original, internal, sources):
    ta, old_ta = stock_texanim(current), stock_texanim(original)
    s = current.archive.public("Stc_icns")
    reserved, stride = struct.unpack_from(">HH", current.data, s)
    frames = [reserved + c * stride + internal for c in range(8)]
    old = [entry(original, old_ta, f) for f in frames]
    used_i, used_t = used_indices(current, ta, 1), used_indices(current, ta, 10)
    descriptors = [desc_at(current, ta, i) for i, _ in old]
    tluts = [tlut_at(current, ta, t) for _, t in old]
    sizes = {check_entry(current, d, t, G.GX_TF_C4) for d, t in zip(descriptors, tluts)}
    if len(sizes) != 1:
        raise ValueError(f"inconsistent copied stock entries: {sizes}")
    w, h, _ = sizes.pop()
    arts = [fit_art(im, (w, h), inset=1) for im in sources]
    reusable = {c for c, (i, t) in enumerate(old) if i not in used_i and t not in used_t
                and sum(other_i == i for other_i, _ in old) == 1
                and sum(other_t == t for _, other_t in old) == 1}
    groups = defaultdict(list)
    for c in reusable:
        groups[current.u32(descriptors[c])].append(c)
    new_images, new_tluts, mapping = [], [], {}
    reused = 0
    for buffer, costumes in groups.items():
        if current.refs(buffer) != len({descriptors[c] for c in costumes}):
            reusable.difference_update(costumes)
            continue
        costumes.sort()
        if len(costumes) == 1:
            pixels, palettes, _ = encode_art(arts[costumes[0]], G.GX_TF_C4)
            palettes = [palettes]
        else:
            pixels, palettes, _ = G.encode_ci_joint([arts[c] for c in costumes], G.GX_TF_C4)
        current.data[buffer:buffer + len(pixels)] = pixels
        for c, palette in zip(costumes, palettes):
            write_tlut(current, tluts[c], palette)
            mapping[frames[c]] = old[c]
            reused += 1
    for c in range(8):
        if frames[c] in mapping:
            continue
        pixels, palette, _ = encode_art(arts[c], G.GX_TF_C4)
        ii = current.u16(ta + 0x14) + len(new_images)
        ti = current.u16(ta + 0x16) + len(new_tluts)
        new_images.append(current.image(descriptors[c], pixels))
        new_tluts.append(current.tlut(tluts[c], palette))
        mapping[frames[c]] = (ii, ti)
    old_tables = []
    if new_images:
        old_tables.append((current.u32(ta + 0xC), current.u16(ta + 0x14)))
    if new_tluts:
        old_tables.append((current.u32(ta + 0x10), current.u16(ta + 0x16)))
    current.add_to_texanim(ta, new_images, new_tluts)
    set_frames(current, ta, mapping)
    removed = current.compact_unreferenced_tables(old_tables)
    return {"size": [w, h], "format": "CI4/RGB5A3", "frames": mapping,
            "source": "chara_2", "reused": reused, "new_images": len(new_images),
            "old_table_bytes_removed": removed}


def write_icon(current, joint, source, label):
    m = current.archive.public("mexSelectChr")
    kids = []
    o = current.u32(current.u32(m) + 8)
    while o:
        kids.append(o)
        o = current.u32(o + 0xC)
    if joint < 1 or joint > len(kids):
        raise ValueError(f"CSS icon joint {joint} outside 1..{len(kids)}")
    jo = kids[joint - 1]
    dob0 = current.u32(jo + 0x10)
    dob1 = current.u32(dob0 + 4)
    mobj = current.u32(dob1 + 8)
    tobj = current.u32(mobj + 8)
    desc, tlut = current.u32(tobj + 0x4C), current.u32(tobj + 0x50)
    w, h, fmt = check_entry(current, desc, tlut, G.GX_TF_C8)
    if (w, h) != (64, 56):
        raise ValueError(f"unsupported copied CSS icon size {w}x{h}")
    palette = bytes(current.data[current.u32(tlut):current.u32(tlut) + 2 * current.u16(tlut + 0xC)])
    template = G.decode(bytes(current.data[current.u32(desc):current.u32(desc) + G.size_of(fmt, w, h)]),
                        fmt, w, h, palette)
    art = icon_art(source, template, label)
    pixels, palette, _ = encode_art(art, fmt)
    # The new joint still points to the host's DObj/MObj/TObj chain. Clone it
    # before changing image pointers so the host's CSS icon remains untouched.
    nd0, nd1 = current.clone(dob0, 0x10), current.clone(dob1, 0x10)
    nm, nt = current.clone(mobj, 0x18), current.clone(tobj, 0x5C)
    current.ptr(nt + 0x4C, current.image(desc, pixels))
    current.ptr(nt + 0x50, current.tlut(tlut, palette))
    current.ptr(nm + 8, nt)
    current.ptr(nd1 + 8, nm)
    current.ptr(nd0 + 4, nd1)
    current.ptr(jo + 0x10, nd0)
    return {"joint": joint, "size": [w, h], "format": "CI8/RGB5A3", "source": "chara_0", "label": label}


def icon_joint(mxdt, external):
    ar = ArchiveEdit(mxdt)
    base = ar.archive.public("mexData")
    meta, menu = ar.u32(base), ar.u32(base + 4)
    css = ar.u32(menu + 4)
    n = struct.unpack_from(">i", ar.data, meta + 12)[0]
    rows = [css + 0xDC + i * 0x1C for i in range(n) if ar.data[css + 0xDC + i * 0x1C + 1] == external]
    if len(rows) != 1:
        raise ValueError(f"MxDt CSS external id {external}: {len(rows)} rows")
    return ar.data[rows[0] + 4]


def install(files, fighter, internal, external, label, source_root=UI_ROOT, iso=ISO_ACE):
    missing = missing_sources(source_root, fighter)
    if missing:
        raise FileNotFoundError(f"{len(missing)} Ultimate UI BNTX files missing, first: {missing[0]}")
    paths = source_paths(source_root, fighter)
    sources = {kind: [load_bntx(p) for p in paths[kind]] for kind in paths}
    disc = mex_hsd.Gcm(iso)
    mnpath, ifpath = (os.path.join(files, name) for name in ("MnSlChr.usd", "IfAll.usd"))
    menu = ArchiveEdit(open(mnpath, "rb").read())
    stock = ArchiveEdit(open(ifpath, "rb").read())
    original_menu = ArchiveEdit(disc.read("MnSlChr.usd"))
    original_stock = ArchiveEdit(disc.read("IfAll.usd"))
    joint = icon_joint(open(os.path.join(files, "MxDt.dat"), "rb").read(), external)
    result = {"fighter": fighter, "icon": write_icon(menu, joint, sources[0][0], label),
              "csp": write_csp(menu, original_menu, external, sources[1]),
              "stock": write_stocks(stock, original_stock, internal, sources[2])}
    menu.save(mnpath)
    stock.save(ifpath)
    result["files"] = {"MnSlChr.usd": os.path.getsize(mnpath), "IfAll.usd": os.path.getsize(ifpath)}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fighter", help="Ultimate internal fighter id (for example trail = Sora)")
    ap.add_argument("--files", required=True, help="mk_slot_files.py output files/ folder")
    ap.add_argument("--dst-k", type=int, required=True)
    ap.add_argument("--dst-e", type=int, required=True)
    ap.add_argument("--label", required=True, help="CSS icon name band")
    ap.add_argument("--ui-root", default=UI_ROOT)
    ap.add_argument("--iso", default=ISO_ACE)
    args = ap.parse_args()
    print(json.dumps(install(args.files, args.fighter, args.dst_k, args.dst_e,
                             args.label, args.ui_root, args.iso), indent=2))


if __name__ == "__main__":
    main()

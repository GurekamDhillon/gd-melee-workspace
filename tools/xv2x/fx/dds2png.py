"""Convert every .dds in a directory to a .png next to it (Pillow).

Usage (run with -I so no local module shadows Pillow):
    python -I dds2png.py <dir> [<dir> ...]

For each .dds (non-recursive) it prints the dimensions and the format read from
the DDS header (FourCC, and DXGI format when the FourCC is DX10), then writes
<name>.png beside it. Formats Pillow cannot decode are reported as FAIL with the
reason; the rest of the directory is still converted.
"""

import os
import struct
import sys

from PIL import Image

DXGI_NAMES = {
    71: "BC1_UNORM", 74: "BC2_UNORM", 77: "BC3_UNORM", 80: "BC4_UNORM",
    83: "BC5_UNORM", 98: "BC7_UNORM", 99: "BC7_UNORM_SRGB",
    28: "R8G8B8A8_UNORM", 87: "B8G8R8A8_UNORM", 61: "R8_UNORM",
}


def read_header(path):
    """Return (width, height, fourcc, dxgi, pixel_flags, rgb_bits) from a DDS file."""
    with open(path, "rb") as f:
        head = f.read(148)
    if len(head) < 128 or head[:4] != b"DDS ":
        raise ValueError("not a DDS file (bad magic)")
    height, width = struct.unpack_from("<II", head, 12)
    pf_flags, = struct.unpack_from("<I", head, 80)
    fourcc = head[84:88].decode("ascii", "replace")
    rgb_bits, = struct.unpack_from("<I", head, 88)
    dxgi = None
    if fourcc == "DX10" and len(head) >= 148:
        dxgi, = struct.unpack_from("<I", head, 128)
    return width, height, fourcc, dxgi, pf_flags, rgb_bits


def describe(fourcc, dxgi, pf_flags, rgb_bits):
    if fourcc == "DX10":
        return "DX10 DXGI=%s(%s)" % (dxgi, DXGI_NAMES.get(dxgi, "?"))
    if fourcc.strip("\x00 "):
        return "FourCC=%s" % fourcc
    if pf_flags & 0x40:
        return "uncompressed RGB %d-bit" % rgb_bits
    return "unknown (pf_flags=0x%x)" % pf_flags


def is_dds(path):
    """True for .dds by extension, or any file whose first bytes are the DDS magic
    (the EMB stores some textures under extensionless names such as DATA000)."""
    if path.lower().endswith(".dds"):
        return True
    if not os.path.isfile(path):
        return False
    with open(path, "rb") as f:
        return f.read(4) == b"DDS "


def convert_dir(d):
    names = sorted(n for n in os.listdir(d) if is_dds(os.path.join(d, n)))
    ok = fail = 0
    for n in names:
        src = os.path.join(d, n)
        dst = os.path.join(d, os.path.splitext(n)[0] + ".png")
        try:
            w, h, fourcc, dxgi, pf, bits = read_header(src)
            fmt = describe(fourcc, dxgi, pf, bits)
        except Exception as e:  # header unreadable
            print("FAIL  %s  header: %s" % (n, e))
            fail += 1
            continue
        try:
            with Image.open(src) as im:
                pil_mode = im.mode
                im.load()
                out = im.convert("RGBA")
                out.save(dst)
            print("OK    %s  %dx%d  %s  pillow_mode=%s -> %s" % (n, w, h, fmt, pil_mode, os.path.basename(dst)))
            ok += 1
        except Exception as e:
            print("FAIL  %s  %dx%d  %s  pillow: %s: %s" % (n, w, h, fmt, type(e).__name__, e))
            fail += 1
    print("dir %s: %d converted, %d failed, %d dds" % (d, ok, fail, len(names)))
    return ok, fail


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    total_fail = 0
    for d in argv:
        if not os.path.isdir(d):
            print("not a directory: %s" % d)
            total_fail += 1
            continue
        _, f = convert_dir(d)
        total_fail += f
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

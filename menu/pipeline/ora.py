"""Minimal OpenRaster (.ora) writer.

Krita, GIMP and Photopea all open these, and Photopea will re-save as .psd if
someone downstream needs one. Layers are trimmed to their bounding box and
given an offset, which keeps the file small without changing composition.
"""
import zipfile
from xml.sax.saxutils import quoteattr

from PIL import Image


def _png_bytes(img):
    import io
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def write_ora(path, size, layers, flat):
    """layers: list of (name, RGBA Image) in bottom-to-top order."""
    w, h = size
    entries = []          # (src, image, x, y, name)
    for i, (name, img) in enumerate(layers):
        bbox = img.getbbox()
        if bbox is None:  # fully transparent layer - keep a 1px stub
            sub, x, y = Image.new("RGBA", (1, 1), (0, 0, 0, 0)), 0, 0
        else:
            sub, x, y = img.crop(bbox), bbox[0], bbox[1]
        entries.append(("data/%02d_%s.png" % (i, name), sub, x, y, name))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<image version="0.0.3" w="%d" h="%d" xres="72" yres="72">' % (w, h),
           '  <stack>']
    for src, sub, x, y, name in reversed(entries):   # .ora stacks top-first
        xml.append('    <layer name=%s src=%s x="%d" y="%d" opacity="1.0" '
                   'visibility="visible" composite-op="svg:src-over"/>'
                   % (quoteattr(name), quoteattr(src), x, y))
    xml += ['  </stack>', '</image>']

    thumb = flat.copy()
    thumb.thumbnail((256, 256), Image.LANCZOS)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype must be first and stored uncompressed
        z.writestr(zipfile.ZipInfo("mimetype"), "image/openraster",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("stack.xml", "\n".join(xml))
        for src, sub, _x, _y, _n in entries:
            z.writestr(src, _png_bytes(sub))
        z.writestr("mergedimage.png", _png_bytes(flat))
        z.writestr("Thumbnails/thumbnail.png", _png_bytes(thumb))

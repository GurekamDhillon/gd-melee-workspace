#!/usr/bin/env python3
"""Build a SYNTHETIC Nucleus-style custom-stage package from the owner's own ACE disc, for tests.

    python tools/nucleus/make_synth_stage.py --iso "$GW_ISO_ACE" --out _build/nucleus-synth [--ext N] [--list]

Takes one m-ex ADDED stage of ACE (its GrXx.dat and its MxDt row) and writes what a MexManager stage export
holds: `stage.json` (the fields of a MexManager project's data/stages/NNN.json: name, fileName, soundBank,
reverb, collisionMaterials, mapDescPointer, onStageInit .. onUnknown4, unknownValue, playlist, assets), the
stage file renamed to a private name, and a generated icon.png. Packed as `<out>/synth-stage.zip`.

Two GD-only extension fields are added so the test needs no table lookup the real posts cannot give:
`gdLineType` (the vanilla stage whose line-type rows the stage uses) - the installer honours it when present.

DISC-DERIVED OUTPUT: it lives under the (git-ignored) --out folder and is never committed or uploaded.
Read-only on the disc. Attribution: consults m-ex's layout (tools/mex_port/mex_hsd.py), copies none of its code.
"""
import argparse, json, os, struct, sys, zlib, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mex_port"))
import mex_hsd as H  # noqa: E402


def png(w, h, rgb):
    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            row += bytes(rgb(x, y))
        rows.append(bytes(row))
    data = zlib.compress(b"".join(rows), 9)

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", data) + chunk(b"IEND", b"")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ext", type=int, default=0, help="external stage id (default: the first added stage whose file is on the disc)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    g = H.Gcm(a.iso)
    arc = H.Archive(g.read("MxDt.dat")).relocate(0)
    root = arc.public("mexData")
    meta = arc.u32(root)
    n_int = arc.s32(meta + 4 + 3 * 4)
    n_ext = arc.s32(meta + 4 + 4 * 4)
    amap = arc.u32(root + 0x28)
    ids = arc.u32(amap)
    audio = arc.u32(amap + 4)
    line = arc.u32(amap + 8)
    plist = arc.u32(amap + 0x14)
    desc = arc.u32(root + 0x2C)
    cands = []
    for ext in range(288, n_ext):
        k = arc.s32(ids + ext * 12)
        if k < 71 or k >= n_int:
            continue
        row = arc.u32(desc + k * 4)
        fn = arc.cstr(arc.u32(row + 8))
        if arc.s32(arc.u32(amap + 0x0C) + k * 8) != 0:
            continue  # a stage with custom items needs the item tables (not supported on a vanilla disc)
        if fn and fn.lstrip("/") in {p.split("/")[-1] for p in g.files}:
            cands.append((ext, k, fn))
    if a.list:
        for c in cands:
            print(c)
        return 0
    if a.ext:
        pick = [c for c in cands if c[0] == a.ext]
    else:
        pick = cands[:1]
    if not pick:
        print("no such added stage with a file on the disc", file=sys.stderr)
        return 1
    ext, k, fn = pick[0]
    row = arc.u32(desc + k * 4)
    w = [arc.u32(row + 4 * i) for i in range(13)]
    ssm, rv1, rv2 = arc.data[audio + 3 * k: audio + 3 * k + 3]
    want = arc.u32(line + k * 8 + 4)
    lt = -1
    for j in range(71):
        if arc.u32(line + j * 8 + 4) == want:
            lt = j
            break
    entries = []
    pcount = arc.s32(plist + k * 8)
    pptr = arc.u32(plist + k * 8 + 4)
    for i in range(max(0, min(pcount, 8))):
        entries.append({"musicID": arc.u16(pptr + 4 * i), "chance": arc.u16(pptr + 4 * i + 2)})
    stem = fn.lstrip("/").split(".")[0]
    newfile = "GrSynA.dat"
    name = "Synth " + stem
    js = {
        "name": name, "location": "", "seriesID": 11, "fileName": "/" + newfile, "additionalFiles": [],
        "soundBank": ssm, "reverbValue1": rv1, "reverbValue2": rv2, "collisionMaterials": want, "mapDescPointer": w[1],
        "onStageInit": w[3], "onStageLoad": w[5], "onStageGo": w[6], "onGo": w[4], "onUnknown2": w[7],
        "onTouchLine": w[8], "onUnknown4": w[9], "unknownValue": w[10], "movingCollisionPointer": 0, "movingCollisionCount": 0,
        "items": [], "mapGOBJs": [], "movingCollisions": [], "playlist": {"entries": entries}, "alternateStages": [],
        "assets": {"icon": "icon.png", "banner": None}, "gdLineType": lt,
    }
    os.makedirs(a.out, exist_ok=True)
    icon = png(64, 56, lambda x, y: (40 + x * 3 % 200, 90 + y * 2 % 150, 160 if (x // 8 + y // 8) % 2 else 60))
    zp = os.path.join(a.out, "synth-stage.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("stage.json", json.dumps(js, indent=2))
        z.writestr(newfile, g.read(fn.lstrip("/")))
        z.writestr("icon.png", icon)
    print("wrote", zp, "from ACE external %d internal %d %s (line-type row %d, bank %d, %d playlist entries)" % (ext, k, fn, lt, ssm, len(entries)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

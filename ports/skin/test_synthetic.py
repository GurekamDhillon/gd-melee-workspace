#!/usr/bin/env python3
"""End-to-end test on made-up data only (no game file is read):
costumebuild synth -> a 6-joint 'retail' costume; a made-up 9-bone source rig (extra twist/helper bones, different
proportions and an arm rotated 40 degrees) -> automap -> retarget -> costumebuild build -> inspect -> jointdiff -> checks.
Asserts: joint tree identical (jointdiff exit 0), DObj count/order kept, weights mapped and renormalised (<=4),
re-posed vertices land where the target skeleton puts them, CI8+palette texture kept CI8, oversize texture downscaled,
alpha-test material flagged, and a tampered costume makes jointdiff fail.
    python test_synthetic.py [workdir]
"""
import base64, json, math, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import skin


def mat(t, rz=0.0):
    c, s = math.cos(rz), math.sin(rz)
    m = np.array([[c, -s, 0, t[0]], [s, c, 0, t[1]], [0, 0, 1, t[2]], [0, 0, 0, 1.0]]); return m


def make_source():
    # name, parent, world position (source units are 2x the target), arm rotated
    B = [("TopN", None, (0, 0, 0)), ("HipN", "TopN", (0, 2, 0)), ("BustN", "HipN", (0, 4, 0)),
         ("LArmJ", "BustN", (1.5, 4.5, 0)), ("LArmTwist", "LArmJ", (2.0, 4.2, 0)), ("LHandN", "LArmJ", (2.5, 3.8, 0)),
         ("RArmJ", "BustN", (-1, 5, 0)), ("HeadN", "BustN", (0, 5.4, 0)), ("HairHelper", "HeadN", (0, 6.2, 0))]
    bones = [{"name": n, "parent": p, "bind": mat(t).reshape(-1).tolist(), "ibind": np.linalg.inv(mat(t)).reshape(-1).tolist()} for n, p, t in B]
    def fp(x, y, ws): return [x, y, 0, 0, 0, 1, x / 4, y / 8, 0, 0, 0, 0, 0, 0, ws]
    objs = [
        {"name": "body", "material": "skin", "visbone": "TopN",
         "tris": [fp(0, 2, [["HipN", 1.0]]), fp(0.5, 2, [["HipN", 0.6], ["BustN", 0.4]]), fp(0, 4, [["BustN", 1.0]])]},
        {"name": "arm", "material": "cut", "visbone": "TopN",
         "tris": [fp(1.5, 4.5, [["LArmJ", 0.4], ["LArmTwist", 0.3], ["LHandN", 0.1], ["BustN", 0.1], ["HeadN", 0.1]]),
                  fp(2.5, 3.8, [["LHandN", 1.0]]), fp(2.0, 4.2, [["LArmTwist", 1.0]])]},
        {"name": "hair", "material": "skin", "visbone": "TopN",
         "tris": [fp(0, 6.2, [["HairHelper", 1.0]]), fp(0.2, 6.2, [["HairHelper", 1.0]]), fp(0, 5.4, [["HeadN", 1.0]])]}]
    pal = bytes(range(256)) * 2
    ci8 = bytes((i * 13) & 255 for i in range(16 * 16))
    big = bytes(512 * 512 * 2)                                   # RGB565 512x512 -> must be downscaled to 256
    tex = [{"name": "t_ci8", "fmt": "CI8", "w": 16, "h": 16, "data": base64.b64encode(ci8).decode(),
            "palette": base64.b64encode(pal).decode(), "palette_fmt": "RGB5A3"},
           {"name": "t_big", "fmt": "RGB565", "w": 512, "h": 512, "data": base64.b64encode(big).decode()}]
    mats = [{"name": "skin", "refs": [{"texture": "t_big", "map": "TexCoord"}]},
            {"name": "cut", "alpha_test": True, "refs": [{"texture": "t_ci8", "map": "TexCoord"}]}]
    return {"model": "synthetic", "bones": bones, "objects": objs, "materials": mats, "textures": tex}


def main(work):
    os.makedirs(work, exist_ok=True); cb = skin.CB
    retail = os.path.join(work, "synth_retail.dat")
    subprocess.run([cb, "synth", retail], check=True)
    src = os.path.join(work, "source.json"); json.dump(make_source(), open(src, "w"))
    # the synthetic retail joints are unnamed in the file (no PlCo): name them by a tiny map file
    groups = {"dobjs": {"0": {"objects": ["body"]}, "1": {"objects": ["arm"]}, "2": {"objects": ["hair"]}}}
    gp = os.path.join(work, "groups.json"); json.dump(groups, open(gp, "w"))
    tgt = skin.read_target(retail)
    names = ["TopN", "HipN", "BustN", "LArmJ", "RArmJ", "HeadN"]
    for j, n in zip(tgt["joints"], names): j["name"] = n
    s = skin.load_source(src)
    mp = skin.automap(s, tgt)
    m = {k: v["target"] for k, v in mp["source_to_target"].items()}
    print("map:", {k: (v["target"], v["confidence"], v["rule"]) for k, v in mp["source_to_target"].items()})
    assert m["LArmTwist"] == "LArmJ" and m["HairHelper"] == "HeadN" and m["HipN"] == "HipN", m
    assert 0.4 < mp["scale"] < 0.5, mp["scale"]          # height ratio 2.7 / 6.2
    sk = skin.retarget(s, tgt, mp, groups)
    json.dump(sk, open(os.path.join(work, "skin.json"), "w"))
    # weights: <=4, sum 1, five source bones collapse to LArmJ/BustN/HeadN
    for d in sk["dobjs"]:
        for t in d["tris"]:
            for v in t["tris"] if False else t:
                assert len(v["w"]) <= 4 and abs(sum(w for _, w in v["w"]) - 1) < 1e-6, v
    # re-pose: the hip vertex (single-bound to HipN) lies at the target HipN origin -> joint-local (0,0,0)
    hipv = sk["dobjs"][0]["tris"][0][0]; assert np.allclose(hipv["p"], [0, 0, 0], atol=1e-4), hipv
    # the hand vertex goes to the target LArmJ's child direction (arm rotated): world position = target LArmJ + R*(d*0.5)
    out = os.path.join(work, "synth_skin.dat")
    subprocess.run([cb, "build", retail, os.path.join(work, "skin.json"), out, os.path.join(work, "report.json")], check=True)
    rep = json.load(open(os.path.join(work, "report.json")))
    fm = {t["name"]: t for t in rep["textures"]}
    assert fm["t_ci8"]["fmt"] == "CI8" and fm["t_big"]["w"] == 256 and fm["t_big"]["fmt"] == "CMP", fm
    for f in (retail, out): subprocess.run([cb, "inspect", f, f + ".inspect.json"], check=True)
    ir, io = json.load(open(retail + ".inspect.json")), json.load(open(out + ".inspect.json"))
    assert len(io["dobjs"]) == 3 and [d["joint"] for d in io["dobjs"]] == [d["joint"] for d in ir["dobjs"]]
    assert io["dobjs"][1]["alpha_test"] and not io["dobjs"][0]["alpha_test"]
    # skinned positions read back from the written file: single-bound verts in joint space -> world via target bind
    W = [np.array(j["world"]) for j in tgt["joints"]]
    v0 = io["dobjs"][0]["verts"]; ws = [W[w[0][0]] @ np.array(v["p"] + [1]) for v in v0 for w in [v["w"]] if len(w) == 1]
    assert any(np.allclose(p[:3], tgt["joints"][1]["pos"], atol=1e-3) for p in ws), ws
    r = subprocess.run([sys.executable, os.path.join(HERE, "jointdiff.py"), retail, out], capture_output=True, text=True)
    print(r.stdout.strip()); assert r.returncode == 0
    # tamper: flip one byte of a joint translation -> jointdiff must fail
    import mex_hsd
    raw = bytearray(open(out, "rb").read()); ar = mex_hsd.Archive(bytes(raw))
    root = ar.public([p for p, _ in ar.publics if p.endswith("_Share_joint")][0]); child = ar.u32(root + 8)
    raw[0x20 + child + 0x2C + 3] ^= 1
    bad = out + ".tampered.dat"; open(bad, "wb").write(raw)
    r = subprocess.run([sys.executable, os.path.join(HERE, "jointdiff.py"), retail, bad], capture_output=True, text=True)
    print(r.stdout.strip()); assert r.returncode == 1 and "trans" in r.stdout
    ck = skin.checks(rep, ir, io, 0, sk["stats"])
    for x in ck["checks"]: print("%s %-34s %s" % ("PASS" if x["pass"] else "FAIL", x["check"], x["detail"]))
    assert ck["netplay_safe"]
    print("ALL SYNTHETIC TESTS PASS")


def _main():
    w = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "skin_synth")
    main(w); test_community(w); test_autogroups(w); print('front demo tree:', build_front_demo(w))


def test_community(work):
    """Community-skin path on made-up files: .pcs (LZ77) container, a heavy mesh for the reduction path, a broken file,
    detection by bone names, and batch mode with source hashes in report.csv."""
    import csv, shutil, argparse
    retail = os.path.join(work, "synth_retail.dat"); ind = os.path.join(work, "skins"); outd = os.path.join(work, "costumes")
    shutil.rmtree(ind, ignore_errors=True); shutil.rmtree(outd, ignore_errors=True); os.makedirs(ind)
    s = make_source()
    # heavy: subdivide the body into ~6000 triangles on a grid (weights blend HipN/BustN by height)
    fps = []
    N = 55
    for i in range(N):
        for k in range(N):
            def v(a, b):
                x, y = 0.6 * a / N, 2 + 2 * b / N; t = b / N
                return [x, y, 0.1 * math.sin(a), 0, 0, 1, a / N, b / N, 0, 0, 0, 0, 0, 0, [["HipN", 1 - t], ["BustN", t]] if 0 < t < 1 else [["HipN" if t == 0 else "BustN", 1.0]]]
            fps += [v(i, k), v(i + 1, k), v(i, k + 1), v(i + 1, k), v(i + 1, k + 1), v(i, k + 1)]
    s["objects"][0]["tris"] = fps
    raw = json.dumps(s).encode()
    open(os.path.join(ind, "heavy.pcs"), "wb").write(skin.lz77_compress(raw))           # compressed container
    open(os.path.join(ind, "plain.json"), "w").write(json.dumps(make_source()))
    open(os.path.join(ind, "broken.pcs"), "wb").write(skin.lz77_compress(raw)[:500])   # truncated
    # the synthetic retail has unnamed joints (J0..): give the template + groups in target names
    names = ["J0", "J1", "J2", "J3", "J4", "J5"]
    m = {"TopN": "J0", "HipN": "J1", "BustN": "J2", "LArmJ": "J3", "LArmTwist": "J3", "LHandN": "J3", "RArmJ": "J4", "HeadN": "J5", "HairHelper": "J5"}
    mp = os.path.join(work, "synthmap.json"); json.dump({"source_to_target": m}, open(mp, "w"))
    gp = os.path.join(work, "groups.json")
    # detection: a template with these bone names wins
    tdir = os.path.join(HERE, "maps", "_synthtest.bones.json"); json.dump({"source_character": "synthtest", "source_bones": list(m), "source_to_target": m}, open(tdir, "w"))
    try:
        det = skin.detect(skin.export_source(os.path.join(ind, "plain.json"), os.path.join(work, "d")))
        assert det[0][1] == "_synthtest" and det[0][0] >= 1.0, det[:2]
        try:
            skin.export_source(os.path.join(ind, "broken.pcs"), os.path.join(work, "b")); assert False, "broken file accepted"
        except skin.SourceError as e:
            print("broken file -> SourceError:", e)
        a = argparse.Namespace(in_dir=ind, out_dir=outd, fighter="luigi", retail=retail, groups=gp, plco=None, map=mp, scale=None,
                               repose="aim", source_costume="00", install=None, slot=None, tri_budget=200)
        skin.LIMITS["file_growth"] = 1e9          # the 2 KB synthetic 'retail' makes the size limit meaningless here
        skin.batch(a)
        rows = list(csv.DictReader(open(os.path.join(outd, "report.csv"))))
        print(rows)
        r = {x["source"]: x for x in rows}
        assert r["broken.pcs"]["result"] == "unreadable source"
        assert r["heavy.pcs"]["result"] == "ok" and r["plain.json"]["result"] == "ok", r
        assert all(len(x["sha256"]) == 64 for x in rows)
        ck = json.load(open(os.path.join(outd, "PlLg_heavy_work", "checks.json")))
        assert ck["netplay_safe"] and any("->" in st for st in ck["steps"]), ck["steps"]
        io = json.load(open(os.path.join(outd, "PlLg_heavy_work", "inspect_out.json")))
        assert io["tris"] <= 260, io["tris"]           # 200 budget (+ the untouched DObjs)
        print("reduction:", [x for x in ck["steps"] if "->" in x])
    finally:
        os.remove(tdir); skin.LIMITS["file_growth"] = 1.6
    print("COMMUNITY-SKIN TESTS PASS")



def write_hsd(data, relocs, roots):
    """Tiny HSD archive writer (synthetic tests only). data: bytes; relocs: offsets holding pointers; roots: {name: off}."""
    import struct
    strs = b""; rt = b""
    for n, off in roots.items():
        rt += struct.pack(">II", off, len(strs)); strs += n.encode() + b"\0"
    body = data + b"".join(struct.pack(">I", r) for r in relocs) + rt + strs
    return struct.pack(">IIIII", 0x20 + len(body), len(data), len(relocs), len(roots), 0) + b"\0" * 12 + body


def synth_fighter_dat(path, hi, low, eyes):
    """ftDataSynth with x8: one model, table 0 = [hi], table 1 = [low], eye texanim list = eyes."""
    import struct
    D = bytearray(0x200); R = []
    def p32(o, v): D[o:o + 4] = struct.pack(">I", v)
    def ptr(o, v): p32(o, v); R.append(o)
    ptr(0x8, 0x40)                            # ftData.x8
    p32(0x40, 1); ptr(0x44, 0x60); p32(0x48, len(eyes)); ptr(0x4C, 0x1C0)   # model_num, vis_table, eye count, eye rows
    for k, lst in enumerate((hi, low)):
        base = 0x80 + k * 0x40
        ptr(0x60 + 4 * k, base)               # vis_table[costume 0][k] -> lookup list (1 model)
        p32(base, 1); ptr(base + 4, base + 0x10)          # model 0: 1 group -> TempS
        p32(base + 0x10, len(lst)); ptr(base + 0x14, base + 0x20)
        D[base + 0x20:base + 0x20 + len(lst)] = bytes(lst)
    ptr(0x1C0, 0x1D0)
    for i, e in enumerate(eyes): D[0x1D0 + 2 * i:0x1D2 + 2 * i] = struct.pack(">H", e)
    open(path, "wb").write(write_hsd(bytes(D), R, {"ftDataSynth": 0}))


def test_autogroups(work):
    import autogroups
    retail = os.path.join(work, "synth_retail.dat"); fd = os.path.join(work, "PlSynth.dat")
    synth_fighter_dat(fd, hi=[0, 1], low=[], eyes=[2])
    vis = autogroups.read_vis(fd); assert vis["tables"][0] == [[[0, 1]]] and vis["eye_dobjs"] == [2], vis
    src = make_source(); src["objects"].append({"name": "eyeball", "material": "eyemat", "visbone": "TopN",
        "tris": [[0, 5.5, 0.1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, [["HeadN", 1.0]]], [0.1, 5.5, 0.1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, [["HeadN", 1.0]]], [0, 5.6, 0.1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, [["HeadN", 1.0]]]]})
    src["materials"].append({"name": "eyemat", "refs": [{"texture": "t_ci8", "map": "TexCoord"}]})
    sp = os.path.join(work, "source_eye.json"); json.dump(src, open(sp, "w"))
    g = autogroups.make_groups(sp, retail, fd, None)
    print(json.dumps(g["_auto"]["why"], indent=0)); print(g["_auto"]["notes"])
    d = g["dobjs"]
    assert d["2"] == "blank" and any("eyeball" in d[k]["objects"] for k in ("0", "1") if isinstance(d[k], dict)), d   # static eyes, animated slot blanked
    filled = [k for k in ("0", "1") if isinstance(d[k], dict)]
    assert filled, d
    assert set(sum((d[k]["objects"] for k in filled), [])) == {"body", "arm", "hair", "eyeball"}, d
    # end to end through skin.py build without --groups
    out = os.path.join(work, "synth_auto.dat")
    import argparse
    skin.LIMITS["file_growth"] = 1e9
    try:
        rc = skin.build(argparse.Namespace(source=sp, fighter="luigi", retail=retail, groups=None, fighter_dat=fd, out=out, plco=None,
                                           map=None, work=None, scale=None, repose="aim", source_costume="00", install=None, name=None, slot=None, tri_budget=50))
    finally:
        skin.LIMITS["file_growth"] = 1.6
    assert rc == 0, rc
    print("AUTOGROUPS TESTS PASS")



def build_front_demo(work):
    """A synthetic 'unpacked Brawl' tree + pre-fetched synthetic Melee files for the front door demo."""
    import shutil
    t = os.path.join(work, "front"); shutil.rmtree(t, ignore_errors=True)
    fd = os.path.join(t, "brawltree", "pf", "fighter", "synthy"); os.makedirs(fd)
    open(os.path.join(fd, "FitSynthy00.pcs"), "wb").write(skin.lz77_compress(json.dumps(make_source()).encode()))
    open(os.path.join(fd, "FitSynthy01.pcs"), "wb").write(b"\x10broken")
    md = os.path.join(t, "front-work", "melee", "luigi"); os.makedirs(md)
    shutil.copy(os.path.join(work, "synth_retail.dat"), os.path.join(md, "PlLgNr.dat"))
    shutil.copy(os.path.join(work, "PlSynth.dat"), os.path.join(md, "PlLg.dat"))
    return t


if __name__ == "__main__":
    _main()

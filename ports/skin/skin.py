#!/usr/bin/env python3
"""Skin a source fighter model onto a retail Melee costume's skeleton (CLI core; the UI only drives this).

The output costume keeps the retail joint tree untouched (count, order, hierarchy, flags, SRT, inverse binds) and the
retail DObj count/order; only meshes, skin weights and TObj images change. So hurtboxes, ECB, hitbox and item
attachment, and everything else the simulation reads from the costume stay identical (see AUDIT_costume_reads.md).

    skin.py target   <retail_costume.dat> [--fighter luigi --plco PlCo.dat] -o target.json
    skin.py automap  <source.json> <target.json> [--map start.json] -o map.json
    skin.py retarget <source.json> <target.json> <map.json> <groups.json> -o skin.json [--scale S] [--repose aim|rigid|none]
    skin.py build    --source <Brawl fighter folder | .pac | source.json> --fighter luigi --retail <PlLgNr.dat>
                     --groups <groups.json> [--map map.json] --out <PlLgXx.dat> [--install MODS_DIR --name "Skin name"]
    skin.py fetch    --fighter luigi --costume Nr --out DIR       (copies PlCo.dat and the costume from GW_ISO_VANILLA)

source.json is the model_export.exe JSON (bones: name/parent/bind/ibind 4x4 row-major world/inverse-world;
objects: name/material/visbone/tris = flat facepoints [px,py,pz, nx,ny,nz, u,v, ..., [ [bone,w], ... ] at 14];
materials; textures with base64 GX data). Nothing here embeds or ships game data.
"""
import argparse, base64, json, math, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
sys.path.insert(0, os.path.join(ROOT, "ports", "ir", "tools"))
CB = os.path.join(HERE, "costumebuild", "bin", "Release", "net8.0", "costumebuild.exe")
MODEL_EXPORT = os.path.join(ROOT, "experiment", "brawl-kirby", "tools", "model", "model_export.exe")

# console limits used by the checks (GameCube / stock m-ex; see README "Limits")
LIMITS = {"max_influences": 4, "max_texture": 256, "file_growth": 1.6, "tri_growth": 1.6}
if os.environ.get("SKIN_FILE_GROWTH"): LIMITS["file_growth"] = float(os.environ["SKIN_FILE_GROWTH"])   # tests only


# ---------------------------------------------------------------- target (retail costume) -----------------------------
def _f32s(ar, off, n):
    import struct
    return list(struct.unpack(">%df" % n, bytes(ar.data[off:off + 4 * n])))


def _ptr(ar, off):
    return ar.u32(off) if off in ar.reloc_set else None


def euler_mat(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def read_target(path, fighter=None, plco=None):
    """Joint tree (depth-first, the figatree/part order), DObjs in global order, names from PlCo's joint_to_part."""
    import mex_hsd
    raw = open(path, "rb").read(); ar = mex_hsd.Archive(raw)
    pub = [s for s, _ in ar.publics if s.endswith("_Share_joint")]
    if not pub: raise SystemExit("%s: no *_Share_joint public (not a fighter costume)" % path)
    joints, dobjs = [], []

    def walk(off, parent):
        while off is not None:
            flags = ar.u32(off + 4); inv = _ptr(ar, off + 0x38)
            j = {"index": len(joints), "parent": parent, "flags": flags, "rot": _f32s(ar, off + 0x14, 3),
                 "scale": _f32s(ar, off + 0x20, 3), "trans": _f32s(ar, off + 0x2C, 3),
                 "ibm": _f32s(ar, inv, 12) if inv is not None else None}
            joints.append(j)
            d = _ptr(ar, off + 0x10)
            if d is not None and not flags & ((1 << 5) | (1 << 14)):
                while d is not None:
                    mo = _ptr(ar, d + 8); ntex = 0
                    t = _ptr(ar, mo + 8) if mo is not None else None
                    while t is not None: ntex += 1; t = _ptr(ar, t + 4)
                    dobjs.append({"index": len(dobjs), "joint": j["index"], "tobjs": ntex})
                    d = _ptr(ar, d + 4)
            c = _ptr(ar, off + 8)
            if c is not None and not flags & (1 << 12): walk(c, j["index"])
            off = _ptr(ar, off + 0xC)

    walk(ar.public(pub[0]), None)
    # bind world matrices: FK of SRT (HSD: T * R(zyx) * S); joints with an IBM use its inverse
    W = []
    for j in joints:
        L = np.eye(4); L[:3, :3] = euler_mat(j["rot"]) @ np.diag(j["scale"]); L[:3, 3] = j["trans"]
        W.append(L if j["parent"] is None else W[j["parent"]] @ L)
    for j, w in zip(joints, W):
        if j["ibm"]:
            m = np.eye(4); m[:3, :] = np.array(j["ibm"]).reshape(3, 4); w = np.linalg.inv(m)
        j["world"] = w.tolist(); j["pos"] = w[:3, 3].tolist()
    names = name_joints(joints, fighter, plco)
    for j, n in zip(joints, names): j["name"] = n
    return {"file": os.path.basename(path), "fighter": fighter, "publics": [s for s, _ in ar.publics],
            "joints": joints, "dobjs": dobjs, "bytes": len(raw)}


def name_joints(joints, fighter, plco):
    """Common joint names via PlCo's joint_to_part table (build_melee_fighter's COMMON list); others ExtraN<i>."""
    if not (fighter and plco):
        return ["J%d" % j["index"] for j in joints]
    import mex_hsd, build_melee_fighter as B
    kind = B.FIGHTERS[fighter][0]
    co = mex_hsd.Archive(open(plco, "rb").read())
    r = co.public("ftLoadCommonData")
    table = co.u32(co.u32(r + 16) + 4 * kind)
    j2p, count = co.u32(table), co.u32(table + 8)
    joint_to_part = list(co.data[j2p:j2p + count])
    holes = set(); entry = _ptr(co, co.u32(r + 20) + 4 * kind)
    if entry is not None:
        arr, n = co.u32(entry), co.u32(entry + 4); holes = {co.data[arr + 4 * i] for i in range(n)}
    out, part = [], 0
    for j in joints:
        while part in holes: part += 1
        c = joint_to_part[part] if part < len(joint_to_part) else 255
        out.append(B.COMMON[c] if c < len(B.COMMON) else "ExtraN%d" % j["index"])
        part += 1
    return out


# ---------------------------------------------------------------- source ------------------------------------------------
def load_source(path):
    s = json.load(open(path))
    for b in s["bones"]:
        m = np.array(b["bind"], float).reshape(4, 4)
        if not np.allclose(m[3], [0, 0, 0, 1]): m = m.T      # column-major export
        b["world"] = m; b["pos"] = m[:3, 3]
    return s


# ---------------------------------------------------------------- auto-mapper -------------------------------------------
SYN = {"bust": "chest", "spine": "chest", "chest": "chest", "waist": "waist", "hip": "hip", "pelvis": "hip",
       "neck": "neck", "head": "head", "shoulder": "shoulder", "clavicle": "clavicle", "arm": "arm", "elbow": "arm",
       "forearm": "arm", "hand": "hand", "wrist": "hand", "leg": "leg", "thigh": "leg", "knee": "knee", "shin": "knee",
       "calf": "knee", "foot": "foot", "ankle": "foot", "toe": "toe", "have": "have", "throw": "throw", "trans": "trans",
       "top": "top", "xrot": "xrot", "yrot": "yrot", "thumb": "thumb", "1st": "f1", "2nd": "f2", "3rd": "f3", "4th": "f4"}


def norm(name):
    """-> (side, key, seg): side 'L'/'R'/'', key a synonym class, seg 'a'/'b'/''."""
    n = name
    side = ""
    m = re.match(r"^([LR])(?=[A-Z0-9])", n) or re.search(r"[_.]([LR])$", n)
    if m: side = m.group(1); n = n[1:] if m.start() == 0 else n[:m.start()]
    seg = ""
    m = re.search(r"N([ab])$", n)
    if m: seg = m.group(1)
    base = re.sub(r"(JA|J|N[ab]?|M[ab]?|E)$", "", n).lower()
    for k, v in SYN.items():
        if base == k or base.startswith(k):
            return side, v + ("_ja" if name.endswith("JA") else ""), seg
    return side, base, seg


def automap(src, tgt, start=None):
    """Every source bone -> a target joint name, with confidence 0..1 and the rule used. start (bone->name) wins."""
    T = tgt["joints"]; tn = {j["name"]: j for j in T}
    # scale: hip-to-head height ratio (falls back to bbox height)
    def height(ps): ps = np.array(ps); return max(1e-6, ps[:, 1].max() - ps[:, 1].min())
    k = height([j["pos"] for j in T]) / height([b["pos"] for b in src["bones"]])
    tkeys = {}
    for j in T:
        if not j["name"].startswith("ExtraN"): tkeys.setdefault(norm(j["name"]), j["name"])
    out = {}; byname = {b["name"]: b for b in src["bones"]}
    for b in src["bones"]:
        if start and b["name"] in start:
            out[b["name"]] = {"target": start[b["name"]], "confidence": 1.0, "rule": "map file"}; continue
        if b["name"] in tn and not b["name"].endswith("JA"):
            out[b["name"]] = {"target": b["name"], "confidence": 1.0, "rule": "same name"}; continue
        key = norm(b["name"])
        if key in tkeys:
            out[b["name"]] = {"target": tkeys[key], "confidence": 0.85, "rule": "synonym"}; continue
        if (key[0], key[1], "") in tkeys:
            out[b["name"]] = {"target": tkeys[(key[0], key[1], "")], "confidence": 0.7, "rule": "synonym (segment)"}; continue
        out[b["name"]] = None
    # unresolved: nearest target joint (scaled position) among descendants of the parent's target, else parent's target
    def tdesc(name):
        i = tn[name]["index"]; res = {i}
        for j in T:
            if j["parent"] in res: res.add(j["index"])
        return res
    for b in src["bones"]:
        if out[b["name"]] is not None: continue
        p = b["parent"]
        while p and out.get(p) is None: p = byname[p]["parent"] if p in byname else None
        cand = tdesc(out[p]["target"]) if p and out.get(p) else set(range(len(T)))
        pos = np.array(b["pos"]) * k
        best = min(cand, key=lambda i: np.linalg.norm(np.array(T[i]["pos"]) - pos))
        d = np.linalg.norm(np.array(T[best]["pos"]) - pos) / height([j["pos"] for j in T])
        out[b["name"]] = {"target": T[best]["name"], "confidence": float(round(max(0.2, 0.6 - d * 2), 2)), "rule": "nearest joint"}
    return {"source_to_target": out, "scale": k}


# ---------------------------------------------------------------- retarget ----------------------------------------------
def _rot_between(a, b):
    a = a / (np.linalg.norm(a) or 1); b = b / (np.linalg.norm(b) or 1)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.999999:
        ax = np.cross(a, [1, 0, 0]);  ax = ax if np.linalg.norm(ax) > 1e-6 else np.cross(a, [0, 1, 0])
        ax /= np.linalg.norm(ax); return 2 * np.outer(ax, ax) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


def bone_transforms(src, tgt, bmap, scale, mode, inherit=()):
    """Per source bone a 4x4 that moves a bind-space source point into the target bind pose."""
    T = {j["name"]: j for j in tgt["joints"]}
    kids = {}
    for j in tgt["joints"]:
        if j["parent"] is not None: kids.setdefault(j["parent"], []).append(j)
    skids = {}
    for b in src["bones"]: skids.setdefault(b["parent"], []).append(b)
    S = np.diag([scale, scale, scale, 1.0])
    M = {}
    SB = {b["name"]: b for b in src["bones"]}
    def folded(b):
        """The nearest ancestor mapped to the same target joint: a helper bone folded into it (HatN, MouthN, toes) must
        ride with that ancestor; re-posing its own origin onto the joint would collapse it (the cap fell into the face)."""
        p = SB.get(b["parent"])
        while p is not None:
            if bmap[p["name"]]["target"] == bmap[b["name"]]["target"]: return p["name"]
            p = SB.get(p["parent"])
        return None
    order, seen = [], set()
    def visit(b):
        if b["name"] in seen: return
        if b["parent"] in SB: visit(SB[b["parent"]])
        seen.add(b["name"]); order.append(b)
    for b in src["bones"]: visit(b)
    for b in order:
        t = T[bmap[b["name"]]["target"]]
        if mode == "none": M[b["name"]] = S; continue
        f = folded(b)
        if f is not None: M[b["name"]] = M[f]; continue
        # opt-in (groups "repose_inherit"): ride with the parent instead of moving this bone's origin onto its joint.
        # Brawl's ankle sits 1.3 above the sole, Melee's 0.25: aiming the foot onto LFootJ sank the shoes into the floor.
        if b["name"] in inherit and b["parent"] in M: M[b["name"]] = M[b["parent"]]; continue
        if mode == "rigid":
            M[b["name"]] = np.array(t["world"]) @ np.linalg.inv(S @ b["world"]) @ S; continue
        # aim: rotate the bone's direction (to its first child mapped elsewhere) onto the target joint's direction
        sp, tp = np.array(b["pos"]) * scale, np.array(t["pos"])
        R = np.eye(3)
        sc = [c for c in skids.get(b["name"], []) if bmap[c["name"]]["target"] != t["name"]]
        tc = [c for c in kids.get(t["index"], [])]
        if sc and tc:
            c = sc[0]; ct = T[bmap[c["name"]]["target"]]
            sd = np.array(c["pos"]) * scale - sp; td = np.array(ct["pos"]) - tp
            if np.linalg.norm(sd) > 1e-6 and np.linalg.norm(td) > 1e-6: R = _rot_between(sd, td)
        A = np.eye(4); A[:3, :3] = R; A[:3, 3] = tp - R @ sp
        M[b["name"]] = A @ S
    return M


def retarget(src, tgt, mp, groups, scale=None, mode="aim", max_infl=LIMITS["max_influences"]):
    bmap = mp["source_to_target"]; scale = scale or mp.get("scale", 1.0)
    tidx = {j["name"]: j["index"] for j in tgt["joints"]}
    tj = tgt["joints"]
    M = bone_transforms(src, tgt, bmap, scale, mode, groups.get("repose_inherit", ()))
    objs = {o["name"]: o for o in src["objects"]}
    mats = {m["name"]: m for m in src.get("materials", [])}
    stats = {"tris": 0, "verts": 0, "trimmed": 0, "max_dropped": 0.0, "max_in": 0}
    out, used_tex = [], set()
    for di_s, g in sorted(groups["dobjs"].items(), key=lambda x: int(x[0])):
        di = int(di_s)
        if isinstance(g, str): g = {"mode": g}
        if g.get("mode") == "keep": out.append({"dobj": di, "mode": "keep"}); continue
        if g.get("mode") == "blank": out.append({"dobj": di, "mode": "blank"}); continue
        tris = []
        for on in g["objects"]:
            fps = objs[on]["tris"]
            for t in range(0, len(fps) - 2, 3):
                tri = []
                for fp in fps[t:t + 3]:
                    acc = {}
                    for bn, w in fp[14]:
                        acc[tidx[bmap[bn]["target"]]] = acc.get(tidx[bmap[bn]["target"]], 0) + w
                    lst = sorted(acc.items(), key=lambda x: -x[1]); stats["max_in"] = max(stats["max_in"], len(lst))
                    if len(lst) > max_infl:
                        stats["trimmed"] += 1; stats["max_dropped"] = max(stats["max_dropped"], sum(w for _, w in lst[max_infl:]))
                        lst = lst[:max_infl]
                    s = sum(w for _, w in lst) or 1
                    lst = [(j, round(w / s, 2)) for j, w in lst]; lst = [(j, w) for j, w in lst if w > 0]
                    lst[0] = (lst[0][0], round(1 - sum(w for _, w in lst[1:]), 2))
                    # re-pose: blend of the per-bone transforms with the source weights
                    p = np.array(fp[0:3] + [1.0]); n = np.array(fp[3:6])
                    tot = sum(w for _, w in fp[14]) or 1
                    P = sum((w / tot) * (M[bn] @ p) for bn, w in fp[14])[:3]
                    N = sum((w / tot) * (M[bn][:3, :3] @ n) for bn, w in fp[14])
                    N = N / (np.linalg.norm(N) or 1)
                    if len(lst) == 1 and tj[lst[0][0]]["ibm"]:          # HSD: single-bound verts are joint-local
                        I = np.array(tj[lst[0][0]]["ibm"]).reshape(3, 4)
                        P = I[:, :3] @ P + I[:, 3]; N = I[:, :3] @ N; N = N / (np.linalg.norm(N) or 1)
                    uvs = [fp[6:8]] + ([fp[8:10]] if len(fp) > 9 and isinstance(fp[8], (int, float)) and g.get("uv_sets", 1) > 1 else [])
                    tri.append({"p": [round(float(x), 6) for x in P], "n": [round(float(x), 5) for x in N], "uvs": uvs,
                                "w": [[int(j), w] for j, w in lst]})
                    stats["verts"] += 1
                tris.append(tri)
        stats["tris"] += len(tris)
        tex = g.get("textures")
        if tex is None:
            m = mats.get(objs[g["objects"][0]]["material"], {})
            tex = [r["texture"] for r in m.get("refs", []) if r.get("map", "TexCoord") == "TexCoord"][:1]
        used_tex.update(t for t in tex if t)
        alpha = g.get("alpha_test")
        if alpha is None:
            alpha = any(mats.get(objs[o]["material"], {}).get("alpha_test", False) for o in g["objects"])
        # each replaced image keeps the source material's wrap: retail TObjs are CLAMP and Brawl UVs run -1..1 (Repeat)
        refs = {r["texture"]: r for o in g["objects"] for r in mats.get(objs[o]["material"], {}).get("refs", [])}
        wm = {"Repeat": "repeat", "Clamp": "clamp", "Mirror": "mirror", "MirroredRepeat": "mirror"}
        wraps = [[wm.get(refs[t].get("u"), "repeat"), wm.get(refs[t].get("v"), "repeat")] if t in refs else (["repeat", "repeat"] if t else None) for t in tex]
        out.append({"dobj": di, "mode": "replace", "objects": g["objects"], "textures": tex, "wraps": g.get("wraps", wraps), "alpha_test": bool(alpha),
                    "cull": g.get("cull", "back"), "tris": tris})
    texs = [t for t in src.get("textures", []) if t["name"] in used_tex]
    missing = used_tex - {t["name"] for t in texs}
    if missing: raise SystemExit("textures not in the source: %s" % sorted(missing))
    return {"retail_joints": len(tj), "retail_dobjs": len(tgt["dobjs"]), "max_texture": groups.get("max_texture", LIMITS["max_texture"]),
            "textures": texs, "dobjs": out, "stats": stats}


# ---------------------------------------------------------------- checks & report ---------------------------------------
def checks(report, inspect_retail, inspect_out, diff_rc, stats, max_infl=LIMITS["max_influences"], tri_budget=None):
    c = []
    def add(name, ok, detail): c.append({"check": name, "pass": bool(ok), "detail": detail})
    add("skeleton identical to retail", diff_rc == 0, "jointdiff.py exit %d" % diff_rc)
    add("object groups preserved", len(inspect_out["dobjs"]) == len(inspect_retail["dobjs"])
        and all(a["joint"] == b["joint"] for a, b in zip(inspect_out["dobjs"], inspect_retail["dobjs"])),
        "%d DObjs (retail %d)" % (len(inspect_out["dobjs"]), len(inspect_retail["dobjs"])))
    add("bone influences <= %d" % max_infl, stats["max_dropped"] <= 0.25,
        "max %d in source, %d verts trimmed, max weight dropped %.2f" % (stats["max_in"], stats["trimmed"], stats["max_dropped"]))
    tr, to = inspect_retail["tris"], inspect_out["tris"]
    lim = tri_budget or tr * LIMITS["tri_growth"]
    add("triangles", to <= max(lim, 1), "%d (retail %d, budget %d)" % (to, tr, lim))
    bad = [t for t in inspect_out["textures"] if t["w"] > LIMITS["max_texture"] or t["h"] > LIMITS["max_texture"]
           or t["fmt"] not in ("I4", "I8", "IA4", "IA8", "RGB565", "RGB5A3", "RGBA8", "CI4", "CI8", "CMP")]
    add("textures native GX, <= %dpx" % LIMITS["max_texture"], not bad, "%d textures, bad: %s" % (len(inspect_out["textures"]), bad))
    rb, ob = inspect_retail["bytes"], inspect_out["bytes"]
    add("file size", ob <= rb * LIMITS["file_growth"], "%d bytes (retail %d, limit x%.1f)" % (ob, rb, LIMITS["file_growth"]))
    netplay = all(x["pass"] for x in c if x["check"] in ("skeleton identical to retail", "object groups preserved"))
    return {"checks": c, "netplay_safe": netplay, "all_pass": all(x["pass"] for x in c)}


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr); raise SystemExit("failed: %s" % os.path.basename(cmd[0]))
    return r


# ---------------------------------------------------------------- sources: community .pac / .pcs ----------------------
class SourceError(Exception):
    pass


def lz77_decompress(raw):
    """Nintendo LZ77 (0x10) / LZ11 (0x11), the .pcs compression. Raises SourceError on a malformed stream."""
    if len(raw) < 4 or raw[0] not in (0x10, 0x11):
        raise SourceError("not an LZ77/LZ11 stream (header 0x%02x)" % (raw[0] if raw else 0))
    typ, size, i = raw[0], int.from_bytes(raw[1:4], "little"), 4
    if size == 0: size, i = int.from_bytes(raw[4:8], "little"), 8
    out = bytearray()
    try:
        while len(out) < size:
            flags = raw[i]; i += 1
            for bit in range(8):
                if len(out) >= size: break
                if not flags & (0x80 >> bit):
                    out.append(raw[i]); i += 1; continue
                if typ == 0x10:
                    b0, b1 = raw[i], raw[i + 1]; i += 2; n = (b0 >> 4) + 3; d = ((b0 & 15) << 8 | b1) + 1
                else:
                    b0 = raw[i]; ind = b0 >> 4
                    if ind == 0:
                        n = ((b0 & 15) << 4 | raw[i + 1] >> 4) + 0x11; d = ((raw[i + 1] & 15) << 8 | raw[i + 2]) + 1; i += 3
                    elif ind == 1:
                        n = ((b0 & 15) << 12 | raw[i + 1] << 4 | raw[i + 2] >> 4) + 0x111; d = ((raw[i + 2] & 15) << 8 | raw[i + 3]) + 1; i += 4
                    else:
                        n = ind + 1; d = ((b0 & 15) << 8 | raw[i + 1]) + 1; i += 2
                if d > len(out): raise SourceError("LZ back-reference before the start of the data (corrupt file)")
                for _ in range(n): out.append(out[-d])
    except IndexError:
        raise SourceError("LZ stream ends early (truncated file)")
    return bytes(out[:size])


def lz77_compress(data):
    """Literal-only LZ77 (0x10) writer: valid input for lz77_decompress; used by the synthetic tests."""
    out = bytearray([0x10]) + len(data).to_bytes(3, "little")
    for k in range(0, len(data), 8):
        out.append(0); out += data[k:k + 8]
    return bytes(out)


def sha256(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def export_source(path, work, costume="00"):
    """Folder | .pac | .pcs | .json -> a checked source dict. Never assumes retail naming inside the file."""
    if os.path.isdir(path):
        allf = sorted(f for f in os.listdir(path) if f.lower().endswith((".pac", ".pcs", ".json")))
        cands = [f for f in allf if costume in f] or allf
        if not cands: raise SourceError("no .pac/.pcs/.json in the folder")
        path = os.path.join(path, cands[0])
    if not os.path.isfile(path): raise SourceError("no such file")
    os.makedirs(work, exist_ok=True)
    head = open(path, "rb").read(1)
    if path.lower().endswith(".pcs") or head in (b"\x10", b"\x11"):
        dec = os.path.join(work, os.path.splitext(os.path.basename(path))[0] + ".dec")
        data = lz77_decompress(open(path, "rb").read()); open(dec, "wb").write(data)
        path = dec + (".json" if data[:1] == b"{" else ".pac"); os.replace(dec, path)
    if not path.lower().endswith(".json"):
        js = os.path.join(work, "source.json")
        if os.path.exists(js): os.remove(js)
        r = subprocess.run([MODEL_EXPORT, path, js], capture_output=True, text=True)
        if r.returncode or not os.path.exists(js):
            raise SourceError("the Brawl model reader could not read it: %s" % ((r.stderr or r.stdout).strip()[-200:] or "no output"))
        path = js
    try:
        s = load_source(path)
    except Exception as e:
        raise SourceError("unreadable model data: %s" % e)
    if not s.get("bones"): raise SourceError("no skeleton in the file (not a fighter model?)")
    if not s.get("objects"): raise SourceError("no mesh objects in the file")
    names = {b["name"] for b in s["bones"]}
    for o in s["objects"]:
        fps = o.get("tris", [])
        if len(fps) % 3: raise SourceError("object %s: triangle list length %d is not a multiple of 3" % (o.get("name"), len(fps)))
        for fp in fps:
            if len(fp) < 15 or not fp[14]: raise SourceError("object %s: a vertex without skin weights" % o.get("name"))
            for bn, _ in fp[14]:
                if bn not in names: raise SourceError("object %s weights unknown bone %s" % (o.get("name"), bn))
    return s


# ---------------------------------------------------------------- templates & detection ---------------------------------
def templates():
    d = os.path.join(HERE, "maps"); out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".bones.json"): out[f[:-11]] = json.load(open(os.path.join(d, f)))
    return out


def detect(src, hint=""):
    """[(score, template, source character)] best first: Jaccard overlap of bone names with each template.
    Tie-break for near-identical rigs (Mario/Luigi): +0.3 when the file/folder name or the model's own name contains
    the template's source character (hint = source path), +0.05 when the rig's bone count matches exactly."""
    names = {b["name"] for b in src["bones"]}; best = []
    h = (hint + " " + str(src.get("model", ""))).lower()
    for k, t in templates().items():
        sb = set(t.get("source_bones") or t["source_to_target"])
        if not sb: continue
        sc = len(names & sb) / len(names | sb)
        ch = str(t.get("source_character", k)).lower()
        if sc >= 0.5 and ch and re.search(r"(fit)?%s(\d\d)?|[\/]%s[\/]" % (re.escape(ch), re.escape(ch)), h): sc += 0.3
        if names == sb: sc += 0.05
        best.append((round(sc, 3), k, t.get("source_character", k)))
    return sorted(best, reverse=True)


# ---------------------------------------------------------------- reduction to budget --------------------------------------
def decimate(tris, budget):
    """Vertex clustering on a growing grid. A cluster key includes the rounded UV and the dominant joint, so texture
    seams and skin-weight boundaries are not welded; merged weights are averaged, cut to 4 and renormalised."""
    if len(tris) <= budget: return tris, 0.0
    P = np.array([v["p"] for t in tris for v in t], float); ext = float(np.ptp(P, 0).max()) or 1.0
    cell = ext / 400
    while True:
        rep, out = {}, []
        for t in tris:
            ks = [(tuple(np.floor(np.array(v["p"]) / cell).astype(int)), tuple(round(x, 2) for x in v["uvs"][0]),
                   max(v["w"], key=lambda x: x[1])[0]) for v in t]
            if len({k[0] for k in ks}) < 3: continue
            for k, v in zip(ks, t): rep.setdefault(k, []).append(v)
            out.append(ks)
        if len(out) <= budget or cell > ext: break
        cell *= 1.25
    merged = {}
    for k, vs in rep.items():
        p = np.mean([v["p"] for v in vs], 0); n = np.mean([v["n"] for v in vs], 0); n = n / (np.linalg.norm(n) or 1)
        acc = {}
        for v in vs:
            for j, w in v["w"]: acc[j] = acc.get(j, 0) + w / len(vs)
        lst = sorted(acc.items(), key=lambda x: -x[1])[:4]; s = sum(w for _, w in lst)
        lst = [[j, round(w / s, 2)] for j, w in lst if round(w / s, 2) > 0]; lst[0][1] = round(1 - sum(w for _, w in lst[1:]), 2)
        merged[k] = {"p": [float(x) for x in p], "n": [float(x) for x in n], "uvs": vs[0]["uvs"], "w": lst}
    return [[merged[k] for k in t] for t in out], cell


def fit_budget(sk, tgt, budget, log):
    """Reduce replaced DObjs proportionally to a triangle budget. Clustering runs on bind-world positions."""
    tot = sum(len(d.get("tris", [])) for d in sk["dobjs"])
    if tot <= budget:
        log.append("triangles %d within budget %d: no reduction" % (tot, budget)); return
    W = [np.array(j["world"]) for j in tgt["joints"]]; I = [np.linalg.inv(w) for w in W]
    def xf(v, M): v["p"] = (M[v["w"][0][0]] @ np.array(list(v["p"]) + [1.0]))[:3].tolist()
    for d in sk["dobjs"]:
        if not d.get("tris"): continue
        for t in d["tris"]:
            for v in t:
                if len(v["w"]) == 1 and tgt["joints"][v["w"][0][0]]["ibm"]: xf(v, W)
        share = max(4, int(budget * len(d["tris"]) / tot)); before = len(d["tris"])
        d["tris"], cell = decimate(d["tris"], share)
        for t in d["tris"]:
            for v in t:
                if len(v["w"]) == 1 and tgt["joints"][v["w"][0][0]]["ibm"]: xf(v, I)
        log.append("DObj %d: %d -> %d triangles (cluster %.4g)" % (d["dobj"], before, len(d["tris"]), cell))


# ---------------------------------------------------------------- one command ------------------------------------------
def build(a):
    """0 ok/installed, 1 internal failure, 2 over the limits (not installed), 3 unreadable source or bad slot config."""
    work = a.work or os.path.splitext(a.out)[0] + "_work"; os.makedirs(work, exist_ok=True)
    log = []
    try:
        src = export_source(a.source, work, a.source_costume)
    except SourceError as e:
        print("SOURCE ERROR (%s): %s" % (os.path.basename(a.source), e)); return 3
    det = detect(src, os.path.abspath(a.source)); log.append("detected source rig: %s" % (", ".join("%s %.2f" % (k, s) for s, k, _ in det[:3]) or "no template"))
    tgt = read_target(a.retail, a.fighter, a.plco)
    json.dump(tgt, open(os.path.join(work, "target.json"), "w"))
    mapfile = a.map
    if not mapfile:
        for cand in ([det[0][1]] if det and det[0][0] >= 0.5 else []) + [a.fighter]:
            p = os.path.join(HERE, "maps", "%s.bones.json" % cand)
            if os.path.exists(p): mapfile = p; break
    start = json.load(open(mapfile))["source_to_target"] if mapfile else None
    if start and isinstance(next(iter(start.values())), dict): start = {k: v["target"] for k, v in start.items()}
    tnames = {j["name"] for j in tgt["joints"]}
    if start: start = {k: v for k, v in start.items() if k in {b["name"] for b in src["bones"]} and v in tnames}
    log.append("bone map: template %s covers %d of %d bones; auto-mapper for the rest"
               % (os.path.basename(mapfile) if mapfile else "none", len(start or {}), len(src["bones"])))
    mp = automap(src, tgt, start)
    json.dump(mp, open(os.path.join(work, "map.json"), "w"), indent=1)
    if getattr(a, "groups", None):
        groups = json.load(open(a.groups))
    else:                                   # no slot config: derive it (autogroups.py; needs the fighter data file)
        import autogroups
        if not getattr(a, "fighter_dat", None): print("SLOT CONFIG ERROR: give --groups or --fighter-dat Pl<code>.dat"); return 3
        groups = autogroups.make_groups(src, a.retail, a.fighter_dat, a.fighter, a.plco, mapfile)
        json.dump(groups, open(os.path.join(work, "groups.auto.json"), "w"), indent=1)
        log += ["autogroups: " + n for n in groups["_auto"]["notes"]] + ["autogroups confidence %.2f%s" % (groups["_auto"]["confidence"], " NEEDS REVIEW" if groups["_auto"]["needs_review"] else "")]
    try:
        sk = retarget(src, tgt, mp, groups, a.scale, a.repose)
    except (KeyError, SystemExit) as e:
        print("SLOT CONFIG ERROR: %s is named in the slot config but not in this source" % e); return 3
    run([CB, "inspect", a.retail, os.path.join(work, "inspect_retail.json")])
    ir = json.load(open(os.path.join(work, "inspect_retail.json")))
    budget = a.tri_budget or int(ir["tris"] * LIMITS["tri_growth"])
    if "_auto" in groups:
        import autogroups; autogroups.post_reduce(sk, groups, tgt, log)
    fit_budget(sk, tgt, budget, log)
    json.dump(sk, open(os.path.join(work, "skin.json"), "w"))
    run([CB, "build", a.retail, os.path.join(work, "skin.json"), a.out, os.path.join(work, "build_report.json")])
    run([CB, "inspect", a.out, os.path.join(work, "inspect_out.json")])
    d = subprocess.run([sys.executable, os.path.join(HERE, "jointdiff.py"), a.retail, a.out], capture_output=True, text=True)
    open(os.path.join(work, "jointdiff.txt"), "w").write(d.stdout + d.stderr)
    br = json.load(open(os.path.join(work, "build_report.json")))
    ck = checks(br, ir, json.load(open(os.path.join(work, "inspect_out.json"))), d.returncode, sk["stats"], tri_budget=budget + ir["tris"])
    ck["low_confidence"] = {k: v for k, v in mp["source_to_target"].items() if v["confidence"] < 0.5}
    ck["source"] = {"file": os.path.basename(a.source), "sha256": sha256(a.source) if os.path.isfile(a.source) else None,
                    "detected": [list(x) for x in det[:3]]}
    ck["steps"] = log + ["texture %s: %s %dx%d (%s)" % (t["name"], t["fmt"], t["w"], t["h"], t["note"]) for t in br["textures"]]
    json.dump(ck, open(os.path.join(work, "checks.json"), "w"), indent=1)
    for line in ck["steps"]: print("  " + line)
    for x in ck["checks"]: print("%s  %-34s %s" % ("PASS" if x["pass"] else "FAIL", x["check"], x["detail"]))
    print("netplay-safe: %s" % ("YES" if ck["netplay_safe"] else "NO"))
    if not ck["all_pass"]:
        os.replace(a.out, a.out + ".rejected")
        print("STOP: over the limits above; written as %s, not installed" % os.path.basename(a.out + ".rejected")); return 2
    if a.install:
        install(a.out, a.install, a.fighter, a.name, a.slot, ck["source"])
    return 0


def batch(a):
    """A folder of skins in -> a folder of costumes + report.csv (source name, sha256, detected rig, result)."""
    import csv, build_melee_fighter as B
    os.makedirs(a.out_dir, exist_ok=True); rows = []
    files = sorted(f for f in os.listdir(a.in_dir) if f.lower().endswith((".pac", ".pcs", ".json")))
    for i, f in enumerate(files):
        b = argparse.Namespace(**vars(a)); b.source = os.path.join(a.in_dir, f); b.work = None; b.name = os.path.splitext(f)[0]
        b.out = os.path.join(a.out_dir, "Pl%s_%s.dat" % (B.FIGHTERS[a.fighter][1], os.path.splitext(f)[0]))
        print("== [%d/%d] %s" % (i + 1, len(files), f))
        try:
            rc = build(b)
        except Exception as e:
            print("ERROR: %s" % e); rc = 1
        ckp = os.path.splitext(b.out)[0] + "_work/checks.json"
        ck = json.load(open(ckp)) if rc in (0, 2) and os.path.exists(ckp) else {}
        det = (ck.get("source") or {}).get("detected") or [[0, "?"]]
        rows.append({"source": f, "sha256": sha256(b.source), "detected": det[0][1],
                     "result": {0: "ok", 1: "error", 2: "over limits", 3: "unreadable source"}.get(rc, rc),
                     "netplay_safe": ck.get("netplay_safe", ""), "costume": os.path.basename(b.out) if rc == 0 else ""})
    with open(os.path.join(a.out_dir, "report.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "sha256", "detected", "result", "netplay_safe", "costume"]); w.writeheader(); w.writerows(rows)
    print("batch: %d ok of %d -> report.csv" % (sum(r["result"] == "ok" for r in rows), len(rows)))
    return 0


def retag_symbols(path, fighter, slot):
    """A costume built from PlXxNr.dat carries Nr's public names (`Ply<Name>5K_Share_joint`); a colour file must carry
    its own (`Ply<Name>5K<Slot>_...`) or the game refuses it. Rewrites the DAT string table in place (it is the tail)."""
    import struct
    b = bytearray(open(path, "rb").read())
    fs, ds, rc, rn, xn = struct.unpack(">5I", b[:20])
    tab = 0x20 + ds + rc * 4; st = tab + (rn + xn) * 8
    names = []
    for i in range(rn + xn):
        o = struct.unpack(">I", b[tab + i * 8 + 4:tab + i * 8 + 8])[0]
        names.append(bytes(b[st + o:b.index(b"\0", st + o)]).decode())
    pre = None
    for n in names:
        m = re.match(r"^(Ply[A-Za-z]+5K)(Nr|[A-Z][a-z])?_", n)
        if m: pre = m.group(1); break
    if not pre: return
    out, strs = [], b""
    for i, n in enumerate(names):
        n = re.sub(r"^%s(Nr|[A-Z][a-z])?_" % pre, "%s%s_" % (pre, "" if slot == "Nr" else slot), n)
        struct.pack_into(">I", b, tab + i * 8 + 4, len(strs)); strs += n.encode() + b"\0"
    b = b[:st] + strs
    struct.pack_into(">I", b, 0, len(b))
    open(path, "wb").write(bytes(b))


def install(dat, mods, fighter, name, slot=None, source=None):
    """Files-only local mod: <mods>/<id>/files/<costume>.dat + mod.json (an m-ex costume row is described in the
    manifest; a port that does not add costumes uses the file as a replacement of the named colour file)."""
    import build_melee_fighter as B
    code = B.FIGHTERS[fighter][1]
    mid = re.sub(r"[^a-z0-9]+", "-", (name or "skin").lower()).strip("-")
    fn = os.path.basename(dat) if slot is None else "Pl%s%s.dat" % (code, slot)
    d = os.path.join(mods, mid, "files"); os.makedirs(d, exist_ok=True)
    import shutil; shutil.copyfile(dat, os.path.join(d, fn))
    if slot: retag_symbols(os.path.join(d, fn), fighter, slot)
    man = {"id": mid, "name": name or mid, "kind": "costume", "fighter": fighter, "files": [fn],
           "mex_costume": {"file": fn, "joint_symbol": "Ply%s5K%s_Share_joint" % (fighter.capitalize(), "" if slot in (None, "Nr") else slot),
                           "ui": "reuse the fighter's existing colour entries (no new art)"}, "source": source}
    mp = os.path.join(mods, mid, "mod.json")
    if os.path.exists(mp):      # several colour slots installed into one mod: keep the earlier files
        old = json.load(open(mp)).get("files", [])
        man["files"] = sorted(set(old) | {fn})
    json.dump(man, open(mp, "w"), indent=1)
    print("installed %s -> %s" % (fn, os.path.join(mods, mid)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("target"); p.add_argument("retail"); p.add_argument("--fighter"); p.add_argument("--plco"); p.add_argument("-o", required=True)
    p = sp.add_parser("automap"); p.add_argument("source"); p.add_argument("target"); p.add_argument("--map"); p.add_argument("-o", required=True)
    p = sp.add_parser("retarget"); [p.add_argument(x) for x in ("source", "target", "map", "groups")]
    p.add_argument("-o", required=True); p.add_argument("--scale", type=float); p.add_argument("--repose", default="aim", choices=("aim", "rigid", "none"))
    p = sp.add_parser("build")
    for x in ("--source", "--fighter", "--retail", "--out"): p.add_argument(x, required=True)
    p.add_argument("--groups", help="slot config; omitted = autogroups (needs --fighter-dat)"); p.add_argument("--fighter-dat")
    p.add_argument("--plco"); p.add_argument("--map"); p.add_argument("--work"); p.add_argument("--scale", type=float)
    p.add_argument("--repose", default="aim", choices=("aim", "rigid", "none")); p.add_argument("--source-costume", default="00")
    p.add_argument("--install"); p.add_argument("--name"); p.add_argument("--slot"); p.add_argument("--tri-budget", type=int)
    p = sp.add_parser("batch")
    for x in ("--in-dir", "--out-dir", "--fighter", "--retail"): p.add_argument(x, required=True)
    p.add_argument("--groups"); p.add_argument("--fighter-dat")
    p.add_argument("--plco"); p.add_argument("--map"); p.add_argument("--scale", type=float); p.add_argument("--repose", default="aim")
    p.add_argument("--source-costume", default="00"); p.add_argument("--install"); p.add_argument("--slot"); p.add_argument("--tri-budget", type=int)
    p = sp.add_parser("detect"); p.add_argument("source")
    p = sp.add_parser("fetch"); p.add_argument("--fighter", required=True); p.add_argument("--costume", default="Nr"); p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "target":
        json.dump(read_target(a.retail, a.fighter, a.plco), open(a.o, "w"), indent=1)
    elif a.cmd == "automap":
        st = json.load(open(a.map))["source_to_target"] if a.map else None
        if st and isinstance(next(iter(st.values())), dict): st = {k: v["target"] for k, v in st.items()}
        json.dump(automap(load_source(a.source), json.load(open(a.target)), st), open(a.o, "w"), indent=1)
    elif a.cmd == "retarget":
        json.dump(retarget(load_source(a.source), json.load(open(a.target)), json.load(open(a.map)), json.load(open(a.groups)), a.scale, a.repose), open(a.o, "w"))
    elif a.cmd == "build":
        sys.exit(build(a))
    elif a.cmd == "batch":
        sys.exit(batch(a))
    elif a.cmd == "detect":
        try:
            print(json.dumps(detect(export_source(a.source, os.path.join(ROOT, "_build", "tmp", "skin-detect")))[:5]))
        except SourceError as e:
            sys.exit("SOURCE ERROR: %s" % e)
    elif a.cmd == "fetch":
        import mex_hsd, build_melee_fighter as B
        iso = os.environ.get("GW_ISO_VANILLA") or sys.exit("GW_ISO_VANILLA is not set (source .env)")
        g = mex_hsd.Gcm(iso); os.makedirs(a.out, exist_ok=True); code = B.FIGHTERS[a.fighter][1]
        for f in ("PlCo.dat", "Pl%s%s.dat" % (code, a.costume)):
            open(os.path.join(a.out, f), "wb").write(g.read(f)); print("wrote", f)


if __name__ == "__main__":
    main()

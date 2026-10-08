"""convert.py - a Fighter (model.py) -> the engine's inputs: plan.json, mesh_<costume>.json, the animation bank.

The same algorithm as ports/ir/tools/authored_fighter.py, with every name taken from the Fighter instead of the Courier:
bones by ROLE (not by name), the file prefix and symbols from the fighter's token, the costume list and textures from the config.
The Courier goes through it too (ports/vanilla-original/fighter.json) and reproduces its previous outputs byte for byte
(tools/geno/artist/test_artist.py::test_courier_regression).
"""
import base64
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image

from . import model as M
from . import spec
from .model import AF, ArtistError

plan_parts = None


def _pp():
    global plan_parts
    if plan_parts is None:
        import plan_parts as pp  # ports/ir/tools, put on sys.path by model.py
        plan_parts = pp
    return plan_parts


def build_plan(f):
    pp = _pp()
    nodes = f.nodes
    trans = f.role_bone.get("translation")
    hips = f.role_bone.get("hips")
    if trans is None or hips is None:
        raise ArtistError("roles 'translation' and 'hips' are required (see the validator)")
    src = []
    for b in f.bones:
        src.append({"index": b.index, "name": b.name, "parent": b.parent, "node": b.node})
    xrot = {"index": len(src), "name": "XRotN", "parent": trans.index, "node": None}
    for j in src:
        if j["parent"] == trans.index:
            j["parent"] = xrot["index"]
    src.append(xrot)
    head_top = f.role_bone.get("head_top")
    doc = {"document_id": f.key, "assets": {"skeletons": [{"joints": [
        {"index": j["index"], "name": ("Headdress" if head_top is not None and j["name"] == head_top.name else j["name"]), "parent": j["parent"]}
        for j in src]}], "bone_roles": []}}
    part_of = {}
    for b in f.bones:
        role = b.role
        if role in spec.ROLE_PART and f.role_bone.get(role) is b:
            part_of[b.index] = spec.ROLE_PART[role]
    for i, c in part_of.items():
        doc["assets"]["bone_roles"].append({"joint": i, "provenance": {"note": "Melee common part " + c}})
    doc["assets"]["bone_roles"].append({"joint": xrot["index"], "provenance": {"note": "Melee common part XRotN"}})
    pl = pp.plan(doc)
    local = {}
    for n in range(len(nodes)):
        local[n] = M._mat_from_node(nodes[n], f.scale)
    world = {}

    def wm(n):
        if n not in world:
            p = f.parent_node.get(n)
            world[n] = (wm(p) if p is not None else np.eye(4)) @ local[n]
        return world[n]

    joints = []
    for pj in pl["joints"]:
        node = None if pj["synthesized"] else src[pj["source"]]["node"]
        if node is None:
            joints.append({"name": pj["name"], "parent": pj["parent"], "local": np.eye(4), "synth": True})
        else:
            joints.append({"name": pj["name"] if pj["name"] != "Headdress" else head_top.name, "parent": pj["parent"],
                           "local": local[node], "node": node, "synth": False})
    names = [j["name"] for j in joints]
    lift = 0.0
    if "XRotN" in names and "YRotN" in names:
        hj = next(j for j in joints if j.get("node") == hips.node)
        lift = float(local[hj["node"]][1, 3])
        xi, yi = names.index("XRotN"), names.index("YRotN")
        joints[xi]["local"] = joints[xi]["local"].copy(); joints[xi]["local"][1, 3] = lift
        for j in joints:
            if j["parent"] == yi:
                j["local"] = j["local"].copy(); j["local"][1, 3] -= lift
    for j in joints:
        j["lift"] = lift
    for i, j in enumerate(joints):
        j["world"] = (joints[j["parent"]]["world"] if j["parent"] is not None else np.eye(4)) @ j["local"]
    err = max(float(np.abs(j["world"] - wm(j["node"])).max()) for j in joints if not j["synth"])
    if err >= 1e-4:
        raise ArtistError("the planned skeleton differs from the glTF's by %g: a node above the root bone has a transform "
                          "(apply the armature's transform, or parent the root bone to the scene root)" % err)
    return pl, joints, err, part_of


def _reduce(w, keep):
    w = sorted(w, key=lambda x: -x[1])[:keep]
    s = sum(x[1] for x in w)
    return [[a, b / s] for a, b in w]


def write_mesh_and_plan(f, out):
    os.makedirs(out, exist_ok=True)
    pl, joints, err, part_of = build_plan(f)
    name_to_plan = {j["name"]: i for i, j in enumerate(joints)}
    skin_to_plan = [name_to_plan[b.name] for b in f.bones]
    mj = []
    for i, j in enumerate(joints):
        loc = j["local"]
        rx, ry, rz = AF.mat_to_euler_zyx(loc[:3, :3])
        inv = np.linalg.inv(j["world"])
        mj.append({"name": j["name"], "parent": -1 if j["parent"] is None else j["parent"],
                   "scale": [1.0, 1.0, 1.0], "rot": [rx, ry, rz], "trans": [float(x) for x in loc[:3, 3]],
                   "ibm": [float(x) for x in inv[:3, :].reshape(-1)]})
    m = M.mesh(f)
    pos, nrm, uv, jts, wts, idx = m["pos"], m["nrm"], m["uv"], m["jts"].astype(int), m["wts"], m["idx"]
    reduce_ok = bool(f.cfg.get("art", {}).get("reduce_influences"))
    lost = 0.0
    verts = []
    for v in range(len(pos)):
        w = [[skin_to_plan[int(jts[v][k])], float(wts[v][k])] for k in range(4) if wts[v][k] > 1e-6]
        s = sum(x[1] for x in w)
        w = [[x[0], x[1] / s] for x in w]
        if len(w) > spec.LIMITS["max_influences"]:
            if not reduce_ok:
                raise ArtistError("vertex %d has %d bone influences; at most %d (run the validator for the full list, or set art.reduce_influences)"
                                  % (v, len(w), spec.LIMITS["max_influences"]))
            lost += sum(sorted((x[1] for x in w), reverse=True)[spec.LIMITS["max_influences"]:])   # weight moved onto the strongest
            w = _reduce(w, spec.LIMITS["max_influences"])
        merged = {}
        for jx, wx in w:
            merged[jx] = merged.get(jx, 0) + wx
        w = [[k, v2] for k, v2 in merged.items()]
        verts.append({"p": [float(x) for x in pos[v]], "n": [float(x) for x in nrm[v]], "uv": [float(uv[v][0]), float(uv[v][1])], "w": w})
    tris = [[verts[idx[i]], verts[idx[i + 1]], verts[idx[i + 2]]] for i in range(0, len(idx), 3)]
    textures = costume_images(f)
    costume_names = [c["name"] for c in f.costumes]
    for cname in costume_names:
        png = textures[cname].convert("RGBA")
        w, h = png.size
        mesh = {"joints": mj,
                "textures": [{"name": "costume_" + cname, "w": w, "h": h, "fmt": "RGBA8",
                              "rgba": base64.b64encode(png.tobytes()).decode()}],
                "dobjs": [{"object": f.token, "subindex": 0, "group": None, "textures": ["costume_" + cname],
                           "wrap": [["ClampToEdge", "ClampToEdge"]],
                           "cull": "Cull_Outside", "xlu": False, "tris": tris}]}
        json.dump(mesh, open(os.path.join(out, "mesh_%s.json" % cname), "w"))
    from . import hurt
    hb_specs = hurt.hurtboxes(f, joints)
    roles = {}
    for b in f.bones:
        if b.role:
            roles.setdefault(b.role, []).append(name_to_plan[b.name])
    by_name = name_to_plan

    def local_pt(bone, pt):
        j = joints[by_name[bone]]
        inv = np.linalg.inv(j["world"])
        p = inv @ np.array([pt[0] * f.scale, pt[1] * f.scale, pt[2] * f.scale, 1.0])
        return [round(float(x), 5) for x in p[:3]]

    hb = []
    for h in hb_specs:
        hb.append({"id": h["id"], "joint": by_name[h["bone"]], "bone": h["bone"], "a": local_pt(h["bone"], h["a"]),
                   "b": local_pt(h["bone"], h["b"]), "radius": round(h["radius"] * f.scale, 5),
                   "height": h["height"], "grabbable": h["grabbable"]})
    ecb = hurt.ecb(f)
    t = spec.clip_table()
    rowclip = {r["row"]: r["clip"] for r in f.rows if r.get("clip")}
    clipnames = set(f.clips)
    row_clips = []
    for k in t["rows_sm"]:
        row_clips.append(rowclip.get(k) or (k if k in clipnames else None))
    unresolved = pl["unresolved"]
    plan = {"scale": f.scale, "joint_count": len(joints), "row_clips": row_clips,
            "joints": [{"index": i, "name": j["name"], "parent": j["parent"], "synth": j["synth"]} for i, j in enumerate(joints)],
            "parts": pl["parts"], "ftdata": pl["ftdata"], "unresolved": unresolved,
            "roles": roles, "role_joint": {b.name: name_to_plan[b.name] for b in f.bones},
            "hurtboxes": hb, "ecb": ecb, "costumes": costume_names, "world_check_error": err}
    json.dump(plan, open(os.path.join(out, "plan.json"), "w"), indent=1)
    return plan, tris, lost


def costume_images(f):
    out = {}
    emb = None
    for c in f.costumes:
        if c["texture"]:
            if not os.path.isfile(c["texture"]):
                raise ArtistError("costume '%s': texture %s does not exist" % (c["name"], c["texture"]))
            out[c["name"]] = Image.open(c["texture"])
        else:
            if emb is None:
                emb = M.embedded_texture(f)
                if emb is None:
                    raise ArtistError("costume '%s' has no texture and the glb embeds none" % c["name"])
            import io
            out[c["name"]] = Image.open(io.BytesIO(emb))
    return out


# ---- animation bank ------------------------------------------------------------------------------------------------
def write_bank(f, out, plan_path=None):
    pl, joints, err, part_of = build_plan(f)
    name_to_plan = {j["name"]: i for i, j in enumerate(joints)}
    trans = f.role_bone["translation"].name
    hips = f.role_bone["hips"].name
    bank = bytearray()
    rows = {}
    worst = 0.0
    sym_fmt = "Ply%s_Share_ACTION_%%s_figatree" % f.token
    for cname in f.clip_order:
        c = f.clips[cname]
        chans = {k: v for k, v in c.chan.items() if k[1] != "scale" and k[0] in name_to_plan}
        nframes = c.frames
        tracks = []
        for j in joints:
            jt = []
            nm = j["name"]
            if not j["synth"] and (nm, "rotation") in chans:
                t, q = chans[(nm, "rotation")]
                if len(t) != nframes:
                    raise ArtistError("clip '%s': bone '%s' has %d keys, the clip has %d (bake every channel on every frame)" % (cname, nm, len(t), nframes))
                eul = AF._unwrap_euler(q)
                for k, ty in enumerate((1, 2, 3)):
                    body, fv, fs = AF._encode_channel(eul[:, k], AF.FRAC_ROT)
                    jt.append((ty, body, fv, fs))
            if not j["synth"] and (nm, "translation") in chans and (nm == hips or (nm == trans and c.root_motion)):
                t, v = chans[(nm, "translation")]
                v = v * f.scale
                if nm == hips and j.get("lift"):
                    v = v.copy(); v[:, 1] -= j["lift"]
                for k, ty in enumerate((5, 6, 7)):
                    body, fv, fs = AF._encode_channel(v[:, k], None)
                    jt.append((ty, body, fv, fs))
            tracks.append(jt)
        sym = sym_fmt % cname
        arc = AF.F.build_tree_archive(sym, nframes - 1, tracks)
        if len(arc) > spec.LIMITS["clip_buffer_bytes"]:
            raise ArtistError("clip '%s' encodes to %d bytes, over the engine's %d byte animation buffer: shorten it or reduce animated bones"
                              % (cname, len(arc), spec.LIMITS["clip_buffer_bytes"]))
        _, tree = AF.F.parse_archive(arc)
        for ji, j in enumerate(joints):
            nm = j["name"]
            if (nm, "rotation") in chans and not j["synth"]:
                t, q = chans[(nm, "rotation")]
                eul = AF._unwrap_euler(q)
                trk = {tr["type"]: tr for tr in tree["joints"][ji]}
                for fr in range(0, nframes, max(1, nframes // 12)):
                    got = [AF.F.evaluate(trk[ty]["keys"], fr) for ty in (1, 2, 3)]
                    worst = max(worst, max(abs(got[k] - eul[fr][k]) for k in range(3)))
        off = len(bank)
        bank += arc
        while len(bank) % 0x20:
            bank.append(0)
        rows[cname] = {"symbol": sym, "frames": nframes, "offset": off, "bytes": len(arc), "tracks": sum(len(t) for t in tracks)}
    fname = "Gn%sAJ.dat" % f.token
    open(os.path.join(out, fname), "wb").write(bytes(bank))
    json.dump({"clips": rows, "bytes": len(bank), "max_euler_error_rad": worst, "tree_frames": "frames-1",
               "rot_precision": "s16 1/4096 rad", "plan_joints": len(joints)}, open(os.path.join(out, "bank.json"), "w"), indent=1)
    pj = os.path.join(out, "plan.json")
    plan = json.load(open(pj, encoding="utf-8"))
    plan["bank"] = {"file": fname, "bytes": len(bank), "clips": rows}
    plan["motion_rows"] = [{"motion": r["motion"], "row": r["row"], "clip": r["clip"], "status": r["status"]} for r in f.rows]
    json.dump(plan, open(pj, "w"), indent=1)
    return fname, len(bank), worst


def fighterbuild_dll():
    """The fighterbuild.dll: $GW_FIGHTERBUILD, else built from this checkout (needs HSDLib at experiment/tooling/HSDLib), else the one in $GW_ROOT."""
    env = os.environ.get("GW_FIGHTERBUILD")
    if env:
        if not os.path.isfile(env):
            raise ArtistError("GW_FIGHTERBUILD=%s does not exist" % env)
        return env
    root = spec.workspace_root()
    fb = os.path.join(root, "ports", "ir", "tools", "fighterbuild")
    if os.path.isdir(os.path.join(root, "experiment", "tooling", "HSDLib")):
        r = subprocess.run(["dotnet", "build", "-c", "Release", "-nologo", "-v", "q"], cwd=fb, capture_output=True, text=True)
        if r.returncode:
            raise ArtistError("fighterbuild did not build (needs the .NET 8+ SDK):\n" + (r.stdout + r.stderr)[-600:])
        return os.path.join(fb, "bin", "Release", "net8.0", "fighterbuild.dll")
    other = os.path.join(os.environ.get("GW_ROOT", ""), "ports", "ir", "tools", "fighterbuild", "bin", "Release", "net8.0", "fighterbuild.dll")
    if os.path.isfile(other):
        return other
    raise ArtistError("fighterbuild is not available: clone HSDLib (Ploaj) to experiment/tooling/HSDLib (SETUP.md), or set GW_FIGHTERBUILD to a built fighterbuild.dll")


def build_models(f, out, log=print):
    """fighterbuild per costume: Gn<Token>_<costume>.dat. Needs the .NET SDK and HSDLib (see build_courier.sh)."""
    dll = fighterbuild_dll()
    low = f.token.lower()
    made = []
    for c in f.costumes:
        mesh = os.path.join(out, "mesh_%s.json" % c["name"])
        dat = os.path.join(out, "Gn%s_%s.dat" % (f.token, c["name"]))
        rep = os.path.join(out, "rep_%s.json" % c["name"])
        r = subprocess.run(["dotnet", dll, "build", mesh, "-", dat, low + "_joint", low + "_matanim", rep, "--pc-palette", "64"],
                           capture_output=True, text=True)
        if r.returncode:
            raise ArtistError("fighterbuild failed for costume %s:\n%s" % (c["name"], (r.stdout + r.stderr)[-800:]))
        v = subprocess.run(["dotnet", dll, "verify", dat, mesh], capture_output=True, text=True)
        log("  %s: %s" % (os.path.basename(dat), (v.stdout.strip().splitlines() or ["?"])[-1]))
        made.append(dat)
    return made

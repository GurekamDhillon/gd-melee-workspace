#!/usr/bin/env python3
"""export_ultimate_mesh.py - an Ultimate fighter's body model -> the neutral mesh JSON mkbuild reads.

    python ports/ir/tools/export_ultimate_mesh.py <fighter> [--costume c00] [-o mesh.json]

The joints are plan_parts.py's (the fighter's own skeleton, depth-first, plus TopN and YRotN); every
vertex keeps its source bone weights 1:1 by joint name. Read with the upstream ssbh_lib
`ssbh_data_json` from model.numshb (meshes), model.numdlb (mesh -> material) and model.numatb
(materials). The mkbuild side is ports/halberd/model/tools/mkbuild (Build.cs reads this format).

Helper bones (H_*, driven by model.nuhlpb at runtime, never keyed): kept 1:1 by default, because
convert_ultimate_anim.bake_helpers keys them; --fold-helpers moves their weights to the nearest
non-helper ancestor instead (for a clip set converted with --no-helpers).

Conventions, checked on Kirby's c00:
  - Skinned meshes (bone_influences) are in model space.
  - Rigid meshes (no influences, parent_bone_name set: Kirby's 17 faces and 7 eyes on 'Body') are in
    that bone's LOCAL space (centred on 0, the bone's X forward); they are moved into model space
    through the bone's rest world matrix here, and weighted 1.0 to it.
  - At most 4 weights per vertex (GX envelopes), renormalised and rounded to 1/100 so envelopes
    dedupe - mkbuild's rule for Meta Knight. Every drop is counted.
  - Mesh objects named *_VIS_O_OBJShape are shown and hidden by the animations' Visibility group;
    each gets its visibility name ('group') for the ModelVis mapping.
  - Only each material's Texture0 (colour) is kept; normal / PRM / cubemap maps have no Melee use.
    Textures are decoded with the upstream Ultimate-Tex CLI and downscaled (--max-texture, 256).
    UVs are passed unflipped. ASSUMED, not verified: SSBH and GX share the V direction (check on screen).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan_parts  # noqa: E402
from convert_ultimate_anim import DECODER, FIGHTERS, INSTANCES, ROOT, rest_of  # noqa: E402

MAX_INFLUENCES = 4
TEXCLI = os.path.join(os.path.dirname(os.path.dirname(DECODER)), "Ultimate-Tex-CLI", "ultimate_tex_cli.exe")


def texture(path, max_size):
    """.nutexb -> RGBA via the upstream Ultimate-Tex CLI, downscaled to max_size (Melee's memory:
    Kirby's seven 512x512 eye sheets are ~900 KB as CMPR, more than Meta Knight's whole costume)."""
    from PIL import Image
    import base64
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "t.png").replace(os.sep, "/")   # the CLI rejects backslash paths
        subprocess.run([TEXCLI, path.replace(os.sep, "/"), png], check=True, capture_output=True)
        im = Image.open(png).convert("RGBA")
    src = im.size
    if max(im.size) > max_size:
        k = max_size / max(im.size)
        im = im.resize((max(4, int(im.width * k)), max(4, int(im.height * k))), Image.LANCZOS)
    alpha = im.getextrema()[3]
    return {"w": im.width, "h": im.height, "source_size": list(src),
            "fmt": "CMPR" if alpha[0] >= 250 else "RGBA8",
            "rgba": base64.b64encode(im.tobytes()).decode()}


def decode(path):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "x.json")
        subprocess.run([DECODER, path, out], check=True, capture_output=True)
        return json.load(open(out))


def attr(entries, i=0):
    return np.asarray(next(iter(entries[i]["data"].values())), dtype=float) if entries else None


def world_rest(plan, rest):
    """Rest world matrix per plan joint (synthesized joints are identity)."""
    world = []
    for j in plan["joints"]:
        m = np.eye(4)
        if not j["synthesized"]:
            t, r, s, _ = rest[j["name"]]
            m[:3, :3] = r.as_matrix() @ np.diag(s)
            m[:3, 3] = t
        world.append(world[j["parent"]] @ m if j["parent"] is not None else m)
    return world


def helper_owner(plan):
    """Joint index -> the joint that takes its skin weights when helper bones are folded: an H_* bone
    goes to its nearest non-helper ancestor (Ultimate's helpers are leaves driven by model.nuhlpb)."""
    J = plan["joints"]; out = {}
    for i, j in enumerate(J):
        k = i
        while k is not None and J[k]["name"].startswith("H_"):
            k = J[k]["parent"]
        if k != i:
            out[i] = k
    return out


def uv_transform(uv, t):
    """Ultimate's layer UV transform (ssbh_wgpu model.wgsl TransformUv, 'ported from Mario's eye
    shader'): x = sx * (u - tz), y = 1 - sy * (1 - v - tw)."""
    sx, sy, tz, tw = t
    return np.stack([sx * (uv[:, 0] - tz), 1 - sy * (1 - uv[:, 1] - tw)], axis=1)


def pose_material_vectors(fighter, clip, param="CustomVector31"):
    """{material: vector} at frame 0 of `clip`'s Material group (the clip that stands for the
    fighter's rest face: its eyes' iris offset)."""
    path = os.path.join(FIGHTERS, fighter, "motion", "body", "c00", clip + ".nuanmb")
    if not clip or not os.path.exists(path):
        return {}
    out = {}
    for g in decode(path)["groups"]:
        if g["group_type"] != "Material":
            continue
        for n in g["nodes"]:
            for t in n["tracks"]:
                if t["name"] == param:
                    v = t["values"]; v = next(iter(v.values())) if isinstance(v, dict) else v
                    out[n["name"]] = [v[0][a] for a in "xyzw"]
    return out


def lod_skip(names, lod):
    """Mesh objects of the other level of detail: Ultimate ships some bodies twice ('body_high' and
    'body_low', both unconditionally drawn by this exporter otherwise: Sora's 1,609 POBJs overflowed
    the renderer's per-frame uniform buffer). Keep `lod` where both exist."""
    other = {"high": "low", "low": "high"}[lod]
    out = set()
    for n in names:
        m = re.search(r"_(high|low)(?=Shape$|_|$)", n, re.I)
        if m and m.group(1).lower() == other and n[:m.start()] + "_" + lod + n[m.end():] in names:
            out.add(n)
    return out


def export(fighter, costume, max_tex=256, fold_helpers=False, face_clip="a00wait1", lod="high"):
    ir = json.load(open(os.path.join(INSTANCES, f"{fighter}.ultimate-body.ir.json"), encoding="utf-8"))
    plan = plan_parts.plan(ir)
    rest = rest_of(ir)
    W = world_rest(plan, rest)
    jidx = {j["name"]: i for i, j in enumerate(plan["joints"])}
    base = os.path.join(FIGHTERS, fighter, "model", "body", costume)
    shb = decode(os.path.join(base, "model.numshb"))["objects"]
    dlb = decode(os.path.join(base, "model.numdlb"))["entries"]
    atb = {m["material_label"]: m for m in decode(os.path.join(base, "model.numatb"))["entries"]}
    mat_of = {(e["mesh_object_name"], e["mesh_object_subindex"]): e["material_label"] for e in dlb}

    fold = helper_owner(plan) if fold_helpers else {}
    posed = pose_material_vectors(fighter, face_clip)
    stats = {"helpers_folded": {plan["joints"][h]["name"]: plan["joints"][k]["name"] for h, k in fold.items()},
             "tris": 0, "verts": 0, "verts_trimmed": 0, "max_weight_dropped": 0.0, "max_influences": 0,
             "rigid_objects": 0, "layer2": {}, "unknown_bones": set()}
    dobjs = []
    skip = lod_skip({o["name"] for o in shb}, lod)
    stats["lod_dropped"] = sorted(skip)
    for o in shb:
        if o["name"] in skip:
            continue
        pos, nrm = attr(o["positions"]), attr(o["normals"])
        uvs = [attr(o["texture_coordinates"], k) for k in range(len(o["texture_coordinates"]))]
        n = len(pos)
        label = mat_of.get((o["name"], o["subindex"]))
        mat = atb.get(label, {})
        tex = next((t["data"] for t in mat.get("textures", []) if t["param_id"] == "Texture0"), None)
        # Texture1 = colour layer 2 (an eye's iris over its white): sampled with the second UV set
        # through CustomVector31, blended over layer 1 by its alpha (CustomBoolean11: added). The
        # transform is baked into the vertex UVs at the face clip's frame 0; the clips' Material
        # tracks move it (the gaze) and are not carried.
        tex1 = next((t["data"] for t in mat.get("textures", []) if t["param_id"] == "Texture1"
                     and not t["data"].startswith("#")), None)
        layers = []
        if tex and tex1 and len(uvs) > 1:
            vec = next((v["data"] for v in mat.get("vectors", []) if v["param_id"] == "CustomVector31"), None)
            xf = posed.get(label) or ([vec[a] for a in "xyzw"] if vec else [1.0, 1.0, 0.0, 0.0])
            uv2 = uv_transform(uvs[1], xf)
            s1 = next((s["data"] for s in mat.get("samplers", []) if s["param_id"] == "Sampler1"), {})
            add = next((b["data"] for b in mat.get("booleans", []) if b["param_id"] == "CustomBoolean11"), False)
            layers.append({"texture": tex1, "uv": "uv2", "blend": "add" if add else "alpha",
                           "wrap": (s1.get("wraps", "Repeat"), s1.get("wrapt", "Repeat")), "transform": xf})
            stats["layer2"][label] = {"texture": tex1, "transform": [round(x, 4) for x in xf],
                                      "from": "clip " + face_clip if label in posed else "material"}
        samp = next((s["data"] for s in mat.get("samplers", []) if s["param_id"] == "Sampler0"), {})
        weights = [[] for _ in range(n)]
        for inf in o["bone_influences"]:
            j = jidx.get(inf["bone_name"])
            if j is None:
                stats["unknown_bones"].add(inf["bone_name"])
                continue
            for vw in inf["vertex_weights"]:
                weights[vw["vertex_index"]].append((fold.get(j, j), vw["vertex_weight"]))
        rigid = not o["bone_influences"]
        if rigid:
            b = o["parent_bone_name"]
            if b not in jidx:
                sys.exit(f"{o['name']}: rigid mesh on unknown bone {b!r}")
            m = W[jidx[b]]
            pos = (m[:3, :3] @ pos.T).T + m[:3, 3]
            nrm = (m[:3, :3] @ nrm[:, :3].T).T
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
            weights = [[(jidx[b], 1.0)] for _ in range(n)]
            stats["rigid_objects"] += 1
        verts = []
        for i in range(n):
            lst = sorted(weights[i], key=lambda x: -x[1])
            acc = {}
            for j, w in lst:
                acc[j] = acc.get(j, 0.0) + w
            lst = sorted(acc.items(), key=lambda x: -x[1])
            if not lst:
                sys.exit(f"{o['name']} vertex {i} has no weight")
            stats["max_influences"] = max(stats["max_influences"], len(lst))
            if len(lst) > MAX_INFLUENCES:
                stats["verts_trimmed"] += 1
                stats["max_weight_dropped"] = max(stats["max_weight_dropped"], sum(w for _, w in lst[MAX_INFLUENCES:]))
                lst = lst[:MAX_INFLUENCES]
            s = sum(w for _, w in lst)
            r = [(j, round(w / s, 2)) for j, w in lst]
            r = [(j, w) for j, w in r if w > 0]
            r[0] = (r[0][0], round(1.0 - sum(w for _, w in r[1:]), 2))
            v = {"p": [float(x) for x in pos[i]], "n": [float(x) for x in nrm[i, :3]], "w": r}
            if uvs:
                v["uvs"] = [[float(u[i, 0]), float(u[i, 1])] for u in uvs]
                v["uv"] = v["uvs"][0]
            if layers:
                v["uv2"] = [float(x) for x in uv2[i]]
            verts.append(v)
        idx = o["vertex_indices"]
        tris = [[verts[idx[k]], verts[idx[k + 1]], verts[idx[k + 2]]] for k in range(0, len(idx), 3)]
        blend = next((b["data"] for b in mat.get("blend_states", []) if b["param_id"] == "BlendState0"), {})
        cull = next((r["data"]["cull_mode"] for r in mat.get("rasterizer_states", [])), "Back")
        vis = re.sub(r"_VIS_O_OBJShape$", "", o["name"]) if o["name"].endswith("_VIS_O_OBJShape") else None
        dobjs.append({"index": len(dobjs), "object": o["name"], "subindex": o["subindex"], "material": label,
                      "group": vis, "rigid_bone": o["parent_bone_name"] if rigid else None,
                      "textures": [tex] if tex else [], "coords": ["TexCoord0"] if tex else [],
                      "maps": ["TexCoord"] if tex else [],
                      "wrap": [(samp.get("wraps", "Repeat"), samp.get("wrapt", "Repeat"))] if tex else [],
                      "lit": True, "spec": None, "env": None,
                      "cull": {"Back": "Cull_Outside", "Front": "Cull_Inside", "None": "Cull_None"}.get(cull, "Cull_Outside"),
                      "layers": layers,
                      "xlu": blend.get("destination_color", "Zero") != "Zero",
                      "tris": tris})
        stats["tris"] += len(tris)
        stats["verts"] += n
    joints = []
    for i, j in enumerate(plan["joints"]):
        if j["synthesized"]:
            t, e, s = [0.0] * 3, [0.0] * 3, [1.0] * 3
        else:
            rt, rr, rs, re_ = rest[j["name"]]
            t, e, s = list(map(float, rt)), list(map(float, re_)), list(map(float, rs))
        ibm = np.linalg.inv(W[i])[:3, :].reshape(-1)
        joints.append({"name": j["name"], "parent": -1 if j["parent"] is None else j["parent"],
                       "scale": s, "rot": e, "trans": t, "ibm": [float(x) for x in ibm]})
    stats["unknown_bones"] = sorted(stats["unknown_bones"])
    textures = []
    for name in sorted({t for d in dobjs for t in d["textures"]} | {l["texture"] for d in dobjs for l in d["layers"]}):
        path = os.path.join(base, name + ".nutexb")
        if not os.path.exists(path):
            sys.exit(f"texture {name} not in {base}")
        textures.append(dict(name=name, **texture(path, max_tex)))
    stats["texture_bytes_rgba"] = sum(t["w"] * t["h"] * 4 for t in textures)
    return {"fighter": fighter, "costume": costume, "joints": joints, "dobjs": dobjs,
            "textures": textures, "stats": stats}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("--costume", default="c00")
    ap.add_argument("-o", "--out")
    ap.add_argument("--max-texture", type=int, default=256)
    ap.add_argument("--lod", choices=("high", "low"), default="high")
    ap.add_argument("--fold-helpers", action="store_true",
                    help="H_* weights -> nearest non-helper ancestor (when the clips do not bake model.nuhlpb)")
    args = ap.parse_args()
    res = export(args.fighter, args.costume, args.max_texture, args.fold_helpers, lod=args.lod)
    out = args.out or os.path.join(ROOT, "_build", "tmp", "ultimate-mesh", f"{args.fighter}_{args.costume}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"))
    st = res["stats"]
    print(f"{args.fighter} {args.costume}: {len(res['joints'])} joints, {len(res['dobjs'])} DObjs, "
          f"{st['tris']} tris, {st['verts']} verts, {st['rigid_objects']} rigid; "
          f"max influences {st['max_influences']}, {st['verts_trimmed']} trimmed "
          f"(max weight dropped {st['max_weight_dropped']:.3f}); unknown bones {st['unknown_bones']} -> {out}")


if __name__ == "__main__":
    sys.exit(main())

"""model.py - everything the importer knows about a character, derived from its glTF (.glb) and one small fighter.json.

    f = load("path/to/fighter.json")        # raises ArtistError for a file that cannot be read at all
    f.bones, f.clips, f.rows, f.hurtboxes, f.costumes, f.mesh()

No Courier names live here. Bone roles come from, in order: fighter.json "roles", the sidecar the Blender exporter writes
(<glb>.geno.json), the glTF armature extras (`geno.roles` / the Courier's `geno_roles`), then a name guess (reported as a warning).
"""
import json
import math
import os
import re
import sys

import numpy as np

from . import spec

_TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ports", "ir", "tools"))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
import authored_fighter as AF  # noqa: E402  (glb reader, accessors, quaternion/euler maths, the figatree channel encoder)


class ArtistError(Exception):
    pass


def strip_comments(text):
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))


def load_json(path):
    try:
        return json.loads(strip_comments(open(path, encoding="utf-8-sig").read()))
    except (OSError, ValueError) as e:
        raise ArtistError("%s: cannot read (%s)" % (path, e))


def camel(key):
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[^A-Za-z0-9]+", key) if p)


class Bone:
    def __init__(self, i, name, node, parent):
        self.index, self.name, self.node, self.parent = i, name, node, parent   # parent: skin index or None
        self.role = None
        self.role_src = None
        self.world = None          # 4x4 rest, glTF space, scaled
        self.deform = False


class Clip:
    def __init__(self, name, anim):
        self.name, self.anim = name, anim
        self.frames = 0
        self.times = None
        self.chan = {}             # (bone name, path) -> (times, values)
        self.root_motion = False
        self.loop = None
        self.hit_frames = []
        self.rows = []             # engine rows this clip is the authored clip of


class Fighter:
    pass


def _mat_from_node(nd, scale):
    t = np.array(nd.get("translation", [0, 0, 0]), dtype=float) * scale
    m = np.eye(4)
    m[:3, :3] = AF.quat_to_mat(nd.get("rotation", [0, 0, 0, 1]))
    m[:3, 3] = t
    return m


def load(cfg_path, need_glb=True):
    cfg_path = os.path.abspath(cfg_path)
    base = os.path.dirname(cfg_path)
    cfg = load_json(cfg_path)
    f = Fighter()
    f.cfg, f.cfg_path, f.base = cfg, cfg_path, base
    f.key = cfg.get("key") or ""
    if not re.match(r"^[a-z0-9][a-z0-9\-]*$", f.key):
        raise ArtistError("%s: key '%s' must be lowercase letters, digits and '-' (it is the define key and the mod folder name)" % (cfg_path, f.key))
    f.name = cfg.get("name") or f.key
    f.token = cfg.get("token") or camel(f.key)
    art = cfg.get("art", {})
    f.scale = float(art.get("scale", 1.0))
    f.glb = os.path.normpath(os.path.join(base, art.get("glb", "")))
    f.findings = []              # derivation notes the validator turns into warnings: (code, where, message, fix)
    f.sidecar = {}
    sc = f.glb + ".geno.json"
    if os.path.exists(sc):
        f.sidecar = load_json(sc)
    if not os.path.isfile(f.glb):
        raise ArtistError("art.glb: %s does not exist" % f.glb)
    try:
        f.g, f.bin = AF.read_glb(f.glb)
    except Exception as e:  # noqa: BLE001
        raise ArtistError("%s is not a readable .glb (%s). Export as glTF Binary (.glb)." % (f.glb, e))
    g = f.g
    nodes = g["nodes"]
    f.nodes = nodes
    f.parent_node = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            f.parent_node[c] = i
    skins = g.get("skins") or []
    f.skins = skins
    f.bones = []
    f.bone_by_name = {}
    f.bone_by_node = {}
    if skins:
        jn = skins[0]["joints"]
        pos = {n: i for i, n in enumerate(jn)}
        for i, n in enumerate(jn):
            b = Bone(i, nodes[n].get("name", "node%d" % n), n, pos.get(f.parent_node.get(n)))
            f.bones.append(b)
            f.bone_by_name[b.name] = b
            f.bone_by_node[n] = b
    # world rest matrices for every node (glTF space)
    f._world = {}

    def wm(n):
        if n not in f._world:
            p = f.parent_node.get(n)
            f._world[n] = (wm(p) if p is not None else np.eye(4)) @ _mat_from_node(nodes[n], f.scale)
        return f._world[n]
    for n in range(len(nodes)):
        wm(n)
    for b in f.bones:
        b.world = f._world[b.node]
    _resolve_roles(f)
    _read_clips(f)
    _resolve_hurtboxes(f)
    _resolve_costumes(f)
    _resolve_rows(f)
    return f


def _armature_extras(f):
    for n in f.nodes:
        ex = n.get("extras") or {}
        if "geno" in ex or "geno_roles" in ex:
            out = {}
            if "geno" in ex:
                try:
                    out = json.loads(ex["geno"]) if isinstance(ex["geno"], str) else ex["geno"]
                except ValueError:
                    out = {}
            if "geno_roles" in ex and "roles" not in out:
                try:
                    out["roles"] = json.loads(ex["geno_roles"]) if isinstance(ex["geno_roles"], str) else ex["geno_roles"]
                except ValueError:
                    pass
            return out
    return {}


def _resolve_roles(f):
    ex = _armature_extras(f)
    f.extras = ex
    cfg_roles = f.cfg.get("roles", {})
    side_roles = f.sidecar.get("roles", {})
    for b in f.bones:
        role = src = None
        if b.name in cfg_roles:
            role, src = cfg_roles[b.name], "fighter.json"
        elif b.name in side_roles:
            role, src = side_roles[b.name], "sidecar"
        elif b.name in ex.get("roles", {}):
            role, src = ex["roles"][b.name], "glTF extras"
        elif b.name in spec.ALL_ROLES:
            role, src = b.name, "bone name"
        if role:
            b.role, b.role_src = spec.canonical_role(role, b.name), src
    used = {b.role for b in f.bones if b.role}
    for b in f.bones:
        if b.role is None:
            g = spec.guess_role(b.name)
            if g and g not in used:
                b.role, b.role_src = g, "guessed from the name"
                used.add(g)
                f.findings.append(("ROLE_GUESSED", "bone '%s'" % b.name,
                                   "bone '%s' was taken to be role '%s' from its name" % (b.name, g),
                                   "make it permanent: add \"%s\": \"%s\" to fighter.json roles (or set the role in Blender with the Geno panel)" % (b.name, g)))
    for b in f.bones:
        if b.role == "head_top":
            pass
    f.role_bone = {}
    for b in f.bones:
        if b.role and b.role not in f.role_bone:
            f.role_bone[b.role] = b


def _skin_bone_names(f):
    return [b.name for b in f.bones]


def _read_clips(f):
    g = f.g
    f.clips = {}
    f.clip_order = []
    cfg_c = f.cfg.get("clips", {})
    side = f.sidecar.get("clips", {})
    root_cfg = set(cfg_c.get("root_motion", []))
    loop_cfg = cfg_c.get("loop", {})
    ignore = set(cfg_c.get("ignore", []))
    for an in g.get("animations", []):
        name = an.get("name", "")
        if name in ignore:
            continue
        c = Clip(name, an)
        chans = {}
        for ch in an["channels"]:
            nd = f.nodes[ch["target"]["node"]]
            smp = an["samplers"][ch["sampler"]]
            times = AF.accessor(f.g, f.bin, smp["input"]).astype(float)
            vals = AF.accessor(f.g, f.bin, smp["output"]).astype(float)
            chans[(nd.get("name", ""), ch["target"]["path"])] = (times, vals)
        c.chan = chans
        c.frames = max((len(t) for t, _ in chans.values()), default=0)
        if chans:
            c.times = max((t for t, _ in chans.values()), key=len)
        sc = side.get(name, {})
        ex = an.get("extras") or {}
        c.hit_frames = list(sc.get("hit_frames") or _extra_list(ex.get("geno_hit_frames")) or [])
        loop = loop_cfg.get(name, sc.get("loop", ex.get("geno_loop")))
        c.loop = loop if loop is None else bool(loop)
        c.root_motion = (name in root_cfg) or bool(sc.get("root_motion")) or bool(ex.get("geno_root_motion"))
        f.clips[name] = c
        f.clip_order.append(name)
    legacy = cfg_c.get("legacy_manifest")
    f.legacy = None
    if legacy:
        f.legacy = load_json(os.path.join(f.base, legacy))
        for lc in f.legacy["clips"]:
            c = f.clips.get(lc["name"])
            if c:
                c.root_motion = bool(lc.get("root_motion"))
                c.loop = bool(lc.get("loop"))
                c.hit_frames = list(lc.get("hit_frames") or [])


def _extra_list(v):
    if v is None:
        return None
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return [int(x) for x in re.findall(r"-?\d+", v)]
    return [int(x) for x in v]


def _padded(src, name, need):
    c = Clip(name, None)
    extra = need - src.frames
    for k, (tm, v) in src.chan.items():
        tm2 = np.concatenate([tm, tm[-1] + (1.0 / 60.0) * np.arange(1, extra + 1)])
        v2 = np.concatenate([v, np.repeat(v[-1:], extra, axis=0)])
        c.chan[k] = (tm2, v2)
    c.frames = need
    c.times = max((t for t, _ in c.chan.values()), key=len)
    c.root_motion, c.loop, c.hit_frames, c.synthetic = src.root_motion, False, [], True
    return c


def clip_translation(f, clip, role="translation"):
    """(total displacement vector of the role's bone over the clip) or None."""
    b = f.role_bone.get(role)
    if not b:
        return None
    ch = clip.chan.get((b.name, "translation"))
    if ch is None:
        return None
    v = ch[1]
    return v[-1] - v[0]


def _resolve_hurtboxes(f):
    hb = f.cfg.get("hurtboxes", "auto")
    f.hurtbox_src = "fighter.json"
    if hb == "auto":
        if f.sidecar.get("hurtboxes"):
            hb, f.hurtbox_src = f.sidecar["hurtboxes"], "sidecar"
        elif f.extras.get("hurtboxes"):
            hb, f.hurtbox_src = f.extras["hurtboxes"], "glTF extras"
        else:
            hb, f.hurtbox_src = None, "auto"
    f.hurtboxes_given = hb
    f.ecb = f.cfg.get("ecb") or f.sidecar.get("ecb") or f.extras.get("ecb")


def _resolve_costumes(f):
    cfg = f.cfg.get("costumes")
    out = []
    if cfg:
        for c in cfg:
            out.append({"name": c["name"], "team": c.get("team"), "texture": os.path.normpath(os.path.join(f.base, c["texture"])) if c.get("texture") else None,
                        "label": c.get("label") or c["name"]})
    elif f.sidecar.get("costumes"):
        for c in f.sidecar["costumes"]:
            out.append({"name": c["name"], "team": c.get("team"), "texture": os.path.normpath(os.path.join(os.path.dirname(f.glb), c["texture"])) if c.get("texture") else None,
                        "label": c.get("label") or c["name"]})
    else:
        out.append({"name": "default", "team": None, "texture": None, "label": "Default"})   # the image embedded in the glb
    f.costumes = out


def embedded_texture(f):
    """The base-colour image embedded in the glb as PNG bytes, or None."""
    g = f.g
    try:
        prim = g["meshes"][0]["primitives"][0]
        mat = g["materials"][prim["material"]]
        ti = mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]
        img = g["images"][g["textures"][ti]["source"]]
        bv = g["bufferViews"][img["bufferView"]]
        off = bv.get("byteOffset", 0)
        return f.bin[off:off + bv["byteLength"]]
    except (KeyError, IndexError):
        return None


def _resolve_rows(f):
    """f.rows: one entry per engine motion row: {motion, row, clip, status, note}. status: own | alias | placeholder | no-animation."""
    t = spec.clip_table()
    cfg_c = f.cfg.get("clips", {})
    cmap = cfg_c.get("map", {})
    served = {}                              # row name -> authored clip name
    virtual = {c for r in t["rows"] for c in r.get("fallback", [])}     # clip names that are not rows but that rows fall back to (ItemSwing1, ItemShoot...)
    for cn in f.clip_order:
        for rn in cmap.get(cn, []):
            served.setdefault(rn, cn)
        if (cn in t["by_name"] and t["by_name"][cn]["tier"] != "none") or cn in virtual:
            served.setdefault(cn, cn)
    for c in f.clips.values():
        c.rows = [r for r, cn in served.items() if cn == c.name]
    f.served = served
    rows = []
    if f.legacy:
        for m in f.legacy["motion_rows"]:
            rows.append({"motion": m["motion"], "row": m["row"], "clip": m.get("clip"), "status": m["status"], "note": m.get("note", "")})
        f.rows = rows
        return
    wait = served.get("Wait")
    for r in t["rows"]:
        n = r["name"]
        if r["tier"] == "none":
            rows.append({"motion": r["motion"], "row": n, "clip": None, "status": "no-animation", "note": ""})
        elif n in served:
            rows.append({"motion": r["motion"], "row": n, "clip": served[n], "status": "own", "note": ""})
        else:
            hit = None
            for k, cand in enumerate(r.get("fallback", [])):
                if cand in served:
                    hit = (served[cand], "alias" if (k == 0 and r.get("share") == "safe") else "placeholder", "plays '%s'" % cand)
                    break
            if hit is None:
                hit = (wait, "placeholder", "plays Wait") if wait else (None, "UNMAPPED", "no Wait clip")
            rows.append({"motion": r["motion"], "row": n, "clip": hit[0], "status": hit[1], "note": hit[2]})
    # A move ends when its clip ends. A placeholder clip shorter than the move's script would cut the move off (measured: the smashes,
    # fair and the counter of a prototype fighter ended in Wait before their hitboxes were live). So a placeholder for a row with a
    # move script gets a copy of the clip held on its last pose for the script's length: "<Row>_pad".
    f.padded = []
    for row, r in zip(rows, t["rows"]):
        tm = r.get("timing")
        if not tm or row["status"] not in ("alias", "placeholder") or row["clip"] not in f.clips:
            continue
        src = f.clips[row["clip"]]
        need = tm["script_frames"] + 2
        if src.frames >= need:
            continue
        nm = (row["row"] + "_pad")[:spec.LIMITS["max_clip_name"]]
        if nm not in f.clips:
            f.clips[nm] = _padded(src, nm, need)
            f.clip_order.append(nm)
        f.padded.append((row["row"], row["clip"], need))
        row["note"] += "; held to %d frames" % need
        row["clip"] = nm
    f.rows = rows


# ---- mesh ----------------------------------------------------------------------------------------------------------
def mesh(f):
    g = f.g
    prim = g["meshes"][0]["primitives"][0]
    at = prim["attributes"]
    out = {"pos": AF.accessor(g, f.bin, at["POSITION"]).astype(float) * f.scale}
    for k, key in (("nrm", "NORMAL"), ("uv", "TEXCOORD_0"), ("jts", "JOINTS_0"), ("wts", "WEIGHTS_0")):
        out[k] = AF.accessor(g, f.bin, at[key]).astype(float) if key in at else None
    out["idx"] = AF.accessor(g, f.bin, prim["indices"]).astype(int) if "indices" in prim else np.arange(len(out["pos"]))
    return out

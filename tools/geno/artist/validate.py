"""validate.py - check a character before the game does, from its glb and fighter.json. No game, no disc.

    python -m tools.geno.artist validate path/to/fighter.json [--json] [--verbose]

Every finding names the thing at fault (node/object, bone, vertex indices, action) and says how to fix it.
BLOCKER: the build would fail or the fighter would crash or be unplayable; the build command stops.
WARNING: it builds and runs, but something is probably not what you meant (or a placeholder will show).
INFO: facts worth knowing (counts, measured values).
Exit status 1 if there is any BLOCKER.
"""
import difflib
import json
import math
import sys

import numpy as np

from . import loco, model as M, spec
from .model import ArtistError

B, W, I = "BLOCKER", "WARNING", "INFO"


class Report:
    def __init__(self):
        self.items = []

    def add(self, sev, code, where, msg, fix=""):
        self.items.append({"severity": sev, "code": code, "where": where, "message": msg, "fix": fix})

    def count(self, sev):
        return sum(1 for i in self.items if i["severity"] == sev)

    @property
    def ok(self):
        return self.count(B) == 0


def _idx_list(ix, n=6):
    ix = [int(i) for i in ix]
    return ", ".join(str(i) for i in ix[:n]) + (" ... (%d in all)" % len(ix) if len(ix) > n else "")


def _quat_angle(a, b):
    d = abs(float(np.dot(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def validate(cfg_path, measure=True):
    r = Report()
    try:
        f = M.load(cfg_path)
    except ArtistError as e:
        r.add(B, "LOAD", cfg_path, str(e), "fix the file named, then run again")
        return r, None
    except Exception as e:  # noqa: BLE001
        r.add(B, "LOAD", cfg_path, "could not read the character: %r" % (e,), "export again as glTF Binary with the options in docs/geno-artist-spec.md section 10")
        return r, None
    for code, where, msg, fix in f.findings:
        r.add(W, code, where, msg, fix)
    _skeleton(f, r)
    _scene(f, r)
    if f.skins:
        try:
            _mesh(f, r)
        except Exception as e:  # noqa: BLE001
            r.add(B, "MESH", "mesh", "the mesh could not be read (%r)" % (e,), "export one skinned mesh with positions, normals, UVs, joints and weights")
    _materials(f, r)
    _clips(f, r)
    _rows(f, r)
    _hurt(f, r)
    if measure:
        _locomotion(f, r)
    return r, f


# ---- skeleton and roles --------------------------------------------------------------------------------------------
def _skeleton(f, r):
    if not f.skins:
        r.add(B, "NO_SKIN", "glb", "the glb has no skin (no armature export)",
              "Blender: select the mesh and the armature, Export glTF with 'Selected Objects' on and Skinning on (Data > Armature); the mesh needs an Armature modifier")
        return
    if len(f.skins) > 1:
        r.add(W, "MULTI_SKIN", "glb", "%d skins; only the first (%s) is used" % (len(f.skins), f.nodes[f.skins[0]["joints"][0]].get("name")),
              "parent every mesh to ONE armature")
    if len(f.bones) + spec.LIMITS["synthesized_joints"] > spec.LIMITS["max_joints_engine"]:
        r.add(B, "BONE_COUNT", "armature", "%d bones; the engine holds %d joints including 3 synthesized (252 bones at most)" % (len(f.bones), spec.LIMITS["max_joints_engine"]),
              "remove helper/IK/control bones from the exported selection (export only the deform skeleton)")
    names = [b.name for b in f.bones]
    for n in sorted({n for n in names if names.count(n) > 1}):
        r.add(B, "BONE_DUP", "bone '%s'" % n, "two bones share the name '%s'" % n, "rename one in Blender (bone names must be unique)")
    # roles
    for role in spec.REQUIRED:
        if role not in f.role_bone:
            hint = [b.name for b in f.bones if spec.guess_role(b.name) in (role,)]
            r.add(B, "ROLE_MISSING", "role '%s'" % role, "no bone has the role '%s' (the engine needs it)" % role,
                  "add \"<bone name>\": \"%s\" to fighter.json roles%s" % (role, " (candidate: %s)" % ", ".join(hint) if hint else "; the starter calls it the same"))
    for role in spec.RECOMMENDED_ROLES:
        if role not in f.role_bone:
            r.add(W, "ROLE_RECOMMENDED", "role '%s'" % role, "no bone has the role '%s'; the converter falls back (see spec section 4) or the feature is lost" % role, "map one in fighter.json roles")
    seen = {}
    for b in f.bones:
        if b.role:
            if b.role not in spec.ALL_ROLES:
                r.add(B, "ROLE_UNKNOWN", "bone '%s'" % b.name, "role '%s' is not a Geno role (%s)" % (b.role, b.role_src), "valid roles: " + ", ".join(spec.ALL_ROLES))
            if b.role in seen:
                r.add(W, "ROLE_DUP", "bone '%s'" % b.name, "role '%s' is already taken by '%s'; this bone becomes a plain joint" % (b.role, seen[b.role]), "give each role to exactly one bone")
            seen.setdefault(b.role, b.name)
    # sides: left is +X
    for b in f.bones:
        if b.role and b.role.endswith(".L") and b.world[0, 3] < -0.05:
            r.add(W, "SIDE_SWAPPED", "bone '%s'" % b.name, "role %s but the bone is at x=%.2f; left must be +X in glTF space" % (b.role, b.world[0, 3]),
                  "swap the L/R roles of this pair in fighter.json, or mirror the character")
        if b.role and b.role.endswith(".R") and b.world[0, 3] > 0.05:
            r.add(W, "SIDE_SWAPPED", "bone '%s'" % b.name, "role %s but the bone is at x=%.2f; right must be -X in glTF space" % (b.role, b.world[0, 3]),
                  "swap the L/R roles of this pair in fighter.json, or mirror the character")
    # rest transforms
    for b in f.bones:
        nd = f.nodes[b.node]
        s = nd.get("scale", [1, 1, 1])
        if max(abs(x - 1) for x in s) > 1e-3:
            r.add(B, "BONE_SCALE", "bone '%s'" % b.name, "rest scale %s (the converter assumes 1)" % [round(x, 4) for x in s],
                  "Blender: select the armature, Object > Apply > All Transforms; keep bone scale at 1 in the rest pose")
    n = f.bones[0].node if f.bones else None
    anc = []
    while n is not None and f.parent_node.get(n) is not None:
        n = f.parent_node[n]
        anc.append(n)
    for n in anc:
        nd = f.nodes[n]
        t, rot, s = nd.get("translation", [0, 0, 0]), nd.get("rotation", [0, 0, 0, 1]), nd.get("scale", [1, 1, 1])
        if max(abs(x) for x in t) > 1e-4 or abs(abs(rot[3]) - 1) > 1e-4 or max(abs(x - 1) for x in s) > 1e-4:
            r.add(B, "ARMATURE_TRANSFORM", "object '%s'" % nd.get("name"), "the armature object above the root bone has a transform (t=%s r=%s s=%s)" % (
                [round(x, 3) for x in t], [round(x, 3) for x in rot], [round(x, 3) for x in s]),
                  "Blender: select the armature (and its meshes), Object > Apply > All Transforms; the armature must sit at the origin, unrotated, scale 1")
    tr = f.role_bone.get("translation")
    if tr is not None:
        y = tr.world[1, 3]
        if abs(y) > 0.3:
            r.add(W, "GROUND", "bone '%s'" % tr.name, "the translation bone is at y=%.2f; it should be at the feet (y=0)" % y,
                  "move the bone's head to the soles in Edit Mode, and the whole character so the soles are at the origin")
    # facing: toes/feet in front (+Z)
    for s in ("L", "R"):
        ft, toe = f.role_bone.get("foot." + s), f.role_bone.get("toe." + s)
        if ft and toe and toe.world[2, 3] - ft.world[2, 3] < 0.05:
            r.add(W, "FACING", "bone '%s'" % toe.name, "the toe is not in front of the foot (z %.2f vs %.2f); the character should face +Z in glTF (-Y in Blender)" % (toe.world[2, 3], ft.world[2, 3]),
                  "rotate the whole character to face -Y in Blender (the exporter's +Y Up converts it to +Z)")
            break
    if len(f.bones) >= 2 and not any(b.parent is None for b in f.bones):
        r.add(B, "SKELETON", "armature", "no root bone found among the exported joints", "export the armature with its root bone selected")


def _scene(f, r):
    meshes = [n for n in f.nodes if "mesh" in n]
    skinned = [n for n in meshes if "skin" in n]
    if len(f.g.get("meshes", [])) != 1 or len(skinned) != 1:
        r.add(B, "MULTI_MESH", "meshes", "%d meshes, %d skinned (%s); the converter builds ONE skinned piece" % (
            len(f.g.get("meshes", [])), len(skinned), ", ".join(n.get("name", "?") for n in meshes)),
              "Blender: join the body parts into one mesh (Ctrl+J), one Armature modifier; hide/delete props from the export selection")
    for m in f.g.get("meshes", []):
        if len(m["primitives"]) != 1:
            r.add(B, "MULTI_PRIMITIVE", "mesh '%s'" % m.get("name"), "%d material slots/primitives; the palette path packs one primitive" % len(m["primitives"]),
                  "give the mesh ONE material slot (costumes swap the texture, not the material)")
    for n in skinned:
        t, rot, s = n.get("translation", [0, 0, 0]), n.get("rotation", [0, 0, 0, 1]), n.get("scale", [1, 1, 1])
        if max(abs(x) for x in t) > 1e-3 or max(abs(x - 1) for x in s) > 1e-3:
            r.add(W, "MESH_TRANSFORM", "object '%s'" % n.get("name"), "the skinned mesh object has a transform (glTF ignores it for skinned meshes)",
                  "Object > Apply > All Transforms on the mesh")


# ---- mesh -----------------------------------------------------------------------------------------------------------
def _mesh(f, r):
    g = f.g
    try:
        prim = g["meshes"][0]["primitives"][0]
    except (KeyError, IndexError):
        return
    at = prim["attributes"]
    for key, why in (("NORMAL", "normals"), ("TEXCOORD_0", "UVs"), ("JOINTS_0", "bone indices"), ("WEIGHTS_0", "bone weights")):
        if key not in at:
            r.add(B, "NO_" + key.split("_")[0], "mesh", "the mesh has no %s" % why,
                  {"NORMAL": "export with 'Normals' on", "TEXCOORD_0": "UV-unwrap the mesh (the texture needs UVs)",
                   "JOINTS_0": "weight-paint to the armature; export with Skinning on", "WEIGHTS_0": "weight-paint to the armature"}[key])
    if "JOINTS_1" in at:
        r.add(B, "INFLUENCES", "mesh", "the mesh has more than 4 influences per vertex (JOINTS_1)", "Weights > Limit Total = 2; Normalize All; export 'Influence' = 4 or 2")
    if any(k not in at for k in ("NORMAL", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0")):
        return
    m = M.mesh(f)
    pos, jts, wts, uv = m["pos"], m["jts"].astype(int), m["wts"], m["uv"]
    ntri = len(m["idx"]) // 3
    r.add(I, "MESH_STATS", "mesh", "%d triangles, %d vertices, %d bones, height %.2f units (y %.2f..%.2f)" % (ntri, len(pos), len(f.bones), pos[:, 1].max() - pos[:, 1].min(), pos[:, 1].min(), pos[:, 1].max()))
    if ntri > 8000:
        r.add(W, "TRI_COUNT", "mesh", "%d triangles; the Courier has 2,580 and the game is a 2001 engine" % ntri, "decimate or retopologise; fewer than ~5,000 draws well with 4 players")
    nz = (wts > 1e-6).sum(axis=1)
    over = np.where(nz > spec.LIMITS["max_influences"])[0]
    if len(over):
        bones = sorted({f.bones[int(j)].name for v in over[:200] for j, w in zip(jts[v], wts[v]) if w > 1e-6})
        r.add(B, "INFLUENCES", "vertices %s" % _idx_list(over), "%d vertices have more than %d bone influences (bones: %s)" % (len(over), spec.LIMITS["max_influences"], ", ".join(bones[:8])),
              "Blender weight paint: Weights > Limit Total (limit 2) then Weights > Normalize All, or set art.reduce_influences=true in fighter.json (moves the extra weight onto the two strongest)")
    s = wts.sum(axis=1)
    bad = np.where(s < 0.99)[0]
    if len(bad):
        r.add(B, "UNWEIGHTED", "vertices %s" % _idx_list(bad), "%d vertices have no/partial bone weight (sum<0.99): they would stay at the origin in game" % len(bad),
              "Weight paint these vertices (select in Edit Mode, assign to a deform bone), then Normalize All")
    far = np.where(np.abs(s - 1.0) > 0.02)[0]
    if len(far) and not len(bad):
        r.add(W, "WEIGHT_SUM", "vertices %s" % _idx_list(far), "%d vertices' weights do not sum to 1" % len(far), "Weights > Normalize All")
    used = {int(j) for v in range(len(pos)) for j, w in zip(jts[v], wts[v]) if w > 1e-6}
    r.add(I, "DEFORM_BONES", "armature", "%d of %d bones carry weight" % (len(used), len(f.bones)))
    if len(used) > spec.LIMITS["palette_bones"]:
        r.add(W, "PALETTE", "mesh", "%d weighted bones; the palette path packs 64 per piece (untested beyond)" % len(used), "merge small bones (fingers, twist bones) into their parents")
    for b in f.bones:
        b.deform = b.index in used
    for role in ("translation", "hips", "item_socket.R", "grab_anchor"):
        b = f.role_bone.get(role)
        if b is not None and b.index in used and role in ("translation", "item_socket.R", "grab_anchor"):
            r.add(W, "WEIGHTED_HELPER", "bone '%s'" % b.name, "the %s bone carries mesh weight; it is a helper that animates independently" % role, "paint those vertices to a body bone")
    ymin = float(pos[:, 1].min())
    height = float(pos[:, 1].max() - ymin)
    if abs(ymin) > 0.5:
        r.add(W, "SOLES", "mesh", "the lowest vertex is at y=%.2f; the soles should be at y=0 (the ECB and ground contact assume it)" % ymin,
              "move the character so its soles are on the ground plane in Blender")
    if height < 6:
        r.add(W, "SCALE_SMALL", "mesh", "height %.2f units; Melee fighters are 8..20 units (the Courier is 11.7). Metres?" % height,
              "scale the character in Blender (1 unit = 1 Melee unit) and apply, or set art.scale to %.1f in fighter.json" % (11.7 / max(height, 0.01)))
    elif height > 24:
        r.add(W, "SCALE_LARGE", "mesh", "height %.2f units; Melee fighters are 8..20 units" % height, "scale down in Blender, or set art.scale to %.2f" % (11.7 / height))
    if uv is not None and len(uv):
        out = np.where((uv < -0.001).any(axis=1) | (uv > 1.001).any(axis=1))[0]
        if len(out):
            r.add(W, "UV_RANGE", "vertices %s" % _idx_list(out), "%d vertices have UVs outside 0..1; textures are clamped, not tiled" % len(out), "pull the UV islands inside the 0..1 square")
    nrm = m["nrm"]
    if nrm is not None and len(nrm):
        ln = np.linalg.norm(nrm, axis=1)
        if (ln < 0.5).any():
            r.add(W, "NORMALS", "mesh", "some normals are zero length", "Mesh > Normals > Recalculate Outside; remove loose vertices")
    f._mesh_stats = {"tris": ntri, "height": height, "ymin": ymin}


def _materials(f, r):
    g = f.g
    mats = g.get("materials", [])
    try:
        pm = g["meshes"][0]["primitives"][0].get("material")
    except (KeyError, IndexError):
        return
    if pm is None:
        r.add(W, "NO_MATERIAL", "mesh", "the primitive has no material; costume textures will still apply", "")
    else:
        mat = mats[pm]
        if mat.get("alphaMode", "OPAQUE") != "OPAQUE":
            r.add(W, "ALPHA", "material '%s'" % mat.get("name"), "alphaMode %s; the converter draws opaque (no blended/cutout materials)" % mat["alphaMode"], "set Blend Mode to Opaque; model transparent parts in geometry")
        if "baseColorTexture" not in mat.get("pbrMetallicRoughness", {}) and not any(c["texture"] for c in f.costumes):
            r.add(B, "NO_TEXTURE", "material '%s'" % mat.get("name"), "no texture on the material and no costume texture in fighter.json", "plug an Image Texture into Base Color (embed it), or list costume textures in fighter.json")
        elif "baseColorTexture" not in mat.get("pbrMetallicRoughness", {}):
            pass
        base = mat.get("pbrMetallicRoughness", {}).get("baseColorFactor")
        if base and any(abs(x - 1) > 0.02 for x in base[:3]):
            r.add(W, "FLAT_COLOR", "material '%s'" % mat.get("name"), "a base colour tint %s is set; the converter uses the texture only" % [round(x, 2) for x in base[:3]], "bake the colour into the texture")
    if len(mats) > 1 and not f.cfg.get("costumes"):
        r.add(W, "MULTI_MATERIAL", "materials", "%d materials in the glb; costumes are textures listed in fighter.json (the first material's image is the default costume)" % len(mats), "")
    from PIL import Image
    for c in f.costumes:
        try:
            if c["texture"]:
                im = Image.open(c["texture"])
            else:
                emb = M.embedded_texture(f)
                if emb is None:
                    r.add(B, "NO_TEXTURE", "costume '%s'" % c["name"], "no texture file and none embedded in the glb", "list the texture in fighter.json costumes")
                    continue
                import io
                im = Image.open(io.BytesIO(emb))
        except Exception as e:  # noqa: BLE001
            r.add(B, "TEXTURE_READ", "costume '%s'" % c["name"], "texture cannot be read (%r)" % (e,), "save it as PNG (RGBA, 8 bit)")
            continue
        w, h = im.size
        if w % 4 or h % 4:
            r.add(W, "TEXTURE_SIZE", "costume '%s'" % c["name"], "texture is %dx%d; GameCube textures want multiples of 4 (powers of two are best)" % (w, h), "resize to e.g. 128x128 or 256x256")
        if max(w, h) > 1024:
            r.add(B, "TEXTURE_SIZE", "costume '%s'" % c["name"], "texture is %dx%d; the maximum is 1024" % (w, h), "downscale (retail fighter textures are 64..256 px)")
        elif max(w, h) > 512:
            r.add(W, "TEXTURE_SIZE", "costume '%s'" % c["name"], "texture is %dx%d; very large for a fighter (the Courier's is 128x64)" % (w, h), "downscale")
    if len({c["name"] for c in f.costumes}) != len(f.costumes):
        r.add(B, "COSTUME_DUP", "costumes", "two costumes share a name", "give each costume a unique name")
    teams = [c["team"] for c in f.costumes if c["team"]]
    for t in set(teams):
        if teams.count(t) > 1:
            r.add(B, "COSTUME_TEAM", "costumes", "team '%s' is declared twice" % t, "declare each team colour once")


# ---- clips and rows -------------------------------------------------------------------------------------------------
def _clips(f, r):
    t = spec.clip_table()
    r.add(I, "CLIPS", "actions", "%d clips, %d total frames" % (len(f.clips), sum(c.frames for c in f.clips.values())))
    if not f.clips:
        r.add(B, "NO_CLIPS", "glb", "no animations in the glb", "Blender: push each Action down to an NLA track (or enable 'Always Sample' + 'NLA Tracks' export); see spec section 10")
        return
    names = list(t["by_name"])
    lower = {n.lower().replace("_", "").replace(" ", ""): n for n in names}
    cmap = f.cfg.get("clips", {}).get("map", {})
    bone_names = {b.name for b in f.bones}
    for cn in f.clip_order:
        c = f.clips[cn]
        if getattr(c, "synthetic", False):
            continue
        where = "action '%s'" % cn
        if len(cn) > spec.LIMITS["max_clip_name"]:
            r.add(B, "CLIP_NAME", where, "name is %d characters; the plan stores 31" % len(cn), "rename the action")
        if c.frames < 2:
            r.add(B, "CLIP_SHORT", where, "%d frame(s); a clip needs at least 2" % c.frames, "key at least the first and last frame")
        # sampling: 1/60 s steps
        if c.times is not None and len(c.times) > 1:
            step = float(np.median(np.diff(c.times)))
            if abs(step - 1.0 / 60) > 1e-4:
                r.add(B, "CLIP_FPS", where, "keys are %.4f s apart (%.1f fps); the converter needs one key per frame at 60 fps" % (step, 1 / step),
                      "Blender: Scene > Frame Rate = 60 and export with 'Always Sample Animations' on, Sampling Rate 1; or re-time the action to 60 fps")
            if abs(float(c.times[0])) > 1e-4:
                r.add(W, "CLIP_START", where, "the clip starts at t=%.3f s, not 0" % c.times[0], "export the action's own frame range (Limit to Playback Range off, 'Use Action Range')")
        bad = [(k[0], len(v[0])) for k, v in c.chan.items() if k[1] != "scale" and len(v[0]) != c.frames and len(v[0]) > 1]
        if bad:
            r.add(B, "CLIP_UNBAKED", where, "bone '%s' has %d keys but the clip has %d: channels are not sampled per frame" % (bad[0][0], bad[0][1], c.frames),
                  "export with 'Always Sample Animations' on (Animation > Sampling), or bake the action (Object > Animation > Bake Action, Only Selected Bones, Visual Keying)")
        for (bn, path), (tm, v) in c.chan.items():
            if bn not in bone_names:
                if bn and not bn.startswith("Armature") and path != "scale":
                    r.add(W, "CLIP_TARGET", where, "animates '%s', which is not a bone of the skin (ignored)" % bn, "if this is a control rig, bake it onto the export skeleton (spec section 8)")
                continue
            if path == "scale" and len(v) and np.abs(v - 1).max() > 0.01:
                r.add(W, "CLIP_SCALE", where, "bone '%s' scale is animated (max %.2f); the engine ignores bone scale" % (bn, np.abs(v - 1).max() + 1), "pose with rotation (and translation on hips) only; remove scale keys")
                break
        # translation on bones that cannot take it
        for (bn, path), (tm, v) in c.chan.items():
            if path == "translation" and bn in bone_names:
                b = f.bone_by_name[bn]
                if b.role in ("hips", "translation"):
                    continue
                rest = np.array(f.nodes[b.node].get("translation", [0, 0, 0]))
                if len(v) and np.abs(v - rest).max() > 0.02:
                    r.add(W, "CLIP_TRANSLATE", where, "bone '%s' is translated (up to %.2f units); the engine honours translation only on the hips and translation bone (measured: limbs collapse)" % (bn, np.abs(v - rest).max()),
                          "use rotation only on this bone; stretch/offset effects need extra bones")
                    break
        # root motion
        mv = M.clip_translation(f, c)
        if mv is not None:
            dist = float(np.linalg.norm(mv))
            if dist > 0.25 and not c.root_motion:
                r.add(W, "ROOT_UNFLAGGED", where, "the translation bone moves %.1f units but the clip is not flagged root motion: that movement is dropped (the engine moves the fighter)" % dist,
                      "add \"%s\" to fighter.json clips.root_motion (only for rolls, getups, ledge moves), or keep the bone in place" % cn)
            if c.root_motion and dist < 0.25:
                r.add(W, "ROOT_EMPTY", where, "flagged root motion but the translation bone does not move", "remove it from clips.root_motion")
        # unmapped / misnamed
        served_rows = c.rows
        if not served_rows:
            key = cn.lower().replace("_", "").replace(" ", "")
            guess = lower.get(key) or (difflib.get_close_matches(cn, names, n=1, cutoff=0.75) or [None])[0]
            r.add(W, "CLIP_UNMAPPED", where, "'%s' matches no engine row and is not in clips.map: it will never play" % cn,
                  ("rename the action to '%s' or " % guess if guess else "rename it to an engine row name (docs/geno-artist-checklist.md) or ") + "add \"%s\": [\"RowName\"] to fighter.json clips.map" % cn)
    for cn, rows in cmap.items():
        if cn not in f.clips:
            r.add(B, "MAP_CLIP", "fighter.json clips.map", "maps '%s', which is not an action in the glb" % cn, "fix the name or export the action")
        for rn in rows:
            if rn not in t["by_name"]:
                r.add(B, "MAP_ROW", "fighter.json clips.map", "'%s' is not an engine row name" % rn, "see data/clip_table.json or docs/geno-artist-checklist.md")
    for cn in f.cfg.get("clips", {}).get("root_motion", []):
        if cn not in f.clips:
            r.add(W, "ROOT_CLIP", "fighter.json clips.root_motion", "'%s' is not an action in the glb" % cn, "fix the name")
    # loop seams and script lengths
    for cn, c in f.clips.items():
        if getattr(c, "synthetic", False):
            continue
        for rn in c.rows:
            row = t["by_name"].get(rn, {})
            if row.get("loop") or c.loop:
                worst = (0.0, None, 0.0)
                for (bn, path), (tm, v) in c.chan.items():
                    if path == "rotation" and len(v) > 2:
                        jump = _quat_angle(v[-1], v[0])
                        step = max(_quat_angle(v[i], v[i + 1]) for i in range(len(v) - 1))
                        excess = jump - (2.0 * step + 3.0)       # the wrap step may be as large as the clip's own fastest step
                        if excess > worst[0]:
                            worst = (excess, bn, jump)
                if worst[0] > 0:
                    r.add(W, "LOOP_SEAM", "action '%s'" % cn, "plays as a loop (row %s) but the wrap from the last frame to the first jumps %.0f degrees on '%s', far more than any step inside the clip: it will pop each cycle" % (rn, worst[2], worst[1]),
                          "make the last key the pose one step BEFORE the first (do not repeat frame 0 at the end, do not stop short of it)")
                break
            tm = row.get("timing")
            if tm:
                if c.frames < tm["script_frames"]:
                    r.add(W, "CLIP_SHORT_FOR_MOVE", "action '%s'" % cn, "%d frames, but the move script for %s runs %d frames: the pose freezes on the last frame while the hitboxes keep going" % (c.frames, rn, tm["script_frames"]),
                          "lengthen the action to at least %d frames (recovery) or shorten via the move's timing in fighter.json moves" % tm["script_frames"])
                fh = tm.get("first_hit_frame")
                if fh is not None and c.hit_frames:
                    if c.hit_frames[0] != fh:
                        r.add(W, "HIT_FRAME", "action '%s'" % cn, "strike pose is at frame %d but the move script's first hitbox is at frame %d" % (c.hit_frames[0], fh),
                              "key the strike pose at frame %d, or shift the hitbox: fighter.json moves.delay {\"%s\": %d}" % (fh, tm["script"], c.hit_frames[0] - fh))
                elif fh is not None:
                    r.add(I, "HIT_UNMARKED", "action '%s'" % cn, "no hit marker; the script's first hitbox starts at frame %d (check the pose in the LAB)" % fh,
                          "add a timeline marker named 'hit' at the strike frame (the Blender panel exports it) to get this checked")


def _rows(f, r):
    t = spec.clip_table()
    st = {}
    for row in f.rows:
        st[row["status"]] = st.get(row["status"], 0) + 1
    r.add(I, "ROWS", "motion rows", "351 rows: %s" % ", ".join("%d %s" % (v, k) for k, v in sorted(st.items())))
    if "Wait" not in f.served and not f.legacy:
        r.add(B, "NO_WAIT", "action 'Wait'", "there is no Wait (idle) clip; every unmapped row falls back to it", "author an idle action named 'Wait'")
    miss = [n for n in t["prototype"] if n not in f.served]
    if miss and not f.legacy:
        r.add(W, "PROTOTYPE_INCOMPLETE", "prototype set", "missing prototype clips: %s (their rows play a placeholder)" % ", ".join(miss), "see docs/geno-artist-checklist.md")
    ph = [row["row"] for row in f.rows if row["status"] == "placeholder"]
    r.add(W if ph else I, "PLACEHOLDERS", "motion rows", "%d rows play a placeholder clip (listed in the build report; not final art)" % len(ph))
    unm = [row["row"] for row in f.rows if row["status"] == "UNMAPPED"]
    if unm:
        r.add(B, "ROWS_UNMAPPED", "motion rows", "rows without any clip: %s" % ", ".join(unm[:6]), "author a Wait clip")
    f._placeholders = ph
    if getattr(f, "padded", None):
        r.add(I, "PADDED", "placeholders", "%d placeholder clips were held on their last pose so the move script is not cut short: %s" % (
            len(f.padded), ", ".join("%s (plays %s, %d frames)" % x for x in f.padded[:5]) + (" ..." if len(f.padded) > 5 else "")))


def _hurt(f, r):
    hb = f.hurtboxes_given
    if hb:
        if len(hb) > spec.LIMITS["max_hurtboxes"]:
            r.add(B, "HURTBOX_COUNT", "hurtboxes", "%d capsules; the engine holds %d" % (len(hb), spec.LIMITS["max_hurtboxes"]), "remove or merge capsules")
        seen = set()
        for h in hb:
            if h["id"] in seen:
                r.add(B, "HURTBOX_DUP", "hurtbox '%s'" % h["id"], "duplicate id", "unique ids")
            seen.add(h["id"])
            if h["bone"] not in f.bone_by_name:
                r.add(B, "HURTBOX_BONE", "hurtbox '%s'" % h["id"], "bone '%s' is not in the skeleton" % h["bone"], "name an exported bone")
            if not h["radius"] > 0:
                r.add(B, "HURTBOX_RADIUS", "hurtbox '%s'" % h["id"], "radius must be positive", "")
            if h.get("height", "mid") not in ("high", "mid", "low"):
                r.add(B, "HURTBOX_HEIGHT", "hurtbox '%s'" % h["id"], "height '%s' is not high/mid/low" % h.get("height"), "")
        r.add(I, "HURTBOXES", "hurtboxes", "%d capsules from %s" % (len(hb), f.hurtbox_src))
    else:
        r.add(I, "HURTBOXES", "hurtboxes", "generated from the skeleton and mesh (fighter.json \"hurtboxes\" can override); check them in the LAB")


def _locomotion(f, r):
    t = spec.clip_table()
    f.ref_speeds = {}
    for rn in t["walk_run_rows"]:
        cn = f.served.get(rn)
        if cn and cn in f.clips and "foot.L" in f.role_bone and "foot.R" in f.role_bone:
            try:
                v = loco.ref_speed(f, f.clips[cn])
            except Exception as e:  # noqa: BLE001
                v = None
            if v:
                f.ref_speeds[rn] = round(v, 3)
    if f.ref_speeds:
        r.add(I, "LOCO", "locomotion", "measured planted-foot speed at rate 1.0 (units/frame): " + ", ".join("%s %.3f" % kv for kv in f.ref_speeds.items()))
    import json as _j, os as _o
    attrs = _j.load(open(_o.path.join(spec.DATA, "default_attributes.json"), encoding="utf-8"))["attributes"]
    attrs.update(f.cfg.get("attributes", {}))
    for rn, key in (("WalkMiddle", "walk_max_vel"), ("Run", "dash_max_velocity")):
        v = f.ref_speeds.get(rn)
        if v:
            rate = attrs[key] / v
            if rate > 3.5:
                r.add(W, "LOCO_RATE", "action '%s'" % f.served[rn], "at the top %s speed (%.2f units/frame) this clip plays at %.1fx: the legs will blur because the stride is short for the speed" % (rn, attrs[key], rate),
                      "lengthen the stride / quicken the cycle (measured %.3f units per frame), or lower attributes.%s in fighter.json (e.g. %.2f for ~3x)" % (v, key, v * 3))
            elif rate < 0.6:
                r.add(W, "LOCO_RATE", "action '%s'" % f.served[rn], "at the top %s speed this clip plays at %.1fx: slow motion" % (rn, rate), "shorten the stride or raise attributes.%s" % key)
    for rn in ("WalkMiddle", "Run"):
        if rn in f.served and rn not in f.ref_speeds and not f.legacy:
            r.add(W, "LOCO_UNMEASURED", "action '%s'" % f.served[rn], "no stance phase found (feet never plant); the walk/run animation rate will be a guess",
                  "set clips.ref_speed {\"%s\": units_per_frame} in fighter.json, or key the feet on the ground for part of the cycle" % rn)


# ---- output ---------------------------------------------------------------------------------------------------------
def format_report(r, verbose=False):
    lines = []
    for sev in (B, W, I):
        items = [i for i in r.items if i["severity"] == sev]
        if sev == I and not verbose:
            items = [i for i in items if i["code"] in ("MESH_STATS", "ROWS", "LOCO", "HURTBOXES", "CLIPS")]
        for i in items:
            lines.append("%-7s %-18s %s: %s" % (sev, i["code"], i["where"], i["message"]))
            if i["fix"]:
                lines.append("          fix: %s" % i["fix"])
    lines.append("%d blocker(s), %d warning(s)" % (r.count(B), r.count(W)))
    return "\n".join(lines)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="validate")
    ap.add_argument("config")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    a = ap.parse_args(argv)
    r, f = validate(a.config)
    if a.json:
        print(json.dumps({"ok": r.ok, "findings": r.items}, indent=1))
    else:
        print(format_report(r, a.verbose))
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

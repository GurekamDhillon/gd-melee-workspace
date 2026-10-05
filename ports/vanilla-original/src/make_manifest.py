"""Assemble manifest.json (+ skeleton.json, hurtboxes.json) from out/clips_data.json, out/courier.glb and common.py.
Plain Python (no Blender). Run after export.py:   python src/make_manifest.py
"""
import json, os, struct, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C

OUT, PKG = C.OUT, C.PKG
def read_glb(path):
    b = open(path, "rb").read()
    l0 = struct.unpack("<I", b[12:16])[0]
    js = json.loads(b[20:20 + l0])
    off = 20 + l0
    l1, t1 = struct.unpack("<II", b[off:off + 8])
    return js, b[off + 8:off + 8 + l1]

def conv(p): return [round(p[0], 4), round(p[2], 4), round(-p[1], 4)]

def main():
    cd = json.load(open(os.path.join(OUT, "clips_data.json")))
    vb = json.load(open(os.path.join(OUT, "validation_blend.json"))) if os.path.exists(os.path.join(OUT, "validation_blend.json")) else {"info": {}}
    js, _ = read_glb(os.path.join(OUT, "courier.glb"))
    rows = json.load(open(os.path.join(PKG, "data", "motion_rows.json")))["rows"]
    clipnames = {c["name"] for c in cd["clips"]}
    al = cd["aliases"]
    row_map = []
    for r in rows:
        n = r["name"]
        if n in clipnames: row_map.append(dict(motion=r["motion"], row=n, clip=n, status="own"))
        elif n in al: row_map.append(dict(motion=r["motion"], row=n, clip=al[n]["clip"], status=al[n]["status"], note=al[n].get("note", "")))
        elif r["retail_subaction"] == -1: row_map.append(dict(motion=r["motion"], row=n, clip=None, status="no-animation", note="the engine plays no clip for this row"))
        else: row_map.append(dict(motion=r["motion"], row=n, clip=None, status="UNMAPPED"))
    bones = []
    for b in C.BONES:
        bones.append(dict(name=b["name"], parent=b["parent"], role=b["role"], deform=b["deform"],
                          rest_head_authoring=list(b["head"]), rest_tail_authoring=list(b["tail"]),
                          rest_head_gltf=conv(b["head"]), rest_tail_gltf=conv(b["tail"])))
    acc = js["accessors"]
    prim = js["meshes"][0]["primitives"][0]
    counts = dict(
        triangles=acc[prim["indices"]]["count"] // 3, vertices_gltf=acc[prim["attributes"]["POSITION"]]["count"],
        vertices_source=vb.get("info", {}).get("vertices"), bones=len(C.BONES), deform_bones=len(C.DEFORM),
        materials_per_costume=1, costume_materials=len(C.COSTUMES), clips=len(cd["clips"]), total_frames=sum(c["frames"] for c in cd["clips"]),
        motion_rows=len(rows), rows_own=sum(1 for r in row_map if r["status"] == "own"),
        rows_alias=sum(1 for r in row_map if r["status"] == "alias"), rows_placeholder=sum(1 for r in row_map if r["status"] == "placeholder"),
        rows_no_animation=sum(1 for r in row_map if r["status"] == "no-animation"),
        hurtboxes=len(C.HURTBOXES), glb_bytes=os.path.getsize(os.path.join(OUT, "courier.glb")))
    full = [c["name"] for c in cd["clips"] if c["status"] == "full"]
    ph = [c["name"] for c in cd["clips"] if c["status"] != "full"]
    man = dict(
        schema="geno-fighter-art-manifest/1", fighter="vanilla-original", display_name="Vanilla Original (the Courier)",
        conventions=dict(
            units="1 unit = 1 Melee unit (the fighter is ~11.7 units to the helmet top, 12.4 to the crest tip); glTF numbers are Melee units, not metres",
            authoring_axes="Blender Z-up, character faces -Y, character's left = +X", gltf_axes="glTF Y-up, character faces +Z, left = +X (Blender exporter -Y-forward -> +Z-forward; same handedness and facing as HSD model space)",
            fps=C.FPS, frame_semantics="clip frame i is time i/60 s; one quaternion (+ location for trans/hips) key on every frame, linear interpolation; clip.frames = key count",
            rest_pose="A-pose, arms 38 degrees from vertical, legs straight, feet flat (soles at y=0)", rotation="quaternions, never euler; no bone scale anywhere (scale channels are constant 1)",
            root_motion="only on the `trans` bone, only in the clips flagged root_motion=true; all other clips are in place", ground="y=0 in glTF space (soles); `trans` origin is at the feet",
            hit_timing="hit_frames[] are clip frames equal to the Striker's script frames; author the overlays at ANIM_RATE 1.0"),
        counts=counts, bones=bones,
        hurtboxes=[dict(id=h["id"], bone=h["bone"], a_gltf=conv(h["a"]), b_gltf=conv(h["b"]), a_authoring=list(h["a"]), b_authoring=list(h["b"]), radius=h["radius"], height=h["height"], grabbable=h["grabbable"]) for h in C.HURTBOXES],
        ecb=C.ECB,
        costumes=[dict(name=c["name"], team=c["team"], description=c["desc"], texture=f"out/tex/costume_{c['name']}.png", material=f"mat_{c['name']}") for c in C.COSTUMES],
        clips=cd["clips"], full_clips=full, placeholder_clips=ph, motion_rows=row_map,
        files=dict(glb="out/courier.glb", textures="out/tex/*.png", blend_model="out/stage1_model.blend", blend_anim="out/stage2_anim.blend"),
    )
    json.dump(man, open(os.path.join(PKG, "manifest.json"), "w"), indent=1)
    json.dump(dict(bones=bones, note="rest positions in authoring (Z-up, -Y forward) and glTF (Y-up, +Z forward) space"), open(os.path.join(PKG, "skeleton.json"), "w"), indent=1)
    json.dump(dict(hurtboxes=man["hurtboxes"], ecb=C.ECB, note="capsule endpoints are rest-pose positions; bone-local offsets = inverse bind matrix x endpoint"), open(os.path.join(PKG, "hurtboxes.json"), "w"), indent=1)
    print("MANIFEST", counts)

if __name__ == "__main__":
    main()

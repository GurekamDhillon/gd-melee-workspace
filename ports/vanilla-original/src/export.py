"""Stage 3: export glTF 2.0 (.glb) with the skin, 179 clips (NLA tracks) and the Geno role/hurtbox data as extras.

    blender --background out/stage2_anim.blend --python export.py -- [out_dir]

Writes <out>/courier.glb. The Geno data is also written as sidecar JSON by make_manifest.py.
Axis/units: authoring Z-up facing -Y (left = +X) -> glTF Y-up facing +Z (left = +X); 1 unit = 1 Melee unit
(the glTF numbers are Melee units, not metres).
"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else C.OUT
arm = bpy.data.objects["Courier_Armature"]
mesh = bpy.data.objects["Courier"]
ad = arm.animation_data
ad.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    pb["geno_role"] = C.BONE[pb.name]["role"]
    pb["geno_deform"] = bool(C.BONE[pb.name]["deform"])
def conv(p):  # authoring -> glTF
    return [round(p[0], 4), round(p[2], 4), round(-p[1], 4)]
geno = dict(
    schema="geno-fighter-art/1", fighter="vanilla-original (the Courier)", units="1 unit = 1 Melee unit; glTF numbers are Melee units",
    roles={b["name"]: b["role"] for b in C.BONES},
    hurtboxes=[dict(id=h["id"], bone=h["bone"], a=conv(h["a"]), b=conv(h["b"]), radius=h["radius"], height=h["height"], grabbable=h["grabbable"]) for h in C.HURTBOXES],
    ecb=C.ECB, costumes=C.COSTUMES,
)
arm["geno"] = json.dumps(geno)
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
path = os.path.join(OUT, "courier.glb")
bpy.ops.export_scene.gltf(
    filepath=path, export_format="GLB", use_selection=True, export_extras=True, export_yup=True, export_apply=False,
    export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_optimize_animation_size=False,
    export_frame_range=False, export_skins=True, export_influence_nb=4, export_all_influences=False, export_def_bones=False,
    export_leaf_bone=False, export_materials="EXPORT", export_image_format="AUTO", export_rest_position_armature=True,
    export_anim_slide_to_zero=False, export_reset_pose_bones=True)
print("EXPORTED", path, os.path.getsize(path))

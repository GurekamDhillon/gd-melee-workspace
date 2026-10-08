"""control_rig.py - bake animation from your own control rig onto the Geno export skeleton.

The game wants ROTATION keys on the export skeleton, one key per frame (translation only on `hips`, and on `translation` for root-motion
clips). A control rig (IK legs, FK/IK switches, custom bones) is fine for ANIMATING, but only the export skeleton is exported. Bake:

    import control_rig
    control_rig.bake(ctrl_obj, export_obj)                      # every action of the control rig -> an action of the same name on export_obj
    control_rig.bake(ctrl_obj, export_obj, bone_map={"Pelvis": "DEF-hips"}, actions=["Wait", "Attack11"])

How: each export bone gets a Copy Transforms constraint toward the control-rig bone it follows (same name by default, or bone_map
export_bone -> control_bone), the bake (visual keying, every frame, constraints cleared) records the result as rotation/location keys
on the export skeleton, and the new action gets the control action's name, frame range and geno_* custom properties.
Run it from Blender's Text Editor or `blender -b file.blend --python-expr "..."`; it needs both rigs in the same scene.
"""
import bpy


def bake(ctrl, export, bone_map=None, actions=None, step=1):
    bone_map = bone_map or {}
    done = []
    ctrl_names = {b.name for b in ctrl.data.bones}
    # constraints: export bone <- control bone
    for pb in export.pose.bones:
        src = bone_map.get(pb.name, pb.name)
        if src in ctrl_names:
            c = pb.constraints.new("COPY_TRANSFORMS")
            c.name = "GENO_BAKE"
            c.target = ctrl
            c.subtarget = src
    ctrl.animation_data_create()
    export.animation_data_create()
    names = actions or [a.name for a in bpy.data.actions if a.id_root in ("OBJECT",) and (a.use_fake_user or a == ctrl.animation_data.action)]
    prev_ctrl, prev_exp = ctrl.animation_data.action, export.animation_data.action
    for name in names:
        act = bpy.data.actions.get(name)
        if act is None:
            continue
        ctrl.animation_data.action = act
        try:
            if len(act.slots):
                ctrl.animation_data.action_slot = act.slots[0]
        except (AttributeError, RuntimeError):
            pass
        fs, fe = int(act.frame_range[0]), int(act.frame_range[1])
        export.animation_data.action = None
        bpy.ops.object.select_all(action="DESELECT")
        export.select_set(True)
        bpy.context.view_layer.objects.active = export
        bpy.ops.nla.bake(frame_start=fs, frame_end=fe, step=step, only_selected=False, visual_keying=True, clear_constraints=False,
                         clear_parents=False, use_current_action=False, bake_types={"POSE"})
        new = export.animation_data.action
        new.name = name + "_baked"
        for k in act.keys():
            if k.startswith("geno_"):
                new[k] = act[k]
        new.use_fake_user = True
        done.append(new.name)
    for pb in export.pose.bones:
        for c in [c for c in pb.constraints if c.name.startswith("GENO_BAKE")]:
            pb.constraints.remove(c)
    ctrl.animation_data.action, export.animation_data.action = prev_ctrl, prev_exp
    return done

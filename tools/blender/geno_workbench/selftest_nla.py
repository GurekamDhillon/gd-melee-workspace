"""Synthetic NLA check; no server, disc, XV2 IR, numpy or scipy required.

blender --background --factory-startup --python-exit-code 1 --python tools/blender/geno_workbench/selftest_nla.py
"""
import json
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from geno_workbench import nla
from geno_workbench.nla_layout import layout


def run():
    arm_data = bpy.data.armatures.new("NLA synthetic")
    arm = bpy.data.objects.new("NLA synthetic", arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bone = arm.data.edit_bones.new("joint")
    bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode="OBJECT")
    pb = arm.pose.bones["joint"]
    pb.rotation_mode = "QUATERNION"
    actions = {}
    for name, offset, gain in (("wind", 0, 1), ("strike", 20, 2)):
        arm.animation_data_create().action = None
        for frame in range(9):
            pb.location = (offset + gain * frame, 0, 0)
            pb.rotation_quaternion = Matrix.Rotation(frame * 0.07, 4, "Z").to_quaternion()
            pb.scale = (1, 1, 1) if name == "wind" else (1 + frame * 0.01, 1, 1)
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            if name != "wind":
                pb.keyframe_insert("scale", frame=frame)
        action = arm.animation_data.action
        action.name = name
        actions[name] = action
    recipe = {"row": "SyntheticKick", "frames": 19, "blend": 2, "segments": [
        {"clip": "wind", "from": 1, "to": 5, "speed": 2, "hold": 2,
         "marks": {"hit": 3}},
        {"clip": "strike", "from": 6, "to": 2, "speed": 2,
         "marks": {"hit": 4}},
    ]}
    expected = {}
    for action_name, source_frame, output_frame in (("wind", 3, 2), ("strike", 4, 16)):
        if action_name == "wind":
            pb.scale = (1, 1, 1)
        arm.animation_data.action = actions[action_name]
        nla.bind_slot(arm.animation_data, actions[action_name])
        bpy.context.scene.frame_set(source_frame)
        bpy.context.view_layer.update()
        expected[output_frame] = pb.matrix.copy()
    # An engine preview can leave unkeyed channels and Euler modes behind.
    pb.scale = (9, 9, 9)
    pb.location = (77, 88, 99)
    pb.rotation_mode = "XYZ"
    track = nla.lay_out_recipe(arm, "synthetic", recipe, actions=actions)
    assert pb.rotation_mode == "QUATERNION"
    recovered = nla.read_recipe(arm, track)
    got = layout(recovered, {"wind": 9, "strike": 9})
    assert got.total_length == 19 and [m.frame for m in got.marks] == [2, 16]
    assert recovered["segments"][0]["hold"] == 2
    assert recovered["segments"][1]["from"] == 6
    assert recovered["segments"][1]["to"] == 2
    bridge = next(s for s in track.strips if json.loads(s.action[nla.PART])["kind"] == "bridge")
    bridge.mute = True
    try:
        nla.read_recipe(arm, track)
    except ValueError:
        pass
    else:
        raise AssertionError("Muted bridge was silently accepted")
    finally:
        bridge.mute = False
    strip_names = [s.name for s in track.strips]
    baked = nla.bake(arm, track, "SyntheticKick")
    assert baked["geno_status"] == "AUTHORED"
    assert json.loads(baked["geno_hit_frames"]) == [2, 16]
    assert [s.name for s in track.strips] == strip_names
    for other in arm.animation_data.nla_tracks:
        other.mute = True
    arm.animation_data.action = baked
    nla.bind_slot(arm.animation_data, baked)
    for frame, pose in expected.items():
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        error = max(abs(pb.matrix[i][j] - pose[i][j]) for i in range(4) for j in range(4))
        assert error < 2e-4, (frame, error)
    # A hold and the first INSERTED smoothstep blend sample, not an overlap.
    for frame, x in ((8, 5), (10, 12), (18, 24)):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        assert abs(pb.location.x - x) < 2e-4, (frame, pb.location.x, x)
    with tempfile.TemporaryDirectory(prefix="geno-nla-check-") as temp:
        project = Path(temp)
        source = project / "splices.json"
        source.write_text('{"untouched": true}\n', encoding="utf-8")
        path, first = nla.save_recipe(project, "synthetic", recovered)
        _, second = nla.save_recipe(project, "synthetic", recovered)
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert path.name == "splices.authored.json"
        assert first != second and len(saved["recipes"]) == 2
        assert source.read_text(encoding="utf-8") == '{"untouched": true}\n'
        assert all(r["status"] == "AUTHORED" and not r["wired"] for r in saved["recipes"].values())
    # Moving the strike leaves the old helper behind; bake must regenerate it.
    strike_strip = [s for s in track.strips if json.loads(s.action[nla.PART])["kind"] == "segment"][1]
    strike_strip.frame_start_ui += 4
    edited = nla.read_recipe(arm, track)
    assert edited["segments"][1]["blend"] == 4 and edited["frames"] == 23
    shifted = nla.bake(arm, track, "SyntheticShift")
    assert json.loads(shifted["geno_hit_frames"]) == [2, 20]
    for t in arm.animation_data.nla_tracks:
        t.mute = True
    arm.animation_data.action = shifted
    nla.bind_slot(arm.animation_data, shifted)
    bpy.context.scene.frame_set(20)
    bpy.context.view_layer.update()
    assert abs(pb.location.x - 28) < 2e-4
    # Failed artist preflight must preserve every editable track and fake user.
    before = [(t.name, [s.name for s in t.strips]) for t in arm.animation_data.nla_tracks]
    fake_users = {a.name: a.use_fake_user for a in bpy.data.actions}
    objects = set(bpy.data.objects)
    with tempfile.TemporaryDirectory(prefix="geno-nla-export-check-") as temp:
        try:
            nla.export_baked(arm, shifted, Path(temp) / "blocked.glb")
        except ValueError as exc:
            assert "ROLE_MISSING" in str(exc) or "MESH_COUNT" in str(exc), exc
        else:
            raise AssertionError("Synthetic one-bone rig unexpectedly passed artist preflight")
        assert not (Path(temp) / "blocked.glb").exists()
    assert before == [(t.name, [s.name for s in t.strips]) for t in arm.animation_data.nla_tracks]
    assert fake_users == {a.name: a.use_fake_user for a in bpy.data.actions}
    assert objects == set(bpy.data.objects)
    # Fractional global retimes survive float32 NLA scale storage.
    fractional_recipe = {"row": "SyntheticKick", "frames": 11, "segments": [
        {"clip": "wind", "from": 0, "to": 6, "marks": {"hit": 3}},
    ]}
    fractional = nla.lay_out_recipe(arm, "fractional", fractional_recipe, actions=actions)
    fractional_read = nla.read_recipe(arm, fractional)
    assert fractional_read["segments"][0].get("speed", 1) == 1
    assert layout(fractional_read, {"wind": 9}).total_length == 11
    fractional_bake = nla.bake(arm, fractional, "SyntheticFraction")
    assert json.loads(fractional_bake["geno_hit_frames"]) == [5]
    for t in arm.animation_data.nla_tracks:
        t.mute = True
    arm.animation_data.action = fractional_bake
    nla.bind_slot(arm.animation_data, fractional_bake)
    bpy.context.scene.frame_set(5)
    bpy.context.view_layer.update()
    assert abs(pb.location.x - 3) < 2e-4
    # Stretching an odd crop uses its sampled endpoint, not an unsampled tail.
    stretched = nla.lay_out_recipe(arm, "stretched", {"row": "SyntheticKick", "segments": [
        {"clip": "wind", "from": 0, "to": 5, "speed": 2},
    ]}, actions=actions)
    stretched.strips[0].scale = 2
    stretched_read = nla.read_recipe(arm, stretched)["segments"][0]
    assert stretched_read["from"] == 0 and stretched_read["to"] == 4
    assert stretched_read.get("speed", 1) == 1
    # Generic action input also supports a one-pose crop and a zero-blend seam.
    single = nla.lay_out_recipe(arm, "single", {"row": "SyntheticKick", "blend": 0, "segments": [
        {"clip": "wind", "from": 3, "to": 3, "hold": 2},
        {"clip": "strike", "from": 0, "to": 1},
    ]}, actions=actions)
    assert nla.read_recipe(arm, single)["segments"][0]["hold"] == 2
    short = nla.bake(arm, single, "SyntheticHold")
    for t in arm.animation_data.nla_tracks:
        t.mute = True
    arm.animation_data.action = short
    nla.bind_slot(arm.animation_data, short)
    for frame, x in ((0, 3), (1, 3), (2, 3), (3, 20), (4, 22)):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        assert abs(pb.location.x - x) < 2e-4, (frame, pb.location.x, x)
    # A one-pose strip has only a tiny support interval; stretching it is not a hold.
    one = nla.lay_out_recipe(arm, "one", {"row": "SyntheticKick", "segments": [
        {"clip": "wind", "from": 3, "to": 3},
    ]}, actions=actions)
    one.strips[0].scale = 2
    try:
        nla.read_recipe(arm, one)
    except ValueError:
        pass
    else:
        raise AssertionError("Stretched one-pose support interval was silently accepted")
    trailing = nla.lay_out_recipe(arm, "trailing", {"row": "SyntheticKick", "segments": [
        {"clip": "wind", "from": 0, "to": 2, "hold": 2},
    ]}, actions=actions)
    hold = next(s for s in trailing.strips if json.loads(s.action[nla.PART])["kind"] == "hold")
    hold.frame_start_ui += 2
    try:
        nla.read_recipe(arm, trailing)
    except ValueError:
        pass
    else:
        raise AssertionError("Detached hold was silently accepted")
    # Resizing the misplaced helper must not disguise its detached start.
    hold.frame_end += 1
    try:
        nla.read_recipe(arm, trailing)
    except ValueError:
        pass
    else:
        raise AssertionError("Resized detached hold was silently accepted")
    # Exercise the actual registration path, including cleanup.
    import geno_workbench
    geno_workbench.register()
    try:
        assert hasattr(bpy.types.Scene, "geno_wb")
        assert bpy.ops.geno_wb.import_clip.get_rna_type()
        assert bpy.ops.geno_wb.layout_recipe.get_rna_type()
        assert bpy.ops.geno_wb.save_strips.get_rna_type()
        assert bpy.ops.geno_wb.bake_export.get_rna_type()
    finally:
        geno_workbench.unregister()
    assert not hasattr(bpy.types.Scene, "geno_wb")
    print("GENO_WB_CHECK nla OK", flush=True)


if __name__ == "__main__":
    run()

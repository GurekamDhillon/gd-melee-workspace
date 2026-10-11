"""Background-Blender check of Geno > Combo (Play string) against the fake workbench server.

    blender -b --factory-startup --python tools/blender/geno_workbench/selftest_combo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy  # noqa: E402
import geno_workbench  # noqa: E402
from geno_workbench import api, client, combo_play as C, combo_play_bpy as CB, fake_engine  # noqa: E402


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        raise SystemExit(1)


def make_fighter():
    """An armature (root > hand) and three clips; hand.x = 10 * clip number + 0.001 * action frame, so a frame tells which clip."""
    bpy.ops.object.armature_add()
    arm = bpy.context.active_object
    arm.name = "Fighter"
    bpy.ops.object.mode_set(mode="EDIT")
    root = arm.data.edit_bones[0]
    root.name = "root"
    hand = arm.data.edit_bones.new("hand")
    hand.head, hand.tail, hand.parent = (0, 0, 1), (0, 0, 1.4), root
    bpy.ops.object.mode_set(mode="OBJECT")
    pb = arm.pose.bones["hand"]
    arm.animation_data_create()
    for number, (name, frames) in enumerate((("SynAlpha", 24), ("SynBeta", 24), ("SynGamma", 24))):
        action = bpy.data.actions.new(name)
        arm.animation_data.action = action
        for f in range(0, frames + 1):
            pb.location = (10.0 * number + 0.001 * f, 0.0, 0.0)
            pb.keyframe_insert("location", frame=f)
    own = bpy.data.actions.new("Own")
    arm.animation_data.action = own
    pb.location = (-5.0, 0, 0)
    pb.keyframe_insert("location", frame=1)
    return arm, pb


def hand_x(scene, pb, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    return pb.location.x


fake = fake_engine.FakeWorkbench()
port = fake.start()
try:
    api._session = api.WbSession(lambda: client.McpClient(port=port, timeout=3.0))
    geno_workbench.register()
    sess = api.session()
    check(sess.connect(), "connected to the fake server")
    scene = bpy.context.scene
    arm, pb = make_fighter()
    check(bpy.ops.geno_wb.combo_refresh() == {"FINISHED"}, "Refresh strings")
    scene.geno_combo_string = "0"
    scene.geno_combo_hitboxes = True
    check(bpy.ops.geno_wb.combo_play() == {"FINISHED"}, "Play string")
    from geno_workbench import panels_combo
    last = panels_combo._STATE["last"]
    plan = last["plan"]
    # alpha: window [6,14] on hit, first hit 3 -> cut 6; beta -> gamma: B>C wins by priority, window [3,12], first hit 4 -> cut 4
    check([s["cut"] for s in plan] == [6, 4, 12], "cuts %r" % [s["cut"] for s in plan])
    check([s["start"] for s in plan] == [1, 7, 11] and last["frames"] == 22, "string frames %r total %r" % ([s["start"] for s in plan], last["frames"]))
    check(scene.frame_start == 1 and scene.frame_end == 22, "scene range is the string")
    ad = arm.animation_data
    check(ad.action is None and any(t.name == CB.TRACK for t in ad.nla_tracks), "the armature's own action is parked, one string track")
    track = [t for t in ad.nla_tracks if t.name == CB.TRACK][0]
    check([s.name for s in track.strips] == ["alpha", "beta", "gamma"] and track.is_solo, "three strips, solo")
    check([round(s.frame_start) for s in track.strips] == [1, 7, 11], "strips start on the string frames")
    # the pose follows: alpha frames 1..6 (action 0.001*n), then beta from its frame 1 = crop 2 + 1 = action frame 3
    check(abs(hand_x(scene, pb, 6) - 0.006) < 1e-4, "frame 6 is alpha's frame 6 (the cancel frame): %r" % pb.location.x)
    check(abs(hand_x(scene, pb, 7) - (10.0 + 0.003)) < 1e-4, "frame 7 is beta's frame 1 (action frame 3): %r" % pb.location.x)
    check(abs(hand_x(scene, pb, 10) - (10.0 + 0.006)) < 1e-4, "frame 10 is beta's cancel frame (move frame 4 = action frame 6): %r" % pb.location.x)
    check(abs(hand_x(scene, pb, 11) - (20.0 + 0.001)) < 1e-4, "frame 11 is gamma's frame 1: %r" % pb.location.x)
    # markers
    names = [m.name for m in scene.timeline_markers]
    cancels = [m for m in scene.timeline_markers if m.name.startswith("CANCEL ")]
    check([m.frame for m in cancels] == [6, 10], "cancel markers at 6 and 10: %r" % [(m.name, m.frame) for m in cancels])
    check(any(n.startswith("ROUTE light A>B [6-14]") for n in names) and any(n.startswith("ROUTE heavy A>C") for n in names), "route markers named with their input: %r" % names)
    # ribbon: one object per input class that appears, coloured by the input table
    ribbon = set(last["ribbon"])
    check({"Combo.moves", "Combo.route.light", "Combo.route.special", "Combo.cancel", "Combo.playhead"} <= ribbon, "ribbon objects %r" % sorted(ribbon))
    mat = bpy.data.objects["Combo.route.light"].data.materials[0]
    colour = mat.node_tree.nodes["Emission"].inputs["Color"].default_value
    check(tuple(round(c, 3) for c in colour[:3]) == tuple(round(c, 3) for c in C.INPUT_COLOURS["light"]), "light route quads are the light colour")
    head = bpy.data.objects["Combo.playhead"]
    x0, x1 = (hand_x(scene, pb, 1), 0), (hand_x(scene, pb, 22), 0)
    scene.frame_set(1); a = head.location.x
    scene.frame_set(22); b = head.location.x
    check(abs((b - a) - 21 * CB.FRAME_W * CB.scale_of(arm)) < 1e-4, "the playhead moves one step per frame (%r)" % (b - a))
    # hitbox spheres: alpha's hit is active on move frames 3-5, beta's on 4-7 (string frames 10-13, clipped to the cut at 10)
    spheres = [bpy.data.objects[n] for n in last["hit_spheres"]]
    check(len(spheres) == 2 and all(s.parent_bone == "hand" for s in spheres), "two hit spheres on the hand bone")
    def visible(obj, frame):
        scene.frame_set(frame)
        return not obj.hide_viewport
    check([visible(spheres[0], f) for f in (2, 3, 5, 6)] == [False, True, True, False], "alpha's sphere shows on frames 3-5 only")
    check([visible(spheres[1], f) for f in (9, 10, 11)] == [False, True, False], "beta's sphere shows only on frame 10 (the cut clips it)")
    # + buffer moves the cut later (kept inside the window)
    scene.geno_combo_buffer = True
    check(bpy.ops.geno_wb.combo_play() == {"FINISHED"}, "Play string with the buffer")
    plan2 = panels_combo._STATE["last"]["plan"]
    check([s["cut"] for s in plan2][:2] == [11, 9], "with the buffer: %r" % [s["cut"] for s in plan2])
    check(len([t for t in arm.animation_data.nla_tracks if t.name == CB.TRACK]) == 1, "replaying leaves one string track")
    # the same sequence to the engine when asked
    scene.geno_combo_engine = True
    check(bpy.ops.geno_wb.combo_play() == {"FINISHED"} and getattr(fake, "played_strings", None) == [0], "Send to game ran play_string on the server")
    # a missing clip is reported, not fatal
    bpy.data.actions.remove(bpy.data.actions["SynBeta"])
    check(bpy.ops.geno_wb.combo_play() == {"FINISHED"} and panels_combo._STATE["last"]["missing_clips"], "a missing clip is listed")
    # Clear gives everything back
    check(bpy.ops.geno_wb.combo_clear() == {"FINISHED"}, "Clear string")
    check(not any(t.name == CB.TRACK for t in arm.animation_data.nla_tracks), "string track removed")
    check(arm.animation_data.action is not None and arm.animation_data.action.name == "Own", "the armature's own action is back")
    check(not [m for m in scene.timeline_markers if m.name.startswith(CB.MARKER_PREFIXES)], "markers removed")
    check(bpy.data.collections.get(CB.COLLECTION) is None and not [o for o in bpy.data.objects if o.name.startswith("Combo.")], "ribbon and spheres removed")
    print("COMBO SELFTEST OK")
finally:
    try:
        geno_workbench.unregister()
    finally:
        fake.stop()

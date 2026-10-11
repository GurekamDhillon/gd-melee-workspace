"""Blender's own screenshot of a fighter with its control rig (GUI Blender, no background mode).

    blender --window-geometry 30000 100 1600 900 RIG.blend --python tools/blender/geno_workbench/anim_rig_screenshot.py -- OUT.png [frame] [rig_only|full] [FRONT|RIGHT]

RIG.blend is a copy that already has the control rig (anim_rig_demo.py --save-blend). The script frames the character in the
front view, hides the deform armature (the controls stay), shows the controls in front of the mesh, jumps to `frame`, takes
bpy.ops.screen.screenshot_area of the 3D view and quits. Screenshots of retail/XV2 art are for local review only: do not commit them.
"""
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(argv[0])
FRAME = int(argv[1]) if len(argv) > 1 else 0
RIG_ONLY = len(argv) > 2 and argv[2] == "rig_only"
VIEW = argv[3] if len(argv) > 3 else "FRONT"      # FRONT, RIGHT, LEFT, BACK


def setup_and_shoot():
    scene = bpy.context.scene
    win = bpy.context.window_manager.windows[0]
    screen = win.screen
    area = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
    if area is None:
        print("SHOT no 3D view")
        bpy.ops.wm.quit_blender()
        return None
    ctrl = next((o for o in bpy.data.objects if o.type == "ARMATURE" and "geno_deform" in o), None)
    arm = bpy.data.objects.get(ctrl["geno_deform"]) if ctrl else None
    for o in bpy.data.objects:
        if o.type == "MESH" and RIG_ONLY:
            o.hide_set(True)
    if arm:
        arm.hide_set(True)
    if ctrl:
        ctrl.hide_set(False)
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ctrl.select_set(True)
        bpy.context.view_layer.objects.active = ctrl
        bpy.ops.object.mode_set(mode="POSE")
        ctrl.data.display_type = "OCTAHEDRAL"
    scene.frame_set(FRAME)
    space = area.spaces.active
    space.shading.type = "SOLID"
    space.shading.show_xray = False
    space.shading.color_type = "SINGLE"
    space.shading.single_color = (.55, .55, .6)
    space.overlay.show_bones = True
    space.overlay.show_extras = True
    space.show_gizmo = False
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_axis(type=VIEW)
        if ctrl:
            bpy.ops.pose.select_all(action="SELECT")
        bpy.ops.view3d.view_selected()
        bpy.ops.pose.select_all(action="DESELECT")
    for _ in range(3):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=str(OUT))
    print("SHOT saved", OUT)
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(setup_and_shoot, first_interval=4.0)

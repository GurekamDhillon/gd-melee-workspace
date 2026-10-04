"""Headless authoring integration fixture; Blender opens a disposable scene."""
import sys
from pathlib import Path
import bpy

root, output = sys.argv[sys.argv.index('--')+1:]
sys.path.insert(0, root)
from tools.blender.gd_mission.scene import collect_scene
from tools.blender.gd_mission.core import export_document

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene['gd_objective'] = 'reach_goal'


def empty(name, x, y, **properties):
    ob = bpy.data.objects.new(name, None)
    scene.collection.objects.link(ob)
    ob.location = (x/6.5, 0, y/6.5)
    for key, value in properties.items():
        ob[key] = value
    return ob


room = empty('Room', 65, 52, gd_chunk='room')
room.scale = (65/6.5, 1, 52/6.5)
empty('Start', 20, 8, gd_marker='start')
goal = empty('Goal', 104, 20, gd_marker='goal')
goal.scale = (12/6.5, 1, 16/6.5)
door = empty('RightDoor', 130, 16, gd_exit='right', gd_exit_slot=1,
             gd_exit_chunk='room', gd_exit_traversal='walk')
doc = collect_scene(scene)
assert not doc['errors'], doc['errors']
assert doc['chunks'][0]['exits'] == [dict(side='right', slot=1, traversal='walk')]
target = export_document(doc, output, 'fixture')
text = (target / 'chunks/room/level.lua').read_text(encoding='utf-8')
assert '["exits"]' in text and '["side"]="right"' in text and '["size"]' in text
door['gd_exit_slot'] = 2
assert any('gd_exit_slot' in error for error in collect_scene(scene)['errors'])
print('Blender exit markers PASS: collection, validation, chunk export')

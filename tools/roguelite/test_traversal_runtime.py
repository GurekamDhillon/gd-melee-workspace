"""Bundled physical traversal lifecycle with real Lua and engine doubles."""
import json
import shutil
import subprocess
import unittest
import prepare
from test_maze_runtime import PRELUDE, ENGINE, HELPERS

class PhysicalRuntimeTests(unittest.TestCase):
    def test_continuous_room_camera_resume_and_terminal(self):
        engine=ENGINE.replace('generator=maze','generator=physical')
        camera=r"""
local followed;local camera_pose;local clamp;local attached
 gd.camera_bounds=function(v) clamp=v;return true end
 gd.camera_set=function(v) camera_pose=v;return true end
 gd.camera_follow=function(p,offset) followed={p=p,offset=offset};return true end
 gd.camera_attach=function(v) attached=v;return true end
"""
        body=r"""
step();settle();click('start')
assert(state().active and ps[2]==nil,'physical entry is not isolated solo play')
local saved=decoded();assert(saved.manifest.generator_version==4)
assert(#saved.manifest.nodes.entry.room.platforms==20 and line_calls==3)
assert(ps[1].x==-390 and clamp==true and followed.p==ps[1])
assert(followed.offset.y==24 and camera_pose.eye.z==180)
local id=state().run.id;local signature=Codec.encode(saved.manifest)
on_unload();assert(attached==0 and clamp==false,'camera ownership leaked')
request=true;tick=0
"""
        resume=r"""
step();settle();click('resume')
assert(state().active and state().run.id==id and Codec.encode(decoded().manifest)==signature)
assert(ps[2]==nil,'CPU introduced on resume')
ps[1].x=390;ps[1].y=0;press(4);settle()
assert(state().run.status=='success' and state().menu=='collection','terminal region did not finish')
assert(decoded().run.status=='success','terminal result not durable')
assert(ps[2]==nil)
gd.camera_follow=function()return false end
click('start');settle()
assert(state().menu=='error' and not state().active,'camera refusal enabled gameplay')
assert(attached==0 and clamp==false,'partial camera claim was not restored')
"""
        wrapped=';(function()\n'+prepare.bundle()+'\nend)()\n'
        code='local SOURCE='+json.dumps(str(prepare.SOURCE))+'\n'+PRELUDE+engine+camera+wrapped+HELPERS+body+wrapped+resume
        result=subprocess.run([shutil.which('lua') or shutil.which('lua5.4'),'-'],input=code,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

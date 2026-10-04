"""Source-extracted standalone controller tests; no game build/launch/assets saved."""
import re
import struct
import subprocess
import sys
from test_stage_switch import ROOT, OUT, compile_test
from test_stage_switch_fix3 import function

def metadata(disc, file):
    from mex_hsd import Archive
    a=Archive(disc.read(file))
    p=a.public('yakumono_param')
    size=84 if file=='GrIz.dat' else 36
    params=list(struct.unpack_from('>'+str(size//4)+'f',a.data,p))
    h=a.public('map_head'); groups=a.u32(h+8); g=groups+2*52
    periods=[]
    if file=='GrSt.dat':
        joint=a.u32(g); anim=a.u32(a.u32(g+4))
        binding=a.u32(g+32)
        print('YS Randall collision bindings:',[struct.unpack_from('>3h',a.data,binding+6*i) for i in range(a.u32(g+36))])
        for depth in range(3):
            if not joint or not anim:break
            print('YS group2 joint/anim depth',depth,'flags',hex(a.u32(joint+4)),'translate',struct.unpack_from('>3f',a.data,joint+44),'aobj',bool(a.u32(anim+8)))
            joint=a.u32(joint+8);anim=a.u32(anim)
        tree=a.u32(a.u32(g+4))
        def walk(at):
            if not at:return
            desc=a.u32(at+8)
            if desc:
                periods.append(struct.unpack_from('>f',a.data,desc+4)[0])
                if struct.unpack_from('>f',a.data,desc+4)[0]==1200:
                    assert a.u32(desc)&(1<<29), 'Randall route AObj must loop'
            walk(a.u32(at));walk(a.u32(at+4))
        walk(tree)
        assert max(periods)==1200, periods
    return params,periods

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(ROOT/'tools/mex_port'))
    from mex_hsd import Gcm
    path=re.search(r'^export GW_ISO_VANILLA="([^"]+)"',(ROOT/'.env').read_text(),re.M)[1]
    disc=Gcm(path)
    ys,periods=metadata(disc,'GrSt.dat'); fod,_=metadata(disc,'GrIz.dat')
    src=(ROOT/'melee/src/melee/gr/grizumi.c').read_text()
    param=re.search(r'struct grIzumi_YakumonoParam \{.*?\};',src,re.S)[0]
    rng=(ROOT/'melee/src/sysdolphin/baselib/random.c').read_text()
    controller=param+'\n'+''.join(function(rng,n) for n in ['HSD_Rand','HSD_Randf','HSD_Randi'])+function(src,'grIzumi_801CC358')
    (OUT/'stage_fod_controller_retail.inc').write_text(controller)
    mp=(ROOT/'melee/src/melee/mp/mplib.c').read_text()
    (OUT/'stage_joint_retail.inc').write_text(function(mp,'mpLib_80055E9C'))
    native=(ROOT/'melee/pc/gameworld/script_stage_slot_native.inc').read_text()
    (OUT/'stage_native_joint_retail.inc').write_text(function(native,'ScriptGame_StageSlotJointUpdate').replace('int ScriptGame_StageSlotJointUpdate','static int ScriptGame_StageSlotJointUpdate',1))
    scope=(ROOT/'melee/pc/gameworld/script_stage_slot_dynamic.inc').read_text()
    functions=''.join(function(scope,n) for n in ['script_slot_context_begin','script_slot_context_end'])
    functions+=''.join(function(native,n) for n in ['ScriptGame_StageSlotOwned','ScriptGame_StageSlotNativeContext','ScriptGame_StageSlotCreated','ScriptGame_StageSlotDestroyed','script_slot_native_scope_begin','ScriptGame_StageSlotProcBegin','ScriptGame_StageSlotParticleBegin','ScriptGame_StageSlotProcEnd','script_slot_native_bytes','script_slot_native_enter','script_slot_native_leave'])
    functions=functions.replace('->unk4','->article').replace('->unk0','->kind')
    # Public functions are static only in this standalone translation unit.
    functions=re.sub(r'(?m)^(int|void) (ScriptGame_)',r'static \1 \2',functions)
    (OUT/'stage_native_lifecycle_retail.inc').write_text(functions)
    story=(ROOT/'melee/src/melee/gr/grstory.c').read_text()
    ysparam=re.search(r'struct grStory_YakumonoParam \{.*?\};',story,re.S)[0]
    ysfunctions=ysparam+'\nstatic struct grStory_YakumonoParam* yakumono_param;\n'
    ysfunctions+=''.join(function(rng,n) for n in ['HSD_Rand','HSD_Randf','HSD_Randi'])+'static int randi(int n){return n?HSD_Randi(n):0;}\n'
    ysfunctions+=''.join(function(story,n) for n in ['reset_shyguy_timer','set_shyguy_spawn_count','frand_amp1','grStory_801E3418','grStory_801E366C'])
    (OUT/'stage_ys_controller_retail.inc').write_text(ysfunctions)
    (OUT/'stage_randall_timer_retail.inc').write_text(function(story,'grStory_801E366C'))
    fobj=(ROOT/'melee/src/sysdolphin/baselib/fobj.c').read_text()
    aobj=(ROOT/'melee/src/sysdolphin/baselib/aobj.c').read_text()
    fh=(ROOT/'melee/src/sysdolphin/baselib/fobj.h').read_text()
    ah=(ROOT/'melee/src/sysdolphin/baselib/aobj.h').read_text()
    defines='\n'.join(re.findall(r'^#define (?:HSD_A_OP_|HSD_A_FRAC_|FOBJ_LOAD_|AOBJ_).*$',fh+'\n'+ah,re.M))+'\n'
    types=defines+re.search(r'struct HSD_FObj \{.*?\};',fh,re.S)[0]+re.search(r'union HSD_ObjData \{.*?\};',fh,re.S)[0]+re.search(r'struct HSD_AObj \{.*?\};',ah,re.S)[0]
    sh=(ROOT/'melee/src/sysdolphin/baselib/spline.h').read_text()
    types+=re.search(r'typedef struct HSD_Spline \{.*?\} HSD_Spline;',sh,re.S)[0]
    types=types.replace('struct HSD_AObj {','typedef struct HSD_AObj {').replace('struct HSD_Obj* hsd_obj;\n};','struct HSD_Obj* hsd_obj;\n}HSD_AObj;')
    (OUT/'stage_animation_types_retail.inc').write_text(types)
    spline=(ROOT/'melee/src/sysdolphin/baselib/spline.c').read_text()
    fns=['HSD_FObjSetState','HSD_FObjGetState','HSD_FObjReqAnim','HSD_FObjReqAnimAll','parseFloat','parseOpCode','parsePackInfo','FObjLaunchKeyData','parseWait','FObjLoadWait','FObjAnimCON','FObjAnimLinear','FObjAnimSPL0','FObjAnimSPL','FObjAnimSLP','FObjAnimKey','FObjLoadData','FObjUpdateAnim','HSD_FObjInterpretAnim','HSD_FObjInterpretAnimAll','FObj_FlushKeyData','HSD_FObjStopAnim','HSD_FObjStopAnimAll']
    interp=spline[spline.index('static void splGetCardinalPoint'):]+ '\nvoid HSD_FObjInterpretAnim(HSD_FObj*,void*,HSD_ObjUpdateFunc,f32);\n'
    interp+=''.join(function(fobj,n) for n in fns)+function(aobj,'HSD_AObjReqAnim')+function(aobj,'HSD_AObjInterpretAnim')
    (OUT/'stage_animation_interpreter_retail.inc').write_text(interp)
    generator=(ROOT/'melee/src/sysdolphin/baselib/generator.c').read_text()
    particle=(ROOT/'melee/src/sysdolphin/baselib/particle.c').read_text()
    (OUT/'stage_particle_cleanup_retail.inc').write_text(function(particle,'HSD_StageSlotParticleLinkClear')+function(generator,'hsd_8039D3AC')+function(generator,'HSD_StageSlotParticlesClear'))
    for name in ['stage_owned_test','stage_native_lifecycle_test','stage_particle_cleanup_test','stage_ys_controller_test','stage_fod_controller_test']:
        exe=OUT/(name+'.exe');compile_test(ROOT/'melee/pc/tests'/(name+'.c'),exe,['/I'+str(OUT)])
        args=[str(v) for v in fod] if name=='stage_fod_controller_test' else []
        subprocess.run([str(exe),*args],check=True,timeout=15)
    exe=OUT/'stage_randall_animation_test.exe';compile_test(ROOT/'melee/pc/tests/stage_randall_animation_test.c',exe,['/I'+str(OUT)])
    result=subprocess.run([str(exe)],input=disc.read('GrSt.dat'),capture_output=True,check=True,timeout=15)
    print(result.stdout.decode())
    print('Randall authored looping route: max AObj end_frame =',max(periods),'frames =',max(periods)/60,'seconds')
    print('YS yakumono numeric parameters:',ys)
    print('FoD yakumono numeric parameters:',fod)

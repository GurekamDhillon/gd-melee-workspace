"""Source-extracted stage-bank cleanup fixture; no game build or launch."""
import subprocess
from test_stage_switch import ROOT, OUT, compile_test
from test_stage_switch_fix3 import function

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    old = (ROOT / 'melee/pc/tests/stage_particle_cleanup_test.c').read_text()
    fixture = old.split('#include "stage_particle_cleanup_retail.inc"')[0]
    fixture = fixture.replace('int numChild,linkNo;', 'int numChild,linkNo,bank;')
    fixture = fixture.replace('HSD_Particle* next;HSD_Generator* gen;',
                              'HSD_Particle* next;int bank;HSD_Generator* gen;')
    generator = (ROOT / 'melee/src/sysdolphin/baselib/generator.c').read_text()
    particle = (ROOT / 'melee/src/sysdolphin/baselib/particle.c').read_text()
    retail = (ROOT / 'melee/pc/gameworld/script_stage_slot_retail.inc').read_text()
    fixture += '\n#define OSReport(...) ((void)0)\n'
    fixture += function(particle, 'HSD_StageSlotParticleLinkClear')
    fixture += function(generator, 'hsd_8039D3AC')
    fixture += function(generator, 'HSD_StageSlotParticlesClear')
    fixture += function(retail, 'script_retail_bank')
    fixture += function(retail, 'script_retail_particles')
    fixture += r'''
static int hooks;
static void deleted(HSD_Particle* p) { assert(p); ++hooks; }
int main(void) {
    int visit,link;
    UserFunc user={deleted};
    for(visit=0;visit<100;++visit) for(link=0;link<16;++link) {
        HSD_JObj joint={2};
        HSD_Generator host={0},owned={0},child={0};
        HSD_Particle hostp={0},p={0},q={0};
        HSD_SList hostqueue={0},queue={0};
        HSD_psAppSRT srt={&owned,2};
        memset(hsd_804D0908,0,sizeof hsd_804D0908);
        host.bank=2;host.linkNo=2;host.next=&owned;
        owned.bank=0x1E;owned.linkNo=link;owned.next=&child;
        child.bank=0x40;child.linkNo=link;child.next=NULL;
        owned.type=0x1900;owned.jobj=&joint;owned.appsrt=&srt;
        owned.numChild=1;child.numChild=1;owned.userfunc=&user;
        hostp.bank=2;hostp.next=&p;p.bank=0x1E;p.gen=&owned;
        p.appsrt=&srt;p.next=&q;q.bank=2;q.gen=&child;
        hsd_804D0908[link]=&hostp;
        if(link==3) { hostp.next=NULL;hsd_804D0908[2]=&hostp;hsd_804D0908[3]=&p; }
        hsd_804D78FC=&host;
        hsd_804D78E2=3;hsd_804D78E0=3;
        hostqueue.data=&host;hostqueue.next=&queue;
        queue.data=&owned;hsd_804D78F4=(u32)&hostqueue;
        script_retail_particles();
        assert(hsd_804D78FC==&host && host.next==NULL);
        assert(hsd_804D0908[link==3?2:link]==&hostp && hostp.next==NULL);
        assert(hsd_804D78E2==1 && hsd_804D78E0==1 && joint.refs==1);
        assert(owned.appsrt==NULL && srt.usedCount==1);
        assert((HSD_SList*)hsd_804D78F4==&hostqueue && hostqueue.next==NULL);
        script_retail_particles();
    }
    assert(freed_particles==3200 && freed_generators==3200);
    assert(freed_queue==1600 && hooks==1600);
    puts("stage banks: 100 visits across all 16 links, parent-bank children, queued generators, hooks/SRT/joints, foreign bank retained passed");
    return 0;
}
'''
    source = OUT / 'stage_teardown_particles_test.c'
    source.write_text(fixture)
    exe = OUT / 'stage_teardown_particles_test.exe'
    compile_test(source, exe, [])
    subprocess.run([str(exe)], check=True, timeout=15)

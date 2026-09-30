#include "gw.h"
#include "gw_compat_linux.h"
#include <dolphin/pad.h>
#include <assert.h>
#include <stdio.h>
static unsigned char gw_gc_origin[4][4],gw_gc_trig_rest[4][2],gw_gc_btn_stuck[4][2];
static int gw_gc_have_origin[4];
#define GW_GC_TRIG_DEAD 200
void gw_log(const char *fmt,...) { (void)fmt; }
#include "gc_adapter_decode.h"
int main(void) {
    unsigned char report[37]={0x21}; PADStatus st[4]; memset(st,0,sizeof st);
    for(int port=0;port<4;++port) {
        unsigned char *p=report+1+9*port;
        p[0]=0x10;
        p[3]=p[4]=p[5]=p[6]=128;
        p[7]=p[8]=10;
    }
    assert(gw_gc_decode(report,st,0));
    for(int port=0;port<4;++port) {
        unsigned char *p=report+1+9*port;
        p[1]=0xff;p[2]=0xf;p[3]=255;p[4]=0;p[5]=200;p[6]=100;p[7]=255;p[8]=10;
    }
    assert(gw_gc_decode(report,st,0));
    for(int port=0;port<4;++port) {
        assert(gw_r16(&st[port].button)==(PAD_BUTTON_A|PAD_BUTTON_B|PAD_BUTTON_X|PAD_BUTTON_Y|PAD_BUTTON_LEFT|PAD_BUTTON_RIGHT|PAD_BUTTON_DOWN|PAD_BUTTON_UP|PAD_BUTTON_START|PAD_TRIGGER_Z|PAD_TRIGGER_L|PAD_TRIGGER_R));
        assert(st[port].stickX==127 && st[port].stickY==-128 && st[port].substickX==72 && st[port].substickY==-28);
        assert(st[port].triggerLeft==255 && st[port].triggerRight==0 && st[port].err==0);
    }
    report[1]=0; gw_gc_decode(report,st,0); assert(!gw_gc_have_origin[0]);
    report[1]=0x20; report[2]=report[3]=0; report[4]=130;
    gw_gc_decode(report,st,0); assert(st[0].stickX==0 && gw_gc_have_origin[0]);
    gw_gc_decode(report,st,1); assert(st[1].button==0 && st[1].triggerLeft==0);
    puts("PASS: four-port USB reports, buttons, axes, trigger calibration and reconnect origins");
}

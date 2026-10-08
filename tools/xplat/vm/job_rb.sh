#!/bin/bash
# job: fake-network rollback session, padgen inputs, SNAP_VERIFY, headless Xvfb + lavapipe
set -u
PKG=/work/pkg/melee-linux-i686
. /work/job.env
RUN=/work/${RUNNAME:-run_rb1}
rm -rf $RUN; mkdir -p $RUN/{card,mods,scripts,scripts-data,cache}
(Xvfb :99 -screen 0 1280x720x24 >$RUN/xvfb.log 2>&1 &) ; sleep 2
export DISPLAY=:99 SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.i686.json
export LD_LIBRARY_PATH=$PKG/lib
export MELEE_CARD_PATH=$RUN/card MELEE_MODS_DIR=$RUN/mods MELEE_SETTINGS_CFG=$RUN/settings.cfg MELEE_SCRIPTS_DIR=$RUN/scripts MELEE_SCRIPT_DATA_DIR=$RUN/scripts-data
export MELEE_FONT_DIR=$PKG/assets/fonts MELEE_MENUTEX_DIR=$PKG/assets/ui MELEE_CACHE_DIR=$RUN/cache
export MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1 MELEE_SKIP_INTRO=1 MELEE_FPS=u MELEE_WINDOW_W=640 MELEE_WINDOW_H=480
export MELEE_SCENE="${SCENE}"
export MELEE_RB_LIVETEST=1 MELEE_RB_FAKE="${FAKE:-3,4,3}" MELEE_RB_INPUT=padgen MELEE_SNAP_VERIFY=${VERIFY:-1} MELEE_RB_LOG=0 MELEE_WRITEWATCH=${WW:-auto}
export MELEE_RB_HASHLOG=$RUN/hashes.csv
cd $RUN
timeout --kill-after=5 ${SECS:-120} $PKG/bin/melee --iso "/mnt/c/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso" > $RUN/run.log 2>&1
echo "melee rc=$?"
ls -la $RUN
grep -a -E "write-watch|snap:|VERIFY|rb: tick|DESYNC|fatal|FATAL|panic" $RUN/melee-pc.log | tail -80

#!/bin/bash
# job: the ACE disc, no scene (the launcher's way), a few runs, look for crashes
set -u
. /work/job.env
PKG=/work/pkg/melee-linux-i686
(Xvfb :99 -screen 0 1280x720x24 >/work/xvfb.log 2>&1 &) ; sleep 2
export DISPLAY=:99 SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.i686.json
export LD_LIBRARY_PATH=$PKG/lib
for i in $(seq 1 ${RUNS:-4}); do
  RUN=/work/ace_$i
  rm -rf $RUN; mkdir -p $RUN/{card,mods,scripts,scripts-data,cache}
  export MELEE_CARD_PATH=$RUN/card MELEE_MODS_DIR=$PKG/mods MELEE_SETTINGS_CFG=$RUN/settings.cfg MELEE_SCRIPTS_DIR=$PKG/scripts MELEE_SCRIPT_DATA_DIR=$RUN/scripts-data
  export MELEE_FONT_DIR=$PKG/assets/fonts MELEE_MENUTEX_DIR=$PKG/assets/ui MELEE_CACHE_DIR=$RUN/cache MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1 MELEE_WINDOW_W=640 MELEE_WINDOW_H=480
  export MELEE_WRITEWATCH=${WW:-auto}
  cd $RUN
  timeout --kill-after=5 ${SECS:-80} $PKG/bin/melee --iso "/mnt/c/SSBM ACE Build v2.0.0.iso" > $RUN/run.log 2>&1
  echo "run $i rc=$? $(grep -a -c . $RUN/melee-pc.log) log lines; last: $(tail -1 $RUN/melee-pc.log | cut -c1-120)"
  grep -a -E "PANIC|SIGSEGV|crash" $RUN/melee-pc.log | head -3
done

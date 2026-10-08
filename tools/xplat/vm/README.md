# A Linux 6.12 VM for the game (userfaultfd write-watch, MELEE_SNAP_VERIFY)

Why: the WSL2 kernel is 6.6, which has no `PAGEMAP_SCAN`, so the Linux write-watch (`pc/platform/gw_writewatch_linux.c`) cannot run
there. This boots Debian trixie's 6.12 kernel under QEMU/KVM (nested KVM works in WSL2 on Windows 11), chroots into the Ubuntu 22.04
32-bit rootfs `~/lb2/rootfs` (read-only, over 9p) and runs the real Linux game headless (Xvfb + lavapipe, no GPU needed).

    # once
    wsl -d Debian -u root chmod 666 /dev/kvm            # again after every WSL restart
    bash mkvm.sh ~/lb2/vm/linux-image-6.12.107+deb13-amd64-unsigned_6.12.107-1_amd64.deb
    mkdir -p ~/desync/work_x && cp -r <unpacked GDMelee-*-linux package> ~/desync/work_x/pkg   # the folder that holds melee-linux-i686
    cp vm_run.sh job_rb.sh ~/desync/work_x/ ; mv ~/desync/work_x/job_rb.sh ~/desync/work_x/job.sh
    printf "RUNNAME=run_x\nSECS=1500\nFAKE=3,4,3\nWW=auto\nSCENE='mode=vs;at=match;p1=fox/c0/hu/stocks99;p2=marth/c0/hu/stocks99;stage=fd;items=3;time=0'\n" > ~/desync/work_x/job.env
    WORK=~/desync/work_x bash runvm.sh ~/desync/vm/x.log 5G 6      # keep this wsl session open: a backgrounded qemu dies with it
    # results: ~/desync/work_x/run_x/melee-pc.log  (grep -a "VERIFY FAIL\|rb: tick\|DESYNC")

`job_rb.sh` is a fake-network rollback session (`MELEE_RB_LIVETEST=1 MELEE_RB_FAKE=lat,jitter,loss% MELEE_RB_INPUT=padgen`) with
`MELEE_SNAP_VERIFY=1`: after every dirty-page save and load the live MEM1 is compared with the slot, so a page the write-watch missed
shows as `snap: VERIFY FAIL`. `job_ace.sh` starts the ACE disc the launcher's way (no scene) a few times and reports crashes.
`THP=madvise|never` changes transparent huge pages (the Debian kernel default is `always`, Arch's is `madvise`).

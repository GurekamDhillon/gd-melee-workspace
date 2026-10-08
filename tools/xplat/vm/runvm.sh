#!/bin/bash
# runvm.sh <logfile> [mem] [smp]   boots the VM; the guest chroots into the Ubuntu 22.04 rootfs and runs /work/vm_run.sh
# env: WORK (the folder shared as /work), ROOTFS (default ~/lb2/rootfs, read-only), ISODIR (shared as /mnt/c, default /mnt/c/iso),
#      THP (always|madvise|never, default always), GW_VM_DIR.   Needs /dev/kvm writable (wsl -u root chmod 666 /dev/kvm).
D=${GW_VM_DIR:-$HOME/desync}
log=${1:-$D/vm/last.log}; mem=${2:-6G}; smp=${3:-6}
exec qemu-system-x86_64 -enable-kvm -cpu host -m $mem -smp $smp -nographic -no-reboot \
  -kernel $D/vm/vmlinuz -initrd $D/vm/initrd.gz -append "console=ttyS0 panic=-1 transparent_hugepage=${THP:-always} quiet loglevel=3" \
  -fsdev local,id=fs0,path=${ROOTFS:-$HOME/lb2/rootfs},security_model=none,readonly=on -device virtio-9p-pci,fsdev=fs0,mount_tag=rootfs \
  -fsdev local,id=fs1,path=${WORK:-$D/work},security_model=none -device virtio-9p-pci,fsdev=fs1,mount_tag=work \
  -fsdev local,id=fs2,path=${ISODIR:-/mnt/c/iso},security_model=none,readonly=on -device virtio-9p-pci,fsdev=fs2,mount_tag=iso \
  -serial file:$log -monitor none

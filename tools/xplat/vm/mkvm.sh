#!/bin/bash
# Build the 6.12 test VM's kernel + initramfs. Runs in WSL Debian (needs gcc, cpio, xz, kmod, dpkg-deb, qemu-system-x86).
#   mkvm.sh <linux-image-6.12*.deb>        (the Debian trixie image deb; ~/lb2/vm has one)
# Output: $D/vm/vmlinuz, $D/vm/initrd.gz  (D = $GW_VM_DIR, default ~/desync)
set -e
D=${GW_VM_DIR:-$HOME/desync}; HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
deb="${1:?usage: mkvm.sh <linux-image-6.12*.deb>}"
mkdir -p $D/k $D/vm $D/initrd/{dev,proc,sys,newroot,mods}
(cd $D/k && dpkg-deb -x "$deb" . && mkdir -p lib && ln -sfn ../usr/lib/modules lib/modules)
V=$(ls $D/k/usr/lib/modules)
depmod -b $D/k $V
i=0; rm -f $D/initrd/mods/*
for m in 9p 9pnet_virtio; do /usr/sbin/modprobe -d $D/k -S $V --show-depends -- $m; done | awk '!s[$0]++' | awk '{print $2}' | grep '\.ko' |
while read -r f; do i=$((i+1)); xz -dc "$f" > $D/initrd/mods/$(printf %02d $i)_$(basename "$f" .xz); done
gcc -O2 -static "$HERE/vminit.c" -o $D/initrd/init
(cd $D/initrd && find . | cpio -o -H newc 2>/dev/null | gzip -9 > $D/vm/initrd.gz)
cp $D/k/boot/vmlinuz-* $D/vm/vmlinuz
ls -la $D/vm

#!/bin/bash
# Rootless Ubuntu userspace, entirely stored in this workspace. Never mounts host /etc writable.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
fs="$root/_build/linux/ubuntu-rootfs"
[ -x "$fs/bin/bash" ] || { echo 'Extract the verified Ubuntu 22.04 base archive first' >&2; exit 1; }
mkdir -p "$fs/work" "$fs/proc" "$fs/dev" "$fs/tmp" "$fs/run"
exec bwrap --unshare-user --uid 0 --gid 0 --die-with-parent \
    --bind "$fs" / --bind "$root" /work \
    --ro-bind /etc/resolv.conf /etc/resolv.conf \
    --proc /proc --dev /dev --tmpfs /tmp --chdir /work \
    --setenv HOME /root --setenv GW_UBUNTU_ROOTLESS 1 --setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    /bin/bash "$@"

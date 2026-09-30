#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt=(apt-get -o APT::Sandbox::User=root)
# A single-user namespace cannot chown files to service accounts. These helpers
# are never used in this build-only rootfs; explicit root-owned, non-setuid
# overrides also keep their package scripts from attempting unmapped ownership.
if [ "${GW_UBUNTU_ROOTLESS:-0}" = 1 ]; then
    for helper in /usr/bin/ssh-agent /usr/lib/dbus-1.0/dbus-daemon-launch-helper; do
        if ! dpkg-statoverride --list "$helper" >/dev/null; then
            dpkg-statoverride --add root root 0755 "$helper"
        fi
    done
    printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
    chmod +x /usr/sbin/policy-rc.d
fi
dpkg --add-architecture i386
"${apt[@]}" update
"${apt[@]}" install -y ca-certificates curl gnupg python3 python3-pip git ninja-build pkg-config \
    build-essential gcc-multilib g++-multilib autoconf automake libtool xz-utils bzip2 \
    libpng-dev:i386 zlib1g-dev:i386 libfreetype6-dev:i386 libsqlite3-dev:i386 libzstd-dev:i386 \
    libasound2-dev:i386 libpulse-dev:i386 libudev-dev:i386 libx11-dev:i386 libx11-xcb-dev:i386 libxext-dev:i386 \
    libxrandr-dev:i386 libxcursor-dev:i386 libxi-dev:i386 libxfixes-dev:i386 libxss-dev:i386 libxinerama-dev:i386 libxtst-dev:i386 \
    libwayland-dev:i386 libxkbcommon-dev:i386 libvulkan-dev:i386 fonts-liberation2
curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --batch --yes --dearmor -o /usr/share/keyrings/llvm.gpg
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/llvm.gpg] https://apt.llvm.org/jammy/ llvm-toolchain-jammy-22 main' > /etc/apt/sources.list.d/llvm.list
"${apt[@]}" update
"${apt[@]}" install -y clang-22 llvm-22-dev lld-22
clang-22 --version | head -1 | grep -F '22.1.8'
python3 -m pip install 'cmake==3.31.6' 'ninja==1.11.1.1'
ln -sf /usr/bin/clang-22 /usr/local/bin/clang
ln -sf /usr/bin/clang++-22 /usr/local/bin/clang++
ln -sf /usr/bin/llvm-config-22 /usr/local/bin/llvm-config
ln -sf /usr/bin/ld.lld-22 /usr/local/bin/ld.lld
dpkg-query -W > /work/_build/linux/ubuntu-packages.txt

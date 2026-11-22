set -e
export PATH=$HOME/.cargo/bin:$PATH
mkdir -p ~/alsa-stub/lib ~/alsa-stub/pc
ln -sf /usr/lib/x86_64-linux-gnu/libasound.so.2 ~/alsa-stub/lib/libasound.so
cat > ~/alsa-stub/pc/alsa.pc <<P
Name: alsa
Description: stub
Version: 1.2.14
Libs: -L$HOME/alsa-stub/lib -lasound
Cflags:
P
ln -sf /usr/lib/x86_64-linux-gnu/libudev.so.1 ~/alsa-stub/lib/libudev.so
cat > ~/alsa-stub/pc/libudev.pc <<P
Name: libudev
Description: stub
Version: 257
Libs: -L$HOME/alsa-stub/lib -ludev
Cflags:
P
export PKG_CONFIG_PATH=$HOME/alsa-stub/pc
cd "/mnt/e/Projects/Melee Workspace/worktrees/plat-release/rust"
export CARGO_PROFILE_DEV_DEBUG=0 CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=$HOME/melee-target
cargo build --release -p melee 2>&1 | tail -40

export PATH=$HOME/.cargo/bin:$PATH
set -e
W="/mnt/e/Projects/Melee Workspace/worktrees"
export CARGO_TARGET_DIR=$HOME/melee-target-rel
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'
cd "$W/rust-release"
bash tools/release/build_rust.sh --melee "$W/plat-release" 2>&1 | tail -25

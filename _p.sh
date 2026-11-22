set -e
W="/mnt/e/Projects/Melee Workspace"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'
cd "$W/worktrees/rust-release"
set -a; . "$W/.env"; set +a
iso="$GW_ISO_VANILLA"; case "$iso" in [A-Za-z]:*) iso="$(wslpath -u "$iso")";; esac
bash tools/release/smoke_release_linux.sh --repo-root "$W" --package "$W/_build/agents/plat-release/out/GDMelee-0.3.0-rs1-rust-linux64-local.tar.xz" --iso "$iso" 2>&1 | grep -v Segmentation

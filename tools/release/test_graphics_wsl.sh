#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# CMake's RCC/Ninja invocation mishandles the apostrophe in the Windows root.
# Test a copy on the Linux filesystem, then return evidence to the worktree.
task_dir=/tmp/gd-linux-graphics-test
mkdir -p "$task_dir/tools/release" "$task_dir/menu" "$task_dir/_build"
cp -a tools/release/launcher "$task_dir/tools/release/"
cp -a menu/SourceSans3 "$task_dir/menu/"
cp -a _build/ui "$task_dir/_build/"
cmake -S "$task_dir/tools/release/launcher/qt" -B "$task_dir/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DLAUNCHER_DEPLOY_QT=OFF
cmake --build "$task_dir/build" -j 8
ctest --test-dir "$task_dir/build" --output-on-failure
mkdir -p _build/graphics-test
cp "$task_dir/build/launcher-tests.txt" _build/graphics-test/

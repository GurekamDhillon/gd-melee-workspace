#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
src="$root/_build/linux/libusb-src"
build="${GW_LIBUSB_BUILD:-$root/_build/linux/libusb}"
[ -f "$src/configure" ] || { echo 'Extract libusb 1.0.29 into _build/linux/libusb-src first' >&2; exit 1; }
mkdir -p "$build"
cd "$build"
CC=clang CFLAGS='-m32 -O2 -g' LDFLAGS=-m32 "$src/configure" --disable-shared --enable-static --disable-udev --prefix="$build/install"
make -j "${GW_JOBS:-8}"
make install

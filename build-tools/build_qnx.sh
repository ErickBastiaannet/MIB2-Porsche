#!/bin/sh
# Run in the locally built QNX 6.5 ARMv7 GCC container; never on the car.
set -eu
root=${1:-/src}
cc=arm-unknown-nto-qnx6.5.0eabi-gcc
ar=arm-unknown-nto-qnx6.5.0eabi-ar
readelf=arm-unknown-nto-qnx6.5.0eabi-readelf
test "$("$cc" -dumpversion)" = 4.9.4
work=$(mktemp -d /tmp/porsche-qnx-build-XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
flags='-std=gnu99 -O2 -Wall -Wextra -Werror -Wno-unused-function -mno-unaligned-access -fPIC'
for profile in handshake_probe capture_receiver; do
    "$cc" $flags -shared -I"$root/build/native" -I"$root/native" \
        "$root/build/native/porsche_$profile.c" \
        "$root/native/porsche_geometry.c" "$root/native/porsche_geometry_file.c" \
        -lsocket -o "$work/libcw-porsche-$profile.so"
done
"$cc" $flags -shared -I"$root/native" \
    "$root/native/porsche_rgi_hook.c" "$root/native/porsche_rgi.c" \
    -o "$work/libcw-porsche-rgi.so"
for component in geometry geometry_file session nvss window window_loader yuv yuv_gl yuv_capture parser pixels frame_quality; do
    "$cc" $flags -I"$root/native" -c "$root/native/porsche_$component.c" -o "$work/$component.o"
done
"$cc" $flags -I"$root/native" -I"$root/build/native" \
    "$root/native/porsche_unit.c" "$root/native/porsche_sha256.c" \
    "$root/native/porsche_wire.c" "$root/native/porsche_dm.c" "$root/native/porsche_jar.c" \
    "$root/native/porsche_geometry.c" "$root/native/porsche_geometry_file.c" \
    "$root/native/porsche_session.c" "$root/native/porsche_nvss.c" \
    -lsocket -o "$work/porsche-carplay"
"$cc" $flags -s -DCW_YUV_RENDERER -Wl,-E -I"$root/native" -I"$root/build/native" \
    "$root/native/porsche_unit.c" "$root/native/porsche_sha256.c" \
    "$root/native/porsche_wire.c" "$root/native/porsche_dm.c" "$root/native/porsche_jar.c" \
    "$root/native/porsche_geometry.c" "$root/native/porsche_geometry_file.c" \
    "$root/native/porsche_session.c" "$root/native/porsche_nvss.c" \
    "$root/native/porsche_yuv.c" "$root/native/porsche_yuv_capture.c" "$root/native/porsche_parser.c" "$root/native/porsche_pixels.c" \
    "$root/native/porsche_yuv_gl.c" "$root/native/porsche_frame_quality.c" "$root/native/porsche_window.c" \
    "$root/native/porsche_window_loader.c" -lsocket -o "$work/porsche-carplay-window-candidate"
"$ar" rcs "$work/libcw-porsche-core.a" "$work/geometry.o" "$work/geometry_file.o" "$work/session.o" "$work/nvss.o" "$work/window.o" "$work/window_loader.o" "$work/yuv.o" "$work/yuv_gl.o" "$work/yuv_capture.o" "$work/parser.o" "$work/pixels.o" "$work/frame_quality.o"
"$cc" $flags -s -Wl,-E -I"$root/native" "$root/unit-query/hidden_yuv.c" \
    "$root/native/porsche_yuv.c" "$root/native/porsche_yuv_capture.c" "$root/native/porsche_parser.c" "$root/native/porsche_pixels.c" \
    "$root/native/porsche_nvss.c" "$root/native/porsche_dm.c" \
    "$root/native/porsche_sha256.c" -lsocket -o "$work/cw-hidden-yuv"
"$cc" $flags -s -DCW_HIDDEN_YUV_LIBRARY -Wl,-E -I"$root/native" "$root/unit-query/hidden_yuv.c" "$root/unit-query/hidden_yuv_window.c" \
    "$root/native/porsche_yuv.c" "$root/native/porsche_yuv_capture.c" "$root/native/porsche_parser.c" "$root/native/porsche_pixels.c" \
    "$root/native/porsche_yuv_gl.c" "$root/native/porsche_window.c" "$root/native/porsche_window_loader.c" \
    "$root/native/porsche_nvss.c" "$root/native/porsche_dm.c" \
    "$root/native/porsche_sha256.c" -lsocket -o "$work/cw-hidden-yuv-window"
"$cc" $flags -I"$root/native" "$root/unit-query/window_selftest.c" \
    "$root/native/porsche_window.c" "$root/native/porsche_window_loader.c" \
    "$root/native/porsche_dm.c" "$root/native/porsche_sha256.c" \
    -lsocket -o "$work/cw-window-selftest"
"$cc" $flags -shared "$root/unit-query/query_stdio.c" -o "$work/libcw-query-stdio.so"
"$cc" $flags -s -I"$root/native" "$root/unit-query/ram_receive.c" \
    -lsocket -o "$work/cw-ram-receive"
mkdir -p "$root/build/qnx"
cp "$work/porsche-carplay" "$root/build/qnx/porsche-carplay"
cp "$work/porsche-carplay-window-candidate" "$root/build/qnx/porsche-carplay-window-candidate"
cp "$work/cw-window-selftest" "$root/build/qnx/cw-window-selftest"
cp "$work/cw-hidden-yuv" "$root/build/qnx/cw-hidden-yuv"
cp "$work/cw-hidden-yuv-window" "$root/build/qnx/cw-hidden-yuv-window"
cp "$work/cw-ram-receive" "$root/build/qnx/cw-ram-receive"
for file in "$work/"*.so "$work/"*.a; do
    name=${file##*/}
    cp "$file" "$root/build/qnx/$name"
    "$readelf" -W -h -A "$file" > "$root/build/qnx/$name.readelf.txt"
done
cd "$root"
sha256sum native/* build/native/* unit-query/query_stdio.c unit-query/window_selftest.c unit-query/hidden_yuv.c unit-query/hidden_yuv_window.c unit-query/ram_receive.c build-tools/prepare_native.py build-tools/build_qnx.sh unit/dio_manager.sh > build/qnx/sources.sha256
sha256sum build/qnx/porsche-carplay build/qnx/porsche-carplay-window-candidate build/qnx/cw-window-selftest build/qnx/cw-hidden-yuv build/qnx/cw-hidden-yuv-window build/qnx/cw-ram-receive build/qnx/*.so > build/qnx/artifacts.sha256
echo "PORSCHE_QNX_BUILD_PASS ARM EABI5; receiver libraries, window/session archive, isolated window diagnostic"

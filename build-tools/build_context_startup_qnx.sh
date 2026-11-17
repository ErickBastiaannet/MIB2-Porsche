#!/bin/sh
set -eu
root=${1:-/src}
out=$root/build/context-startup
cc=arm-unknown-nto-qnx6.5.0eabi-gcc
"$cc" -std=gnu99 -O2 -Wall -Wextra -Werror -Wno-unused-function -mno-unaligned-access -fPIC -s -DCW_YUV_RENDERER -Wl,-E \
 -I"$root/native" -I"$root/build/native" \
 "$out/porsche_unit.c" "$root/native/porsche_sha256.c" "$root/native/porsche_wire.c" \
 "$root/native/porsche_dm.c" "$root/native/porsche_jar.c" "$root/native/porsche_geometry.c" \
 "$root/native/porsche_geometry_file.c" "$root/native/porsche_session.c" "$root/native/porsche_nvss.c" \
 "$root/native/porsche_yuv.c" "$root/native/porsche_yuv_capture.c" "$root/native/porsche_parser.c" \
 "$root/native/porsche_pixels.c" "$root/native/porsche_yuv_gl.c" "$root/native/porsche_frame_quality.c" \
 "$root/native/porsche_window.c" "$root/native/porsche_window_loader.c" -lsocket -o "$out/cw-window-startup"
echo CONTEXT_STARTUP_QNX_BUILD_PASS

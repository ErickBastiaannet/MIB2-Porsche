#!/bin/sh
# Local Linux fixtures only. No QNX output devices are accessed.
set -eu
root=${1:-/src}
work=$(mktemp -d /tmp/porsche-carplay-test-XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
flags='-std=gnu99 -Wall -Wextra -Werror -fno-pie -no-pie -fsanitize=address,undefined -g'
cc $flags -I"$root/native" "$root/native/porsche_rgi.c" "$root/tests/test_rgi.c" -o "$work/rgi"
"$work/rgi"
cc $flags -I"$root/native" \
  "$root/native/porsche_geometry.c" "$root/native/porsche_geometry_file.c" \
  "$root/native/porsche_session.c" "$root/tests/test_session.c" -o "$work/session"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/session" "$root/build/geometry.record" >"$work/session.log" 2>&1
cat "$work/session.log"
cc $flags -Wno-unused-function -Wno-unused-variable -I"$root/build/native" \
  "$root/build/native/test_display.c" "$root/native/porsche_geometry.c" \
  "$root/native/porsche_geometry_file.c" -ldl -pthread -o "$work/display"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/display" >"$work/display.log" 2>&1
cat "$work/display.log"
cc $flags -I"$root/native" "$root/native/porsche_nvss.c" \
  "$root/tests/test_nvss.c" -o "$work/nvss"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/nvss" >"$work/nvss.log" 2>&1
cat "$work/nvss.log"
cc $flags -I"$root/native" "$root/native/porsche_frame_quality.c" \
  "$root/tests/test_frame_quality.c" -o "$work/frame-quality"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/frame-quality" >"$work/frame-quality.log" 2>&1
cat "$work/frame-quality.log"
cc $flags -Wno-unused-function -Wno-unused-variable -I"$root/build/native" \
  "$root/build/native/test_capture_display.c" "$root/native/porsche_geometry.c" \
  "$root/native/porsche_geometry_file.c" -ldl -pthread -o "$work/capture-display"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/capture-display" >"$work/capture-display.log" 2>&1
cat "$work/capture-display.log"
cc $flags -Wno-unused-function -Wno-unused-variable -I"$root/build/native" \
  "$root/tests/test_listener.c" "$root/native/porsche_geometry.c" \
  "$root/native/porsche_geometry_file.c" -ldl -pthread -o "$work/listener"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/listener"
cc $flags -I"$root/native" "$root/native/porsche_sha256.c" \
  "$root/native/porsche_wire.c" "$root/native/porsche_dm.c" \
  "$root/tests/test_support.c" -o "$work/support"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/support" "$work" "$root/tests/fixtures/panamera-mu1417-contexts.txt" >"$work/support.log" 2>&1
cat "$work/support.log"
cc $flags -Wno-misleading-indentation -I"$root/native" "$root/native/porsche_window.c" \
  "$root/tests/test_window.c" -o "$work/window"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/window" >"$work/window.log" 2>&1
cat "$work/window.log"
cc $flags -I"$root/native" "$root/native/porsche_yuv.c" \
  "$root/tests/test_yuv.c" -pthread -o "$work/yuv"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/yuv"
cc $flags -I"$root/native" "$root/tests/test_yuv_gl.c" -ldl -o "$work/yuv-gl"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/yuv-gl"
cc $flags -I"$root/native" "$root/native/porsche_yuv.c" \
  "$root/tests/test_yuv_capture.c" -pthread -ldl -o "$work/yuv-capture"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/yuv-capture"
cc $flags -I"$root/native" "$root/tests/test_parser.c" -ldl -o "$work/parser"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/parser"
cc $flags -I"$root/native" "$root/native/porsche_pixels.c" \
  "$root/tests/test_pixels.c" -o "$work/pixels"
ASAN_OPTIONS=handle_segv=0:halt_on_error=1:detect_leaks=1 \
  timeout -k 1 15 "$work/pixels"

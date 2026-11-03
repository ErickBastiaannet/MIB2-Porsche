#!/bin/sh
set -eu
root=${1:-/src}
mkdir -p "$root/build/host-test"
flags='-std=gnu99 -O1 -g -Wall -Wextra -Werror -Wno-misleading-indentation'
cc $flags -DCW_RUNTIME='"/tmp/cw-runtime"' -DCW_DMDT='"/tmp/cw-runtime/dmdt"' \
  -DCW_DISPLAY_CONFIG='"/tmp/cw-runtime/dm-profile"' \
  -DCW_DISPLAY_CONFIG_SHA='"9a971b17b2d01db1d4a80ccd749d6c6ce5206b23ce0989071432c3dd894b40a9"' \
  -I"$root/native" -I"$root/build/native" \
  "$root/native/porsche_unit.c" "$root/native/porsche_sha256.c" "$root/native/porsche_jar.c" \
  "$root/native/porsche_wire.c" "$root/native/porsche_dm.c" \
  "$root/native/porsche_geometry.c" "$root/native/porsche_geometry_file.c" \
  "$root/native/porsche_session.c" "$root/native/porsche_nvss.c" -ldl \
  -o "$root/build/host-test/porsche-carplay"
cc $flags -shared -fPIC -I"$root/native" "$root/tests/fake_nvss.c" -o "$root/build/host-test/libnvss_video.so"
cc $flags -shared -fPIC "$root/unit-query/query_stdio.c" -o "$root/build/host-test/libcw-query-stdio.so"
cc $flags -DCW_RUNTIME='"/tmp/cw-runtime"' -DCW_DMDT='"/tmp/cw-runtime/dmdt"' \
  -DCW_DISPLAY_CONFIG='"/tmp/cw-runtime/dm-profile"' \
  -DCW_DISPLAY_CONFIG_SHA='"9a971b17b2d01db1d4a80ccd749d6c6ce5206b23ce0989071432c3dd894b40a9"' \
  -I"$root/native" "$root/unit-query/visible_decode.c" "$root/native/porsche_nvss.c" \
  "$root/native/porsche_dm.c" "$root/native/porsche_wire.c" "$root/native/porsche_sha256.c" -ldl \
  -o "$root/build/host-test/cw-visible-decode"
cc $flags -DCW_RUNTIME='"/tmp/cw-runtime"' -DCW_DMDT='"/tmp/cw-runtime/dmdt"' \
  -DCW_DISPLAY_CONFIG='"/tmp/cw-runtime/dm-profile"' \
  -DCW_DISPLAY_CONFIG_SHA='"9a971b17b2d01db1d4a80ccd749d6c6ce5206b23ce0989071432c3dd894b40a9"' \
  -I"$root/native" -I"$root/tests" "$root/unit-query/visible_window.c" \
  "$root/native/porsche_window.c" "$root/tests/fake_window_loader.c" \
  "$root/native/porsche_dm.c" "$root/native/porsche_wire.c" "$root/native/porsche_sha256.c" \
  -o "$root/build/host-test/cw-visible-window"

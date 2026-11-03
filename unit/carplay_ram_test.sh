#!/bin/sh
# Bounded MU1417 field test. Nothing below writes /mnt/app.
set -u
SD=
for CANDIDATE in /fs/sda0 /fs/sdb0; do
    if [ -s "$CANDIDATE/online/carplay-ram/porsche-carplay" ]; then SD=$CANDIDATE; break; fi
done
[ -n "$SD" ] || { echo "ERROR: RAM-test payload ontbreekt"; exit 1; }
SOURCE="$SD/online/carplay-ram"
ROOT=/ramdisk/connectwow-carplay-test
STOCK=/mnt/app/eso/bin/apps/dio_manager.cw-stock
[ -x "$STOCK" ] || { echo "ERROR: originele DIO-back-up ontbreekt; herstel eerst stock"; exit 1; }
rm -rf "$ROOT" && mkdir -p "$ROOT" || exit 1
for NAME in porsche-carplay libcw-porsche-capture_receiver.so libcw-porsche-rgi.so libcw-query-stdio.so payload.manifest; do
    cp "$SOURCE/$NAME" "$ROOT/$NAME" || exit 1
done
chmod 755 "$ROOT/porsche-carplay" || exit 1
while IFS=' ' read -r EXPECTED NAME; do
    [ "$("$ROOT/porsche-carplay" --hash "$ROOT/$NAME")" = "$EXPECTED" ] || {
        echo "ERROR: beschadigd bestand $NAME"; exit 1;
    }
done < "$ROOT/payload.manifest"
rm -f /ramdisk/cw-porsche-alt-ring.bin /ramdisk/cw-porsche-altstream.ready \
    /ramdisk/cw-carplay-ready.v1 /ramdisk/cw-porsche-airplay.log \
    /ramdisk/cw-porsche-carplay.log /ramdisk/cw-porsche-rgi.log
"$ROOT/porsche-carplay" --prime-geometry "$ROOT" >"$ROOT/prime.log" 2>&1 || {
    echo "ERROR: geometrie kon niet worden bepaald"; exit 1;
}
(
    CARPLAY_ALTSCREEN_ENABLE=1
    CARPLAY_ALTSCREEN_LOG=/ramdisk/cw-porsche-airplay.log
    CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture
    CW_RGI_ENABLE=0
    LD_PRELOAD="$ROOT/libcw-porsche-rgi.so:$ROOT/libcw-porsche-capture_receiver.so"
    export CARPLAY_ALTSCREEN_ENABLE CARPLAY_ALTSCREEN_LOG CARPLAY_ALTSCREEN_CAPTURE_DIR CW_RGI_ENABLE LD_PRELOAD
    exec "$STOCK"
) >"$ROOT/dio.log" 2>&1 &
CHILD=$!
(
    unset LD_PRELOAD
    LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib
    export LD_LIBRARY_PATH
    exec "$ROOT/porsche-carplay" --run-test "$ROOT" "$CHILD" 60
) >"$ROOT/supervisor.log" 2>&1 &
SUPERVISOR=$!
echo "RAM-test actief: verbind CarPlay en open Apple Kaarten. Maximaal 60 seconden."
wait "$SUPERVISOR"
RESULT=$?
kill -TERM "$CHILD" 2>/dev/null
wait "$CHILD" 2>/dev/null
mount -uw "$SD" 2>/dev/null
mkdir -p "$SD/connectwow-carplay-logs"
OUT="$SD/connectwow-carplay-logs/latest"
rm -rf "$OUT" && mkdir -p "$OUT"
for FILE in "$ROOT"/*.log /ramdisk/cw-porsche-*.log /ramdisk/cw-carplay-*.v1 /ramdisk/cw-carplay-*.v3; do
    [ -f "$FILE" ] && cp "$FILE" "$OUT/${FILE##*/}"
done
if [ -s /ramdisk/cw-carplay-ready.v1 ]; then
    echo DISPLAY_ACTIVE > "$OUT/result.txt"
else
    echo NO_VALID_VIDEO > "$OUT/result.txt"
fi
echo "supervisor_exit=$RESULT" >> "$OUT/result.txt"
mount -ur "$SD" 2>/dev/null
echo "Test klaar: $OUT/result.txt"
exit 0

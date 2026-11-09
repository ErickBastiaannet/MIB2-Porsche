#!/bin/ksh
# One-probe-boot HMI wrapper. An unconfirmed candidate automatically falls
# back to the stock HMI on the next boot, so a bad bridge cannot loop forever.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
JAR=$ROOT/PorscheCarPlayBridge.experimental.jar
STATE=/mnt/persist/connectwow-carplay/controls-v15
COMPLETE=1
for REQUIRED in installed.manifest enabled cw-window-candidate cw-receiver-controls.so cw-rgi.so libcw-query-stdio.so launcher.sh; do
    [ -s "$ROOT/$REQUIRED" ] || COMPLETE=0
done
SDLOG=
for SD in /fs/sda0 /fs/sdb0; do
    if [ -d "$SD" ]; then SDLOG=$SD/connectwow-carplay-logs/v15; break; fi
done
[ -z "$SDLOG" ] || { mkdir -p "$SDLOG"; echo "HMI wrapper start profile=15" > "$SDLOG/hmi-boot.txt"; }

if [ "$COMPLETE" -eq 1 ] && [ -s "$ROOT/confirmed" ] && [ -s "$JAR" ]; then
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
    export VMOPTIONS
    [ -z "$SDLOG" ] || echo "full hook=confirmed" >> "$SDLOG/hmi-boot.txt"
elif [ "$COMPLETE" -eq 1 ] && [ -s "$STATE/pending" ] && [ -s "$JAR" ]; then
    # /mnt/app is read-only during a normal boot. Consume the one-shot ticket
    # on the writable persist volume so a failed candidate cannot load again.
    rm -f "$STATE/pending"
    echo attempted > "$STATE/attempted"
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
    export VMOPTIONS
    [ -z "$SDLOG" ] || echo "full hook=one-shot" >> "$SDLOG/hmi-boot.txt"
else
    [ -z "$SDLOG" ] || echo "full hook=stock-fallback" >> "$SDLOG/hmi-boot.txt"
fi

exec /bin/ksh "$STOCK" "$@"

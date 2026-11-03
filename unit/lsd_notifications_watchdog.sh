#!/bin/ksh
# One-probe-boot wrapper for the isolated CarPlay notification class only.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/v14-6
STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
JAR=$ROOT/PorscheCarPlayNotifications.experimental.jar
SDLOG=
for SD in /fs/sda0 /fs/sdb0; do
    if [ -d "$SD" ]; then SDLOG=$SD/connectwow-carplay-logs/v14-6; break; fi
done
if [ -n "$SDLOG" ]; then
    mkdir -p "$SDLOG"
    echo "HMI wrapper start profile=14.6" > "$SDLOG/hmi-boot.txt"
fi

if [ -s "$ROOT/confirmed" ] && [ -s "$JAR" ]; then
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
    export VMOPTIONS
    [ -z "$SDLOG" ] || echo "notification hook=confirmed" >> "$SDLOG/hmi-boot.txt"
elif [ -s "$ROOT/pending" ] && [ -s "$JAR" ]; then
    rm -f "$ROOT/pending"
    echo attempted > "$ROOT/attempted"
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
    export VMOPTIONS
    [ -z "$SDLOG" ] || echo "notification hook=one-shot" >> "$SDLOG/hmi-boot.txt"
else
    [ -z "$SDLOG" ] || echo "notification hook=stock-fallback" >> "$SDLOG/hmi-boot.txt"
fi

exec /bin/ksh "$STOCK" "$@"

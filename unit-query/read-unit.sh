#!/bin/sh
# Read existing registrations only. Does not install a JAR, route video or reboot.
set -u
umask 077
BASE=${0%/*}
case "$BASE" in "$0"|"") echo "ERROR: use the absolute SD-card script path"; exit 1;; esac
FIXTURE=0
if [ "${1:-}" = "--fixture-root" ]; then
    FIXTURE=1
    MMX=${2:?Missing fixture root}
    BASE=${3:?Missing fixture output}
elif [ "${1:-}" = "--mmx-child" ]; then
    MMX=
elif [ -r /net/mmx/ifs/lsd.jxe ]; then
    command -v on >/dev/null 2>&1 || { echo "ERROR: MMX dispatch unavailable"; exit 1; }
    case "$0" in /net/mmx/*) SCRIPT=${0#/net/mmx};; *) SCRIPT=$0;; esac
    exec on -f mmx sh "$SCRIPT" --mmx-child
elif [ -r /ifs/lsd.jxe ]; then
    MMX=
else
    echo "ERROR: MMX firmware not found; nothing changed"
    exit 1
fi
DMDT="$MMX/eso/bin/apps/dmdt"
[ -x "$DMDT" ] || { echo "ERROR: dmdt unavailable"; exit 1; }
[ -r "$BASE/libcw-query-stdio.so" ] || { echo "ERROR: SD query helper missing"; exit 1; }
OUT="$BASE/porsche-runtime-$$"
mkdir "$OUT" || exit 1
FAILED=0
for query in gd gc gs; do
    if [ "$FIXTURE" -eq 1 ]; then
        "$DMDT" "$query" > "$OUT/$query.txt" 2>&1
        STATUS=$?
    else
        LD_PRELOAD="$BASE/libcw-query-stdio.so" \
        LD_LIBRARY_PATH=/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib \
        IPL_CONFIG_DIR=/etc/eso/production \
        "$DMDT" "$query" > "$OUT/$query.txt" 2>&1
        STATUS=$?
    fi
    FOUND=0
    while IFS= read -r line; do
        case "$query:$line" in
            gd:*"displaymanager knows "*"displayables:"*) FOUND=1;;
            gc:*"displaymanager knows "*"contexts:"*) FOUND=1;;
            gs:*"displaymanager reports the following system information:"*) FOUND=1;;
        esac
    done < "$OUT/$query.txt"
    if [ "$STATUS" -ne 0 ] || [ "$FOUND" -ne 1 ]; then
        echo "ERROR: $query response incomplete (status $STATUS)"
        FAILED=1
    fi
done
{
    echo "Read-only runtime query; no video routing, installation or reboot."
    echo "=== Existing HMI image size ==="
    ls -ln "$MMX/ifs/lsd.jxe"
    echo "=== Existing cluster flags ==="
    for flag in enableKombiMapMOST enableKombiMapFPK; do
        if [ -e "$MMX/mnt/app/eso/hmi/$flag" ]; then echo "$flag: present"; else echo "$flag: absent"; fi
    done
    echo "=== MOST device nodes (listing only) ==="
    ls -l "$MMX/dev/mlb/isoTX2" "$MMX/dev/mlb/debug/isoTX2"
} > "$OUT/unit.txt" 2>&1
echo "=== System/display sizes and active contexts ==="
while IFS= read -r line; do echo "$line"; done < "$OUT/gs.txt"
if [ "$FAILED" -ne 0 ]; then
    echo "INCOMPLETE: $OUT (reports retained; no unit files changed)"
    exit 1
fi
echo "COMPLETE: $OUT"
echo "Original unit files, certificates, hosts and settings were not changed."

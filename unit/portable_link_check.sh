#!/bin/ksh
set -e
cd "$(dirname "$0")"
unset LD_PRELOAD || :
JAVA_HOME=/ifs/jre
export JAVA_HOME
LD_LIBRARY_PATH=/ifs/jre/bin:/armle/lib:/armle/usr/lib:/eso/lib
export LD_LIBRARY_PATH
CW_LINK_JAR=$(pwd)/PorscheNavigationPriority.test.jar
[ -s "$CW_LINK_JAR" ] || exit 1
/armle/usr/bin/env JAVA_HOME=/ifs/jre LD_LIBRARY_PATH=/ifs/jre/bin:/armle/lib:/armle/usr/lib:/eso/lib /ifs/jre/bin/j9 -Xverify:all -Xmx32m -Xbootclasspath:/ifs/lsd.jxe -Xbootclasspath/p:$CW_LINK_JAR org.connectwow.tests.RuntimeLinkProbe de.audi.tghu.navi.app.cluster.CombiBAPListener de.audi.tghu.navi.app.cluster.ClusterService de.audi.tghu.navi.app.cluster.PorscheRouteGuidance de.audi.tghu.navi.app.cluster.NavigationPriorityRuntime de.audi.tghu.navi.app.dsi.DSINavigationDispatcher org.connectwow.carplay.PorscheCluster org.connectwow.carplay.PorscheClusterControls org.connectwow.carplay.PorscheNavigationPriority > link-check.log 2>&1 &
CW_LINK_PID=$!
function cw_link_cleanup {
    trap - 0
    if [ "$CW_LINK_PID" -gt 1 ]; then
        kill -TERM "$CW_LINK_PID" 2>/dev/null || :
        sleep 1
        kill -KILL "$CW_LINK_PID" 2>/dev/null || :
        wait "$CW_LINK_PID" 2>/dev/null || :
    fi
}
trap cw_link_cleanup 0
trap 'exit 1' 1 2 15
CW_LINK_COUNT=0
while kill -0 "$CW_LINK_PID" 2>/dev/null && [ "$CW_LINK_COUNT" -lt 20 ]; do
    sleep 1
    CW_LINK_COUNT=$((CW_LINK_COUNT+1))
done
if kill -0 "$CW_LINK_PID" 2>/dev/null; then
    kill -TERM "$CW_LINK_PID" 2>/dev/null || :
    sleep 1
    kill -KILL "$CW_LINK_PID" 2>/dev/null || :
    wait "$CW_LINK_PID" 2>/dev/null || :
    CW_LINK_PID=0
    echo PRIORITY_J9_LINK_TIMEOUT
    exit 1
fi
CW_LINK_RC=0
wait "$CW_LINK_PID" || CW_LINK_RC=$?
CW_LINK_PID=0
cat link-check.log
[ "$CW_LINK_RC" -eq 0 ] || exit 1
echo PRIORITY_J9_LINK_PASS

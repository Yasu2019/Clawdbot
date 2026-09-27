#!/bin/bash
# INC-188: start the next run as soon as the current one ends (keeps the engine slot busy).
# usage: launch_after.sh <current_tag> <next_tag> [nt]
# Waits until no engine for <current_tag> is alive AND its newest log shows NORMAL or ERROR
# TERMINATION (a crash without either is left to the watchdog's auto-resume). Then launches
# <next_tag> with chain_P1r19_21.sh and adds it to the watchdog tag file (current tag kept so the
# watchdog still auto-finalizes it). Log: data/workspace/launch_after_log.txt
export MSYS_NO_PATHCONV=1
CUR=$1; NEXT=$2; NT=${3:-12}
R="D:/Clawdbot_Docker_20260125"; W="$R/clawstack_v2/data/work"; WS="$R/data/workspace"
C=clawstack-unified-openradioss-1
LOG="$WS/launch_after_log.txt"
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
log "waiting for $CUR to end, then launch $NEXT (nt=$NT)"
while true; do
  alive=$(docker exec $C bash -c 'for p in /proc/[0-9]*; do c=$(tr "\0" " " < $p/cmdline 2>/dev/null); case "$c" in /opt/openradioss/*engine_linux64_gf*"-i PANEL4MM_'"$CUR"'_"*) echo 1;; esac; done' 2>/dev/null)
  f=$(ls -t "$W"/engine_run$CUR.log "$W"/engine_run${CUR}_r*.log 2>/dev/null | head -1)
  end=$(tail -60 "$f" 2>/dev/null | grep -o "NORMAL TERMINATION\|ERROR TERMINATION" | head -1)
  if [ -z "$alive" ] && [ -n "$end" ]; then break; fi
  sleep 120
done
log "$CUR ended: $end ($f)"
[ -f "$W/PANEL4MM_${NEXT}_0000.rad" ] || { log "deck for $NEXT missing - abort"; exit 2; }
printf '%s\n%s\n' "$CUR" "$NEXT" > "$WS/openradioss_watch_tags.txt"
docker exec -d -e TAGS="$NEXT" -e NT="$NT" $C bash /work/chain_P1r19_21.sh && log "launched $NEXT" || log "launch of $NEXT FAILED"

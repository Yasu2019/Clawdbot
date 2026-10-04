#!/bin/bash
# INC-188: resume <resume_tag> as soon as <wait_tag> has ended (NORMAL or ERROR TERMINATION and no
# engine alive), then put the held queue back. Used 2026-10-04 to finish P1r25f (solver crashed with
# a segmentation violation at standard 0.5675 ms) before continuing the already-started P1r26f.
# usage: resume_after.sh <wait_tag> <resume_tag> [nt]
# While it waits: <resume_tag> is not in the watch tags (no auto-resume), the queue sits in
# openradioss_queue.hold.txt (nothing new is launched). Log: data/workspace/launch_after_log.txt
export MSYS_NO_PATHCONV=1
WAIT=$1; RES=$2; NT=${3:-12}
R="D:/Clawdbot_Docker_20260125"; W="$R/clawstack_v2/data/work"; WS="$R/data/workspace"
C=clawstack-unified-openradioss-1
LOG="$WS/launch_after_log.txt"
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
log "resume_after: waiting for $WAIT to end, then resume $RES (nt=$NT)"
while true; do
  alive=$(docker exec $C bash /work/engine_ctl.sh any 2>/dev/null | awk -v t="$WAIT" '$2==t')
  f=$(ls -t "$W"/engine_run$WAIT.log "$W"/engine_run${WAIT}_r*.log 2>/dev/null | head -1)
  end=$(tail -60 "$f" 2>/dev/null | grep -o "NORMAL TERMINATION\|ERROR TERMINATION" | head -1)
  [ -z "$alive" ] && [ -n "$end" ] && break
  sleep 60
done
log "resume_after: $WAIT ended ($end, $(basename "$f"))"
grep -qx "$RES" "$WS/openradioss_watch_tags.txt" || echo "$RES" >> "$WS/openradioss_watch_tags.txt"
echo "$(date '+%Y-%m-%d %H:%M:%S') resume_after $RES" > "$WS/.memcap.lock"
out=$(docker exec -e NT=$NT $C bash /work/openradioss_restart_prep.sh "$RES" --go 2>&1 | grep -E "restart file|LAUNCHED|ABORT|REFUSE")
log "resume_after: resume $RES -> $out"
echo "$(date '+%Y-%m-%d %H:%M:%S') $RES: resumed by resume_after.sh after $WAIT ended ($end): $(echo "$out" | grep -E 'LAUNCHED|ABORT|REFUSE' | cut -c1-80)" >> "$WS/ALARM_openradioss_p1r13_16.txt"
if [ -s "$WS/openradioss_queue.hold.txt" ]; then
  cat "$WS/openradioss_queue.hold.txt" >> "$WS/openradioss_queue.txt" && rm -f "$WS/openradioss_queue.hold.txt"
  log "resume_after: queue restored: $(tr '\n' ' ' < "$WS/openradioss_queue.txt")"
fi

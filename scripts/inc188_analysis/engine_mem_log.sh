#!/bin/bash
# INC-188: log OpenRadioss engine memory against simulated time (one line per INTERVAL s).
# Output: data/workspace/engine_mem_log.tsv  (local time, tag, RSS MB, peak RSS MB, T from the newest engine log)
# Runs forever (waits while no engine is alive); single instance (lock), kept alive by c0_bisect_keeper.ps1.
export MSYS_NO_PATHCONV=1
C=${C:-clawstack-unified-openradioss-1}
W="D:/Clawdbot_Docker_20260125/clawstack_v2/data/work"
OUT=${OUT:-"D:/Clawdbot_Docker_20260125/data/workspace/engine_mem_log.tsv"}
INTERVAL=${INTERVAL:-60}
[ -f "$OUT" ] || printf 'time\ttag\trss_mb\thwm_mb\tT_s\n' > "$OUT"
# Fast memory cap (2026-09-30): the watchdog checks every 5 min, so on average it restarted from a
# restart file 3.3 min old (P1r21: 11 restarts). Checking every minute and restarting only when the
# newest restart file is 20-120 s old cuts the redone work to under ~1 min. The watchdog keeps its own
# (slower) memory cap as a fallback; both take data/workspace/.memcap.lock (skip if < 180 s old).
WS="D:/Clawdbot_Docker_20260125/data/workspace"
CAP_MB=${CAP_MB:-8000}
MEMCAP_LOG=${MEMCAP_LOG:-"$WS/openradioss_memcap_log.txt"}
ALARM_FILE=${ALARM_FILE:-"$WS/ALARM_openradioss_p1r13_16.txt"}
MEMCAP_LOCK=${MEMCAP_LOCK:-"$WS/.memcap.lock"}
memcap_fast() {  # $1=tag $2=rss_MB
  [ -n "$NO_MEMCAP" ] && return
  [ "$2" -gt "$CAP_MB" ] 2>/dev/null || return
  local rst age now; now=$(date +%s)
  rst=$(ls -t "$W"/PANEL4MM_$1_*_0001.rst 2>/dev/null | grep -v "_0000_0001.rst" | head -1)
  [ -n "$rst" ] || return
  age=$((now - $(stat -c %Y "$rst")))
  { [ "$age" -ge 20 ] && [ "$age" -le 120 ]; } || return
  if [ -f "$MEMCAP_LOCK" ] && [ $((now - $(stat -c %Y "$MEMCAP_LOCK"))) -lt 180 ]; then return; fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') mem_log $1" > "$MEMCAP_LOCK"
  [ -n "$DRY" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') $1 RSS $2 MB > cap $CAP_MB, rst ${age}s old -> DRY (would restart)" >> "$MEMCAP_LOG"; return; }
  local st res
  st=$(docker exec $C bash /work/engine_ctl.sh stop "$1" 2>&1)
  res=$(docker exec -e NT=12 $C bash /work/openradioss_restart_prep.sh "$1" --go 2>&1 | grep -E "LAUNCHED|REFUSE|ABORT|failed|Error" | head -1)
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1 RSS $2 MB > cap $CAP_MB, rst ${age}s old -> FAST RESTART: $st; $res" >> "$MEMCAP_LOG"
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1: MEMCAP(fast) RSS $2 MB > $CAP_MB -> $st; resume from $(basename "$rst") (${age}s old): $res" >> "$ALARM_FILE"
}
LOCK=${OWNER_LOCK:-"D:/Clawdbot_Docker_20260125/data/workspace/.engine_mem_log.owner"}; me="$$-$(date +%s%N)"; echo "$me" > "$LOCK"
while true; do
  [ "$(cat "$LOCK" 2>/dev/null)" = "$me" ] || exit 0
  # one line per live engine (2026-10-01: two engines can run at once)
  lines=$(docker exec $C bash -c 'for p in /proc/[0-9]*; do c=$(tr "\0" " " < $p/cmdline 2>/dev/null); case "$c" in /opt/openradioss/*engine_linux64_gf*) t=${c#*-i PANEL4MM_}; t=${t%%_0*}; r=$(awk "/VmRSS/{print int(\$2/1024)}" $p/status); h=$(awk "/VmHWM/{print int(\$2/1024)}" $p/status); echo "$t $r $h";; esac; done' 2>/dev/null)
  if [ -z "$lines" ]; then [ -n "$ONESHOT" ] && exit 0; sleep "$INTERVAL"; continue; fi
  while read -r tg rss hwm; do
    [ -n "$tg" ] || continue
    f=$(ls -t "$W"/engine_run$tg.log "$W"/engine_run${tg}_r*.log 2>/dev/null | head -1)
    T=$(grep "NC=" "$f" 2>/dev/null | tail -1 | awk '{for(i=1;i<NF;i++) if($i=="T=") print $(i+1)}')
    printf '%s\t%s\t%s\t%s\t%s\n' "$(date '+%m-%d %H:%M:%S')" "$tg" "$rss" "$hwm" "$T" >> "$OUT"
    memcap_fast "$tg" "$rss"
  done <<< "$lines"
  [ -n "$ONESHOT" ] && exit 0
  sleep "$INTERVAL"
done

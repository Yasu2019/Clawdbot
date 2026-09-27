#!/bin/bash
# INC-188: log OpenRadioss engine memory against simulated time (one line per INTERVAL s).
# Output: data/workspace/engine_mem_log.tsv  (local time, tag, RSS MB, peak RSS MB, T from the newest engine log)
# Runs forever (waits while no engine is alive); single instance (lock), kept alive by c0_bisect_keeper.ps1.
export MSYS_NO_PATHCONV=1
C=clawstack-unified-openradioss-1
W="D:/Clawdbot_Docker_20260125/clawstack_v2/data/work"
OUT="D:/Clawdbot_Docker_20260125/data/workspace/engine_mem_log.tsv"
INTERVAL=${INTERVAL:-60}
[ -f "$OUT" ] || printf 'time\ttag\trss_mb\thwm_mb\tT_s\n' > "$OUT"
LOCK="D:/Clawdbot_Docker_20260125/data/workspace/.engine_mem_log.owner"; me="$$-$(date +%s%N)"; echo "$me" > "$LOCK"
while true; do
  [ "$(cat "$LOCK" 2>/dev/null)" = "$me" ] || exit 0
  line=$(docker exec $C bash -c 'for p in /proc/[0-9]*; do c=$(tr "\0" " " < $p/cmdline 2>/dev/null); case "$c" in /opt/openradioss/*engine_linux64_gf*) t=${c#*-i PANEL4MM_}; t=${t%%_0*}; r=$(awk "/VmRSS/{print int(\$2/1024)}" $p/status); h=$(awk "/VmHWM/{print int(\$2/1024)}" $p/status); echo "$t $r $h";; esac; done' 2>/dev/null | head -1)
  if [ -z "$line" ]; then sleep "$INTERVAL"; continue; fi
  set -- $line
  f=$(ls -t "$W"/engine_run$1.log "$W"/engine_run$1_r*.log 2>/dev/null | head -1)
  T=$(grep "NC=" "$f" | tail -1 | awk '{for(i=1;i<NF;i++) if($i=="T=") print $(i+1)}')
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date '+%m-%d %H:%M:%S')" "$1" "$2" "$3" "$T" >> "$OUT"
  sleep "$INTERVAL"
done

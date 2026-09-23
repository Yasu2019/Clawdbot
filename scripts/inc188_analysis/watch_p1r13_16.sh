#!/bin/bash
# P1r13-16 anomaly watchdog. Reads the host-side bind mount, so it still works if the docker API dies.
# Emits a line ONLY when a job's state changes to something bad (or recovers). Silence = healthy.
WORKDIR="D:/Clawdbot_Docker_20260125/clawstack_v2/data/work"
declare -A prev
declare -A stalecnt
POLL=${POLL:-60}
while true; do
  now=$(date +%s)
  for t in P1r13 P1r14 P1r15 P1r16; do
    # after a restart the engine writes engine_run<TAG>_r<N>.log: follow the newest log, not the original
    f=$(ls -t "$WORKDIR"/engine_run${t}.log "$WORKDIR"/engine_run${t}_r*.log 2>/dev/null | head -1)
    [ -z "$f" ] && f="$WORKDIR/engine_run${t}.log"
    state="OK"; extra=""
    if [ ! -f "$f" ]; then
      state="LOG_MISSING"
    else
      mt=$(stat -c %Y "$f" 2>/dev/null)
      # a transient stat failure on the bind mount must not read as "57 years stale": skip this tick
      if [ -z "$mt" ] || [ "$mt" -le 0 ] 2>/dev/null; then continue; fi
      age=$((now - mt))
      nc=$(tail -n 40 "$f" | grep 'NC=' | tail -1)
      if tail -n 60 "$f" | grep -q "ERROR TERMINATION"; then
        state="ERROR_TERMINATION"
      elif tail -n 60 "$f" | grep -q "NORMAL TERMINATION"; then
        state="NORMAL_TERMINATION"
      elif [ "$age" -gt 600 ] && [ "${stalecnt[$t]:-0}" -ge 1 ]; then
        state="STALE"; extra="age=${age}s"
      elif [ "$age" -gt 600 ]; then
        stalecnt[$t]=$(( ${stalecnt[$t]:-0} + 1 ))
        state="${prev[$t]:-OK}"
      elif [ -n "$nc" ]; then
        stalecnt[$t]=0
        dt=$(echo "$nc" | sed -n 's/.*DT= *\([0-9.E+-]*\).*/\1/p')
        dmm=$(echo "$nc" | sed -n 's/.*DM\/M= *\([0-9.E+-]*\).*/\1/p')
        low=$(awk -v d="$dt" 'BEGIN{ if (d+0 < 5e-10) print 1; else print 0 }')
        if [ "$low" = "1" ]; then state="DT_COLLAPSE"; extra="DT=${dt}"; fi
        nz=$(awk -v m="$dmm" 'BEGIN{ if (m+0 != 0) print 1; else print 0 }')
        if [ "$nz" = "1" ]; then state="MASS_SCALING"; extra="DM/M=${dmm}"; fi
      fi
    fi
    if [ "${prev[$t]}" != "$state" ]; then
      if [ -n "${prev[$t]}" ] || [ "$state" != "OK" ]; then
        echo "$(date +%H:%M:%S) $t -> $state $extra | ${nc:0:90}"
      fi
      prev[$t]="$state"
    fi
  done
  sleep "$POLL"
done

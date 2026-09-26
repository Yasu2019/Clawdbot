#!/bin/bash
# INC-188: automatic bisection of the COCKCROFT C0 at which the round hole separates.
# Runs detached on the host (started via WMI so it survives editor/AI sessions).
#
# Each round: wait until the watchdog's auto-finalize has written FINALIZED_<tag> for the current run,
# run round_hole_separation.py on its last frame, update the bracket, build the next deck with
# make_c0_variant.py (only C0 + names + tstop differ from the base deck) and launch it with nt=12.
# Bracket: NOSEP = lowest C0 known NOT to separate, SEP = highest C0 known to separate.
# Stops when NOSEP-SEP <= TOL_MPA or after MAX_RUNS runs. Log: $STATE_DIR/c0_bisect_log.txt
export MSYS_NO_PATHCONV=1
R="D:/Clawdbot_Docker_20260125"
W="$R/clawstack_v2/data/work"
VTK="F:/clawstack_data/inc188/vtk"
SCR="$R/scripts/inc188_analysis"
BASE_DIR="$R/data/workspace/openradioss_inc188_trials"
BASE_TAG=P1r19                     # reduced round-first deck (C0 in it is replaced)
TSTOP=3.3e-4
C=clawstack-unified-openradioss-1
STATE="$R/data/workspace/c0_bisect_state.txt"   # lines: CUR=<tag> CUR_C0=<MPa> NOSEP=<MPa> SEP=<MPa|none> N=<runs>
LOG="$R/data/workspace/c0_bisect_log.txt"
TAGS_FILE="$R/data/workspace/openradioss_watch_tags.txt"
TOL_MPA=${TOL_MPA:-2}
MAX_RUNS=${MAX_RUNS:-4}
POLL=${POLL:-300}
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }

# single instance
LOCK="$R/data/workspace/.c0_bisect.owner"; me="$$-$(date +%s%N)"; echo "$me" > "$LOCK"

. "$STATE"
log "start: CUR=$CUR C0=$CUR_C0 NOSEP=$NOSEP SEP=$SEP N=$N"
while true; do
  [ "$(cat "$LOCK" 2>/dev/null)" = "$me" ] || { log "another instance took over, exit"; exit 0; }
  f=$(ls -t "$W"/engine_run$CUR.log "$W"/engine_run${CUR}_r*.log 2>/dev/null | head -1)
  if [ -n "$f" ] && tail -60 "$f" | grep -q "ERROR TERMINATION"; then
    log "$CUR ERROR TERMINATION - stopping bisection, needs a human"; exit 2
  fi
  if [ ! -f "$VTK/FINALIZED_$CUR" ]; then sleep "$POLL"; continue; fi

  lt=$(echo "$CUR" | tr 'P' 'p')
  last=$(ls "$VTK/${lt}_vtk"/f*.vtk | sort | tail -1)
  ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/round_hole_separation.py" "$CUR" "$last" "$VTK/${lt}_vtk/f001.vtk" >> "$LOG" 2>&1 ) \
    || { log "$CUR separation check FAILED"; exit 3; }
  ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/round_hole_bridge_angles.py" "$CUR" "$last" "$VTK/${lt}_vtk/f001.vtk" >> "$LOG" 2>&1 ) || log "$CUR angle table failed (non-fatal)"
  sep=$(python -c "import json;print(json.load(open(r'$VTK/round_hole_sep_$CUR.json'))['separated'])")
  [ -n "$FAKE_SEP" ] && sep=$FAKE_SEP     # test hook only
  if [ "$sep" = "True" ]; then SEP=$CUR_C0; else NOSEP=$CUR_C0; fi
  N=$((N + 1))
  log "$CUR (C0=$CUR_C0 MPa) separated=$sep -> bracket SEP=$SEP NOSEP=$NOSEP after $N runs"

  if [ "$SEP" = "none" ]; then
    NEXT=$(python -c "print(round($NOSEP/2, 1))")
  else
    width=$(python -c "print(1 if $NOSEP-$SEP <= $TOL_MPA else 0)")
    [ "$width" = 1 ] && { log "DONE: separates at C0 <= $SEP MPa, not at $NOSEP MPa (tol $TOL_MPA)"; exit 0; }
    NEXT=$(python -c "print(round(($NOSEP+$SEP)/2, 1))")
  fi
  [ "$N" -ge "$MAX_RUNS" ] && { log "DONE: MAX_RUNS reached; bracket SEP=$SEP NOSEP=$NOSEP (next would be $NEXT)"; exit 0; }

  tag="P1r19c$(echo "$NEXT" | tr '.' 'p')"
  [ -n "$DRY" ] && { log "DRY: would build+launch $tag (C0=$NEXT MPa)"; exit 0; }
  ( cd "$R" && PYTHONIOENCODING=utf-8 python "$SCR/make_c0_variant.py" "$BASE_DIR" "$BASE_TAG" "$tag" "${NEXT}e6" "$W" "$TSTOP" 1.5e-5 >> "$LOG" 2>&1 ) \
    || { log "deck build for $tag FAILED"; exit 4; }
  echo "$tag" > "$TAGS_FILE"
  docker exec -d -e TAGS="$tag" -e NT=12 $C bash /work/chain_P1r19_21.sh || { log "launch of $tag FAILED"; exit 5; }
  log "launched $tag (C0=$NEXT MPa)"
  CUR=$tag; CUR_C0=$NEXT
  printf 'CUR=%s\nCUR_C0=%s\nNOSEP=%s\nSEP=%s\nN=%s\n' "$CUR" "$CUR_C0" "$NOSEP" "$SEP" "$N" > "$STATE"
done

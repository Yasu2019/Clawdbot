#!/bin/bash
# INC-188: bisection of the COCKCROFT C0 at which the round hole separates - per-frame version.
# Replaces c0_bisect.sh (which waited for the full run + finalize, ~8.5 h per point).
#
# For the current run, every new animation frame (older than FRAME_AGE s, so it is fully written)
# is converted to VTK into vtk_interim/ (finalize_runs.sh reuses these) and checked with
# round_hole_separation.py against f001.
#   - separated=True in CONFIRM consecutive frames -> SEP=C0, the engine is stopped early, next C0 launched
#   - engine NORMAL TERMINATION and last frame not separated -> NOSEP=C0, next C0 launched
#   - ERROR TERMINATION -> ALARM file, stop (needs a human)
# Bracket: NOSEP = lowest C0 known NOT to separate, SEP = highest C0 known to separate.
# Stops when NOSEP-SEP <= TOL_MPA or after MAX_RUNS runs.
# Runs detached on the host (started via WMI). Log: data/workspace/c0_bisect_log.txt
export MSYS_NO_PATHCONV=1
R="D:/Clawdbot_Docker_20260125"
W="$R/clawstack_v2/data/work"
VTK="F:/clawstack_data/inc188/vtk"
SCR="$R/scripts/inc188_analysis"
BASE_DIR="$R/data/workspace/openradioss_inc188_trials"
BASE_TAG=P1r19f                    # P1r19 + fast air approach (make_fast_approach.py)
TSTOP=2.4e-4                       # = old 0.339 ms after contact (contact 0.06 ms instead of 0.159 ms)
C=clawstack-unified-openradioss-1
STATE="$R/data/workspace/c0_bisect_state.txt"   # CUR= CUR_C0= NOSEP= SEP= N=
LOG="$R/data/workspace/c0_bisect_log.txt"
ALARM="$R/data/workspace/ALARM_c0_bisect.txt"
TAGS_FILE="$R/data/workspace/openradioss_watch_tags.txt"
TOL_MPA=${TOL_MPA:-2}
MAX_RUNS=${MAX_RUNS:-4}
POLL=${POLL:-120}
FRAME_AGE=${FRAME_AGE:-90}
CONFIRM=${CONFIRM:-2}
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
alarm() { log "ALARM: $*"; echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$ALARM"; }

LOCK="$R/data/workspace/.c0_bisect.owner"; me="$$-$(date +%s%N)"; echo "$me" > "$LOCK"

. "$STATE"
SEPRUN=0          # consecutive separated frames in the current run
LASTCHK=0         # last frame index checked in the current run
# after a restart: re-check only the last two frames already checked (kept on D:), so SEPRUN is rebuilt
lk=$(ls "$VTK"/round_hole_sep_${CUR}_f[0-9][0-9][0-9].json 2>/dev/null | sed 's/.*_f\([0-9]*\)\.json/\1/' | sort -n | tail -1)
[ -n "$lk" ] && [ $((10#$lk - 2)) -gt 0 ] && LASTCHK=$((10#$lk - 2))
log "start (per-frame): CUR=$CUR C0=$CUR_C0 NOSEP=$NOSEP SEP=$SEP N=$N"

engine_log() { ls -t "$W"/engine_run$CUR.log "$W"/engine_run${CUR}_r*.log 2>/dev/null | head -1; }

convert() {  # $1=frame number (3 digits) -> path of the VTK on the host, empty on failure
  local lt fr=$1; lt=$(echo "$CUR" | tr 'P' 'p')
  local out="$W/vtk_interim/${lt}_vtk/f$fr.vtk"
  if [ ! -s "$out" ]; then
    docker exec $C bash -c "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:\$LD_LIBRARY_PATH; \
      export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files; mkdir -p /work/vtk_interim/${lt}_vtk; cd /work; \
      nice -n 5 /opt/openradioss/OpenRadioss/exec/anim_to_vtk_linux64_gf PANEL4MM_${CUR}A$fr > /work/vtk_interim/${lt}_vtk/f$fr.vtk.part 2>/dev/null; \
      grep -q '^POINTS ' /work/vtk_interim/${lt}_vtk/f$fr.vtk.part && mv /work/vtk_interim/${lt}_vtk/f$fr.vtk.part /work/vtk_interim/${lt}_vtk/f$fr.vtk" \
      || { rm -f "$out.part"; return 1; }
  fi
  echo "$out"
}

stop_engine() {
  [ -n "$DRY" ] && { echo "DRY: would stop engine $CUR"; return; }
  docker exec $C bash -c 'for p in /proc/[0-9]*; do c=$(tr "\0" " " < $p/cmdline 2>/dev/null); case "$c" in /opt/openradioss/*engine_linux64_gf*"-i PANEL4MM_'"$CUR"'_"*) kill ${p#/proc/} && echo killed ${p#/proc/};; esac; done'
}

next_run() {  # uses SEP/NOSEP/N; launches the next C0 or exits
  N=$((N + 1))
  log "bracket after $N runs: SEP=$SEP NOSEP=$NOSEP"
  if [ "$SEP" = "none" ]; then
    NEXT=$(python -c "print(round($NOSEP/2, 1))")
  else
    [ "$(python -c "print(1 if $NOSEP-$SEP <= $TOL_MPA else 0)")" = 1 ] && {
      log "DONE: separates at C0 <= $SEP MPa, not at $NOSEP MPa (tol $TOL_MPA)"
      printf 'CUR=%s\nCUR_C0=%s\nNOSEP=%s\nSEP=%s\nN=%s\nDONE=1\n' "$CUR" "$CUR_C0" "$NOSEP" "$SEP" "$N" > "$STATE"; exit 0; }
    NEXT=$(python -c "print(round(($NOSEP+$SEP)/2, 1))")
  fi
  [ "$N" -ge "$MAX_RUNS" ] && { log "DONE: MAX_RUNS; bracket SEP=$SEP NOSEP=$NOSEP (next would be $NEXT)"
      printf 'CUR=%s\nCUR_C0=%s\nNOSEP=%s\nSEP=%s\nN=%s\nDONE=1\n' "$CUR" "$CUR_C0" "$NOSEP" "$SEP" "$N" > "$STATE"; exit 0; }
  local tag="P1r19fc$(echo "$NEXT" | tr '.' 'p')"
  [ -n "$DRY" ] && { log "DRY: would build+launch $tag (C0=$NEXT MPa)"; exit 0; }
  ( cd "$R" && PYTHONIOENCODING=utf-8 python "$SCR/make_c0_variant.py" "$BASE_DIR" "$BASE_TAG" "$tag" "${NEXT}e6" "$W" "$TSTOP" 1.5e-5 >> "$LOG" 2>&1 ) \
    || { alarm "deck build for $tag FAILED"; exit 4; }
  echo "$tag" > "$TAGS_FILE"
  docker exec -d -e TAGS="$tag" -e NT=12 $C bash /work/chain_P1r19_21.sh || { alarm "launch of $tag FAILED"; exit 5; }
  log "launched $tag (C0=$NEXT MPa)"
  CUR=$tag; CUR_C0=$NEXT; SEPRUN=0; LASTCHK=0
  printf 'CUR=%s\nCUR_C0=%s\nNOSEP=%s\nSEP=%s\nN=%s\n' "$CUR" "$CUR_C0" "$NOSEP" "$SEP" "$N" > "$STATE"
}

while true; do
  [ "$(cat "$LOCK" 2>/dev/null)" = "$me" ] || { log "another instance took over, exit"; exit 0; }
  f=$(engine_log)
  if [ -n "$f" ] && tail -60 "$f" | grep -q "ERROR TERMINATION"; then alarm "$CUR ERROR TERMINATION - bisection stopped"; exit 2; fi
  normal=0; [ -n "$f" ] && tail -60 "$f" | grep -q "NORMAL TERMINATION" && normal=1

  # newest complete frame
  now=$(date +%s); latest=0
  for a in $(ls "$W"/PANEL4MM_${CUR}A[0-9][0-9][0-9] 2>/dev/null | sort); do
    [ $((now - $(stat -c %Y "$a"))) -ge "$FRAME_AGE" ] || [ "$normal" = 1 ] || continue
    latest=$((10#${a: -3}))
  done

  if [ "$latest" -gt "$LASTCHK" ] && [ "$latest" -ge 2 ]; then
    first=$(convert 001) || { log "$CUR f001 convert failed, retry"; sleep "$POLL"; continue; }
    # check every new frame in order (so CONFIRM counts consecutive frames)
    for k in $(seq $((LASTCHK + 1)) "$latest"); do
      [ "$k" -lt 2 ] && continue
      fr=$(printf '%03d' "$k")
      v=$(convert "$fr") || { log "$CUR f$fr convert failed, retry"; break; }
      ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/round_hole_separation.py" "${CUR}_f$fr" "$v" "$first" >> "$LOG" 2>&1 ) \
        || { alarm "$CUR f$fr separation check FAILED"; exit 3; }
      sep=$(python -c "import json;print(json.load(open(r'$VTK/round_hole_sep_${CUR}_f$fr.json'))['separated'])")
      [ -n "$FAKE_SEP" ] && sep=$FAKE_SEP     # test hook only
      LASTCHK=$k
      if [ "$sep" = "True" ]; then SEPRUN=$((SEPRUN + 1)); else SEPRUN=0; fi
      # keep f001 + the newest two frames on D:; older interim frames are removed (finalize reconverts)
      old=$(printf '%03d' $((k - 2)))
      [ "$k" -gt 3 ] && rm -f "$W/vtk_interim/$(echo "$CUR" | tr 'P' 'p')_vtk/f$old.vtk"
      if [ "$SEPRUN" -ge "$CONFIRM" ]; then
        ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/round_hole_bridge_angles.py" "${CUR}_f$fr" "$v" "$first" >> "$LOG" 2>&1 ) || true
        log "$CUR (C0=$CUR_C0 MPa) SEPARATED at f$fr (confirmed $CONFIRM frames) - stopping engine early"
        SEP=$CUR_C0
        # next_run rewrites the watchdog tag file within ~1 min; the watchdog needs 2x600 s of
        # silence before it would auto-resume the stopped engine
        stopped=$(stop_engine); log "$CUR: $stopped"
        next_run
        continue 2
      fi
    done
  fi

  if [ "$normal" = 1 ] && [ "$LASTCHK" -ge "$latest" ] && [ "$latest" -ge 2 ]; then
    ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/round_hole_bridge_angles.py" "${CUR}_f$(printf '%03d' $latest)" \
        "$W/vtk_interim/$(echo "$CUR" | tr 'P' 'p')_vtk/f$(printf '%03d' $latest).vtk" "$W/vtk_interim/$(echo "$CUR" | tr 'P' 'p')_vtk/f001.vtk" >> "$LOG" 2>&1 ) || true
    log "$CUR (C0=$CUR_C0 MPa) finished, not separated at last frame f$(printf '%03d' $latest)"
    NOSEP=$CUR_C0
    next_run
    continue
  fi
  sleep "$POLL"
done

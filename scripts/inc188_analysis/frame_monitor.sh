#!/bin/bash
# INC-188: per-frame round-hole monitor for every watched run (tags in openradioss_watch_tags.txt).
# Each new animation frame (older than FRAME_AGE s, or the run has terminated) is converted to VTK in
# vtk_interim/<tag>_vtk/ (finalize_runs.sh reuses these) and checked with
#   punch_penetration_check.py  (live blank elements inside the round punch -> contact health)
#   round_hole_separation.py    (slug still attached to the main sheet?)
# One line per frame in data/workspace/round_hole_frames.tsv. A first "separated=True" or a
# penetration count > PEN_ALARM writes data/workspace/ALARM_round_hole.txt (new event only).
# Single instance (lock file, newest wins). Restarted by c0_bisect_keeper.ps1.
export MSYS_NO_PATHCONV=1
R="D:/Clawdbot_Docker_20260125"
W="$R/clawstack_v2/data/work"
WS="$R/data/workspace"
VTK="F:/clawstack_data/inc188/vtk"
SCR="$R/scripts/inc188_analysis"
C=clawstack-unified-openradioss-1
TAGS_FILE=${TAGS_FILE:-"$WS/openradioss_watch_tags.txt"}
TSV=${TSV:-"$WS/round_hole_frames.tsv"}
ALARM=${ALARM:-"$WS/ALARM_round_hole.txt"}
LOG=${LOG:-"$WS/frame_monitor_log.txt"}
POLL=${POLL:-120}
FRAME_AGE=${FRAME_AGE:-90}
PEN_ALARM=${PEN_ALARM:-100}
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
LOCK=${LOCK:-"$WS/.frame_monitor.owner"}; me="$$-$(date +%s%N)"; echo "$me" > "$LOCK"
[ -f "$TSV" ] || printf 'time\ttag\tframe\tt_ms\tpunch_inside\tslug_live\tslug_in_main\tmain_min_dist_t0_mm\tseparated\n' > "$TSV"
log "start"

convert() {  # $1=tag $2=frame(3 digits) -> host path of the VTK, empty + rc 1 on failure
  local lt; lt=$(echo "$1" | tr 'P' 'p')
  local out="$W/vtk_interim/${lt}_vtk/f$2.vtk"
  if [ ! -s "$out" ]; then
    docker exec $C bash -c "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:\$LD_LIBRARY_PATH; \
      export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files; mkdir -p /work/vtk_interim/${lt}_vtk; cd /work; \
      nice -n 5 /opt/openradioss/OpenRadioss/exec/anim_to_vtk_linux64_gf PANEL4MM_$1A$2 > /work/vtk_interim/${lt}_vtk/f$2.vtk.part 2>/dev/null; \
      grep -q '^POINTS ' /work/vtk_interim/${lt}_vtk/f$2.vtk.part && mv /work/vtk_interim/${lt}_vtk/f$2.vtk.part /work/vtk_interim/${lt}_vtk/f$2.vtk" \
      || { rm -f "$out.part"; return 1; }
  fi
  echo "$out"
}

while true; do
  [ "$(cat "$LOCK" 2>/dev/null)" = "$me" ] || { log "another instance took over, exit"; exit 0; }
  for tag in $(tr -d '\r' < "$TAGS_FILE" 2>/dev/null | grep -E '^[A-Za-z0-9_]+$'); do
    f=$(ls -t "$W"/engine_run$tag.log "$W"/engine_run${tag}_r*.log 2>/dev/null | head -1)
    ended=0; [ -n "$f" ] && tail -60 "$f" | grep -q "TERMINATION" && ended=1
    now=$(date +%s)
    for a in $(ls "$W"/PANEL4MM_${tag}A[0-9][0-9][0-9] 2>/dev/null | sort); do
      fr=${a: -3}
      [ "$fr" = 001 ] && continue
      [ -n "$FRAMES" ] && ! echo "$fr" | grep -qE "^($FRAMES)$" && continue   # test hook
      grep -q "^[^	]*	$tag	$fr	" "$TSV" && continue
      [ $((now - $(stat -c %Y "$a"))) -ge "$FRAME_AGE" ] || [ "$ended" = 1 ] || continue
      first=$(convert "$tag" 001) || { log "$tag f001 convert failed"; break; }
      v=$(convert "$tag" "$fr") || { log "$tag f$fr convert failed"; break; }
      pen=$(PYTHONIOENCODING=utf-8 python "$SCR/punch_penetration_check.py" "$v" 2>>"$LOG" | sed -n 's/.*inside punch \([0-9,]*\).*/\1/p' | tr -d ',')
      ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/round_hole_separation.py" "${tag}_f$fr" "$v" "$first" >> "$LOG" 2>&1 ) \
        || { log "$tag f$fr separation check failed"; break; }
      row=$(python -c "import json;d=json.load(open(r'$VTK/round_hole_sep_${tag}_f$fr.json'));print('\t'.join(str(d[k]) for k in ('t_ms','slug_live','slug_live_in_main','main_min_dist_to_hole_centre_t0_mm','separated')))")
      set -- $row
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date '+%m-%d %H:%M:%S')" "$tag" "$fr" "$1" "${pen:-NA}" "$2" "$3" "$4" "$5" >> "$TSV"
      if [ "$5" = "True" ] && ! grep -q "$tag SEPARATED" "$ALARM" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $tag SEPARATED first at f$fr (t=$1 ms)" >> "$ALARM"
      fi
      core=$(python -c "import json;print(json.load(open(r'$VTK/round_hole_sep_${tag}_f$fr.json')).get('core_separated'))")
      if [ "$core" = "True" ] && ! grep -q "$tag CORE SEPARATED" "$ALARM" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $tag CORE SEPARATED first at f$fr (t=$1 ms): slug core r<0.24 mm detached; $3 rim elements still attached" >> "$ALARM"
      fi
      if [ -n "$pen" ] && [ "$pen" -gt "$PEN_ALARM" ] && ! grep -q "$tag PENETRATION" "$ALARM" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $tag PENETRATION: $pen live blank elements inside the round punch at f$fr (contact lost?)" >> "$ALARM"
      fi
    done
  done
  sleep "$POLL"
done

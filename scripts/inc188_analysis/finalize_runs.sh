#!/bin/bash
# INC-188: post-process P1r13-P1r16 automatically as each engine finishes.
# For every run that shows NORMAL TERMINATION in its newest engine log (engine_run<TAG>[_rN].log)
# and has its last animation frame (A041):
#   1. convert all 41 animation frames to VTK inside the openradioss container (one at a time),
#      reusing the interim frames already converted, and move each finished frame to F: (size check)
#   2. extract the 6-hotspot time series      -> F:/clawstack_data/inc188/vtk/timeseries_<TAG>.json
#   3. whole-sheet erosion scan (t=0 geometry) -> F:/clawstack_data/inc188/vtk/rupture_sites_<TAG>.json
# Only real solver output is used. Progress: F:/clawstack_data/inc188/finalize_log.txt
export MSYS_NO_PATHCONV=1
W="D:/Clawdbot_Docker_20260125/clawstack_v2/data/work"
VTK="F:/clawstack_data/inc188/vtk"
LOG="F:/clawstack_data/inc188/finalize_log.txt"
SCR="D:/Clawdbot_Docker_20260125/scripts/inc188_analysis"
C=clawstack-unified-openradioss-1
NFR=41
mkdir -p "$VTK"
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }

finished() {  # $1=TAG
  local f; f=$(ls -t "$W"/engine_run$1.log "$W"/engine_run$1_r*.log 2>/dev/null | head -1)
  [ -n "$f" ] && tail -40 "$f" | grep -q "NORMAL TERMINATION" && [ -f "$W/PANEL4MM_$1A0$NFR" ]
}

process() {  # $1=TAG
  local tag=$1 lt; lt=$(echo "$1" | tr 'P' 'p')
  local out="$VTK/${lt}_vtk"; mkdir -p "$out"
  log "$tag: finalize start"
  for i in $(seq 1 $NFR); do
    local fr; fr=$(printf '%03d' "$i")
    local dst="$out/f$fr.vtk"
    [ -s "$dst" ] && continue
    local interim="$W/vtk_interim/${lt}_vtk/f$fr.vtk"
    if [ -s "$interim" ]; then
      cp "$interim" "$dst.part" && [ "$(stat -c %s "$dst.part")" = "$(stat -c %s "$interim")" ] && mv "$dst.part" "$dst" \
        && { log "$tag f$fr reused interim"; continue; }
      rm -f "$dst.part"; log "$tag f$fr interim copy FAILED"; return 1
    fi
    local t0; t0=$(date +%s)
    docker exec $C bash -c "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:\$LD_LIBRARY_PATH; \
      export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files; mkdir -p /work/vtk_final_tmp; cd /work; \
      nice -n 5 /opt/openradioss/OpenRadioss/exec/anim_to_vtk_linux64_gf PANEL4MM_${tag}A$fr > /work/vtk_final_tmp/${lt}_f$fr.vtk.part 2>/dev/null; \
      grep -q '^POINTS ' /work/vtk_final_tmp/${lt}_f$fr.vtk.part" || { log "$tag f$fr convert FAILED"; rm -f "$W/vtk_final_tmp/${lt}_f$fr.vtk.part"; return 1; }
    local src="$W/vtk_final_tmp/${lt}_f$fr.vtk.part" sz
    sz=$(stat -c %s "$src")
    cp "$src" "$dst.part" && [ "$(stat -c %s "$dst.part")" = "$sz" ] && mv "$dst.part" "$dst" && rm -f "$src" \
      || { log "$tag f$fr move to F: FAILED"; return 1; }
    log "$tag f$fr converted $(( $(date +%s) - t0 ))s $sz B"
  done
  local n; n=$(ls "$out"/f*.vtk | wc -l)
  [ "$n" -eq $NFR ] || { log "$tag: only $n/$NFR frames, stop"; return 1; }
  log "$tag: all $NFR frames on F:, extracting time series"
  ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/extract_multi_run_timeseries.py" "$tag" >> "$LOG" 2>&1 ) || { log "$tag extract FAILED"; return 1; }
  log "$tag: whole-sheet scan"
  ( cd "$VTK" && PYTHONIOENCODING=utf-8 python "$SCR/scan_rupture_sites.py" "$tag" "$out/f0$NFR.vtk" "$out/f001.vtk" >> "$LOG" 2>&1 ) || { log "$tag scan FAILED"; return 1; }
  echo done > "$VTK/FINALIZED_$tag"
  log "$tag: FINALIZED"
}

while true; do
  left=0
  for tag in ${TAGS:-P1r13 P1r14 P1r15 P1r16}; do
    [ -f "$VTK/FINALIZED_$tag" ] && continue
    left=$((left+1))
    if finished "$tag"; then process "$tag" || { log "$tag: processing error, will retry next loop"; sleep 300; }; fi
  done
  [ "$left" -eq 0 ] && { log "ALL FINALIZED"; exit 0; }
  sleep 120
done

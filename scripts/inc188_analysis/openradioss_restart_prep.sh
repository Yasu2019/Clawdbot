#!/bin/bash
# OpenRadioss engine RESTART helper (runs INSIDE the openradioss container; /work is the bind mount).
#
# usage: bash /work/openradioss_restart_prep.sh <TAG> [--go]        e.g. TAG=P1r13
#   default = DRY RUN: checks and prints the plan, writes nothing, launches nothing.
#   --go    = writes the next-run engine deck and launches the engine detached.
#
# Lessons built in (memory: feedback_openradioss_restart_and_process_kill):
#  1. Re-running the same _0001.rad restarts from NC=0. A restart needs a NEW engine deck whose
#     first line is /RUN/<root>/<N+1>; the engine then reads <root>_<N:04d>_0001.rst.
#  2. pkill/pgrep are unreliable here: liveness is decided ONLY by scanning /proc/*/cmdline.
#     If any engine for this TAG is alive, REFUSE (two engines writing the same files corrupt them).
#  3. The engine overwrites ONE restart file every 20000 cycles. If the live .rst is missing or
#     looks truncated, restore a snapshot from F:\clawstack_data\inc188\rst_snapshots\<TAG>\ onto
#     the HOST path D:\Clawdbot_Docker_20260125\clawstack_v2\data\work\ FIRST (the container cannot
#     see F:), then run this script.
TAG="$1"; MODE="$2"
[ -z "$TAG" ] && { echo "usage: $0 <TAG> [--go]"; exit 1; }
ROOT="PANEL4MM_${TAG}"
cd /work || exit 1

# ---- 1. liveness by /proc scan (never pgrep/pkill) ----
alive=""
for p in /proc/[0-9]*; do
  c=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
  case "$c" in
    /opt/openradioss/*engine_linux64_gf*"-i ${ROOT}_"*) alive="$alive $(basename "$p")";;
  esac
done
if [ -n "$alive" ]; then
  echo "REFUSE: an engine for ${TAG} is still alive (PID:${alive}). Do NOT start a second one."
  exit 2
fi

# ---- 2. find the current run number N (highest existing engine deck _000N.rad, N>=1) ----
N=0
for f in ${ROOT}_00[0-9][0-9].rad; do
  [ -e "$f" ] || continue
  n=$(echo "$f" | sed -n "s/^${ROOT}_00\([0-9][0-9]\)\.rad$/\1/p" | sed 's/^0*//'); n=${n:-0}
  [ "$n" -gt "$N" ] && N=$n
done
[ "$N" -lt 1 ] && { echo "ABORT: no engine deck ${ROOT}_0001.rad found"; exit 3; }
NEXT=$((N+1)); NNN=$(printf '%04d' "$N"); NEXTNNN=$(printf '%04d' "$NEXT")
RST="${ROOT}_${NNN}_0001.rst"
ENG="${ROOT}_${NNN}.rad"
NEWENG="${ROOT}_${NEXTNNN}.rad"

# ---- 3. the restart file must exist and be plausible ----
if [ ! -f "$RST" ]; then
  echo "ABORT: restart file $RST missing."
  if [ "$N" -ge 2 ]; then
    PREV=$(printf '%04d' $((N-1)))
    echo "  Run $N deck already exists but wrote no restart file. If that run never produced output, remove ${ROOT}_${NNN}.rad and rerun this script to retry from ${ROOT}_${PREV}_0001.rst."
  fi
  echo "  Otherwise restore a snapshot onto the host work dir first (F: clawstack_data/inc188/rst_snapshots/${TAG})."
  exit 4
fi
size=$(stat -c %s "$RST"); ref=$(stat -c %s "${ROOT}_0000_0001.rst" 2>/dev/null || echo 0)
mt=$(stat -c %y "$RST" | cut -d. -f1)
lastnc=$(grep -h '^ NC=' "engine_run${TAG}.log" 2>/dev/null | tail -1 | sed 's/ERR=.*//')
echo "TAG=$TAG  current run N=$N  next run=$NEXT"
echo "restart file : $RST  size=$size B  (starter restart $ref B)  written $mt"
echo "last log line: ${lastnc:-none}"
if [ "$ref" -gt 0 ]; then
  lo=$((ref*98/100)); hi=$((ref*102/100))
  if [ "$size" -lt "$lo" ] || [ "$size" -gt "$hi" ]; then
    echo "ABORT: restart file size is not within 2% of the starter restart file -> likely truncated/corrupt"; exit 5
  fi
fi

# ---- 4. build the next-run engine deck (first line /RUN/<root>/<NEXT>) ----
first=$(head -1 "$ENG" | tr -d '\r')      # engine decks are CRLF (written on Windows): strip the CR before comparing
case "$first" in "/RUN/${ROOT}/${N}") ;; *) echo "ABORT: unexpected first line in $ENG: $first"; exit 6;; esac
[ -e "$NEWENG" ] && { echo "ABORT: $NEWENG already exists (a previous restart was prepared; inspect it)"; exit 7; }
LOGNEW="engine_run${TAG}_r${NEXT}.log"
echo "---- plan ----"
echo "new deck     : $NEWENG   (copy of $ENG with first line /RUN/${ROOT}/${NEXT})"
echo "launch       : OMP_NUM_THREADS=4 engine_linux64_gf -i $NEWENG -nt 4 > /work/$LOGNEW 2>&1 &"
if [ "$MODE" != "--go" ]; then echo "DRY RUN: nothing written, nothing launched. Add --go to execute."; exit 0; fi

# keep the deck's CRLF style: replace line 1 including its CR, leave every other line byte-for-byte
sed "1s#.*#/RUN/${ROOT}/${NEXT}$(printf '\r')#" "$ENG" > "$NEWENG" || { echo "ABORT: cannot write $NEWENG"; exit 8; }
[ "$(head -1 "$NEWENG" | tr -d '\r')" = "/RUN/${ROOT}/${NEXT}" ] || { echo "ABORT: deck first line check failed"; exit 9; }
export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH
export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files
ENGINE_BIN="${ENGINE_BIN:-/opt/openradioss/OpenRadioss/exec/engine_linux64_gf}"   # override only for tests
OMP_NUM_THREADS=4 nohup "$ENGINE_BIN" -i "$NEWENG" -nt 4 > "/work/$LOGNEW" 2>&1 &
echo "LAUNCHED (PID $!). Verify NC continues from the restart cycle, not from 0:  tail -3 /work/$LOGNEW"

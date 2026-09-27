#!/bin/bash
# INC-188 engine helper (runs inside the openradioss container; called by the Windows watchdog so
# no shell quoting has to survive PowerShell 5.1).
#   engine_ctl.sh rss  <TAG>  -> "<pid> <rss_MB>" for the live engine of TAG, nothing if none
#   engine_ctl.sh stop <TAG>  -> SIGTERM the engine of TAG, wait up to 60 s, then SIGKILL; prints what it did
# The match requires the command line to START with the engine path, so this shell never matches itself.
#   engine_ctl.sh any         -> one line "<pid> <tag>" per live starter or engine (any tag), nothing if none
cmd=$1; tag=$2
if [ "$cmd" = "any" ]; then
  for p in /proc/[0-9]*; do
    c=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
    case "$c" in /opt/openradioss/*_linux64_gf*"-i PANEL4MM_"*) t=${c#*-i PANEL4MM_}; echo "${p#/proc/} ${t%%_0*}";; esac
  done
  exit 0
fi
[ -n "$tag" ] || { echo "usage: engine_ctl.sh rss|stop TAG | any"; exit 2; }
pids() {
  for p in /proc/[0-9]*; do
    c=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
    case "$c" in /opt/openradioss/*engine_linux64_gf*"-i PANEL4MM_${tag}_"*) echo "${p#/proc/}";; esac
  done
}
case "$cmd" in
  rss)
    for p in $(pids); do echo "$p $(awk '/VmRSS/{print int($2/1024)}' /proc/$p/status)"; done ;;
  stop)
    ps_=$(pids); [ -n "$ps_" ] || { echo "no engine for $tag"; exit 0; }
    kill $ps_; for i in $(seq 1 60); do [ -z "$(pids)" ] && { echo "stopped $ps_ (TERM, ${i}s)"; exit 0; }; sleep 1; done
    kill -9 $(pids) 2>/dev/null; sleep 2; [ -z "$(pids)" ] && echo "stopped $ps_ (KILL)" || { echo "FAILED to stop $ps_"; exit 1; } ;;
  *) echo "unknown command $cmd"; exit 2 ;;
esac

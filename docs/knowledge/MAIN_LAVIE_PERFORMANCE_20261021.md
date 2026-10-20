# Main LAVIE P1r41f performance investigation

Incident MAIN-LAVIE-PERF-20261021; Beads Clawdbot_Docker_20260125-chn1.
Read-only live investigation2026-10-21 04:21-04:26 JST, host DESKTOP-TFDRIPE.
Sources: authenticated SSH, Windows GetSystemTimes/CIM/process CPU counters,
local monitor8111, direct LibreHardwareMonitor8085 sensors, WSL procfs and
current native solver logs/output/deck. Raw evidence stays local in
artifacts/main-lavie-performance-20261021; no raw private telemetry published.

## Findings and evidence limits

1. Actual computation is active. P1r41f enginePID508, MPI1/10SMP threads,6 physical
   cores/12logical processors (i7-8750H), guest12logical CPUs, affinity0-11.
   Guest5.005s sample: engine977.42% of ONE logical CPU, approximately9.77 logical
   CPU equivalents. Guest total busy81.13% of12logical, iowait0.017%.
   Host separate5s GetSystemTimes busy98.72% of12logical. Separate Windows5s
   process sample04:26: vmmemWSL1001.88% ofONE logical CPU, no similarly large
   competing host process. Samples have different time windows and denominators;
   do not force host/guest counters to agree or treat threads as physical cores.
2. Sustained low measured clock at high measured temperature is a strong suspect.
   Direct LHM04:24:24: core clocks1003.6-1304.7MHz, core average93.8C, package95C,
   package power11.1W. Repeated direct readings04:25:54-04:25:58 also around
   1.1-1.3GHz/core average93.5-93.7C/package power10.8-10.9W. Fan RPM/control and
   hardware thermal/power-limit reason bits unavailable in these readings.
   Thermal/cooling or firmware/power limitation is plausible, not conclusively
   separated. Sensor accuracy is not independently calibrated. No fan100% claim.
3. The monitor's is_throttling=false does NOT rule out hardware throttling.
   Actual remote monitor_agent.py assigns is_throttling from its own configured
   target_limit<NORMAL_PERCENT. It is a software CPU-cap state, not hardware
   PROCHOT/thermal/power-limit telemetry. Likewise CIM CurrentClockSpeed2208MHz
   is contradicted by direct per-core LHM clocks near1.1GHz and Windows processor
   performance counter~60%; do not pick the convenient2208MHz as effective clock.
   High Performance plan and maximum processor state100% were read live; other
   hidden cooling/boost queries did not return usable values, so unconfirmed.
4. RAM shortage is not supported by this interval. DIMMs8+32GiB=40GiB, Windows
   visible39.89GiB, available16.84GiB; vmmem working set12.66GiB separately.
   Guest MemTotal19.48GiB, MemAvailable13.44GiB; engineRSS5.36GiB, VmSwap0.
   Guest swap5GiB completely free;5s major-fault/swap-in/swap-out deltas all0.
   Host and guest free RAM must NOT be added. User .wslconfig query returned no
   content; configured cap unverified, effective guest memory measured directly.
   DIMM/OS difference~0.11GiB is not the large EVO discrepancy from prior cases.
5. Native model is expensive:341245nodes; observed DT1e-9s and target0.001004s,
   approximately1004000steps if DT stays constant. Deck /DT/NODA/CST2/0 with
   scale0.9 and target minimum1e-9; /DT/BRICK/DEL minimum3e-10. The nodal setting
   is a mass-scaling control, not simply an arbitrary upper time-step cap.
   Raising it can change inertia/results; no claim that doing so preserves
   crack accuracy. Printed DM/M~1.5513e-8 in the observed stage is not a guarantee
   for a higher setting or later contact/fracture stage.
6. Throughput NC86300->88300:2000steps/1655.84s=1.208steps/s. At sim88.3us,
   target1004us, recent-window extrapolation~8.77days remaining. Native remaining
   estimate is a different estimator; neither is a completion guarantee.
   K10 contemporaneous P1r45f run9 showed2000steps/813.42s~2.46steps/s, including
   an output/checkpoint slowdown. Different case/stage/layout and competing jobs
   prevent a controlled hardware speed ratio. No same-checkpoint cross-host
   benchmark performed, and no additional heavy solver dispatched on any host.
7. Main current restart file2,403,608,657bytes at03:37:23; Starter restart also
   present. File existence/size alone does not verify compatibility or a safe
   restart. No2.4GB hashing/copy, checkpoint overwrite, force-stop, WSL shutdown,
   reboot, thread change, solver input edit or monitor restart performed.

## Prioritized improvement plan

- First: investigate actual cooling/airflow/fan and OEM AC/power-limit behavior.
  Fan speed and heatsink condition require additional evidence; opening/cleaning
  hardware or repasting requires a maintenance plan and recoverable shutdown.
  Do not raise temperature thresholds to cure low clock or disable protections.
- Next safe maintenance/test opportunity: same-case bounded6/8/10-thread
  comparison at controlled thermal state, using independently verified native
  restart and exact solver/layout compatibility. More threads than physical
  cores is not proof of benefit, and6threads is not proven faster yet. Preserve
  known-good checkpoints and use isolated output directories. Do not run a second
  benchmark beside the active engine and call the comparison representative.
- Only after accuracy criteria are defined: isolated timestep/mass-scaling or
  mesh/contact sensitivity study comparing mass change, energy balance, contact
  force/displacement and crack initiation/path. No unvalidated timestep increase
  or approximate substitute presented as a faster equivalent calculation.
- Monitor correction backlog: distinguish software_cpu_cap_active from hardware
  limit evidence and expose actual sensor clock with timestamp/source. Keep the
  old flag compatible until consumer review; no current daemon hot-replacement.

## Four linked quality records (operational draft, unscored)

FMEA: failure mode=CPU utilization/NORMAL software flag mistaken for full hardware
performance; effect=slowdown missed and unsafe tuning risk; observed cause of
misinterpretation=software-flag semantics/CIM clock choice. Physical root cause
of low clock remains UNKNOWN. Prevention=direct interval throughput plus per-core
clock/average temperature/limit reasons; detection verified by this investigation.
S/O/D/RPN/action priority remain unassessed, not invented. Owner role=orchestrator;
physical maintenance and validation remain open, no named owner invented.

FTA top event=unexpectedly long valid computation. OR branches: small stable DT
times expensive mesh (observed); reduced effective clock (observed, thermal vs
power cause unresolved); parallel scaling inefficiency (hypothesis); memory/I/O
pressure (not supported by sampled interval, cannot rule out checkpoint bursts).
No unsupported branch is labeled a proven root cause.

QC process chart: confirm host/case/job ownership -> sample host/guest CPU with
denominators -> compare DIMM/OS/guest RAM separately -> measure clock/average
temperature and actual limit reason -> derive cycles/s from native log ->
verify case restart before any change -> compare numerical accuracy and real
speed -> document residual unknowns. No bypass of existing acceptance gates.

Control Plan: every performance diagnosis requires timestamped throughput,
topology, memory layers, real clock and average temperature, software-vs-hardware
flag distinction. Acceptance=complete evidence with unknowns marked, not an
invented temperature threshold. Reaction=hold unsupported tuning, preserve job,
plan verified recovery/controlled comparison. Each knowledge sync needs read-back
or hash evidence; documentation alone does not prove a physical repair.

## Official references checked2026-10-21

- https://2024.help.altair.com/2024/hwsolvers/rad/topics/solvers/rad/dt_noda_keyword3_engine_r.htm
- https://2023.help.altair.com/2023/hwsolvers/rad/topics/solvers/rad/theory_dynamic_analysis_time_step_control_r.htm

These references explain nodal timestep/mass scaling. They do not establish this
host's thermal fault, a new acceptable mass ratio, or changed-case accuracy.

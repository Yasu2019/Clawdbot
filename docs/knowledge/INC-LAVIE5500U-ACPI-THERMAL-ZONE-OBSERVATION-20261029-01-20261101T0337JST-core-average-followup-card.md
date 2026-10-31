# Thermal telemetry follow-up — 2026-11-01 03:35 JST

Incident: `INC-LAVIE5500U-ACPI-THERMAL-ZONE-OBSERVATION-20261029-01`

The one-minute SYSTEM health history supplied 15 LHM CPU temperature samples from 03:21:04.804 to 03:35:04.914 JST. Only `Core (Tctl/Tdie)` was available: mean 87.81°C, minimum 75.125°C, maximum 92.25°C. `Core Average` was unavailable in all 15 samples; fan sensor status was `no_fan_value_exposed`. These are observation-only data; do not label Tctl average as Core Average or infer physical fan speed.

At 03:35:04.914 JST, a separate ACPI thermal-zone reading was 90.05°C; its mapping to CPU/Core Average remains UNKNOWN. The active plan was `Clawstack AC Maximum Performance`; System Cooling Policy indices were AC=1, DC=1 (active cooling policy). This confirms Windows policy configuration only, not maximum physical fan RPM/duty.

No BIOS, fan, threshold, power, job, task, checkpoint, or solver setting was changed. Core Average telemetry, fan feedback, ACPI mapping, and physical maximum fan operation remain unverified. The 92.25°C Tctl maximum is a single rolling-window observation and is not a trip-point/limit finding.
## 2026-11-01 03:31–03:45 JST — updated rolling thermal window

Health history now contains 15 LHM `Core (Tctl/Tdie)` samples from 03:31:04.886 to 03:45:05.062 JST: mean 86.65°C, min 83.25°C, max/latest 94.125°C. This is the Tctl channel and does not satisfy the requested `Core Average` signal, which remains unavailable. The latest separate ACPI channel was 95.05°C; mapping remains UNKNOWN, so do not combine it with Tctl. All-sample CPU mean was 31.18% across 12 logical processors, with the latest health sample 24.95% over 2.026 s. These are observations, not fan-control commands. The two existing Python batch jobs were running; no job/thermal setting changed. The 03:35 window already showed the last verified AC/DC active cooling policy; no physical fan speed is exposed. Evidence `artifacts/new-lavie/live-resource-cooling-snapshot-20261101T0337JST.md`.
## 2026-11-01 03:31–03:45 JST — rolling thermal window refresh (captured 03:46)

Fifteen LHM samples reported literal `Core (Tctl/Tdie)` mean 86.65 C, minimum 83.25 C, maximum/latest 94.125 C. `Core Average` was unavailable and no fan RPM/duty value was exposed. The separate ACPI channel read 95.05 C; its mapping is UNKNOWN and it is not combined with Tctl. Across the 15 samples CPU averaged 31.18% across all 12 logical processors; the latest sample was 24.95% over 2.026 s. These observations do not prove thermal throttling or physical fan speed. No cooling, power, BIOS, job or task setting changed. Evidence: `artifacts/new-lavie/live-resource-thermal-followup-20261101T0346JST.md`.
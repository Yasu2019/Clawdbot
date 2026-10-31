# Thermal telemetry follow-up — 2026-11-01 03:35 JST

Incident: `INC-LAVIE5500U-ACPI-THERMAL-ZONE-OBSERVATION-20261029-01`

The one-minute SYSTEM health history supplied 15 LHM CPU temperature samples from 03:21:04.804 to 03:35:04.914 JST. Only `Core (Tctl/Tdie)` was available: mean 87.81°C, minimum 75.125°C, maximum 92.25°C. `Core Average` was unavailable in all 15 samples; fan sensor status was `no_fan_value_exposed`. These are observation-only data; do not label Tctl average as Core Average or infer physical fan speed.

At 03:35:04.914 JST, a separate ACPI thermal-zone reading was 90.05°C; its mapping to CPU/Core Average remains UNKNOWN. The active plan was `Clawstack AC Maximum Performance`; System Cooling Policy indices were AC=1, DC=1 (active cooling policy). This confirms Windows policy configuration only, not maximum physical fan RPM/duty.

No BIOS, fan, threshold, power, job, task, checkpoint, or solver setting was changed. Core Average telemetry, fan feedback, ACPI mapping, and physical maximum fan operation remain unverified. The 92.25°C Tctl maximum is a single rolling-window observation and is not a trip-point/limit finding.
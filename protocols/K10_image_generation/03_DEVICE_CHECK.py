from __future__ import annotations

import json
import sys

try:
    import openvino as ov
except Exception as exc:
    print("FAILED: openvino import error")
    print(str(exc))
    sys.exit(1)

core = ov.Core()
devices = core.available_devices

info = {}
for dev in devices:
    try:
        info[dev] = core.get_property(dev, "FULL_DEVICE_NAME")
    except Exception:
        info[dev] = "UNKNOWN"

print("OpenVINO devices detected:")
print(json.dumps(info, indent=2))

preferred = "GPU" if "GPU" in devices else "CPU"
print("")
print(f"Preferred device: {preferred}")

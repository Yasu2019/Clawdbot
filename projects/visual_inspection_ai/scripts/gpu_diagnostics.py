import json
import platform
import sys

import _bootstrap
from inspection_ai.learning.resource_guard import current_resources


def main() -> None:
    result = {"python": sys.version, "platform": platform.platform(), "resources": current_resources().__dict__}
    try:
        import torch
        result["torch"] = torch.__version__
        result["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            result["gpu_name"] = torch.cuda.get_device_name(0)
            result["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
    except Exception as exc:
        result["torch_error"] = repr(exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

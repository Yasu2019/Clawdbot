# -*- coding: utf-8 -*-
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json
from mecha_studio.core.scanner import scan

print(json.dumps(scan([]), ensure_ascii=False, indent=2))

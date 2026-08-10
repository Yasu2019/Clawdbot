# -*- coding: utf-8 -*-
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mecha_studio.core.project import create_sample_project
print(create_sample_project())

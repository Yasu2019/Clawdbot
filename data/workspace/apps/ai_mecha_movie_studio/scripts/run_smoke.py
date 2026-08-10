# -*- coding: utf-8 -*-
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mecha_studio.core.paths import WORKSPACE
from mecha_studio.core.project import create_sample_project
from mecha_studio.core.pipeline import run_smoke

p = WORKSPACE / "sample_mecha_movie"
if not (p / "project.json").exists():
    p = create_sample_project()
print(run_smoke(p))

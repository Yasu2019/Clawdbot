import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_weldline_wrapper_requires_auditable_proxy_status(tmp_path):
    case = tmp_path / "case"
    (case / "constant").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "constant" / "C").write_text(
        "FoamFile { version 2.0; format ascii; class volVectorField; object C; }\n"
        "internalField nonuniform List<vector>\n2\n( (0 0 0) (1 0 0) )\n;\n"
        "boundaryField {}\n"
    )
    out = tmp_path / "weld.json"
    r = subprocess.run(
        [sys.executable, "scripts/derive_openfoam_weldline_kpis.py",
         "--case", str(case), "--output", str(out)],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    result = json.loads(out.read_text())
    assert result["formal_status"] == "PROXY_ONLY"
    assert result["visual_qc_required"] is True
    assert result["weldline_count"] == 0

# -*- coding: utf-8 -*-
"""Focused regressions for the Moldflow continuous-improvement P0 fixes."""

import json
import sys
import tempfile
import unittest
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cae_self_growth_gates as gates
import cae_te_engine as engine
import moldflow_step_case_builder as builder
import moldflow_continuous_improvement_supervisor as supervisor
import moldflow_injection_pressure_kpi as pressure_kpi
import moldflow_part_weight_kpi as weight_kpi


ALPHA_FIELD = """FoamFile { object alpha.polymer; }
internalField nonuniform List<scalar>
2
(
0.5
1
)
;
boundaryField
{
}
"""


class MoldflowCiRegressionTests(unittest.TestCase):
    def test_part_weight_uses_alpha_volume_and_polymer_density(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "1").mkdir()
            (run / "constant").mkdir()
            (run / "cad_manifest.json").write_text(
                json.dumps({"mesh_mode": "blockmesh_bbox", "bbox_mm": {"length": 100, "width": 60, "height": 2}}),
                encoding="utf-8",
            )
            (run / "1" / "alpha.polymer").write_text(
                "internalField nonuniform List<scalar> 2(1 0.5);", encoding="utf-8"
            )
            (run / "constant" / "thermophysicalProperties.polymer").write_text(
                "equationOfState { rho 1000; }", encoding="utf-8"
            )
            result = weight_kpi.extract(run, 9.0)
            self.assertEqual(9.0, result["part_weight_proxy_g"])
            self.assertEqual(0.0, result["absolute_error_pct"])

    def test_polymer_density_parameter_reaches_openfoam(self):
        template = "equationOfState { rho 1200; } transport { mu MU_CONST_PLACEHOLDER; }"
        out = engine._inject_parameters_openfoam(
            "constant/thermophysicalProperties.polymer",
            template,
            {"viscosity_model": "wlf", "T_melt": 513, "polymer_density_kg_m3": 765},
        )
        self.assertIn("rho 765;", out)

    def test_compressible_closed_cavity_starts_p_and_p_rgh_consistently(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "0").mkdir()
            for name, initial in (("p", 101325), ("p_rgh", 0)):
                (run / "0" / name).write_text(
                    f"internalField uniform {initial};\nboundaryField\n{{\noutlet\n{{\ntype calculated;\nvalue uniform {initial};\n}}\n}}",
                    encoding="utf-8",
                )
            (run / "0" / "U").write_text(
                "boundaryField\n{\noutlet\n{\ntype zeroGradient;\n}\n}", encoding="utf-8"
            )
            (run / "0" / "alpha.polymer").write_text(
                "boundaryField\n{\noutlet\n{\ntype zeroGradient;\n}\n}", encoding="utf-8"
            )
            builder.apply_compressible_closed_cavity_options(
                run, {"compressible_closed_cavity": True}
            )
            for name in ("p", "p_rgh"):
                field = (run / "0" / name).read_text(encoding="utf-8")
                self.assertIn("internalField   uniform 101325;", field)
                self.assertNotIn("value           uniform 0;", field)

    def test_cross_wlf_parameters_reach_openfoam_polymer_viscosity(self):
        template = "transport { mu MU_CONST_PLACEHOLDER; }"
        default = engine._inject_parameters_openfoam(
            "constant/thermophysicalProperties.polymer",
            template,
            {"viscosity_model": "wlf", "T_melt": 513},
        )
        tuned = engine._inject_parameters_openfoam(
            "constant/thermophysicalProperties.polymer",
            template,
            {
                "viscosity_model": "wlf",
                "T_melt": 513,
                "cross_wlf_D1": 2.6e9,
            },
        )
        self.assertNotEqual(default, tuned)
        self.assertLess(float(re.search(r"mu\s+([0-9.]+)", tuned).group(1)),
                        float(re.search(r"mu\s+([0-9.]+)", default).group(1)))

    def test_gate_pressure_uses_enabled_gate_mean_and_gauge_reference(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "0").mkdir()
            (run / "0.1").mkdir()
            (run / "0" / "p").write_text(
                "internalField uniform 100000;\nboundaryField { inlet2 { value uniform 100000; } }",
                encoding="utf-8",
            )
            (run / "0.1" / "p").write_text(
                "boundaryField\n{\ninlet2\n{\nvalue nonuniform List<scalar> 2(1100000 1300000);\n}\n}",
                encoding="utf-8",
            )
            (run / "gate_spec.resolved.json").write_text(
                json.dumps({"gates": [{"patch": "inlet2", "enabled": True}]}),
                encoding="utf-8",
            )
            result = pressure_kpi.extract(run, 1.0)
            self.assertEqual(1.1, result["maximum_injection_pressure_proxy_mpa"])
            self.assertEqual(10.0, result["absolute_error_pct"])

    def test_supervisor_rejects_uncalibrated_pressure(self):
        cfg = {
            "hard_gates": {
                "alpha_polymer_max": 1.05,
                "fill_fraction_min_pct": 99.0,
            },
            "reference": {
                "max_injection_pressure_mpa": 10.8794,
                "part_weight_g": 9.0911,
            },
            "calibration_tolerances": {
                "max_injection_pressure_absolute_error_pct": 10.0
            },
        }
        trial = {
            "defects_detected": {
                "alpha_max": 1.0,
                "fill_fraction_pct": 99.05,
                "max_injection_pressure_proxy_mpa": 12.693725,
            }
        }
        self.assertEqual("injection_pressure_calibration", supervisor.decide(trial, cfg)["capability"])

    def test_openfoam_trap_message_is_not_fpe(self):
        tags = gates.tag_openfoam_log(
            "Floating point exception trapping enabled (FOAM_SIGFPE).\nEnd\n"
        )
        self.assertNotIn("foam_fpe", tags)
        self.assertIn(
            "foam_fpe",
            gates.tag_openfoam_log("Floating point exception (core dumped)\n"),
        )

    def test_precise_openfoam_time_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            time_dir = Path(temp) / "1.096174"
            time_dir.mkdir()
            (time_dir / "alpha.polymer").write_text(ALPHA_FIELD, encoding="utf-8")
            out = engine._extract_vof_fill_kpis(Path(temp))
        self.assertEqual(75.0, out["fill_fraction_pct"])
        self.assertEqual(1.096174, out["fill_time_s"])
        self.assertFalse(out["fill_complete"])
        self.assertEqual(1.0, out["alpha_max"])

    def test_corner_vent_moves_center_far_face_to_wall(self):
        full = builder.blockmesh_dict_text(100, 60, 2)
        corner = builder.blockmesh_dict_text(
            100, 60, 2, vent_layout="corner_far_edge"
        )
        full_outlet = full.split("outlet", 1)[1].split("walls", 1)[0]
        corner_outlet = corner.split("outlet", 1)[1].split("walls", 1)[0]
        corner_walls = corner.split("walls", 1)[1].split("frontAndBack", 1)[0]
        self.assertIn("(3 11 13 5)", full_outlet)
        self.assertNotIn("(3 11 13 5)", corner_outlet)
        self.assertIn("(3 11 13 5)", corner_walls)

    def test_independent_gate_and_corner_vent_mesh(self):
        text = builder.blockmesh_independent_vent_dict_text(
            100, 60, 2, nx=50, ny=30, gate_width_mm=4, vent_width_mm=2
        )
        blocks = re.findall(
            r"hex\s*\([^)]*\)\s*\(50\s+(\d+)\s+1\)", text
        )
        self.assertEqual(5, len(blocks))
        self.assertEqual(30, sum(int(value) for value in blocks))
        outlet = text.split("outlet", 1)[1].split("walls", 1)[0]
        self.assertEqual(2, outlet.count("(" ) - 1)
        self.assertIn("(0 2 0)", text)
        self.assertIn("(0 28 0)", text)
        self.assertIn("(0 32 0)", text)
        self.assertIn("(0 58 0)", text)

    def test_reproducibility_requires_three_hard_gate_passes(self):
        trials = []
        for index in range(3):
            trials.append(
                {
                    "id": f"candidate16_repeat{index}",
                    "verdict": "SUCCESS",
                    "defects_detected": {
                        "fill_fraction_pct": 99.05,
                        "fill_time_s": 0.97,
                        "max_injection_pressure_proxy_mpa": 11.0,
                        "part_weight_proxy_g": 9.0911,
                        "nonphysical": {"alpha_max": 1.0},
                    },
                }
            )
        cfg = {
            "promotion_trial_prefix": "candidate16_",
            "hard_gates": {
                "fill_fraction_min_pct": 99.0,
                "alpha_polymer_min": 0.0,
                "alpha_polymer_max": 1.05,
                "reproducibility_spread_max_pct": 5.0,
            },
            "promotion": {"minimum_repeated_passes": 3},
            "reference": {
                "max_injection_pressure_mpa": 10.8794,
                "part_weight_g": 9.0911,
            },
            "calibration_tolerances": {
                "max_injection_pressure_absolute_error_pct": 10.0,
                "part_weight_absolute_error_pct": 5.0,
            },
        }
        old_log = supervisor.CAE_LOG
        try:
            with tempfile.TemporaryDirectory() as temp:
                supervisor.CAE_LOG = Path(temp) / "cae_te_log.json"
                supervisor.CAE_LOG.write_text(
                    __import__("json").dumps({"trials": trials}), encoding="utf-8"
                )
                evidence = supervisor.reproducibility_evidence(cfg)
        finally:
            supervisor.CAE_LOG = old_log
        self.assertTrue(evidence["reproducible"])
        self.assertEqual(3, evidence["qualifying_passes"])
        self.assertEqual(0.0, evidence["fill_spread_percentage_points"])

if __name__ == "__main__":
    unittest.main()

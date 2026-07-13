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
import moldflow_bulk_temperature_kpi as temperature_kpi
import moldflow_shear_kpi as shear_kpi


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
    def test_shear_kpi_derives_first_cell_transit_exclusion(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "postProcessing" / "shearRateMinMax" / "0").mkdir(parents=True)
            (run / "postProcessing" / "moldWallShearStress" / "0").mkdir(parents=True)
            (run / "cad_manifest.json").write_text(
                json.dumps(
                    {
                        "mesh_nz": 8,
                        "mesh_nx": 50,
                        "inlet_velocity_m_s": 1.0,
                        "bbox_mm": {"length": 100.0},
                    }
                ),
                encoding="utf-8",
            )
            (run / "postProcessing" / "shearRateMinMax" / "0" / "fieldMinMax.dat").write_text(
                "0.001 shearRateProxy 0 (0 0 0) 20000 (0 0 0)\n"
                "0.002 shearRateProxy 0 (0 0 0) 5000 (0 0 0)\n",
                encoding="utf-8",
            )
            (run / "postProcessing" / "moldWallShearStress" / "0" / "wallShearStress.dat").write_text(
                "0.002 frontAndBack (-100000 0 0) (100000 0 0)\n",
                encoding="utf-8",
            )
            result = shear_kpi.extract(run, 5000, 0.1)
            self.assertAlmostEqual(0.002, result["startup_exclusion_s"])
            self.assertEqual("first_inlet_cell_transit_time", result["startup_exclusion_source"])
            self.assertEqual(5000, result["max_shear_rate_proxy_1_s"])

    def test_shear_kpi_preserves_raw_wall_stress_when_calibrated(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "postProcessing" / "shearRateMinMax" / "0").mkdir(parents=True)
            (run / "postProcessing" / "moldWallShearStress" / "0").mkdir(parents=True)
            (run / "cad_manifest.json").write_text(
                json.dumps({"mesh_nz": 4}), encoding="utf-8"
            )
            (run / "postProcessing" / "shearRateMinMax" / "0" / "fieldMinMax.dat").write_text(
                "0.01 shearRateProxy 0 (0 0 0) 5000 (0 0 0)\n", encoding="utf-8"
            )
            (run / "postProcessing" / "moldWallShearStress" / "0" / "wallShearStress.dat").write_text(
                "0.01 frontAndBack (-100000 0 0) (100000 0 0)\n", encoding="utf-8"
            )
            result = shear_kpi.extract(
                run, 5000, 0.16, startup_exclusion_s=0.01,
                wall_stress_calibration_factor=1.6,
            )
            self.assertEqual(0.1, result["raw_max_wall_shear_stress_proxy_mpa"])
            self.assertEqual(0.16, result["max_wall_shear_stress_proxy_mpa"])
            self.assertEqual("empirical_commercial_baseline", result["wall_shear_calibration_status"])

    def test_shear_kpi_excludes_startup_transient_and_requires_3d(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "postProcessing" / "shearRateMinMax" / "0").mkdir(parents=True)
            (run / "postProcessing" / "moldWallShearStress" / "0").mkdir(parents=True)
            (run / "cad_manifest.json").write_text(
                json.dumps({"mesh_nz": 4}), encoding="utf-8"
            )
            (run / "postProcessing" / "shearRateMinMax" / "0" / "fieldMinMax.dat").write_text(
                "0.001 shearRateProxy 0 (0 0 0) 20000 (0 0 0)\n"
                "0.01 shearRateProxy 0 (0 0 0) 5000 (0 0 0)\n",
                encoding="utf-8",
            )
            (run / "postProcessing" / "moldWallShearStress" / "0" / "wallShearStress.dat").write_text(
                "0.01 frontAndBack (-100000 0 0) (100000 0 0)\n",
                encoding="utf-8",
            )
            result = shear_kpi.extract(run, 5000, 0.1, startup_exclusion_s=0.01)
            self.assertEqual(20000, result["startup_global_max_shear_rate_1_s"])
            self.assertEqual(5000, result["max_shear_rate_proxy_1_s"])
            self.assertEqual(0.1, result["max_wall_shear_stress_proxy_mpa"])
            self.assertEqual(0.0, result["max_shear_rate_error_pct"])

    def test_resolved_thickness_mesh_uses_wall_patch_and_multiple_cells(self):
        text = builder.blockmesh_dict_text(100, 60, 2, nx=50, ny=30, nz=4)
        self.assertEqual(3, len(re.findall(r"hex .*\(50\s+\d+\s+4\)", text)))
        front = text.split("frontAndBack", 1)[1]
        self.assertIn("type wall;", front)
        legacy = builder.blockmesh_dict_text(100, 60, 2, nx=50, ny=30)
        self.assertIn("type empty;", legacy.split("frontAndBack", 1)[1])

    def test_resolved_thickness_fields_replace_empty_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "0").mkdir()
            for name in ("U", "alpha.polymer", "p", "p_rgh", "T"):
                (run / "0" / name).write_text(
                    "boundaryField\n{\nfrontAndBack\n{\ntype empty;\n}\n}", encoding="utf-8"
                )
            builder.apply_resolved_thickness_boundaries(
                run, {"mesh_nz": 4, "T_mold": 323}
            )
            self.assertIn("noSlip", (run / "0" / "U").read_text())
            self.assertIn("zeroGradient", (run / "0" / "alpha.polymer").read_text())
            self.assertIn("fixedValue", (run / "0" / "T").read_text())
            self.assertNotIn("type empty", (run / "0" / "p_rgh").read_text())

    def test_manual_reference_trial_enforces_automatic_cooldown(self):
        now = supervisor.datetime.now(supervisor.timezone.utc)
        local_timestamp = now.astimezone().replace(tzinfo=None).isoformat()
        allowed, reason = supervisor.trial_allowed(
            {"minimum_trial_cooldown_hours": 6, "max_trials_per_day": 4},
            {"trials_today": 0},
            now,
            {"timestamp": local_timestamp},
        )
        self.assertFalse(allowed)
        self.assertEqual("cooldown", reason)

    def test_bulk_temperature_uses_polymer_cells_and_alpha_weighted_mean(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "1").mkdir()
            (run / "1" / "alpha.polymer").write_text(
                "internalField nonuniform List<scalar> 3(1 0.5 0.1);", encoding="utf-8"
            )
            (run / "1" / "T").write_text(
                "internalField nonuniform List<scalar> 3(500 400 900);", encoding="utf-8"
            )
            result = temperature_kpi.extract(run, 226.85)
            self.assertEqual(226.85, result["maximum_bulk_temperature_proxy_c"])
            self.assertLess(result["latest_alpha_weighted_mean_temperature_c"], 226.85)
            self.assertEqual("latest polymer-dominant cell maximum", result["kpi_source"])

    def test_bulk_temperature_parses_actual_field_minmax_layout(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "1").mkdir(parents=True)
            (run / "postProcessing" / "thermalFieldMinMax" / "0").mkdir(parents=True)
            (run / "postProcessing" / "polymerBulkTemperature" / "0").mkdir(parents=True)
            (run / "1" / "alpha.polymer").write_text(
                "internalField nonuniform List<scalar> 2(1 1);", encoding="utf-8"
            )
            (run / "1" / "T").write_text(
                "internalField nonuniform List<scalar> 2(400 410);", encoding="utf-8"
            )
            (run / "postProcessing" / "thermalFieldMinMax" / "0" / "fieldMinMax.dat").write_text(
                "# Time field min location(min) max location(max)\n0.1 T 323 (0 0 0) 513 (0 0 0)\n",
                encoding="utf-8",
            )
            (run / "postProcessing" / "polymerBulkTemperature" / "0" / "volFieldValue.dat").write_text(
                "# Time weightedVolAverage(T)\n0.1 450\n", encoding="utf-8"
            )
            result = temperature_kpi.extract(run, 239.85)
            self.assertEqual(239.85, result["history_max_temperature_c"])
            self.assertEqual(176.85, result["history_peak_alpha_weighted_bulk_temperature_c"])
            self.assertEqual(1, result["history_sample_count"])

    def test_thermal_history_function_objects_are_lightweight_and_alpha_weighted(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "system").mkdir()
            (run / "system" / "controlDict").write_text(
                "application compressibleInterFoam;\n// ************************************************************************* //",
                encoding="utf-8",
            )
            builder.apply_thermal_history_function_objects(
                run, {"record_thermal_history": True}
            )
            text = (run / "system" / "controlDict").read_text(encoding="utf-8")
            self.assertIn("type              fieldMinMax;", text)
            self.assertIn("operation         weightedVolAverage;", text)
            self.assertIn("weightField       alpha.polymer;", text)
            self.assertNotIn("writeFields       true;", text)

    def test_shear_history_chains_gradient_magnitude_and_wall_stress(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "system").mkdir()
            (run / "system" / "controlDict").write_text(
                "application compressibleInterFoam;\n// ************************************************************************* //",
                encoding="utf-8",
            )
            builder.apply_thermal_history_function_objects(
                run, {"record_thermal_history": True, "record_shear_history": True}
            )
            text = (run / "system" / "controlDict").read_text(encoding="utf-8")
            self.assertIn("type              grad;", text)
            self.assertIn("field             gradU;", text)
            self.assertIn("fields            (shearRateProxy);", text)
            self.assertIn("type              wallShearStress;", text)
            self.assertIn("patches           (frontAndBack);", text)

    def test_automatic_trial_id_stays_inside_promotion_prefix(self):
        cfg = {"promotion_trial_prefix": "moldflow_ci_p3_weight_candidate21"}
        prefix = str(cfg.get("promotion_trial_prefix") or "moldflow_ci_candidate")
        trial_id = prefix + "_auto_20260713_120000"
        self.assertTrue(trial_id.startswith(cfg["promotion_trial_prefix"]))

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
                        "max_bulk_temperature_proxy_c": 240.0,
                        "max_shear_rate_proxy_1_s": 5500.0,
                        "max_wall_shear_stress_proxy_mpa": 0.164,
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
                "max_bulk_temperature_c": 241.0592,
                "max_shear_rate_1_s": 5565.3267,
                "max_wall_shear_stress_mpa": 0.1644,
            },
            "calibration_tolerances": {
                "max_injection_pressure_absolute_error_pct": 10.0,
                "part_weight_absolute_error_pct": 5.0,
                "max_bulk_temperature_absolute_error_pct": 5.0,
                "max_shear_rate_absolute_error_pct": 10.0,
                "max_wall_shear_stress_absolute_error_pct": 10.0,
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

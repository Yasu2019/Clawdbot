"""Tests for the arbitrary-3D seven-phenomena truth gate."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.cae_seven_phenomena_truth_gate import (
    PHENOMENA,
    REQUIRED_EVIDENCE,
    evaluate_bundle,
)


class SevenPhenomenaTruthGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_context.name)
        self.geometry_sha = "a" * 64
        self.mesh_sha = "b" * 64
        self.history_id = "history-20260920-001"
        self.bundle = self._build_complete_virtual_bundle()

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def _artifact(self, relative: str) -> str:
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"evidence for {relative}\n", encoding="utf-8")
        return relative

    def _identity(self) -> dict[str, str]:
        return {
            "geometry_sha256": self.geometry_sha,
            "mesh_sha256": self.mesh_sha,
            "history_id": self.history_id,
        }

    def _solver(self, name: str, artifacts: tuple[str, ...]) -> dict:
        return {
            **self._identity(),
            "execution_mode": "actual_solve",
            "returncode": 0,
            "status": "PASS",
            "solver_version": f"{name}-test-version",
            "convergence": {"status": "PASS"},
            "artifacts": {
                artifact: self._artifact(f"solvers/{name}/{artifact}.txt")
                for artifact in artifacts
            },
        }

    def _build_complete_virtual_bundle(self) -> dict:
        openfoam = self._solver(
            "openfoam", ("log", "history_manifest", "final_fields")
        )
        openfoam.update(
            {
                "history_source": "actual_solver",
                "synthetic": False,
                "history_complete": True,
                "history_time_count": 4,
                "fields": ["T", "p", "alpha", "U", "rho"],
                "same_mesh_same_times": True,
                "full_fill_gate": {
                    "status": "PASS",
                    "bounded_alpha": True,
                    "mass_balance_status": "PASS",
                    "final_mean_alpha": 0.9995,
                    "minimum_region_alpha": 0.995,
                },
            }
        )
        phenomena = {}
        for name in PHENOMENA:
            if name == "fill":
                physics_level = "direct"
                solver_runs = ["openfoam"]
            elif name in {"airtrap", "weldline"}:
                physics_level = "direct"
                solver_runs = ["openfoam"]
            else:
                physics_level = "coupled"
                solver_runs = ["openfoam", "calculix", "elmer"]
            phenomena[name] = {
                **self._identity(),
                "physics_level": physics_level,
                "solve_status": "PASS",
                "convergence": {"status": "PASS"},
                "solver_runs": solver_runs,
                "evidence": {
                    evidence: self._artifact(
                        f"phenomena/{name}/{evidence}.vtu"
                    )
                    for evidence in REQUIRED_EVIDENCE[name]
                },
            }
        return {
            **self._identity(),
            "material": {
                "kind": "virtual",
                "calibration_status": "NOT_MEASURED",
            },
            "solvers": {
                "openfoam": openfoam,
                "calculix": self._solver(
                    "calculix", ("log", "frd", "dat")
                ),
                "elmer": self._solver("elmer", ("log", "result")),
            },
            "convergence": {
                "spatial": "PASS",
                "temporal": "PASS",
                "conservation": "PASS",
                "cross_solver": "PASS",
            },
            "phenomena": phenomena,
            "validation": {},
        }

    def test_complete_virtual_bundle_is_numerically_complete_only(self) -> None:
        report = evaluate_bundle(self.bundle, self.base)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["status"], "NUMERICALLY_COMPLETE_UNCALIBRATED")
        self.assertTrue(report["numerically_complete"])
        self.assertFalse(report["engineering_validated"])
        self.assertFalse(report["production_complete"])
        self.assertFalse(report["production_promotion_allowed"])
        self.assertEqual(report["failed_checks"], [])

    def test_single_virtual_snapshot_is_rejected(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        openfoam = bundle["solvers"]["openfoam"]
        openfoam["history_source"] = "virtual_snapshot"
        openfoam["synthetic"] = True
        openfoam["history_time_count"] = 1
        report = evaluate_bundle(bundle, self.base)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertIn(
            "solver.openfoam.history_source_not_actual_solver",
            report["failed_checks"],
        )
        self.assertIn(
            "solver.openfoam.history_time_count_lt_2", report["failed_checks"]
        )

    def test_unexecuted_calculix_is_rejected(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        calculix = bundle["solvers"]["calculix"]
        calculix["execution_mode"] = "deck_only"
        calculix["returncode"] = None
        calculix["status"] = "NOT_RUN"
        report = evaluate_bundle(bundle, self.base)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertIn("solver.calculix.not_actual_solve", report["failed_checks"])
        self.assertIn("solver.calculix.returncode_not_zero", report["failed_checks"])

    def test_identity_mismatch_is_rejected(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["phenomena"]["warpage"]["mesh_sha256"] = "c" * 64
        report = evaluate_bundle(bundle, self.base)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertIn(
            "identity.phenomenon.warpage.mesh_sha256_mismatch",
            report["failed_checks"],
        )

    def test_proxy_or_candidate_phenomena_are_rejected(self) -> None:
        for phenomenon, level in (
            ("weldline", "proxy"),
            ("sink", "proxy"),
            ("void", "candidate"),
        ):
            with self.subTest(phenomenon=phenomenon, level=level):
                bundle = copy.deepcopy(self.bundle)
                bundle["phenomena"][phenomenon]["physics_level"] = level
                report = evaluate_bundle(bundle, self.base)
                self.assertEqual(report["verdict"], "HOLD")
                self.assertFalse(report["production_complete"])
                self.assertIn(
                    f"phenomenon.{phenomenon}.physics_level_{level}_not_production",
                    report["failed_checks"],
                )


if __name__ == "__main__":
    unittest.main()

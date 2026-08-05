# -*- coding: utf-8 -*-
import unittest

import cae_fidelity_mode as cfm


class CaeFidelityModeTests(unittest.TestCase):
    def test_list_modes(self):
        modes = {m["id"] for m in cfm.list_fidelity_modes()}
        self.assertEqual(modes, {"quick", "shell_proxy", "coarse_3d", "thermo_3d"})

    def test_alias_shell(self):
        out = cfm.apply_fidelity_mode({}, "shell")
        self.assertEqual(out["fidelity_mode"], "shell_proxy")
        self.assertEqual(out["mesh_mode"], "blockmesh_bbox")
        self.assertEqual(out["physics_category"], "resin_fill_vof")
        self.assertEqual(out["accuracy_band_label"], "PROXY_GAP")

    def test_explicit_keys_preserved_unless_force(self):
        base = {"fidelity_mode": "quick", "mesh_nx": 99, "mesh_mode": "gmsh_volume"}
        out = cfm.apply_fidelity_mode(base)
        self.assertEqual(out["mesh_nx"], 99)
        self.assertEqual(out["mesh_mode"], "gmsh_volume")
        forced = cfm.apply_fidelity_mode(base, force=True)
        self.assertEqual(forced["mesh_mode"], "blockmesh_bbox")
        self.assertNotEqual(forced["mesh_nx"], 99)

    def test_thermo_keeps_snappy_cool(self):
        out = cfm.apply_fidelity_mode({}, "thermo_3d")
        self.assertEqual(out["mesh_mode"], "snappyhexmesh")
        self.assertEqual(out["physics_category"], "resin_fill_cool")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            cfm.apply_fidelity_mode({}, "not-a-mode")


if __name__ == "__main__":
    unittest.main()

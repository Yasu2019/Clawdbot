# -*- coding: utf-8 -*-
"""Contract tests for the read-only Moldflow MCP readiness bridge."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import importlib.util
import sys as _sys
import types
import unittest
from pathlib import Path


SERVER = Path(__file__).with_name("moldflow_mcp_server.py")


def _load_server():
    class _Settings:
        host = ""
        port = 0

    class _FastMCP:
        def __init__(self, _name):
            self.settings = _Settings()
            self.tool_names = []

        def tool(self):
            def decorator(function):
                self.tool_names.append(function.__name__)
                return function
            return decorator

    fastmcp = types.ModuleType("mcp.server.fastmcp")
    fastmcp.FastMCP = _FastMCP
    class _TransportSecuritySettings:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    transport_security = types.ModuleType("mcp.server.transport_security")
    transport_security.TransportSecuritySettings = _TransportSecuritySettings
    server_package = types.ModuleType("mcp.server")
    mcp_package = types.ModuleType("mcp")
    _sys.modules.setdefault("mcp", mcp_package)
    _sys.modules.setdefault("mcp.server", server_package)
    _sys.modules.setdefault("mcp.server.fastmcp", fastmcp)
    _sys.modules.setdefault("mcp.server.transport_security", transport_security)
    spec = importlib.util.spec_from_file_location("moldflow_mcp_server", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MoldflowMcpContractTests(unittest.TestCase):
    def test_status_is_fail_closed(self):
        server = _load_server()
        status = server.collect_status()
        self.assertEqual(status["mode"], "operation_validation")
        self.assertFalse(status["analysis_enabled"])

    def test_invalid_bitness_is_rejected(self):
        server = _load_server()
        self.assertIn('"ok": false', server.moldflow_probe_com(16))

    def test_state_inspection_rejects_invalid_bitness(self):
        server = _load_server()
        self.assertIn('"ok": false', server.moldflow_inspect_state(16))

    def test_expected_tools_are_registered(self):
        server = _load_server()
        expected = {
            "moldflow_bridge_status",
            "moldflow_probe_com",
            "moldflow_inspect_state",
            "moldflow_inspect_active_study",
            "moldflow_open_study_by_name",
            "moldflow_save_as_active_study_copy",
            "moldflow_autofix_active_study_copy",
            "moldflow_mesh_active_study_copy",
            "moldflow_find_gate_candidate_active_study_copy",
            "moldflow_set_gate_active_study_copy",
            "moldflow_inspect_members",
            "moldflow_readiness_gate",
            "moldflow_create_study_checkpoint",
            "moldflow_import_cad_checkpoint",
            "moldflow_new_study",
            "moldflow_configure_study",
            "moldflow_start_analysis",
            "moldflow_analysis_status",
            "moldflow_export_results",
            "moldflow_export_fill_stages",
            "moldflow_fetch_file_base64",
            "moldflow_export_materials",
        }
        self.assertTrue(expected.issubset(set(server.mcp.tool_names)))

    def test_fill_stages_defaults_and_parser(self):
        server = _load_server()
        stages = server._default_fill_stages()
        self.assertEqual([s["key"] for s in stages], ["initial", "mid", "final"])
        self.assertAlmostEqual(stages[0]["fraction"], 0.10)
        self.assertAlmostEqual(stages[1]["fraction"], 0.50)
        self.assertAlmostEqual(stages[2]["fraction"], 1.00)
        parsed = server._parse_fill_stages_json(
            '[{"key":"initial","fraction":0.1,"label_ja":"初期"}]'
        )
        self.assertEqual(parsed[0]["key"], "initial")
        with self.assertRaises(ValueError):
            server._parse_fill_stages_json('[{"key":"bad!","fraction":0.1}]')

    def test_write_tools_are_fail_closed_by_default(self):
        server = _load_server()
        result = server.moldflow_new_study("blocked", "blocked", "missing.step")
        self.assertIn("write operations are disabled", result)

    def test_new_copy_tools_are_fail_closed_by_default(self):
        server = _load_server()
        self.assertIn(
            "write operations are disabled",
            server.moldflow_save_as_active_study_copy("source.sdy", "copy.sdy"),
        )
        self.assertIn("write operations are disabled", server.moldflow_mesh_active_study_copy("copy.sdy"))
        self.assertIn("write operations are disabled", server.moldflow_set_gate_active_study_copy("copy.sdy", 1))
        self.assertIn(
            "write operations are disabled",
            server.moldflow_create_study_checkpoint("scratch", "study"),
        )
        self.assertIn(
            "write operations are disabled",
            server.moldflow_import_cad_checkpoint("study.sdy", "missing.stl"),
        )

    def test_gate_candidate_rejects_invalid_study_name(self):
        server = _load_server()
        result = server.moldflow_find_gate_candidate_active_study_copy('bad"name')
        self.assertIn("expected_study_name is invalid", result)

    def test_vbs_runner_rejects_invalid_bitness(self):
        server = _load_server()
        result = server._run_vbs_code("WScript.Quit 0", bitness=16)
        self.assertEqual(result["error"], "bitness must be 32 or 64")

    def test_new_study_uses_moldflow_2010_importfile2_contract(self):
        source = SERVER.read_text(encoding="utf-8")
        self.assertIn("Synergy.ImportFile2", source)
        self.assertNotIn("StudyDoc.AddFile", source)

    def test_save_as_uses_proven_synergy_createobject_contract(self):
        source = SERVER.read_text(encoding="utf-8")
        self.assertIn('Set Synergy = CreateObject("synergy.Synergy")', source)

    def test_active_study_tools_do_not_use_unreliable_getobject(self):
        source = SERVER.read_text(encoding="utf-8")
        self.assertNotIn('GetObject(, "synergy.Synergy")', source)

    def test_running_mesh_inspection_skips_export_model(self):
        source = SERVER.read_text(encoding="utf-8")
        self.assertIn('GATE_INSPECTION_SKIPPED=mesh_in_progress', source)
        self.assertIn('If MeshStatusValue = "Running" Or MeshStatusValue = "Pending" Then', source)

    def test_checkpointed_mesh_saves_before_launch_and_accepts_running(self):
        source = SERVER.read_text(encoding="utf-8")
        tool_start = source.index("def moldflow_mesh_active_study_copy")
        pre_save = source.index('WScript.Echo "PRE_MESH_SAVE_OK="', tool_start)
        launch = source.index("StudyDoc.MeshNow False", pre_save)
        running = source.index('WScript.Echo "MESH_STARTED=true"', launch)
        empty = source.index('WScript.Echo "ERROR=EMPTY_MESH"', running)
        self.assertLess(pre_save, launch)
        self.assertLess(launch, running)
        self.assertLess(running, empty)

    def test_checkpoint_tools_require_identity_and_save(self):
        source = SERVER.read_text(encoding="utf-8")
        self.assertIn("CHECKPOINT=study_created_and_saved", source)
        self.assertIn("CHECKPOINT=cad_imported_and_saved", source)
        self.assertIn("ERROR=ACTIVE_STUDY_MISMATCH", source)

    def test_gate_setter_resolves_node_by_entity_id(self):
        source = SERVER.read_text(encoding="utf-8")
        start = source.index("def moldflow_set_gate_active_study_copy")
        end = source.index("def moldflow_inspect_members", start)
        tool_source = source[start:end]
        self.assertIn("StudyDoc.GetFirstNode()", tool_source)
        self.assertIn("StudyDoc.GetEntityID(Ent)", tool_source)
        self.assertNotIn("CreateEntityList", tool_source)


if __name__ == "__main__":
    unittest.main()

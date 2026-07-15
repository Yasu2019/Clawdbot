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
            "moldflow_inspect_members",
            "moldflow_readiness_gate",
            "moldflow_new_study",
            "moldflow_configure_study",
            "moldflow_start_analysis",
            "moldflow_analysis_status",
            "moldflow_export_results",
            "moldflow_export_materials",
        }
        self.assertTrue(expected.issubset(set(server.mcp.tool_names)))

    def test_write_tools_are_fail_closed_by_default(self):
        server = _load_server()
        result = server.moldflow_new_study("blocked", "blocked", "missing.step")
        self.assertIn("write operations are disabled", result)


if __name__ == "__main__":
    unittest.main()

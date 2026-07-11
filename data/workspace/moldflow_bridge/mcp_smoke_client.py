# -*- coding: utf-8 -*-
"""Bounded MCP initialize/list-tools smoke test for the Dynabook bridge."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def run(url: str) -> dict[str, object]:
    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            return {"ok": True, "tools": sorted(tool.name for tool in tools.tools)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    try:
        result = asyncio.run(asyncio.wait_for(run(args.url), timeout=max(1, min(args.timeout, 30))))
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

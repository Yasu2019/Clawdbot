# -*- coding: utf-8 -*-
"""Read relevant COM type-library member names embedded in synergy.exe."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path

import pythoncom


KEYWORDS = (
    "IMPORT",
    "ADD",
    "NEW",
    "OPEN",
    "STUDY",
    "PROJECT",
    "MESH",
    "MATERIAL",
    "ANALYSIS",
    "RUN",
    "SAVE",
)


def inspect_typelib(executable: Path) -> dict[str, object]:
    library = pythoncom.LoadTypeLibEx(str(executable))
    types: list[dict[str, object]] = []
    for type_index in range(library.GetTypeInfoCount()):
        type_info = library.GetTypeInfo(type_index)
        type_name = library.GetDocumentation(type_index)[0] or f"type_{type_index}"
        type_attr = type_info.GetTypeAttr()
        function_count = int(type_attr[6])
        members: list[dict[str, object]] = []
        for function_index in range(function_count):
            descriptor = type_info.GetFuncDesc(function_index)
            names = list(type_info.GetNames(descriptor[0]))
            if not names:
                continue
            member_name = str(names[0])
            searchable = f"{type_name}.{member_name}".upper()
            if not any(keyword in searchable for keyword in KEYWORDS):
                continue
            members.append(
                {
                    "name": member_name,
                    "parameters": [str(value) for value in names[1:]],
                    "memid": int(descriptor[0]),
                }
            )
        if members:
            types.append({"type": str(type_name), "members": members})
    return {
        "ok": True,
        "executable": str(executable),
        "type_count": library.GetTypeInfoCount(),
        "matching_types": types,
        "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exe",
        default=r"C:\Program Files\Autodesk\Moldflow Insight 2010\bin\synergy.exe",
    )
    args = parser.parse_args()
    executable = Path(args.exe)
    if not executable.is_file():
        print(json.dumps({"ok": False, "error": f"not found: {executable}"}))
        return 1
    try:
        result = inspect_typelib(executable)
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "read_only": True}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

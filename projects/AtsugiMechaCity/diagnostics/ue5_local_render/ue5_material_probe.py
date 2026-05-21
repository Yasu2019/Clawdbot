import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import unreal

OUT_DIR = Path(r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render")
REPORT = OUT_DIR / "ue5_material_probe_report.json"


def safe_call(label, func):
    try:
        value = func()
        return {"ok": True, "value": str(value), "type": str(type(value))}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "type": str(type(exc))}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tools = unreal.AssetToolsHelpers.get_asset_tools()

    result = {
        "material_editing_library": [n for n in dir(unreal.MaterialEditingLibrary) if "material" in n.lower() or "expression" in n.lower() or "connect" in n.lower()],
        "has_create_material_expression": hasattr(unreal.MaterialEditingLibrary, "create_material_expression"),
        "has_constant3": hasattr(unreal, "MaterialExpressionConstant3Vector"),
        "has_constant": hasattr(unreal, "MaterialExpressionConstant"),
        "material_property_members": [n for n in dir(unreal.MaterialProperty) if "BASE" in n or "ROUGH" in n or "EMISSIVE" in n or "METALLIC" in n],
        "tests": {},
    }

    unreal.EditorAssetLibrary.make_directory("/Game/CodexGenerated")
    result["tests"]["create_game_material"] = safe_call(
        "create_game_material",
        lambda: tools.create_asset("CodexProbeMat", "/Game/CodexGenerated", unreal.Material, unreal.MaterialFactoryNew()),
    )
    mat = tools.create_asset("CodexProbeMat2", "/Game/CodexGenerated", unreal.Material, unreal.MaterialFactoryNew())
    result["mat_is_none"] = mat is None
    if mat is not None:
        result["material_dir_sample"] = [n for n in dir(mat) if "color" in n.lower() or "rough" in n.lower() or "expression" in n.lower() or "material" in n.lower()][:100]
        result["tests"]["create_base_expr_positional"] = safe_call(
            "create_base_expr_positional",
            lambda: unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0),
        )
        result["tests"]["create_base_expr_keyword"] = safe_call(
            "create_base_expr_keyword",
            lambda: unreal.MaterialEditingLibrary.create_material_expression(
                material=mat,
                expression_class=unreal.MaterialExpressionConstant3Vector,
                node_pos_x=-400,
                node_pos_y=0,
            ),
        )
        result["tests"]["create_base_expr_new"] = safe_call(
            "create_base_expr_new",
            lambda: unreal.new_object(unreal.MaterialExpressionConstant3Vector, mat),
        )

    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


main()

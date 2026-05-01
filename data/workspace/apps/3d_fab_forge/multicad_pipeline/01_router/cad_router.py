from dataclasses import dataclass
from typing import List

@dataclass
class CadRecommendation:
    primary: str
    secondary: str
    reason: str
    caution: str

RULES = {
    "busbar": CadRecommendation(
        "CadQuery or build123d", "FreeCAD",
        "板物・穴・R・押し出しが中心で、パラメトリック生成に向く",
        "複雑な曲げ履歴やGD&T判断は人間確認が必要"
    ),
    "inspection_jig": CadRecommendation(
        "CadQuery", "OpenSCAD",
        "治具・スペーサー・ブラケットは寸法変数化しやすい",
        "ねじ・逃げ・嵌合は実測補正を必ず入れる"
    ),
    "dxf_extrude": CadRecommendation(
        "FreeCAD", "SolveSpace",
        "DXF読み込みとGUI確認はFreeCADが便利",
        "DXFの線分閉合・重複線・スケール崩れに注意"
    ),
    "organic_surface": CadRecommendation(
        "Blender", "FreeCAD",
        "有機曲面やキャラクタ形状はCADよりDCCが向く",
        "寸法精度が必要な機械部品には不向き"
    ),
    "mold_base": CadRecommendation(
        "FreeCAD", "CadQuery",
        "金型ベースやプレート構成はFreeCADで確認しやすい",
        "順送金型全体の完全自動化は危険。段階分割する"
    ),
}

def recommend(shape_type: str) -> CadRecommendation:
    key = shape_type.strip().lower()
    return RULES.get(key, CadRecommendation(
        "CadQuery", "FreeCAD",
        "未知形状はまず安全なパラメトリック部品として生成し、FreeCADで確認する",
        "OpenCodeGOに失敗ログを読ませて選定ルールを更新する"
    ))

if __name__ == "__main__":
    for t in ["busbar", "inspection_jig", "dxf_extrude", "organic_surface", "mold_base", "unknown"]:
        r = recommend(t)
        print(f"[{t}] primary={r.primary} / secondary={r.secondary}")
        print(f"  reason : {r.reason}")
        print(f"  caution: {r.caution}\n")

# OpenCodeGO × Multi-CAD Pipeline 本気版

目的: FreeCAD単体で失敗しやすいCAD自動生成を、CadQuery / build123d / OpenSCAD / SolveSpace / FreeCADで分担し、OpenCodeGOに選定・実行・失敗分析をさせるための現場投入スターターです。

## 基本思想
- FreeCADは母艦・確認・STEP/DXF処理用
- CadQuery/build123dはパラメトリック3D自動生成用
- OpenSCADは単純治具・ブラケット・3Dプリント形状用
- SolveSpaceは2D拘束や簡易機構確認用
- OpenCodeGO/Codexは、CAD選定・コード修正・失敗ログの知識化を担当

## まず行うこと
1. `00_install/INSTALL_WINDOWS_K10.md` を読む
2. `01_router/cad_router.py` を実行して形状タイプ別の推奨CADを確認
3. `02_examples/` のコードを1つずつ実行
4. `04_prompts/opencodego_master_prompt.md` をOpenCodeGOに渡す
5. 失敗したら `03_logs/failure_log_template.md` に記録して、次回選定ルールに反映

## 重要な安全ルール
- 既存STEPやDXFを上書きしない
- 出力先は必ず `outputs/日時_案件名/` に分離
- FreeCADマクロは最初にコピー品で試す
- Codex/OpenCodeGOには「削除・上書き禁止」を明示

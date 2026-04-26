# Codex 実装依頼文（初回）
あなたは、Dockerコンテナ内に導入済みの FreeCAD を使って、
2D DXF から編集可能な FCStd を自動生成する実装担当です。

最終目的は、メッシュ変換ではなく、
FreeCAD の PartDesign ベースの生成ツリーを持つ FCStd を作ることです。

必須条件:
- 出力は FCStd
- 生成ツリーは Body + Sketch + Pad + Hole + Pocket を基本にする
- ザグリは原則 PartDesign Hole を使う
- 不要なテーパを絶対に入れない
- Loft/Sweep/メッシュ近似は禁止
- 寸法が曖昧な箇所は勝手に確定せず、report に保留として出す
- ユーザーが後から FreeCAD GUI で修正、削除、追加工できる構成にする

入力前提:
- ユーザーが DXF から不要な外枠、表題欄、不要寸法線を削除済み
- 第三角法の正面図/側面図/平面図がある
- ザグリなど必要寸法線は残っている場合がある

実装してほしいもの:
1. DXF解析モジュール
2. ビュー検出または config で bbox 指定
3. 閉ループ抽出
4. feature inference
5. FreeCAD builder
6. FCStd出力
7. STEP/STL/PNG出力
8. report.md/report.json 出力
9. 不要テーパ検出
10. README

推奨構成:
- dxf_parser.py
- dxf_cleaner.py
- view_detector.py
- loop_detector.py
- annotation_parser.py
- feature_inference.py
- freecad_builder.py
- validators.py
- reporters.py
- main.py
- macros/build_from_dxf.FCMacro

実装ルール:
- ベース形状は Sketch_BaseProfile + Pad_Base
- 穴は Hole_Through_xx または Hole_CBore_xx
- 開口は Pocket_xx
- 無意味な Sketch001 などの名前は避ける
- 失敗時ログを残す
- 中途成果物も保存する
- 初版は semi-auto config 前提でよい
- 完全自動よりも、安定・編集可能・不要テーパ無しを優先する

まず最初に、
(1) コンテナ内 FreeCAD 実行方法確認
(2) Python import 可否確認
(3) ezdxf 利用可否確認
(4) サンプルDXFで最小PoC作成
の順で進めてください。

その後、
- 実装計画
- ディレクトリ構成
- 主要ファイル
- 実行コマンド
- 初回PoC結果
を示し、
次に本実装へ進んでください。

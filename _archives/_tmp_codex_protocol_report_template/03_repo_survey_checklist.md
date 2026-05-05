# Repo Survey Checklist

## 1. 調査の目的
- 似たようなアプリが既に存在するかを確認する
- 一部融合で済むかを判断する
- 全部取り込みが妥当かを判断する
- 既存採用優先が妥当かを判断する
- 今回は保留にすべきかを判断する
- 新規実装の必要性を確認する

## 2. 優先検索キーワード
- kinematics
- hub
- die
- mold
- press
- stamping
- progressive
- stage
- sequence
- animation
- cad
- freecad
- dxf
- stl
- step
- portal
- app
- viewer
- transform
- geometry
- process
- openradioss
- openfoam
- solver

## 3. 優先確認場所
- apps/
- portal/
- dashboard/
- ui/
- scripts/
- tools/
- docs/
- archived/
- experiments/
- legacy/
- compose/
- docker/

## 4. 候補ごとの確認項目
- 名前
- パス
- 何をするものか
- 今回の目的に近いか
- そのまま使えるか
- 一部使えるか
- 放置されていないか
- 依存関係は重いか
- UI導線はあるか
- 既存ユーザーに影響するか
- 置換すると危険か
- ラップや拡張で対応可能か
- solver 連携余地があるか

## 5. 分類
各候補に、次のどれかを付けること。
- reuse
- integrate
- import_and_adapt
- hold
- reject
- new_build

## 6. 必須出力
- 類似アプリ一覧表
- 推奨方針
- 推奨理由
- 触るべきコード
- 今回は触らないコード
- 想定リスク
- 競合一覧

# 05. CAE / FEM 成功失敗経験の蓄積仕様

## 5.1 目的
OpenFOAM / OpenRadioss / Impact 等で、成功条件だけでなく**失敗条件**を蓄積し、
次回の設定判断や原因切り分けに活かす。

## 5.2 追加コレクション
- `cae_run_memory`
- `cae_failure_memory`
- `cae_success_pattern_memory`
- `cae_lesson_memory`

## 5.3 1レコードの考え方
1 run = 1記録
- solver
- バージョン
- 入力条件
- 境界条件
- 接触条件
- 材料モデル
- mesh条件
- 収束結果
- 実行時間
- エラーログ
- 人の所感

## 5.4 cae_run_memory 推奨項目
- run_id
- source_org
- tool_name (`OpenFOAM`, `OpenRadioss`, `Impact`)
- tool_version
- simulation_type
- project_name
- material
- geometry_type
- mesh_size
- element_type
- contact_type
- friction
- time_step
- solver_settings
- boundary_conditions
- initial_conditions
- result_status (`success`, `failed`, `partial`)
- failure_mode
- error_signature
- wall_clock_time
- output_files
- summary
- lesson

## 5.5 失敗経験で特に残すべきもの
- 収束しない
- 接触貫通
- メッシュ破綻
- 時間刻み不適切
- 材料モデル不整合
- ログの代表エラー文
- どの変更で改善したか

## 5.6 成功パターンで残すべきもの
- どの条件で収束したか
- どうメッシュを調整したか
- 接触条件の安全域
- solver選択理由
- 計算時間と精度の妥協点

## 5.7 CAE比較機能
`POST /compare/cae-run`
入力:
- 現在のrun条件
- error_signature
- tool_name

出力:
- 類似失敗run
- 過去に効いた修正
- 推奨修正順序
- 再発可能性
- 注意点

## 5.8 横断一般化例
- `接触開始直後に材料が飛ぶ場合、初期クリアランスと接触剛性の同時見直しが有効`
- `細かすぎるメッシュ単独ではなく、接触設定・増分設定とセットで調整すべき`
- `陽解法に逃げる前に境界条件固定の過不足を確認`

## 5.9 取込元
- 手動入力JSON
- solver log
- run summary markdown
- 既存 scripts の出力
- OpenClaw / Antigravity が生成した作業ログ

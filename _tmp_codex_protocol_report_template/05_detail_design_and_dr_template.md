# Detailed Design and DR Template

## 1. 対象機能名

## 2. 背景と目的

## 3. 今回の採用判断
- Reuse / Integrate / Import and Adapt / Hold / New Build
- 判断理由

## 4. スコープ
### In Scope
### Out of Scope

## 5. ユーザーフロー
1.
2.
3.

## 6. 入力
- 入力ファイル形式
- 単位
- 原点
- スケール
- 入力バリデーション

## 7. 出力
- 可視化データ
- 中間データ
- ログ
- エラー
- ユーザー向け説明

## 8. 処理フロー
- 読込
- ステージ推定
- 可視化変換
- kinematics_hub 連携
- Portal 導線
- 将来 solver 連携
- 結果表示

## 9. データ構造
- stage
- operation
- geometry_ref
- annotation
- camera_hint
- display_flag
- solver_bridge_hint

## 10. UI仕様
- 起動導線
- ボタン
- ステージ切替
- 再生 / 停止
- 注釈表示
- エラー表示

## 11. エラー処理
- 非対応形式
- 形状不足
- 変換失敗
- 可視化失敗
- 既存ルート競合

## 12. 既存システム影響
- 影響箇所
- 非影響箇所
- ロールバック方法

## 13. テスト項目
- 正常系
- 異常系
- 文字化け
- UI崩れ
- データ欠落
- 既存影響

## 14. DR 確認項目
- 要件一致
- 既存資産との整合
- ユーザー価値
- 分かりやすさ
- 拡張性
- 実装コスト
- リスク
- Portal 統合妥当性
- OpenRadioss / OpenFOAM 連携余地

## 15. DR 結果
- Go / No-Go / Hold
- 保留事項
- 宿題

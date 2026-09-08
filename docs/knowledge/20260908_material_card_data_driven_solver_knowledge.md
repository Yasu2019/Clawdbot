# 材料実測値で再校正できる樹脂CAE計算系

## 決定

仮想PP値でのスクリーニング計算と、実測材料値による設計判断用計算を明確に分離する。実測値を入力したとき、材料カードからOpenFOAM辞書を生成し、同じ計算ケースへ明示的にインストールできる経路を正とする。

## 実装の正本

- 入力契約: `config/material_card_schema.json`
- 仮想カード（校正不可）: `config/virtual_material_pp_screening.json`
- 変換・検証: `scripts/prepare_material_card.py`
- 手順: `docs/operations/material_card_calibration_workflow.md`
- 自動テスト: `tests/test_material_card_preflight.py`
- 生成辞書: `constant/generalizedPolymerThermo`

## データ状態ゲート

`VIRTUAL_SCREENING_ONLY` は数値安定性・傾向確認だけ、`MEASURED_UNCALIBRATED` は実測値入力済みだが比較校正前、`CALIBRATED`/`VALIDATED` は校正・ホールドアウト検証後とする。仮想カードのゲートは意図的に閉じる。

## 連成の意味

Cross-WLF係数は粘度・運動量方程式へ、Tait 2-domain係数は密度・圧力方程式へ、熱物性値は熱方程式へ渡る。したがって、正しい温度・せん断速度・圧力範囲の実験値へ置換すれば、入力値がソルバーの物理連成へ直接反映される。測定範囲外の外挿や測定誤差がある場合は精度を保証せず、誤差評価を残す。

## 検証結果

2026-09-08、仮想カードのpreflightとケースインストールを含む3テストが合格。コミット `a1f9f69ead` をGitHubへpush済み。既存の仮想熱計算・メッシュ・アニメーション成果物は基準ケースとして保持する。

## 運用上の注意

材料カードを変更しただけでは計算結果は変わらない。必ず `prepare_material_card.py --case ...` を実行し、生成manifestの `material_id`、`data_status`、`installed_dictionary` を計算記録へ残す。秘密情報・トークンは永続メモリへ保存しない。

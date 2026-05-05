# AI IE CostDown Complete Kit v4 - Spaghetti Analysis 対応版

## 目的

このZIPは、既存ミニPC側のMOST・サーブリッグ法コードを置換せず、
未対応だった「スパゲッティ図分析コード」を追加するための差分パッケージです。

方針は **MERGE_ADAPTER_ONLY** です。

- 既存MOSTコード：置換しない
- 既存サーブリッグ法コード：置換しない
- 既存OpenClaw/Clawstack/Portal：上書きしない
- スパゲッティ図分析：新規追加。ただし既存実装が検出された場合は保留
- OpenCodeGO：解析結果レビュー、改善案生成、分類辞書更新に使う
- 定期収集ルール：既存スケジューラへジョブ追加のみ

## 追加した主な機能

1. X/Y時系列CSVからスパゲッティ図を生成
2. ゾーン滞在時間を集計
3. 歩行距離、移動速度、往復回数を計算
4. A-B-A往復、長距離移動、滞在偏り、ムダ動線候補を検出
5. 改善前後比較レポートを生成
6. OpenCodeGOへ投げるレビュー用プロンプトを生成
7. Streamlit GUIでCSVをアップロードして可視化
8. Portalカード統合仕様を追加
9. 既存システム棚卸し・融合/保留判定ゲートを追加

## 使い方

### 1. サンプル実行

```bash
cd ai_ie_costdown_complete_kit_v4_spaghetti
python spaghetti/core/spaghetti_analyzer.py \
  --input spaghetti/samples/sample_trace_before.csv \
  --layout spaghetti/config/sample_layout.json \
  --output spaghetti/reports/before_report
```

### 2. 改善前後比較

```bash
python spaghetti/core/compare_before_after.py \
  --before spaghetti/samples/sample_trace_before.csv \
  --after spaghetti/samples/sample_trace_after.csv \
  --layout spaghetti/config/sample_layout.json \
  --output spaghetti/reports/compare_report
```

### 3. GUI起動

```bash
pip install streamlit pandas matplotlib numpy
streamlit run spaghetti/gui/spaghetti_gui.py
```

## 入力CSVフォーマット

最小形式：

```csv
timestamp,tag_id,x,y
2026-05-01 09:00:00.000,worker_anon_01,1.2,2.3
```

推奨形式：

```csv
timestamp,tag_id,x,y,z,quality,source
2026-05-01 09:00:00.000,worker_anon_01,1.2,2.3,1.1,0.91,uwb
```

## 注意

- 作業者監視目的で使わないこと
- 個人名ではなく匿名IDを使うこと
- 動画・位置情報の保存期間、閲覧権限を決めること
- UWB/BLE/カメラの測位誤差を前提に、改善前後比較の傾向分析として使うこと

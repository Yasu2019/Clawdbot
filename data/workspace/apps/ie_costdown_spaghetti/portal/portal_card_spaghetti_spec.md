# Portalカード仕様：AI IE Spaghetti Analyzer

## カード名

AI IE 動線・スパゲッティ図分析

## 目的

UWB / BLE / カメラ / 手入力CSVから得たX/Y時系列データを使い、
歩行ムダ、滞在時間、往復回数、改善前後差を見える化する。

## 入力

- trace CSV
- layout JSON
- before CSV
- after CSV
- タグ匿名化ルール
- ゾーン定義

## 出力

- スパゲッティ図PNG
- 滞在ヒートマップPNG
- tag_summary.csv
- zone_dwell_summary.csv
- transition_summary.csv
- waste_patterns.csv
- before_after_comparison.csv
- Markdownレポート

## UI

1. CSVアップロード
2. レイアウトJSONアップロード
3. 解析実行
4. 図表示
5. CSV/Markdownダウンロード
6. OpenCodeGOレビューキューへ送る

## 安全表示

このカードは個人監視・人事評価用ではありません。
工程改善、歩行ムダ削減、作業負荷低減、レイアウト改善のための匿名分析用です。

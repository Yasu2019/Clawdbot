# Fable5・他モデルへの引継ぎ

## Fable5の役割

Fable5は常時コーディングではなく、以下のGate監査に使用します。

- Gate 1 要求定義
- Gate 2 基本設計
- Gate 3 1製品PoC
- Gate 4 REVIEW・継続学習
- Gate 5 100 ms性能評価
- Gate 6 現場試験前
- Gate 7 本番候補

## 監査パケット

Fable5へ全リポジトリを毎回読ませず、次だけを渡します。

- 変更目的
- 変更ファイル一覧
- 主要差分
- 自動テスト結果
- 精度・速度比較
- 失敗例画像
- 未解決リスク
- 判断してほしい事項
- ロールバック方法

`scripts/build_audit_packet.py` がMarkdown形式のパケットを生成します。

# ロールバック手順

## 前提
arscontexta は markdown ベースなので、破壊的 DB migration 型ではない可能性が高いが、
hooks / templates / generated folders による運用影響はあり得る。

## 巻き戻し条件
- ノイズノートが多すぎる
- MOC が読みにくい
- Claude Code 利用量が重すぎる
- 実務速度が改善しない
- 既存運用と競合する

## 手順
1. sandbox Vault なら丸ごと破棄
2. 本番導入済みなら Git で revert
3. 生成された hooks / commands / folders を無効化
4. plugin を uninstall
5. 既存手動運用へ戻す
6. 失敗要因を記録

## 最低限の成功条件
- 検索しやすくなった
- 過去知見への再到達が速い
- AI へ渡す文脈説明が減った
これを満たさないなら本採用不要

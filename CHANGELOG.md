# CHANGELOG

すべてのAIエージェントは作業終了時に本ファイルへ追記すること（新しい日付を上へ）。
書式: `## YYYY-MM-DD` の下に `- [担当AI] 変更概要（関連bd ID / commit）`

## 2026-07-05

- [Fable5] **T049修正**: fem_impact@thinkpadサイレント即死の根本原因(`set -euo pipefail`下の`ls|wc -l`代入でexit2伝播)を特定・修正。QC実測値のKPI化・入力欠如の顕在化(exit7)・意味ゲート自動停止(全track, 連続8失敗でTelegram通知)・爆発デッキ無効化・practicalデッキ2本デプロイ。オーケストレータ再起動済(bd `e3dn`)
- [Fable5] 5アプリ進捗を4ソース(Beads/ByteRover/Obsidian/過去トラDB)横断照合し `HANDOVER_MASTER_INDEX.md` §7に反映。CETOL bd未追跡ギャップ解消(bd `iy63`)、fem_impact空回り前兆を検知しbd `e3dn`起票、Moldflow自動レポート停止(LAVIE要人間起動)を明記
- [Fable5] Fable5終了後継続開発プロトコルv2.0を恒久化（`docs/handover/FABLE5_CONTINUATION_PROTOCOL_V2.md`）。引き継ぎ資産マスターインデックス新設（`docs/handover/HANDOVER_MASTER_INDEX.md`）。ルートCHANGELOG運用開始（bd `azrr`）
- [Fable5] （既存・参考）API保全モード移行: walk_tier1c supervisor cycle3学習中、u7キューデーモン+受付API(8118)+自動起動 稼働（commit ad49c904b）

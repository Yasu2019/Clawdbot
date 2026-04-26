# DECISIONS.md - 採用判断履歴

## D-001: Game Studios思想の採用

- 判断: 採用
- 理由: 役割別エージェント、スラッシュコマンド、自動フック、ファイルベース記憶は OpenClaw の継続開発に有効。
- 注意: ゲーム開発向け名称・モデル固定指定は、そのまま採用しない。

## D-002: 49体エージェントの完全模倣

- 判断: 部分採用
- 理由: 49体をそのまま増やすと運用が重くなるため、OpenClawでは Tier1/Tier2/Tier3 の役割設計だけを採用する。

## D-003: act.md方式

- 判断: 採用
- 理由: セッション切れ・別AIツールへの引き継ぎに強い。
- OpenClaw名: ACT.md

## D-004: SQL操作

- 判断: 強制制限
- 内容: SQL Serverは読み取り専用を原則とし、INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATEは禁止。

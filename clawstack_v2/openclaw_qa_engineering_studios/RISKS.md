# RISKS.md - リスク一覧

| ID | リスク | 重要度 | 対策 |
|---|---|---:|---|
| R-001 | 既存Portalカードとの重複 | 高 | check_portal_duplicate.py を実行 |
| R-002 | Dockerポート衝突 | 高 | check_port_conflict.py を実行 |
| R-003 | SQL Server書き込み事故 | 最高 | check_sql_readonly.py と読み取り専用接続文字列 |
| R-004 | VBAの破壊的処理 | 高 | check_vba_destructive.py を実行 |
| R-005 | IATF条項の根拠不足 | 中 | check_iatf_evidence.py を実行 |
| R-006 | Bearer token / APIキー漏洩 | 最高 | check_secret_leak.py を実行 |
| R-007 | ACT.md未更新による作業迷子 | 中 | check_act_updated.py を実行 |

# 自己修復ハーネス+ゴールデン回帰 (2026-07-10)
- 発見: tri-track 7/8 05:51停止(58h) / 監視役2本(死活・成長監査)7/7から死亡(77h) — 監視役の死は自己申告できない再発
- self_heal_loops.py(毎時): tri-track再起動 / supervisor T054型2点セット / **監視役自身の蘇生**。安全: MAINTENANCE_LOCK・24h2回上限・全行動jsonl監査・dry-run
- audit G3強化: verify_log=trueで誤差ログ実績まで検証(resin_fill 25%)
- cetol_golden_regression.py(日次): 既知解3ケースをHub:8004で検証、偽PASSしない(API_OFFLINE明示)
- テスト: 8+3+5件PASS。dry-run実測で停止2件を正検知
- 詳細: docs/handover/SELF_HEAL_AND_GOLDEN_LOOPS_20260710.md

# 自己修復ハーネス+ゴールデン回帰 導入 (2026-07-10 ユーザー指示)

> 背景: 7/10監査で ①tri-track(Moldflow/OpenRadioss学習ループ)が7/8 05:51から停止 ②監視役(死活再チェック/成長監査)自身が7/7から死亡、を発見。「監視役の死は自己申告できない」の再発。

## 導入物

| 部品 | 役割 | 登録 |
|---|---|---|
| `scripts/self_heal_loops.py` | 毎時: tri-track stale>2h→watchdog再実行 / supervisor stale>4h+busy+学習プロセス不在→T054復旧2点セット / **監視役自身がstale>26h→直接実行で蘇生** | `register_self_heal_task.bat`(毎時+起動時) |
| `scripts/cetol_golden_regression.py` | 毎日07:40: 既知解公差スタック3ケースをHub(:8004)で検証、誤差推移をjsonl記録(商用接近のG3証拠) | `register_cetol_golden_task.bat` |
| growth_loop_audit.py **G3強化** | verify_log=trueのループは誤差ログの存在+直近誤差<=max_err_pctまで検証(resin_fill_cadに適用: 25%) | manifest済み |

## 安全設計(T054「ガーディアン自己破壊」対策)

- `data/workspace/MAINTENANCE_LOCK` 存在中は一切行動しない(DBメンテ時はこのファイルを置く)
- 同一対象への自動復旧は24hに2回まで→超過は escalate_human 記録のみ
- 全行動は `self_heal_log.jsonl` に監査可能な形で残る。--dry-runあり
- supervisor復旧は「学習プロセス不在」を確認してから(生きている長時間学習は触らない)

## テスト

self_heal決定ロジック8件 / audit G3 3件追加(計22件) / cetol解析解5件 — 全PASS
dry-run実測: tri-track 58.7h stale → restart検知 / dead_project_recheck 77.5h → 蘇生検知(正しい判断を確認済み)

## ユーザー作業(2ダブルクリック)

1. `scripts\register_self_heal_task.bat` — 登録+**即時1回実行**(tri-trackがその場で再起動される)
2. `scripts\register_cetol_golden_task.bat` — 登録+即時1回実行(Hub :8004起動中ならPASS/FAILが出る)

## 自己学習ループの現在地(商用接近の観点)

- **Moldflow**: 学習3点セット(G1物理ゲート/paramラーナー/ゴールデン)は7/7配布済み。ループ再開後、G3が誤差実績で毎日監査される。乱数→学習への転換はG4シフト(≥0.15)で機械判定
- **CETOL**: 真の「学習」はユーザー実測データ(L6)まで不可。まず本回帰で計算精度の証拠を毎日蓄積
- **メカRL**: 自走中(cycle2)。self_healがT054型デッドロックを自動処置
- **Visual Inspection**: 自動昇格なしは安全設計(意図的)。学習=REVIEW確定→Challenger作成→**人間昇格**の半自動ループ

## bd起票要(次のbd可能セッション)

self-heal導入 / tri-track 7/8停止の根本原因調査(T054関連疑い) / スケジュールタスク07:30/07:35が実行されていない原因確認(register_*.logを見る)
